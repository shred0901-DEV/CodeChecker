# 技術仕様書 (CodeChecker Technical Specifications)

## 1. 動作環境 & 技術スタック

| 区分 | 技術 / ライブラリ | 用途 / バージョン |
| :--- | :--- | :--- |
| **ランタイム** | Python | 3.10+ (Windows / macOS / Linux) |
| **デスクトップGUI** | `pywebview` | WebベースのUIをネイティブウィンドウ（Edge WebView2 on Windows）で描画 |
| **フロントエンド** | HTML5 / CSS3 / ES6+ | UIコンポーネント (フレームワーク非依存で軽量) |
| **UIスタイル** | Tailwind CSS (ローカルバンドル) | 完全ローカル化されたモダンでレスポンシブなダーク調デザイン |
| **アイコン & フォント** | FontAwesome 6 Free (ローカル) | WebフォントおよびCSSを完全ローカルバンドル |
| **コード表示・パース** | Prism.js / Marked.js / DOMPurify | シンタックスハイライト、Markdownパース、DOMサニタイズ（全ローカル） |
| **静的解析エンジン** | `semgrep` + 内蔵ルール + `pefile` | ソースコード (30+言語対応) および Windows PEバイナリ (EXE/DLL) 包括セキュリティ診断 |
| **ローカルLLM** | Ollama REST API (`/api/generate`) | `http://localhost:11434` を通じたローカル推論 (VRAM即時解放対応) |
| **AI連携方式** | Ollama / Codex CLI / 公式REST API群 | ローカル推論、CLIサンドボックス実行、およびクラウド公式API直接連携 (BYOK) |
| **自動テスト** | Python `unittest` | 47テストケースによる網羅的自動回帰テスト (所要時間 ~0.25秒) |

---

## 2. 対応AIプロバイダ仕様

CodeChecker は以下のAI実行環境に対応しています：

| プロバイダID | ツール名称 | 実行形式・エンドポイント | 備考 |
| :--- | :--- | :--- | :--- |
| **`ollama`** | **Ollama** (ローカルLLM) | REST API (`/api/generate`) | 完全オフライン動作。メモリ・VRAM自動解放（`keep_alive: 0`）対応 |
| **`codex`** | **Codex CLI** (OpenAI) | `codex exec --sandbox read-only --ephemeral --skip-git-repo-check -` | 引数リスト・`shell=False`、読み取り専用サンドボックス、セッション一時化、隔離ディレクトリ実行 |
| **`chatgpt`** | **ChatGPT API** (OpenAI 公式) | `POST https://api.openai.com/v1/chat/completions` | `gpt-4o-mini`, `gpt-4o`, `o3-mini` 対応。Bearer認証。推論モデル対応 |
| **`claude`** | **Claude API** (Anthropic 公式) | `POST https://api.anthropic.com/v1/messages` | `claude-3-7-sonnet-20250219`, `claude-3-5-haiku-20241022` 対応。x-api-key認証 |
| **`gemini`** | **Gemini API** (Google 公式) | `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `gemini-3.8-flash`, `gemini-3.8-pro`, `gemini-2.5-flash` 対応。`x-goog-api-key` ヘッダー認証 |
| **`disabled`**| **AI無効 (高速)** | N/A | 静的解析のみを瞬時に実行（外部通信・ローカル推論なし） |

### サブプロセス制御 & セキュリティ仕様
- Windows環境におけるサブプロセス実行時、`creationflags=subprocess.CREATE_NO_WINDOW`（`0x08000000`）を付与し、CLIやSemgrepの実行時に黒いコンソール画面が一瞬表示される現象を完全抑制。
- プロンプトは標準入力（stdin）経由で安全にパイプ通信し、コマンドライン引数は `shell=False` のリスト形式で起動することでOSコマンドインジェクションを完全排除。
- **Codex CLI の安全隔離実行 (SEC-CLI)**:
  - `--sandbox read-only` を必須指定し、ファイルの新規作成・書き込みやローカルシェルコマンドの実行を強制ブロック。
  - `--ephemeral` によりセッション履歴やロールアウトファイルをローカルディスクに残さずメモリ上のみで完結。
  - プロセス起動時のカレントワーキングディレクトリ（`cwd`）を `.temp/cli_sandbox/` に隔離し、CodeChecker 本体のコードベースへの不必要なアクセスや探索を物理的に遮断。
  - プロンプトにてツール実行やファイル編集の禁止を明示。
- **Ollama のリソース管理**:
  - プロバイダ切り替え時およびアプリ終了時に `unload_model()` を呼び出し、VRAM/RAMをOSへ即時返還。
- **公式 AI API の安全直接連携 (SEC-API)**:
  - 公式SDK（openai, anthropic, google-genai 等）を同梱せず、標準的な `requests` でエンドポイントを直接呼び出すことで、アプリの肥大化と不要な依存関係の混入を回避。
  - **Function Calling / Tool Use の完全排除**: AIにローカルファイル操作やコマンド実行の権限を一切与えず、純粋なテキスト生成（Text-in, Text-out）のみに限定。
  - **データ送信の局所化**: ファイル全体ではなく、指摘箇所の前後15行（約30行）のスニペットのみを抽出して送信。PEバイナリ実体データは送信を遮断。
  - **ヘッダー認証の徹底**: Gemini API では URL クエリパラメータ（`?key=...`）ではなく `x-goog-api-key` HTTPヘッダーを採用し、ProxyやサーバーログからのAPIキー漏洩（CWE-598）を遮断。
  - **キー保護とサニタイズ**: UIマスキング表示、空送信による既存キー上書き保護、および配布パッケージ生成スクリプト（`build_release.py`, `build_public_release.py`）によるキー自動消去。

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
  - エラーやタイムアウト時はキャッシュに保存しないため、いつでも安全に再試行可能。
- **AI生成ステータス表示の同期**:
  - 各脆弱性カードに、どのAIプロバイダによって解説・修正提案が生成されたかを示すバッジ（例: `Ollamaによって生成済み`、`ChatGPT APIによって生成済み` 等）を表示。
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
  - Tailwind CSS, FontAwesome, Prism.js, Marked.js, DOMPurify の全外部アセットを `web/vendor/` にローカルバンドル。外部ネットワーク未接続環境でも同一のダークテーマ・アイコン・ハイライト・Markdown表示を提供。

---

## 4. 完全ポータブル設計 & セキュリティ仕様 (SEC-03, PERF-01)

- **Zip Bomb & Zip Slip 多層防御 (SEC-03)**:
  - ZIP 展開前に `zf.infolist()` を走査し、総ファイル数上限（最大1,000件）、展開後総サイズ上限（最大200MB）、単一ファイル上限（最大100MB）、異常圧縮比率（200倍以上）を事前検証。
  - さらに展開中ストリームのバイト積算による二重チェックを行い、メタデータ偽装型 Zip Bomb も安全に遮断。
  - 展開先パストラバーサル（Zip Slip）の自動除外。
- **ポータブル設定永続化 (`settings.json`)**:
  - アプリ直下の `settings.json` にプロバイダ選択、Ollama設定、CLI設定、API設定（キー・モデル）を完全集約。
  - OS レジストリやユーザープロファイルを一切汚さず、USBメモリ等での持ち運び運用に対応。
