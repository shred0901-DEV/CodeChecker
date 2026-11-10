# 配布およびパッケージング仕様書 (Distribution & Packaging Guide)

## 1. 概要
本ドキュメントは、CodeChecker を第三者、学習者、または社内開発チームへ配布するための現行パッケージ仕様、および今後検討・推進する**スタンドアロン配布パッケージ化（インストーラー化 / 単一EXE化 / 組み込みPython同梱型）**に関する仕様・ロードマップを定義します。

---

## 2. 開発・デバッグ用配布パッケージ (`release/`)

Python 3.10+ がインストールされている環境を対象とした動作確認・デバッグ用ポータブルパッケージです。
以下のスクリプトを実行することで、最新のソースコードおよびアセットが `release/` ディレクトリに自動同期されます。
また、開発者の個人 API キーが配布物に混入しないよう、同期完了時に `release/settings.json` の API キーが自動的に空文字化（サニタイズ）されます。

```bash
python scripts/build_release.py
```

### ディレクトリ構成
```text
release/
├── run.bat              # アプリケーション起動バッチ (コンソール付き / 依存チェック付き)
├── run_silent.vbs       # 黒い画面を出さずに直接起動する VBScript
├── setup.bat            # 初回環境構築バッチ (pip install -r requirements.txt)
├── README.txt           # 配布用簡易マニュアル (UTF-8)
├── main.py              # アプリ起動エントリーポイント
├── settings.json        # ポータブル設定ファイル (APIキー自動サニタイズ済み)
├── SECURITY_REPORT.md   # アプリ安全性レポート
├── requirements.txt     # 必要パッケージ定義
├── codechecker/         # バックエンド Python ソースコード
│   ├── ai/              # AIプロバイダ (Ollama, Codex CLI, ChatGPT/Claude/Gemini 公式API)
│   └── scanner/         # 静的解析エンジン (Semgrep, 内蔵ルール, pefile)
├── web/                 # フロントエンド (完全ローカルバンドル化されたHTML/CSS/JS)
├── docs/                # 技術仕様書・マニュアル一式
└── samples/             # 動作検証・学習用サンプルコード
    ├── sample_vulnerable.py
    ├── sample_vulnerable.zip
    ├── sample_vulnerable.exe
    └── sample_vulnerable.dll
```

---

## 2.1 完全自己完結・ポータブル配布パッケージ (`release_public/` - 案A)

Python の事前インストールが一切不要な、完全自己完結型の配布用パッケージです。
公式の Windows x86-64 Embeddable Python を内部に同梱し、必要な全依存ライブラリがあらかじめ組み込まれています。

以下のビルドスクリプトを実行することで、オフライン環境・ホストキャッシュを活用してワンクリックで `release_public/` を自動生成できます。
開発者個人の API キーは自動サニタイズされ、配布先で安全に利用開始できます。

```bash
python scripts/build_public_release.py
```

### ディレクトリ構成
```text
release_public/
├── python/              # Windows x86-64 Embeddable Python (3.10.11)
│   ├── python.exe       # 同梱Pythonインタプリタ
│   ├── python310._pth   # site-packages 有効化パッチ適用済み
│   └── Lib/site-packages/ # pywebview, semgrep, pefile, requests 等の全ライブラリ
├── run.bat              # 同梱Pythonを相対パスで呼び出す起動バッチ
├── run_silent.vbs       # 黒い画面を出さずに直接起動する VBScript
├── README.txt           # 利用者向け説明書 (Python不要の案内)
├── main.py              # アプリ起動エントリーポイント
├── settings.json        # ポータブル設定ファイル (APIキー自動サニタイズ済み)
├── SECURITY_REPORT.md   # アプリ安全性レポート
├── codechecker/         # アプリケーションソースコード (公式APIモジュール含む)
├── web/                 # 完全ローカル化されたフロントエンドアセット
├── docs/                # ドキュメント一式
└── samples/             # サンプルコードおよびテスト用バイナリ
```

---

## 3. 単体テストによる品質保証

配布パッケージ作成前および更新時には、必ず以下の単体テストを実行して品質と安全性を検証します：

```bash
python -m unittest discover -s tests -v
```

- **全47テストケース**: スキャンエンジン、Zip Bomb/Slip防御、CLIサンドボックス隔離、各種公式APIプロバイダ（OpenAI/Anthropic/Gemini）のリクエスト・レスポンス検証、APIキーマスキング等を約0.25秒で網羅検証します。
