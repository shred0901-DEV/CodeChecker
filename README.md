# CodeChecker - ソースコード & バイナリ脆弱性診断 / AI修正提案デスクトップアプリ

![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-47%20passed-success.svg)
![Offline](https://img.shields.io/badge/offline-100%25%20ready-brightgreen.svg)
![Ollama](https://img.shields.io/badge/Ollama-ready-orange.svg)
![Codex](https://img.shields.io/badge/Codex%20CLI-ready-blue.svg)
![ChatGPT](https://img.shields.io/badge/ChatGPT%20API-ready-emerald.svg)
![Claude](https://img.shields.io/badge/Claude%20API-ready-amber.svg)
![Gemini](https://img.shields.io/badge/Antigravity%20Agent%20API-ready-sky.svg)

CodeChecker は、ソースコードおよび Windows 実行バイナリ（EXE/DLL）のセキュリティ脆弱性を静的解析（SAST）と AI（ローカルLLM / Codex CLI / 各種クラウド公式API）のハイブリッド方式で検出し、具体的な修正コード・設定変更案を提示する完全オフライン・ポータブル対応のデスクトップアプリケーションです。

---

## 📥 アプリのダウンロード方法

**[👉 Windows専用Embedded版（Pythonインストール不要）をダウンロード](https://github.com/shred0901-DEV/CodeChecker/raw/refs/heads/main/CodeChecker_Embedded.zip)**

**[👉 通常版をダウンロード](https://github.com/shred0901-DEV/CodeChecker/raw/refs/heads/main/CodeChecker.zip)**

※任意のディレクトリに解凍してご利用ください。

## クイックスタート (Embedded版を除く)

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# テストスイートの実行 (全47テスト)
python -m unittest discover -s tests -v

# アプリケーション起動
python main.py
```

※ Windows 環境では、`setup.bat`で依存パッケージのインストール、`run.bat`でアプリケーションが起動できます。
黒いコンソール画面を出さずに直接起動できる `run_silent.vbs` もご利用いただけます。
Embedded版の場合は、基本的に`run_silent.vbs`で起動してください。

Macの場合は、`setup.bat`、`run.bat`、`run_silent.vbs`が使えないので削除してください。

## 主な特徴

- 📁 **柔軟な入力 & 安全なファイル処理**:
  - フォルダ選択、単一ソースファイル、`.zip` アーカイブ、`.exe` / `.dll` のドラッグ＆ドロップに対応。
  - **Zip Slip**（パストラバーサル）および **Zip Bomb**（高圧縮攻撃）を5重の検査で完全防御。
- 🛡️ **包括的なハイブリッド静的解析**:
  - **Semgrep**: Python, JS/TS, Java, Go, C/C++, PHP, C# 等 30 以上の主要言語に対応。
    ※無償版のため、ファイル横断分析は非対応です。
  - **内蔵セキュリティルール**: シークレット漏洩、RCE、SQLインジェクション、安全でないデシリアライズ等を高速検出。
  - **Windows PE バイナリ診断 (pefile)**: ASLR / DEP / CFG / 署名の不備、危険なAPI呼び出し（`strcpy`, `system` 等）、埋め込みシークレットを静的走査。
- 🤖 **柔軟かつ安全なマルチAI解説 & 修正提案**:
  - **Ollama連携**: ローカルLLM（`gemma4:12b-it-q4_K_M` 等）による完全オフライン推論。プロバイダ切替時およびアプリ終了時の VRAM/RAM 自動解放に対応。
  - **Codex CLI連携**: OpenAI Codex CLI（非対話 exec モード）による高精度推論。`--sandbox read-only` や空の隔離作業ディレクトリにより安全性を保証。
  - **公式 AI API 直接連携 (BYOK)**:
    - **ChatGPT API (OpenAI)**: `gpt-4o-mini`, `gpt-4o`, `o3-mini` 等に対応。
    - **Claude API (Anthropic)**: `claude-3-7-sonnet-20250219`, `claude-3-5-haiku-20241022` 等に対応。
    - **Antigravity Agent API (Google Gemini)**: `gemini-3.8-flash`, `gemini-3.8-pro`, `gemini-2.5-flash` 等に対応。ヘッダー認証（`x-goog-api-key`）によりURL経由のキー漏洩を防止。
    - ※各APIとも Function Calling（自動実行権限）を一切排除し、指摘前後の限定スニペット（約30行）のみを送信するデータ最小化設計。
  - **AI無効モード**: 外部通信やローカル推論を行わず、静的解析結果のみを瞬時に確認可能。
- 🌐 **完全オフライン動作（閉域網対応）**:
  - Tailwind CSS, FontAwesome, Prism.js, Marked.js, DOMPurify をすべてローカルにバンドル。外部CDN接続を一切行いません。
- 🔒 **堅牢なセキュリティ設計**:
  - DOMPurify による徹底したXSS無害化、サブプロセスの `shell=False` 配列引数化、一時展開ファイルの自動清掃（`.temp/`）、配布用パッケージ生成時の API キー自動サニタイズ（消去）機構。
- 📊 **インタラクティブ・ダッシュボード**:
  - 危険度別（🔴高 / 🟡中 / 🟢低）の即時フィルタリング、ソースコードプレビュー、OSエクスプローラー連携（バイナリ向け）。
- 📄 **レポート出力**:
  - AI解説・修正提案を含めた Markdown（`.md`）および HTML（`.html`）形式でのエクスポートに対応。

---

## ドキュメント一覧

詳細な仕様や設計思想、運用ルールについては [docs](docs/) ディレクトリ内のドキュメントをご参照ください：

- 🏗️ [システムアーキテクチャ設計書 (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)
- ⚙️ [技術仕様書 (docs/TECH_SPECS.md)](docs/TECH_SPECS.md)
- 📖 [利用者マニュアル (docs/USER_GUIDE.md)](docs/USER_GUIDE.md)
- 🛡️ [安全性評価 & 脆弱性対策レポート (SECURITY_REPORT.md)](SECURITY_REPORT.md)
- 📦 [配布およびパッケージ仕様書 (docs/DISTRIBUTION.md)](docs/DISTRIBUTION.md)

---
