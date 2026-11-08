# 配布および学習用パッケージ仕様書 (Distribution Guide)

## 1. 概要
CodeChecker を学習用教材として第三者やチームメンバーに配布するための構成および手順を定義します。

---

## 2. 配布ディレクトリ構成 (`release/`)

```text
release/
├── run.bat              # アプリケーション起動バッチ (ダブルクリックで起動)
├── setup.bat            # 初回環境構築バッチ (依存ライブラリの自動インストール)
├── README.txt           # 配布用簡易マニュアル (UTF-8)
├── main.py              # アプリ起動エントリーポイント
├── requirements.txt     # 必要パッケージ定義
├── codechecker/         # バックエンド Python ソースコード
├── web/                 # フロントエンド HTML/CSS/JS 資産
├── docs/                # 技術仕様書・マニュアル一式
└── samples/             # 学習・動作検証用サンプルコード
    ├── sample_vulnerable.py
    └── sample_vulnerable.zip
```

---

## 3. バッチファイルの仕様

### `run.bat` (通常起動用)
1. **文字コード設定**: 日本語Windows環境での文字化けを防ぐため `chcp 65001` (UTF-8) を指定。
2. **Pythonの検出**: `where python` コマンドで実行環境の有無を確認し、未導入の場合は案内を表示して `pause`。
3. **自己修復機能**: 依存ライブラリ（`pywebview`, `semgrep` 等）が未導入の場合は自動的に `pip install -r requirements.txt` を実行。
4. **起動**: `python main.py` を呼び出し、異常終了時はエラーコードを表示して画面を閉じずに一時停止。

### `setup.bat` (初回セットアップ専用)
- 起動前に依存パッケージのみを個別にインストールしておきたい学習者向けバッチ。

---

## 4. 配布パッケージの再生成コマンド

コードの修正や機能追加を行った後、以下のスクリプトを実行することで `release/` ディレクトリを最新化できます。

```bash
python scripts/build_release.py
```

配布時は、この `release/` フォルダをそのままZIP圧縮して配布可能です。

