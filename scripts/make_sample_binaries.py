import os
import sys
import struct
import pefile
from typing import Dict, Any

def create_sample_binaries():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_dir = os.path.join(base_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)

    src_exe = os.path.join(sys.prefix, "python.exe")
    src_dll = os.path.join(sys.prefix, "python3.dll")

    if not os.path.exists(src_dll):
        src_dll = os.path.join(sys.prefix, "vcruntime140.dll")

    # 1. sample_vulnerable.exe の作成
    out_exe_path = os.path.join(samples_dir, "sample_vulnerable.exe")
    build_vulnerable_pe(
        src_path=src_exe,
        out_path=out_exe_path,
        is_dll=False,
        target_name="sample_vulnerable.exe"
    )

    # 2. sample_vulnerable.dll の作成
    out_dll_path = os.path.join(samples_dir, "sample_vulnerable.dll")
    build_vulnerable_pe(
        src_path=src_dll,
        out_path=out_dll_path,
        is_dll=True,
        target_name="sample_vulnerable.dll"
    )

    print(f"Sample binaries successfully created in: {samples_dir}")

def build_vulnerable_pe(src_path: str, out_path: str, is_dll: bool, target_name: str):
    with open(src_path, "rb") as f:
        data = bytearray(f.read())

    pe = pefile.PE(data=data)
    is_64bit = (pe.FILE_HEADER.Machine == 0x8664)

    # 1. ASLR, DEP/NX, CFG を無効化 (DllCharacteristics を書き換え)
    opt_offset = pe.OPTIONAL_HEADER.get_file_offset()
    dll_char_offset = opt_offset + (70 if is_64bit else 46)

    # DYNAMIC_BASE(0x0040), NX_COMPAT(0x0100), GUARD_CF(0x4000) をクリア
    current_char = pe.OPTIONAL_HEADER.DllCharacteristics
    vulnerable_char = current_char & ~(0x0040 | 0x0100 | 0x4000)
    struct.pack_into("<H", data, dll_char_offset, vulnerable_char)

    # 2. デジタル署名ディレクトリエントリをクリア (未署名化)
    sec_dir_offset = opt_offset + (128 if is_64bit else 112)
    struct.pack_into("<II", data, sec_dir_offset, 0, 0)

    # 3. インポート関数名に危険なAPI (strcpy, system, VirtualAllocEx 等) を注入
    # 既存のインポート名文字列領域を探して危険な名前に置き換える
    target_apis = [b"strcpy\x00", b"system\x00", b"VirtualAllocEx\x00", b"CreateRemoteThread\x00"]
    api_idx = 0

    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            for imp in entry.imports:
                if imp.name and len(imp.name) > 8 and api_idx < len(target_apis):
                    name_offset = imp.name_offset
                    inj_api = target_apis[api_idx]
                    if name_offset and name_offset + len(inj_api) <= len(data):
                        data[name_offset:name_offset + len(inj_api)] = inj_api
                        api_idx += 1

    # 4. 埋め込みシークレット & 危険な通信URL & 難読化コマンドを注入
    # バイナリ末尾にダミーセクションまたはペイロードとして安全に埋め込み
    secret_payload = (
        b"\x00" * 32 +
        b"=== SECURITY TEST EMBEDDED ARTIFACTS ===\x00" +
        b"AKIAIOSFODNN7EXAMPLE\x00" +
        b"-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAz7R4x1234567890EXAMPLE==\n-----END RSA PRIVATE KEY-----\x00" +
        b"api_key = 'sk_live_9876543210abcdef9876543210'\x00" +
        b"http://insecure-backend-api.internal.local:8080/v1/debug\x00" +
        b"powershell.exe -enc VwByAGkAdABlAC0ASABvAHMAdAAgACIASABlAGwAbABvACIA\x00" +
        b"\x00" * 32
    )
    data.extend(secret_payload)

    with open(out_path, "wb") as f:
        f.write(data)

    print(f"Generated: {out_path} ({len(data)} bytes)")

if __name__ == "__main__":
    create_sample_binaries()

