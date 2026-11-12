import os
import json
import shutil
import zipfile

def build_release():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    release_dir = os.path.join(base_dir, "release")

    print(f"Release build starting: {release_dir}")

    # クリーンアップ
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir, exist_ok=True)

    # 1. codechecker パッケージのコピー
    shutil.copytree(
        os.path.join(base_dir, "codechecker"),
        os.path.join(release_dir, "codechecker"),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )

    # 2. web アセットのコピー
    shutil.copytree(
        os.path.join(base_dir, "web"),
        os.path.join(release_dir, "web")
    )

    # 3. docs のコピー
    shutil.copytree(
        os.path.join(base_dir, "docs"),
        os.path.join(release_dir, "docs")
    )

    # 4. 学習・検証用サンプル（ソースコード ＆ EXE/DLLバイナリ）の準備
    samples_dir = os.path.join(release_dir, "samples")
    os.makedirs(samples_dir, exist_ok=True)
    sample_src = os.path.join(base_dir, "tests", "sample_target", "vulnerable_app.py")
    if os.path.exists(sample_src):
        sample_dest = os.path.join(samples_dir, "sample_vulnerable.py")
        shutil.copy2(sample_src, sample_dest)
        with zipfile.ZipFile(os.path.join(samples_dir, "sample_vulnerable.zip"), "w") as z:
            z.write(sample_dest, "sample_vulnerable.py")

    # サンプルバイナリ (EXE/DLL) の同梱
    root_samples = os.path.join(base_dir, "samples")
    for bin_name in ["sample_vulnerable.exe", "sample_vulnerable.dll"]:
        bin_path = os.path.join(root_samples, bin_name)
        if os.path.exists(bin_path):
            shutil.copy2(bin_path, os.path.join(samples_dir, bin_name))

    # 5. 単一ファイルのコピー (run_silent.vbs, settings.json, SECURITY_REPORT.md 含む)
    for fname in ["main.py", "requirements.txt", "run.bat", "run_silent.vbs", "setup.bat", "settings.json"]:
        src_path = os.path.join(base_dir, fname)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(release_dir, fname))

    # 配布用 settings.json から個人APIキーをサニタイズ除去 (ポータブル配布時の秘密情報漏洩防止)
    release_settings = os.path.join(release_dir, "settings.json")
    if os.path.exists(release_settings):
        try:
            with open(release_settings, "r", encoding="utf-8") as f:
                sdata = json.load(f)
            if "apis" in sdata:
                for k in sdata["apis"]:
                    sdata["apis"][k]["api_key"] = ""
            with open(release_settings, "w", encoding="utf-8") as f:
                json.dump(sdata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: settings.json sanitize error: {e}")

    # 安全性レポートを release フォルダ直下にも配置
    sec_report_src = os.path.join(base_dir, "docs", "SECURITY_REPORT.md")
    if os.path.exists(sec_report_src):
        shutil.copy2(sec_report_src, os.path.join(release_dir, "SECURITY_REPORT.md"))

    # 6. 配布用 README.txt の作成
    readme_text = """============================================================
  CodeChecker - ソースコード脆弱性診断 & AI修正提案 (学習用配布版)
============================================================

本ツールは、ソースコードの脆弱性を静的解析とAI（ローカルLLM/商用LLM）の
ハイブリッド方式で検出し、原因解説と具体的な修正コードを学習するための教材アプリです。

【動作要件】
- OS: Windows 10 / 11
- Python 3.10 以上 (PATHが通っていること)
- (推奨) Ollama、Codex CLI、または各種公式AI API (ChatGPT / Claude / Gemini)

【起動方法】
- 通常起動: 「run_silent.vbs」をダブルクリック（黒い画面を出さずに起動）
- ログ確認用起動: 「run.bat」をダブルクリック（コマンドプロンプト付きで起動）
- 初回環境構築: 「setup.bat」で依存パッケージを一括インストール

【学習・利用手順】
1. アプリが起動したら、付属の「samples」フォルダ、または「samples/sample_vulnerable.zip」、
   あるいは「samples/sample_vulnerable.exe」「samples/sample_vulnerable.dll」を
   画面上のドロップゾーンにドラッグ＆ドロップ（またはファイル選択）してください。
2. 「チェック開始」ボタンを押下します。
3. 検出された脆弱性（高・中・低）の一覧から項目を選択し、
   AIによる「脆弱性の要約」「修正方針」「推奨修正コード/コンパイルオプション」を確認して学習してください。

【ドキュメント】
詳細な技術仕様やマニュアル、安全性レポートは「docs」フォルダおよび直下に格納されています。
- SECURITY_REPORT.md   : アプリケーション安全性評価 & 脆弱性対策レポート (アプリ自体の安全性)
- docs/USER_GUIDE.md   : 利用マニュアル
- docs/ARCHITECTURE.md : システムアーキテクチャ設計書
- docs/TECH_SPECS.md   : 技術仕様書
- docs/DISTRIBUTION.md : 配布パッケージ仕様書
============================================================
"""
    with open(os.path.join(release_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_text)

    # 7. 配布用 ZIP アーカイブの生成 (CodeChecker.zip)
    zip_dest = os.path.join(base_dir, "CodeChecker.zip")
    print(f"[7/7] 配布用 ZIP アーカイブを作成中: {zip_dest}")
    if os.path.exists(zip_dest):
        os.remove(zip_dest)

    with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, release_dir)
                zf.write(file_path, rel_path)

    zip_size_kb = os.path.getsize(zip_dest) / 1024
    print(f"      ZIP 作成完了: {zip_size_kb:.2f} KB ({zip_size_kb / 1024:.2f} MB)")

    print("=" * 60)
    print("Release build & CodeChecker.zip completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    build_release()
