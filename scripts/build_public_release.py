import os
import sys
import json
import shutil
import zipfile
import urllib.request
import subprocess
import re
import importlib.metadata as im

PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
PYTHON_ZIP_NAME = "python-3.10.11-embed-amd64.zip"

def get_required_top_level_entries(req_file: str) -> set:
    """requirements.txt に記載されたパッケージとその依存関係のみをホワイトリスト抽出"""
    base_pkgs = []
    with open(req_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                m = re.match(r"^([a-zA-Z0-9_\-]+)", line)
                if m:
                    base_pkgs.append(m.group(1))

    all_dists = set()
    queue = list(base_pkgs)
    while queue:
        curr = queue.pop(0)
        try:
            d = im.distribution(curr)
            name = d.metadata["Name"]
            if name.lower() not in [x.lower() for x in all_dists]:
                all_dists.add(name)
                if d.requires:
                    for r in d.requires:
                        if "extra ==" in r:
                            continue
                        m = re.match(r"^([a-zA-Z0-9_\-]+)", r)
                        if m:
                            queue.append(m.group(1))
        except Exception:
            pass

    top_entries = set()
    for dname in all_dists:
        try:
            d = im.distribution(dname)
            if d.files:
                for f in d.files:
                    parts = f.parts
                    if parts:
                        top_entries.add(parts[0])
        except Exception:
            pass
    return top_entries

def build_public_release():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "release_public")
    temp_dir = os.path.join(base_dir, ".temp")
    os.makedirs(temp_dir, exist_ok=True)

    print("=" * 60)
    print("  CodeChecker 配布用パッケージ (案A: Embeddable Python同梱) ビルド")
    print("=" * 60)
    print(f"出力先ディレクトリ: {target_dir}")

    # 1. release_public の初期化
    os.makedirs(target_dir, exist_ok=True)
    python_dir = os.path.join(target_dir, "python")
    site_packages_dir = os.path.join(python_dir, "Lib", "site-packages")

    # 機械学習ライブラリ等の不要な混入を防ぐため、site-packages をクリーン初期化
    if os.path.exists(site_packages_dir):
        # 不要な巨大ライブラリ（torch, tensorrt 等）が存在する場合は全リセット
        has_bloat = any(os.path.exists(os.path.join(site_packages_dir, b)) for b in ["torch", "tensorrt_libs", "onnxruntime"])
        if has_bloat:
            print("[1/7] 既存の巨大ライブラリを検知したため、site-packages をクリーンアップします...")
            shutil.rmtree(site_packages_dir)
            os.makedirs(site_packages_dir, exist_ok=True)

    has_valid_python = (
        os.path.exists(os.path.join(python_dir, "python.exe")) and
        os.path.exists(site_packages_dir) and
        len(os.listdir(site_packages_dir)) > 0
    )

    if has_valid_python:
        print("[1-5/7] クリーンな Embeddable Python 環境を検出しました。再利用します。")
    else:
        print("[1/7] Embeddable Python 環境を初期化中...")
        if not os.path.exists(os.path.join(python_dir, "python.exe")):
            os.makedirs(python_dir, exist_ok=True)

            # 2. Embeddable Python の取得
            local_zip_path = os.path.join(temp_dir, PYTHON_ZIP_NAME)
            if not os.path.exists(local_zip_path) or os.path.getsize(local_zip_path) < 5 * 1024 * 1024:
                print(f"[2/7] Python Embeddable パッケージをダウンロード中...\n      URL: {PYTHON_EMBED_URL}")
                urllib.request.urlretrieve(PYTHON_EMBED_URL, local_zip_path)
                print(f"      ダウンロード完了 ({os.path.getsize(local_zip_path):,} bytes)")
            else:
                print(f"[2/7] キャッシュされた Python Embeddable を使用: {local_zip_path}")

            # 3. Python の展開
            print("[3/7] Embeddable Python を展開中...")
            with zipfile.ZipFile(local_zip_path, "r") as zf:
                zf.extractall(python_dir)

            # 4. python310._pth のパッチ適用 (site-packages & 相対パス有効化)
            print("[4/7] python310._pth を設定中 (site-packages 有効化)...")
            pth_file = os.path.join(python_dir, "python310._pth")
            if os.path.exists(pth_file):
                with open(pth_file, "w", encoding="utf-8") as f:
                    f.write("python310.zip\n")
                    f.write(".\n")
                    f.write("Lib\\site-packages\n")
                    f.write("..\n")
                    f.write("import site\n")

        # 5. 依存パッケージのインストール (Lib/site-packages 配下に展開)
        os.makedirs(site_packages_dir, exist_ok=True)
        req_file = os.path.join(base_dir, "requirements.txt")

        print("[5/7] 依存ライブラリを同梱Python環境に配置中...")
        # ホスト環境からホワイトリスト形式で厳密に依存パッケージのみを同期
        host_sp = os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages")
        allowed_entries = get_required_top_level_entries(req_file)
        print(f"      必要依存モジュール数: {len(allowed_entries)} 個をホワイトリスト同期します...")

        copied_count = 0
        for item in allowed_entries:
            src_item = os.path.join(host_sp, item)
            dst_item = os.path.join(site_packages_dir, item)
            if os.path.exists(src_item) and not os.path.exists(dst_item):
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item)
                else:
                    shutil.copy2(src_item, dst_item)
                copied_count += 1
        print(f"      ホワイトリスト同期完了 ({copied_count} 個のエントリを配置)")

    # 6. アプリケーションコード & アセットのコピー
    print("[6/7] CodeChecker のコードおよびアセットをコピー中...")
    for mod_name in ["codechecker", "web", "docs"]:
        target_mod = os.path.join(target_dir, mod_name)
        if os.path.exists(target_mod):
            shutil.rmtree(target_mod)
        shutil.copytree(
            os.path.join(base_dir, mod_name),
            target_mod,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )

    # サンプルファイル
    samples_dir = os.path.join(target_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    sample_src = os.path.join(base_dir, "tests", "sample_target", "vulnerable_app.py")
    if os.path.exists(sample_src):
        sample_dest = os.path.join(samples_dir, "sample_vulnerable.py")
        shutil.copy2(sample_src, sample_dest)
        with zipfile.ZipFile(os.path.join(samples_dir, "sample_vulnerable.zip"), "w") as z:
            z.write(sample_dest, "sample_vulnerable.py")

    root_samples = os.path.join(base_dir, "samples")
    for bin_name in ["sample_vulnerable.exe", "sample_vulnerable.dll"]:
        bin_path = os.path.join(root_samples, bin_name)
        if os.path.exists(bin_path):
            shutil.copy2(bin_path, os.path.join(samples_dir, bin_name))

    # 単一ファイル
    for fname in ["main.py", "settings.json", "SECURITY_REPORT.md"]:
        src_path = os.path.join(base_dir, fname)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(target_dir, fname))

    # 配布用 settings.json から個人APIキーをサニタイズ除去 (ポータブル配布時の秘密情報漏洩防止)
    pub_settings = os.path.join(target_dir, "settings.json")
    if os.path.exists(pub_settings):
        try:
            with open(pub_settings, "r", encoding="utf-8") as f:
                sdata = json.load(f)
            if "apis" in sdata:
                for k in sdata["apis"]:
                    sdata["apis"][k]["api_key"] = ""
            with open(pub_settings, "w", encoding="utf-8") as f:
                json.dump(sdata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: settings.json sanitize error: {e}")

    # 同梱Python専用ランチャー (run.bat)
    run_bat_content = """@echo off
setlocal
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo   CodeChecker (ポータブル同梱版) を起動しています...
echo ============================================================

".\\python\\python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [エラー] アプリケーションが終了コード %ERRORLEVEL% で停止しました。
    pause
)
"""
    with open(os.path.join(target_dir, "run.bat"), "w", encoding="utf-8") as f:
        f.write(run_bat_content)

    # 同梱Python専用サイレントランチャー (run_silent.vbs)
    run_vbs_content = """Set ws = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
ws.CurrentDirectory = strPath
ws.Run Chr(34) & strPath & "\\python\\python.exe" & Chr(34) & " main.py", 0, False
"""
    with open(os.path.join(target_dir, "run_silent.vbs"), "w", encoding="utf-8") as f:
        f.write(run_vbs_content)

    # 配布用 README.txt
    readme_text = """============================================================
  CodeChecker - ソースコード脆弱性診断 & AI修正提案 (ポータブル配布版)
============================================================

本パッケージは、Pythonの事前インストールが一切不要な「完全自己完結型ポータブル版」です。
お使いのWindows PCにPythonが導入されていなくても、解凍するだけで即座に利用できます。

【動作要件】
- OS: Windows 10 / 11 (64bit)
- Pythonのインストール: 不要 (アプリに同梱済み)
- (推奨) Ollama または Codex CLI (OpenAI)

【起動方法】
- 通常起動: 「run_silent.vbs」をダブルクリック
  (コマンドプロンプトの黒い画面を出さずに、アプリ画面だけが直接起動します)
- ログ確認用起動: 「run.bat」をダブルクリック
  (コンソール画面付きで起動し、エラーログや動作状況を確認できます)

【使い方】
1. 「run_silent.vbs」をダブルクリックしてアプリを起動します。
2. ドロップゾーンに、スキャンしたいフォルダや「samples」フォルダ内のファイル
   (sample_vulnerable.py, sample_vulnerable.zip, sample_vulnerable.exe 等)
   をドラッグ＆ドロップしてください。
3. 「チェック開始」ボタンを押すと、脆弱性が診断されます。
4. 各脆弱性を選択すると、原因の解説とAIによる修正提案コードを確認できます。

【ポータブル性について】
- 本アプリはPCのレジストリやユーザーフォルダ、システムテンポラリを一切汚しません。
- フォルダごとUSBメモリ等にコピーして持ち運ぶことも可能です。
- 不要になった場合は、このフォルダをそのまま削除するだけで完全にアンインストールされます。
============================================================
"""
    with open(os.path.join(target_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_text)

    # 7. 検証テスト
    print("[7/7] 同梱Pythonの自己診断テストを実行中...")
    test_cmd = [
        os.path.join(python_dir, "python.exe"),
        "-c",
        "import webview, semgrep, pefile, requests, yaml; print('Verification: ALL REQUIRED PACKAGES LOADED SUCCESSFULLY!')"
    ]
    test_res = subprocess.run(test_cmd, capture_output=True, text=True, encoding="utf-8")
    if test_res.returncode != 0:
        print(f"[ERROR] 検証テスト失敗:\n{test_res.stderr}")
        raise RuntimeError("同梱Pythonでのモジュールインポート検証に失敗しました")
    
    print(f"      {test_res.stdout.strip()}")

    # 8. 配布用 ZIP アーカイブの生成 (CodeChecker_Embedded.zip)
    zip_dest = os.path.join(base_dir, "CodeChecker_Embedded.zip")
    print(f"[8/8] 配布用 ZIP アーカイブを作成中: {zip_dest}")
    if os.path.exists(zip_dest):
        os.remove(zip_dest)

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, target_dir)
                zf.write(file_path, rel_path)

    zip_size_mb = os.path.getsize(zip_dest) / (1024 * 1024)
    print(f"      ZIP 作成完了: {zip_size_mb:.2f} MB")

    print("=" * 60)
    print("  ビルド完了: release_public/ および CodeChecker_Embedded.zip が正常に生成されました！")
    print("=" * 60)

if __name__ == "__main__":
    build_public_release()
