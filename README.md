# CodeChecker - ソースコード脆弱性診断 & AI修正提案デスクトップアプリ

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-brightgreen.svg)
![Ollama](https://img.shields.io/badge/Ollama-ready-orange.svg)

CodeChecker は、ソースコードの脆弱性をハイブリッド方式（静的解析 ＋ AI解説・修正提案）で検出・可視化するデスクトップアプリケーションです。

---

## 主な特徴

- 📁 **柔軟な入力方式**: スキャン対象のフォルダ選択だけでなく、`.zip` ファイルのドラッグ＆ドロップにも対応（安全な展開処理）。
- 🛡️ **高精度な静的解析 (SAST)**:
  - **Semgrep**: Python, JS/TS, Java, Go, C/C++, PHP 等 30 以上の言語に対応。
  - **内蔵セキュリティルール**: シークレット漏洩、RCE、SQLインジェクション、危険なデシリアライズ等を高速検出。
- 🤖 **ハイブリッドAI解説 & 修正提案**:
  - **Ollama連携**: ローカルLLM（`gemma4:12b-it-q4_K_M` 等）を呼び出し、完全オフラインで「なぜ危険か」「どう修正すべきか（Diff付きコード）」を詳細生成。
  - **Codex CLI連携**: OpenAI Codex CLI（非対話 exec モード）へのプロンプトパイプ渡しに対応。
- 📊 **危険度分類ダッシュボード**: 🔴高 / 🟡中 / 🟢低 で分類し、インタラクティブに絞り込み。
- 📄 **レポート出力**: Markdown / HTML 形式でエクスポート可能。

---

## ドキュメント

技術的詳細および利用マニュアルは [docs](docs/) ディレクトリに保管されています：
- 🏗️ [システムアーキテクチャ設計書 (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)
- ⚙️ [技術仕様書 (docs/TECH_SPECS.md)](docs/TECH_SPECS.md)
- 📖 [利用者マニュアル (docs/USER_GUIDE.md)](docs/USER_GUIDE.md)

---

## クイックスタート

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# アプリケーション起動
python main.py
```

