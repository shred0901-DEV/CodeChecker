import os
import re
from typing import List, Dict, Any, Optional

try:
    import pefile
    HAS_PEFILE = True
except ImportError:
    HAS_PEFILE = False

# 危険なインポートAPI辞書 (API名: (Severity, CWE, タイトル, 詳細解説))
DANGEROUS_IMPORT_APIS: Dict[str, tuple] = {
    # メモリ破壊・バッファオーバーフロー系
    "strcpy": ("HIGH", "CWE-120", "古典的バッファオーバーフローの危険 (strcpy)", "バッファ境界チェックを行わないため、スタックオーバーフローや任意コード実行の標的になります。strcpy_s または strlcpy への置換を推奨します。"),
    "wcscpy": ("HIGH", "CWE-120", "古典的バッファオーバーフローの危険 (wcscpy)", "ワイド文字列の境界チェックを行いません。wcscpy_s を使用してください。"),
    "strcat": ("HIGH", "CWE-120", "バッファオーバーフローの危険 (strcat)", "境界チェックを行わず文字列を連結します。strcat_s を使用してください。"),
    "wcscat": ("HIGH", "CWE-120", "バッファオーバーフローの危険 (wcscat)", "wcscat_s を使用してください。"),
    "gets": ("HIGH", "CWE-120", "極めて危険な標準入力関数 (gets)", "バッファ長を指定できないため、入力によって確実にオーバーフローします。fgets や gets_s を使用してください。"),
    "_getws": ("HIGH", "CWE-120", "極めて危険な標準入力関数 (_getws)", "fgetws や _getws_s を使用してください。"),
    "sprintf": ("HIGH", "CWE-120", "書式文字列バッファオーバーフロー (sprintf)", "出力バッファ長の上限チェックがありません。snprintf または sprintf_s を使用してください。"),
    "wsprintfA": ("HIGH", "CWE-120", "書式文字列バッファオーバーフロー (wsprintfA)", "バッファ長上限（1024文字）の検証が不十分なAPIです。StringCbPrintfA 等を使用してください。"),
    "wsprintfW": ("HIGH", "CWE-120", "書式文字列バッファオーバーフロー (wsprintfW)", "StringCbPrintfW 等を使用してください。"),
    "vsprintf": ("HIGH", "CWE-120", "バッファオーバーフローの危険 (vsprintf)", "vsnprintf または vsprintf_s を使用してください。"),
    "scanf": ("MEDIUM", "CWE-120", "入力バッファオーバーフローの危険 (scanf)", "幅指定のないフォーマットでバッファオーバーフローが発生します。sscanf_s 等を使用してください。"),

    # コマンド実行・外部プロセス起動系
    "system": ("HIGH", "CWE-78", "シェルコマンド直接実行 (system)", "外部から操作可能な文字列が渡されるとOSコマンドインジェクションが発生します。CreateProcessW 等で引数を個別に渡してください。"),
    "_wsystem": ("HIGH", "CWE-78", "シェルコマンド直接実行 (_wsystem)", "OSコマンドインジェクションの危険があります。CreateProcessW を使用してください。"),
    "WinExec": ("HIGH", "CWE-78", "古いプロセス実行関数 (WinExec)", "引数のエスケープや未クォートパスの脆弱性を招きやすい古い16bit互換APIです。CreateProcessW を使用してください。"),
    "_popen": ("MEDIUM", "CWE-78", "パイプ付きコマンド実行 (_popen)", "シェルを介してコマンドを実行するため、インジェクションリスクがあります。"),
    "_wpopen": ("MEDIUM", "CWE-78", "パイプ付きコマンド実行 (_wpopen)", "シェルを介してコマンドを実行するため、インジェクションリスクがあります。"),

    # プロセス注入・ステルス・アンチデバッグ系
    "VirtualAllocEx": ("MEDIUM", "CWE-749", "他プロセスメモリ確保 (VirtualAllocEx)", "他プロセスの仮想メモリ空間を操作するAPIです。DLLインジェクションやコード改ざんに悪用されるリスクがあります。"),
    "WriteProcessMemory": ("MEDIUM", "CWE-749", "他プロセスメモリ書込み (WriteProcessMemory)", "他プロセスのメモリ書き換えに使用されます。不正な改ざんやインジェクションのリスクを検証してください。"),
    "CreateRemoteThread": ("HIGH", "CWE-749", "リモートスレッド生成 (CreateRemoteThread)", "他プロセス内でスレッドを実行するAPIです。マルウェアやチートツールで多用されるDLLインジェクションの代表的APIです。"),
    "SetWindowsHookExA": ("MEDIUM", "CWE-749", "グローバルフック設定 (SetWindowsHookExA)", "キーロガーやGUIイベント盗聴、全プロセスへのDLLインジェクションに悪用される可能性があります。"),
    "SetWindowsHookExW": ("MEDIUM", "CWE-749", "グローバルフック設定 (SetWindowsHookExW)", "キーロガーやGUIイベント盗聴、全プロセスへのDLLインジェクションに悪用される可能性があります。"),
    "IsDebuggerPresent": ("LOW", "CWE-489", "アンチデバッグ検知処理 (IsDebuggerPresent)", "デバッガの存在を検知して動作を変えるコードが含まれている可能性があります。"),
    "CheckRemoteDebuggerPresent": ("LOW", "CWE-489", "アンチデバッグ検知処理 (CheckRemoteDebuggerPresent)", "外部デバッガの検知処理が行われています。"),

    # ダウンロード・安全でない通信
    "URLDownloadToFileA": ("MEDIUM", "CWE-319", "簡易ファイルダウンロード (URLDownloadToFileA)", "平文HTTP経由でバイナリやファイルをダウンロードする場合、中間者攻撃 (MitM) や改ざんの危険があります。"),
    "URLDownloadToFileW": ("MEDIUM", "CWE-319", "簡易ファイルダウンロード (URLDownloadToFileW)", "平文HTTP経由でのダウンロード時に中間者攻撃の危険があります。")
}

# 埋め込みシークレット検出用正規表現パターン
EMBEDDED_PATTERNS = [
    {
        "id": "pe-secret-aws-key",
        "title": "バイナリ内に埋め込まれたAWSアクセスキー",
        "severity": "HIGH",
        "cwe": "CWE-798",
        "regex": re.compile(rb"\b(AKIA[0-9A-Z]{16})\b"),
        "description": "バイナリ内のデータ領域にAWSアクセスキーIDが直接埋め込まれています。リバースエンジニアリングによってクラウド認証情報が漏洩します。"
    },
    {
        "id": "pe-secret-private-key",
        "title": "バイナリ内に埋め込まれた秘密鍵",
        "severity": "HIGH",
        "cwe": "CWE-312",
        "regex": re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
        "description": "バイナリ内に暗号鍵（秘密鍵）が直接埋め込まれています。バイナリ配布により秘密鍵が第三者に抽出される危険があります。"
    },
    {
        "id": "pe-secret-generic-token",
        "title": "バイナリ内に埋め込まれたAPIトークン/シークレット",
        "severity": "HIGH",
        "cwe": "CWE-798",
        "regex": re.compile(rb"""(?:api_key|apikey|secret_key|app_secret|auth_token|access_token)[\s:=]{1,4}['"]?([a-zA-Z0-9_\-]{16,})['"]?""", re.IGNORECASE),
        "description": "APIキーや認証トークンと思われる機密文字列がバイナリ内に直接ハードコードされています。"
    },
    {
        "id": "pe-network-insecure-http",
        "title": "平文HTTP通信エンドポイントの埋め込み",
        "severity": "MEDIUM",
        "cwe": "CWE-319",
        "regex": re.compile(rb"""\b(http://(?:[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}|[a-zA-Z0-9_\-\.]+)(?::\d+)?(?:/[a-zA-Z0-9_\-\./\?=%&]*)?)\b""", re.IGNORECASE),
        "description": "暗号化されていない平文の HTTP URL がハードコードされています。通信内容の盗聴や改ざん（中間者攻撃）のリスクがあります。HTTPS への変更を推奨します。"
    },
    {
        "id": "pe-suspicious-encoded-ps",
        "title": "難読化されたPowerShellコマンドの埋め込み",
        "severity": "HIGH",
        "cwe": "CWE-95",
        "regex": re.compile(rb"""powershell(?:\.exe)?\s+-(?:enc|encodedcommand|e)\s+([A-Za-z0-9+/=]{20,})""", re.IGNORECASE),
        "description": "Base64エンコードで難読化されたPowerShell実行コマンドが埋め込まれています。悪意あるペイロード実行の痕跡である可能性があります。"
    }
]

class PEScanner:
    """Windows PEバイナリ (EXE/DLL) 包括的静的セキュリティスキャナ"""

    def __init__(self):
        self.available = HAS_PEFILE

    def is_pe_file(self, file_path: str) -> bool:
        """指定ファイルがPEバイナリ (EXE/DLL) かを判定"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".exe", ".dll", ".sys", ".ocx"]:
            return False

        try:
            with open(file_path, "rb") as f:
                header = f.read(2)
                return header == b"MZ"
        except Exception:
            return False

    def scan_file(self, file_path: str, base_dir: str) -> List[Dict[str, Any]]:
        """1つのPEファイルを包括的に解析し、脆弱性・リスクのリストを返す"""
        if not self.available or not self.is_pe_file(file_path):
            return []

        if os.path.isfile(base_dir) or file_path == base_dir:
            rel_path = os.path.basename(file_path)
        else:
            rel_path = os.path.relpath(file_path, base_dir).replace("\\", "/")
        findings = []

        try:
            # fast_load=False でImportやResourceも完全解析
            pe = pefile.PE(file_path, fast_load=False)
        except Exception as e:
            # 破損または解析不能ファイル
            return findings

        try:
            # 1. コンパイラ保護・エクスプロイト緩和策 (Exploit Mitigations)
            mitigation_findings = self._check_mitigations(pe, rel_path, file_path)
            findings.extend(mitigation_findings)

            # 2. 危険なインポートAPI検査 (Dangerous Imports)
            import_findings = self._check_dangerous_imports(pe, rel_path, file_path)
            findings.extend(import_findings)

            # 3. 埋め込みマニフェスト / UAC権限検査 (Privilege Escalation)
            manifest_findings = self._check_manifest(pe, rel_path, file_path)
            findings.extend(manifest_findings)

            # 4. 埋め込み文字列・シークレット検査 (Embedded Secrets / URLs)
            string_findings = self._check_embedded_strings(file_path, rel_path)
            findings.extend(string_findings)

        finally:
            try:
                pe.close()
            except Exception:
                pass

        return findings

    def _check_mitigations(self, pe: "pefile.PE", rel_path: str, full_path: str) -> List[Dict[str, Any]]:
        """エクスプロイト防御策 (ASLR, DEP, CFG, デジタル署名等) のチェック"""
        findings = []
        is_dll = bool(pe.FILE_HEADER.Characteristics & 0x2000)
        is_64bit = (pe.FILE_HEADER.Machine == 0x8664)

        opt_header = getattr(pe, "OPTIONAL_HEADER", None)
        if not opt_header:
            return findings

        dll_char = getattr(opt_header, "DllCharacteristics", 0)

        # 1. ASLR (Address Space Layout Randomization)
        has_aslr = bool(dll_char & 0x0040)  # IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE
        if not has_aslr:
            findings.append({
                "id": f"pe-mitigation-no-aslr-{rel_path}",
                "rule_id": "pe-mitigation-no-aslr",
                "title": "ASLR (アドレス空間配置ランダム化) が無効",
                "severity": "HIGH",
                "cwe": "CWE-119",
                "file": rel_path,
                "full_path": full_path,
                "line": 1,
                "end_line": 1,
                "code": f"OptionalHeader.DllCharacteristics = 0x{dll_char:04X} (DYNAMIC_BASE: False)",
                "description": "バイナリが実行時に固定メモリアドレスへロードされるため、バッファオーバーフロー等のメモリ破壊時にROP攻撃等のエクスプロイトが極めて容易になります。リンカーオプション `/DYNAMICBASE` を有効にして再ビルドしてください。",
                "source": "pe-binary"
            })

        # 2. DEP / NX (Data Execution Prevention)
        has_dep = bool(dll_char & 0x0100)  # IMAGE_DLLCHARACTERISTICS_NX_COMPAT
        if not has_dep:
            findings.append({
                "id": f"pe-mitigation-no-dep-{rel_path}",
                "rule_id": "pe-mitigation-no-dep",
                "title": "DEP/NX (データ実行防止機能) が無効",
                "severity": "HIGH",
                "cwe": "CWE-119",
                "file": rel_path,
                "full_path": full_path,
                "line": 1,
                "end_line": 1,
                "code": f"OptionalHeader.DllCharacteristics = 0x{dll_char:04X} (NX_COMPAT: False)",
                "description": "スタックやヒープ等のデータ領域に配置された不正コード（シェルコード）の実行をOSが防止できません。リンカーオプション `/NXCOMPAT` を有効にして再ビルドしてください。",
                "source": "pe-binary"
            })

        # 3. Control Flow Guard (CFG)
        has_cfg = bool(dll_char & 0x4000)  # IMAGE_DLLCHARACTERISTICS_GUARD_CF
        if not has_cfg:
            findings.append({
                "id": f"pe-mitigation-no-cfg-{rel_path}",
                "rule_id": "pe-mitigation-no-cfg",
                "title": "Control Flow Guard (CFG) が無効",
                "severity": "MEDIUM",
                "cwe": "CWE-691",
                "file": rel_path,
                "full_path": full_path,
                "line": 1,
                "end_line": 1,
                "code": f"OptionalHeader.DllCharacteristics = 0x{dll_char:04X} (GUARD_CF: False)",
                "description": "間接関数呼び出しの遷移先アドレス検証が無効です。攻撃者による関数ポインタ書き換え（ROP/JOP）を防ぐため、コンパイラオプション `/guard:cf` を有効にすることを推奨します。",
                "source": "pe-binary"
            })

        # 4. Authenticode デジタル署名
        has_signature = False
        try:
            sec_dir = opt_header.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]]
            if sec_dir.VirtualAddress > 0 and sec_dir.Size > 0:
                has_signature = True
        except Exception:
            has_signature = False

        if not has_signature:
            findings.append({
                "id": f"pe-mitigation-no-signature-{rel_path}",
                "rule_id": "pe-mitigation-no-signature",
                "title": "Authenticode デジタル署名が未付与",
                "severity": "LOW",
                "cwe": "CWE-347",
                "file": rel_path,
                "full_path": full_path,
                "line": 1,
                "end_line": 1,
                "code": "SecurityDirectory: VirtualAddress=0, Size=0 (No Authenticode Signature)",
                "description": "バイナリに改ざん検知・発行元証明のためのデジタル署名が付与されていません。正規のコードサイニング証明書（signtool）で署名することを推奨します。",
                "source": "pe-binary"
            })

        return findings

    def _check_dangerous_imports(self, pe: "pefile.PE", rel_path: str, full_path: str) -> List[Dict[str, Any]]:
        """危険なWindows API / C標準関数のインポートをチェック"""
        findings = []
        if not hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            return findings

        seen_apis = set()

        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode("utf-8", errors="ignore").lower()
            for imp in entry.imports:
                if not imp.name:
                    continue
                func_name = imp.name.decode("utf-8", errors="ignore")

                if func_name in DANGEROUS_IMPORT_APIS and func_name not in seen_apis:
                    seen_apis.add(func_name)
                    severity, cwe, title, desc = DANGEROUS_IMPORT_APIS[func_name]

                    findings.append({
                        "id": f"pe-api-{func_name}-{rel_path}",
                        "rule_id": f"pe-api-{func_name}",
                        "title": title,
                        "severity": severity,
                        "cwe": cwe,
                        "file": rel_path,
                        "full_path": full_path,
                        "line": 1,
                        "end_line": 1,
                        "code": f"Import: {dll_name}!{func_name}()",
                        "description": f"バイナリが安全でない可能性のある外部API `{func_name}` ({dll_name}) を呼び出しています。\n{desc}",
                        "source": "pe-binary"
                    })

        return findings

    def _check_manifest(self, pe: "pefile.PE", rel_path: str, full_path: str) -> List[Dict[str, Any]]:
        """マニフェスト (UAC 権限昇格設定) のチェック"""
        findings = []
        if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
            return findings

        manifest_xml = None
        try:
            for res_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                if res_type.id == 24:  # RT_MANIFEST
                    for entry in res_type.directory.entries:
                        for lang in entry.directory.entries:
                            data = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                            manifest_xml = data.decode("utf-8", errors="ignore")
                            break
        except Exception:
            pass

        if not manifest_xml:
            return findings

        # UAC requestedExecutionLevel チェック
        m_level = re.search(r"""requestedExecutionLevel\s+[^>]*level=["']([^"']+)["']""", manifest_xml, re.IGNORECASE)
        if m_level:
            level = m_level.group(1).lower()
            if level == "requireadministrator":
                findings.append({
                    "id": f"pe-uac-require-admin-{rel_path}",
                    "rule_id": "pe-uac-require-admin",
                    "title": "UAC管理者権限の常時要求 (requireAdministrator)",
                    "severity": "MEDIUM",
                    "cwe": "CWE-250",
                    "file": rel_path,
                    "full_path": full_path,
                    "line": 1,
                    "end_line": 1,
                    "code": f'<requestedExecutionLevel level="{m_level.group(1)}" uiAccess="false" />',
                    "description": "アプリケーション起動時に常に管理者権限への昇格を強制します。最小権限の原則（asInvoker）に従い、一般ユーザー権限で動作させるか、昇格が必要な操作のみを別プロセスに分離することを検討してください。",
                    "source": "pe-binary"
                })

        # autoElevate チェック
        if re.search(r"""<autoElevate[^>]*>true</autoElevate>""", manifest_xml, re.IGNORECASE):
            findings.append({
                "id": f"pe-uac-auto-elevate-{rel_path}",
                "rule_id": "pe-uac-auto-elevate",
                "title": "UAC Auto-Elevate 設定の存在",
                "severity": "HIGH",
                "cwe": "CWE-269",
                "file": rel_path,
                "full_path": full_path,
                "line": 1,
                "end_line": 1,
                "code": "<autoElevate>true</autoElevate>",
                "description": "ユーザープロンプトなしで管理者権限へ自動昇格する設定が含まれています。信頼されたWindowsシステムバイナリ以外では深刻な権限昇格脆弱性につながるリスクがあります。",
                "source": "pe-binary"
            })

        return findings

    def _check_embedded_strings(self, full_path: str, rel_path: str) -> List[Dict[str, Any]]:
        """バイナリ内の文字列からハードコードされた機密情報や不審な通信先を検出"""
        findings = []

        try:
            # 50MBを超える巨大バイナリの場合は先頭15MBのみチェックして負荷抑制
            with open(full_path, "rb") as f:
                raw_bytes = f.read(15 * 1024 * 1024)
        except Exception:
            return findings

        for pat in EMBEDDED_PATTERNS:
            matches = pat["regex"].findall(raw_bytes)
            if not matches:
                continue

            # ユニークなマッチを最大3件まで報告
            unique_matches = []
            for m in matches:
                val = m if isinstance(m, (bytes, bytearray)) else m[0]
                val_str = val.decode("utf-8", errors="ignore").strip()
                # 誤検知フィルタ（極端に短いものや一般的プレースホルダーを除外）
                if len(val_str) > 7 and not val_str.startswith("http://schemas.") and not val_str.startswith("http://www.w3.org"):
                    if val_str not in unique_matches:
                        unique_matches.append(val_str)
                if len(unique_matches) >= 3:
                    break

            for idx, match_val in enumerate(unique_matches, 1):
                findings.append({
                    "id": f"{pat['id']}-{rel_path}-{idx}",
                    "rule_id": pat["id"],
                    "title": pat["title"],
                    "severity": pat["severity"],
                    "cwe": pat["cwe"],
                    "file": rel_path,
                    "full_path": full_path,
                    "line": 1,
                    "end_line": 1,
                    "code": f"Embedded String: \"{match_val}\"",
                    "description": pat["description"],
                    "source": "pe-binary"
                })

        return findings

    def scan_files(self, file_paths: List[str], base_dir: str) -> List[Dict[str, Any]]:
        """複数ファイルを順次スキャン"""
        all_findings = []
        for path in file_paths:
            all_findings.extend(self.scan_file(path, base_dir))
        return all_findings

