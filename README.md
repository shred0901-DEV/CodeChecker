# CodeChecker - ソースコード & バイナリ脆弱性診断 / AI修正提案デスクトップアプリ

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-40%20passed-success.svg)
![Offline](https://img.shields.io/badge/offline-100%25%20ready-brightgreen.svg)
![Ollama](https://img.shields.io/badge/Ollama-ready-orange.svg)
![Codex](https://img.shields.io/badge/Codex%20CLI-ready-blue.svg)

CodeChecker は、ソースコードおよび Windows 実行バイナリ（EXE/DLL）のセキュリティ脆弱性を静的解析（SAST）と AI（LLM）のハイブリッド方式で検出し、具体的な修正コード・設定変更案を提示する完全オフライン・ポータブル対応のデスクトップアプリケーションです。

---

## 主な特徴

- 📁 **柔軟な入力 & 安全なファイル処理**:
  - フォルダ選択、単一ソースファイル、`.zip` アーカイブ、`.exe` / `.dll` のドラッグ＆ドロップに対応。
  - **Zip Slip**（パストラバーサル）および **Zip Bomb**（高圧縮攻撃）を5重の検査で完全防御。
- 🛡️ **包括的なハイブリッド静的解析**:
  - **Semgrep**: Python, JS/TS, Java, Go, C/C++, PHP, C# 等 30 以上の主要言語に対応。
  - **内蔵セキュリティルール**: シークレット漏洩、RCE、SQLインジェクション、安全でないデシリアライズ等を高速検出。
  - **Windows PE バイナリ診断 (pefile)**: ASLR / DEP / CFG / 署名の不備、危険なAPI呼び出し（`strcpy`, `system` 等）、埋め込みシークレットを静的走査。
- 🤖 **安全なマルチAI解説 & 修正提案**:
  - **Ollama連携**: ローカルLLM（`gemma4:12b-it-q4_K_M` 等）による完全オフライン推論。VRAM/RAMの自動解放に対応。
  - **Codex CLI連携**: OpenAI Codex CLI（非対話 exec モード）による高精度推論。`--sandbox read-only` や空の隔離作業ディレクトリにより安全性を保証。
  - **AI無効モード**: ネットワーク通信やCLI呼び出しを行わず、静的解析結果のみを瞬時に確認可能。
- 🌐 **完全オフライン動作（閉域網対応）**:
  - Tailwind CSS, FontAwesome, Prism.js, Marked.js, DOMPurify をすべてローカルにバンドル。外部CDN接続を一切行いません。
- 🔒 **堅牢なセキュリティ設計**:
  - DOMPurify による徹底したXSS無害化、サブプロセスの `shell=False` 配列引数化、一時展開ファイルの自動清掃（`.temp/`）。
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
- 📋 [コード監査結果 & 作業引き継ぎ書 (docs/AUDIT_AND_HANDOVER.md)](docs/AUDIT_AND_HANDOVER.md)
- 📦 [配布およびパッケージ仕様書 (docs/DISTRIBUTION.md)](docs/DISTRIBUTION.md)

---

## クイックスタート

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# テストスイートの実行 (全40テスト)
python -m unittest discover -s tests -v

# アプリケーション起動
python main.py
```

※ Windows 環境では、黒いコンソール画面を出さずに直接起動できる `run_silent.vbs` もご利用いただけます。
