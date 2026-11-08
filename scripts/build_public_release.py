import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess

PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip"
PYTHON_ZIP_NAME = "python-3.10.11-embed-amd64.zip"

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
    if os.path.exists(target_dir):
        print("[1/7] 既存の release_public フォルダをクリーンアップ中...")
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    python_dir = os.path.join(target_dir, "python")
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
    site_packages_dir = os.path.join(python_dir, "Lib", "site-packages")
    os.makedirs(site_packages_dir, exist_ok=True)
    req_file = os.path.join(base_dir, "requirements.txt")

    print("[5/7] 依存ライブラリを同梱Python環境にインストール中 (pip target)...")
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", site_packages_dir,
        "-r", req_file,
        "--no-user"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        print(f"[ERROR] pip install 失敗:\n{res.stderr}")
        raise RuntimeError("依存パッケージのインストールに失敗しました")
    print("      ライブラリのインストール完了")

    # 6. アプリケーションコード & アセットのコピー
    print("[6/7] CodeChecker のコードおよびアセットをコピー中...")
    shutil.copytree(
        os.path.join(base_dir, "codechecker"),
        os.path.join(target_dir, "codechecker"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    shutil.copytree(
        os.path.join(base_dir, "web"),
        os.path.join(target_dir, "web")
    )
    shutil.copytree(
        os.path.join(base_dir, "docs"),
        os.path.join(target_dir, "docs")
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
    print("=" * 60)
    print("  ビルド完了: release_public/ が正常に生成されました！")
    print("=" * 60)

if __name__ == "__main__":
    build_public_release()
