# 技術仕様書 (CodeChecker Technical Specifications)

## 1. 動作環境 & 技術スタック

| 区分 | 技術 / ライブラリ | 用途 / バージョン |
| :--- | :--- | :--- |
| **ランタイム** | Python | 3.10+ (Windows / macOS / Linux) |
| **デスクトップGUI** | `pywebview` | WebベースのUIをネイティブウィンドウ（Edge WebView2 on Windows）で描画 |
| **フロントエンド** | HTML5 / CSS3 / ES6+ | UIコンポーネント (フレームワーク非依存で軽量) |
| **UIスタイル** | Tailwind CSS (CDN) | モダンでレスポンシブなダーク/ライト調デザイン |
| **コード表示** | Prism.js / Marked.js | シンタックスハイライト、Markdownパース |
| **静的解析エンジン** | `semgrep` (Python package / CLI) + 内蔵ルール + `pefile` | ソースコード (30+言語対応) および Windows PEバイナリ (EXE/DLL) 包括セキュリティ診断 |
| **ローカルLLM** | Ollama REST API (`/api/generate`) | `http://localhost:11434` を通じた高速ローカル推論 |
| **AI連携** | Ollama (REST API) / Codex CLI (`subprocess` パイプライン) | ローカルLLMおよびOpenAI Codex CLIと連携 |

---

## 2. 対応AIプロバイダ仕様

CodeChecker は以下のAI実行環境に対応しています：

| プロバイダID | ツール名称 | 実行形式 | 備考 |
| :--- | :--- | :--- | :--- |
| **`ollama`** | **Ollama** (ローカルLLM) | REST API (`/api/generate`) | 完全オフライン動作。メモリ自動アンロード対応 |
| **`codex`** | **Codex CLI** (OpenAI) | `codex exec --skip-git-repo-check -` | 引数リスト・`shell=False` による安全な非対話パイプライン実行 |
| **`disabled`**| **AI無効 (高速)** | N/A | 静的解析のみを瞬時に実行 |

### サブプロセス制御 & セキュリティ仕様
- Windows環境におけるサブプロセス実行時、`creationflags=subprocess.CREATE_NO_WINDOW`（`0x08000000`）を付与し、CLIやSemgrepの実行時に黒いコンソール画面が一瞬表示される現象を完全抑制。
- プロンプトは標準入力（stdin）経由で安全にパイプ通信し、コマンドライン引数は `shell=False` のリスト形式で起動することでOSコマンドインジェクションを完全排除。

---

## 2.1 EXE / DLL 包括バイナリ診断仕様 (PEセキュリティスキャナ)

Windows PEバイナリ（`.exe`, `.dll`, `.sys`, `.ocx`）に対し、`pefile` を用いて以下の4大セキュリティ検査をミリ秒単位で包括実行：
1. **エクスプロイト緩和策 (Exploit Mitigations)**:
   - ASLR (`IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE`) の有無 (HIGH: CWE-119)
   - DEP/NX (`IMAGE_DLLCHARACTERISTICS_NX_COMPAT`) の有無 (HIGH: CWE-119)
   - Control Flow Guard (`IMAGE_DLLCHARACTERISTICS_GUARD_CF`) の有無 (MEDIUM: CWE-691)
   - Authenticode デジタル署名 (`IMAGE_DIRECTORY_ENTRY_SECURITY`) の有無 (LOW: CWE-347)
2. **危険なAPIインポート (Dangerous Imports)**:
   - メモリ破壊系: `strcpy`, `strcat`, `gets`, `sprintf`, `vsprintf`, `scanf` (HIGH/MEDIUM: CWE-120)
   - プロセス起動系: `system`, `_wsystem`, `WinExec`, `_popen` (HIGH/MEDIUM: CWE-78)
   - プロセス注入/フック系: `CreateRemoteThread`, `VirtualAllocEx`, `WriteProcessMemory`, `SetWindowsHookEx` (HIGH/MEDIUM: CWE-749)
   - アンチデバッグ系: `IsDebuggerPresent`, `CheckRemoteDebuggerPresent` (LOW: CWE-489)
3. **埋め込みシークレット & 危険な通信 (Embedded Artifacts)**:
   - AWSアクセスキー、秘密鍵、APIトークン (HIGH: CWE-798, CWE-312)
   - 平文HTTP通信URL (`http://...`) (MEDIUM: CWE-319)
   - 難読化PowerShellコマンド (`powershell -enc ...`) (HIGH: CWE-95)
4. **マニフェスト / UAC権限検査**:
   - `requireAdministrator` 常時管理者要求 (MEDIUM: CWE-250)
   - `autoElevate` 自動昇格 (HIGH: CWE-269)
5. **AI解説・修正提案との連携**:
   - バイナリ指摘に対しても、コンパイラ・リンカーオプション（`/DYNAMICBASE`, `/NXCOMPAT`, `/guard:cf` 等）や安全な代替API（`strcpy_s` 等）への書き換え指針をAIが提示。

---

## 3. UI連携・非同期制御仕様

- **非同期通信の競合保護（Race Condition Prevention）**:
  - 指摘アイテムの連続選択やプロバイダ切替時、各AIリクエストにインクリメントID（`explanationRequestId`）を付与。
  - レスポンス受信時に「最新リクエストID」かつ「現在選択中の指摘ID」と一致するかを厳密に検証ガードし、古い応答による表示上書きを防止。
  - 表示可能になるまでの間はローディングスピナーとともに「推論を実行中 (処理中)...」を明示。
- **AIプロバイダ切替 & キャッシュ制御**:
  - ヘッダーのプロバイダ選択変更時は自動生成を行わず、設定のみを更新。
  - 「AI解説を再生成」ボタン押下時に、選択プロバイダで生成を実行。すでに同プロバイダ・同モデルで生成済みの指摘はキャッシュから即時復元。
- **AI生成ステータス表示の同期**:
  - 各脆弱性カードに、どのAIプロバイダによって解説・修正提案が生成されたかを示すバッジ（例: `Ollamaによって生成済み`）を表示。
  - 推論処理中や再生成中は非表示を維持し、詳細欄のAI解説・バッジが表示準備完了したタイミングと完全に同期して表示。
  - スキャン実行時には一覧の生成ステータスを自動クリア。
- **スキャン中のUIロック（ぼかしオーバーレイ）**:
  - スキャン実行開始時、「危険度ボタン（サマリーカード）」および「左右2ペイン（脆弱性一覧・詳細）」の領域全体に `backdrop-blur-md` の半透明ぼかしオーバーレイを展開。
  - スキャン処理中に誤ってボタンや指摘項目をクリック・操作することを防止し、結果描画完了時に自動解除。
- **リンクのスマートハンドリング & バイナリ連携 (UX-01)**:
  - Webリンク (`http://`, `https://`): オレンジ色 (`#fb923c`) + 外部アイコン `[↗]` で表示。OS標準ブラウザで開く。
  - ソースコードファイルリンク: スカイブルー (`#38bdf8`) + 破線下線 + ファイルアイコン `[📄]` で表示。VS Code（行指定 `-g`）またはOS既定エディタで開く。
  - PEバイナリ（EXE/DLL）指摘選択時: ヘッダーのボタン表記が「ファイルの場所を開く」（フォルダアイコン）に動的切替。クリック時は OS エクスプローラー（`explorer.exe /select,"<フルパス>"`）を起動し、テキストエディタでの文字化けやフリーズを防止。
- **コードプレビューのハイライト言語動的切替 (UX-02)**:
  - 対象ファイルの拡張子（`.py`, `.js`, `.ts`, `.cpp`, `.cs`, `.go`, `.java` 等）に応じて Prism 言語クラスを動的切替。バイナリ指摘時は `language-none` を適用。
- **完全オフライン動作保証（閉域網対応 ARC-01）**:
  - Tailwind Play CDN, FontAwesome, Prism.js, Marked.js, DOMPurify の全外部アセットを `web/vendor/` にローカルバンドル。外部ネットワーク未接続環境でも同一のダークテーマ・アイコン・ハイライト・Markdown表示を提供。

---

## 4. 完全ポータブル設計 & セキュリティ仕様 (SEC-03, PERF-01)

- **Zip Bomb & Zip Slip 多層防御 (SEC-03)**:
  - ZIP 展開前に `zf.infolist()` を走査し、総ファイル数上限（最大1,000件）、展開後総サイズ上限（最大200MB）、単一ファイル上限（最大100MB）、異常圧縮比率（200倍以上）を事前検証。
  - さらに展開中ストリームのバイト積算による二重チェックを行い、メタデータ偽装型 Zip Bomb も安全に遮断。
  - 展開先パストラバーサル（Zip Slip）の自動除外。
- **拡張子ホワイトリストによる高速ファイル走査 (PERF-01)**:
  - 静的解析対象のプログラミング言語拡張子ホワイトリスト（`SOURCE_EXTENSIONS`）を定義。
  - `.json`, `.csv`, `.log`, `.sqlite`, `.xml`, `.txt`, `.md` などのデータファイル・ログを内蔵ルール正規表現スキャンから除外し、走査速度を大幅に向上。
- **アプリ内一時フォルダ (`.temp/`)**:
  - ZIPアーカイブ展開先をOSの `%TEMP%` ではなく、アプリディレクトリ直下の `.temp/` 配下に隔離。
  - スキャン実行時およびアプリ起動・終了時に `.temp/` 配下の作業ファイルを自動クリーンアップ。
- **アプリ内設定保存 (`settings.json`)**:
  - CLIコマンド設定やモデル選択情報をアプリディレクトリ直下の `settings.json` に自己完結保存。
  - レジストリや Windows の `AppData` を一切汚さず、フォルダごと移動・削除するだけで完結するクリーンなポータブル構成を実現。
- **Ollama VRAM/RAM リソースの即時解放**:
  - アプリ終了時（`finally` 節および `atexit` ハンドラ）や、Ollama から別プロバイダへ切り替えた際に、Ollama へアンロードリクエスト（`keep_alive: 0`）を自動送信。
  - アプリ終了後に GPU VRAM やシステム RAM が占有されたまま残る現象を完全に防止。
