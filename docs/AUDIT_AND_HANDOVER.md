# CodeChecker コード監査結果 & 作業引き継ぎ書 (AUDIT & HANDOVER)

本ドキュメントは、CodeChecker プロジェクト全体のコード監査結果、フェーズ別の改修状況、および次回作業（Phase 3: 中長期改善候補）を引き継ぐための詳細仕様をまとめたものです。

---

## 1. プロジェクト概要と進捗状況

CodeChecker は、ソースコードおよび Windows PE バイナリ（EXE/DLL）のセキュリティ脆弱性を静的解析（Built-in ルール / Semgrep / pefile）で検出し、LLM（Ollama / Codex CLI）と連携して日本語の解説と修正提案を提示するデスクトップアプリケーション（PyWebView / Python 3.10+）です。

### 全体進捗ステータス
- **Phase 1（即時対応推奨 & 規約対応）**: **【完了済 (Completed)】**
  - **BUG-01**: 重複排除キーの改修により、バイナリ全指摘（15件）の完全出力に成功。
  - **SEC-01**: AI 解説描画部での HTML サニタイズ適用による XSS 脆弱性の排除。
  - **SEC-02**: `cli_provider.py` の `shell=True` を廃止し、引数リスト形式の安全な `shell=False` 実行へ改修。
  - **BUG-02**: HTML レポート出力時に AI 解説・修正提案を含めるように改修。
  - **CLI-01**: 規約上使用不可の 3大CLI（Gemini, Antigravity, Claude）を全削除し、「Ollama」「Codex CLI」「AI無効」に集約。
- **Phase 2（短期改善推奨）**: **【完了済 (Completed)】**
  - **TST-01**: Python 標準 `unittest` に準拠した包括的テストスイート（全29テストケース）を構築（全件 PASS）。
  - **BUG-03**: 単一ファイルスキャン時にコピーを廃止して元の実パスを保持し、「エディタで開く」連携を正常化。
  - **RES-01**: スキャン開始時の一時フォルダ安全解放と `cleanup_all_temp` により、`.temp` 内のリソース蓄積（リーク）を完全防止。
  - **BUG-04**: 内蔵コマンド実行ルール（`builtin-cmdi-system`）の正規表現を改善し、リスト引数（配列渡し）の安全な呼び出しを誤検知除外。
  - **BUG-05**: 進捗通知（`on_progress`）で `json.dumps` による完全エスケープを適用し、JS 構文エラーを防止。
- **ソース管理（GitHub）**: **【完了済 (Completed)】**
  - `.gitignore` の整備、Git 初期化（`main` ブランチ）、GitHub リモート（`https://github.com/shred0901-DEV/CodeChecker.git`）への初回プッシュ完了。
- **Phase 3（中長期改善候補）**: **【次回対応対象 (Current Target)】**
  - Zip Bomb 防御（SEC-03）、外部 CDN アセットのローカルバンドル化（ARC-01）、ファイル拡張子走査の最適化（PERF-01）、バイナリ指摘時の「ファイルの場所を開く」対応（UX-01）、コードプレビューのハイライト言語自動切替（UX-02）。

---

## 2. 課題一覧と対応ステータス

| ID | 優先度 | 確度 | 対象ファイル | 問題概要 | ステータス |
|---|---|---|---|---|:---:|
| **BUG-01** | **Critical** | Confirmed | `codechecker/scanner/engine.py` | 重複排除ロジックの不備により、PE等の同一行指摘がロストする | **完了 (Phase 1)** |
| **SEC-01** | **High** | Confirmed | `web/js/app.js` | AI解説描画時のサニタイズ欠如による Stored / DOM XSS 脆弱性 | **完了 (Phase 1)** |
| **SEC-02** | **High** | Confirmed | `codechecker/ai/cli_provider.py` | CLI 実行時の `shell=True` による OS コマンドインジェクションのリスク | **完了 (Phase 1)** |
| **BUG-02** | **High** | Confirmed | `codechecker/api.py` | HTML レポートエクスポート時に AI 解説の出力処理が欠落している | **完了 (Phase 1)** |
| **CLI-01** | **High** | Confirmed | 全般 | 規約上使用不可となった Gemini / Antigravity / Claude CLI の残存 | **完了 (Phase 1)** |
| **TST-01** | **High** | Confirmed | `tests/` 全般 | 自動テストスイートの欠如（アドホックな print スクリプトのみ） | **完了 (Phase 2)** |
| **BUG-03** | **Medium** | Confirmed | `scanner/file_manager.py`<br>`codechecker/api.py` | 単一ファイルスキャン時に一時コピー先のパスが記録され元ファイルを開けない | **完了 (Phase 2)** |
| **RES-01** | **Medium** | Confirmed | `scanner/engine.py`<br>`file_manager.py` | 複数回スキャン実行時に `.temp/` 内の一時フォルダが蓄積し続ける（リソースリーク） | **完了 (Phase 2)** |
| **BUG-04** | **Medium** | Confirmed | `scanner/builtin_rules.py` | コマンド実行ルールの正規表現により推奨されるリスト形式が誤検知される | **完了 (Phase 2)** |
| **BUG-05** | **Low** | Confirmed | `codechecker/api.py` | `on_progress` 内の文字列エスケープ不備による JS 構文エラー発生リスク | **完了 (Phase 2)** |
| **SEC-03** | **Medium** | Probable | `scanner/file_manager.py` | ZIP 展開処理における Zip Bomb（展開サイズ・ファイル数爆発）防御の欠落 | **次回対応 (Phase 3)** |
| **ARC-01** | **Medium** | Confirmed | `web/index.html` | Tailwind, FontAwesome, Prism, Marked の外部 CDN 依存によるオフライン動作不能 | **次回対応 (Phase 3)** |
| **PERF-01**| **Medium** | Probable | `scanner/file_manager.py` | 拡張子フィルタ不足により巨大なデータファイルやログも走査対象になる | **次回対応 (Phase 3)** |
| **UX-01** | **Enhancement** | Probable | `web/js/app.js`, `codechecker/api.py` | バイナリ指摘に対しても「エディタで開く」が実行され文字化けする | **次回対応 (Phase 3)** |
| **UX-02** | **Enhancement** | Probable | `web/index.html`, `web/js/app.js` | コードプレビュー欄のシンタックスハイライトが `language-python` 固定 | **次回対応 (Phase 3)** |
| **ARC-02** | **Low** | Confirmed | `codechecker/app.py`, `codechecker/api.py` | PyWebView 内部非公開 API（`_dnd_state`）への直接依存 | 現状維持推奨 |

---

## 3. 次回チャットで実施する中長期改善タスク (Phase 3 詳細仕様)

次回チャットでは、アプリケーションの堅牢性・オフライン完全対応・パフォーマンス・UI/UX の向上を目的として、以下の **5項目（Phase 3）** を実装します。

### タスク 1: ZIP 展開処理における Zip Bomb 防御 (SEC-03)
- **対象**: `codechecker/scanner/file_manager.py` (`extract_zip_safely`), `tests/test_file_manager.py`
- **背景**: 現状の `extract_zip_safely` は Zip Slip（パストラバーサル）を防いでいますが、展開後サイズやファイル数の上限チェックがありません。悪意ある高圧縮 ZIP（Zip Bomb）によりディスク容量枯渇やフリーズを引き起こす恐れがあります。
- **改修要件**:
  - 解凍前に `zf.infolist()` を走査し、展開後サイズ合計の上限（例: 最大 200MB）および総ファイル数上限（例: 最大 1,000ファイル）をチェック。超過時は安全に例外（`ValueError("ZIP展開上限を超過しました: Zip Bombの可能性があります")`）を送出。
  - 各ファイルの非圧縮サイズと圧縮サイズの比率（圧縮率）が極端に異常なエントリも防御。
  - `tests/test_file_manager.py` に上限超過時の防御テストケースを追加。

### タスク 2: 外部 CDN アセットのローカルバンドル化 (ARC-01)
- **対象**: `web/index.html`, `web/css/`, `web/js/`, `web/vendor/`
- **背景**: Tailwind CSS (Play CDN)、FontAwesome、Prism.js、Marked.js を外部 CDN からロードしているため、インターネット非接続環境（オフライン・社内閉域網）でアプリを起動した際に UI スタイル・アイコン・シンタックスハイライト・Markdown レンダリングが完全に崩壊します。
- **改修要件**:
  - 外部 CDN の JS/CSS/フォントリソースをダウンロードし、`web/vendor/`（または `web/css/`, `web/js/`）配下にローカル配置。
  - `web/index.html` の `<script src="...">` および `<link rel="...">` をすべてローカル相対パス参照に変更。
  - 完全オフライン（機内モード・閉域網）環境でも、オンライン時と同一の美しいダークテーマ・アイコン・ハイライト・Markdown 表示が動作することを保証。

### タスク 3: ファイル走査の最適化と拡張子ホワイトリスト導入 (PERF-01)
- **対象**: `codechecker/scanner/file_manager.py` (`collect_files`), `tests/test_file_manager.py`
- **背景**: `collect_files` において、`EXCLUDED_EXTENSIONS` 以外のファイル（10MB以下）をすべてソースコードとみなしているため、巨大な `.json`, `.csv`, `.log`, `.sqlite`, `.xml`, `.txt` 等も内蔵ルールの正規表現走査にかけられ、走査速度が低下しています。
- **改修要件**:
  - 静的解析の対象とするプログラミング言語の拡張子セット（ホワイトリスト: `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.go`, `.c`, `.cpp`, `.h`, `.hpp`, `.cs`, `.php`, `.rb`, `.sh`, `.bat`, `.ps1` 等）を明確に定義。
  - 明らかなデータファイル（`.json`, `.csv`, `.log`, `.xml`, `.txt`, `.md` 等）は内蔵ルールの走査対象から除外し、スキャン処理時間を大幅に短縮。
  - 単一ファイルスキャン時は、指定されたファイルの拡張子がホワイトリストに含まれていれば即座に対象とする。

### タスク 4: バイナリ指摘時の「ファイルの場所を開く」対応 (UX-01)
- **対象**: `web/js/app.js`, `codechecker/api.py` (`open_source_file` / `open_file_location`)
- **背景**: PE バイナリ（EXE/DLL）の指摘を選択した状態でも、ヘッダーに「エディタで開く」が表示され、クリックするとテキストエディタでバイナリを開いてしまい、文字化けやエディタのフリーズを招きます。
- **改修要件**:
  - バイナリ指摘（`source == 'pe-binary'` または拡張子が `.exe`, `.dll`）選択時は、ボタンの表記を「ファイルの場所を開く」に変更し、アイコンをフォルダアイコン（`fa-folder-open`）に切り替え。
  - クリック時はテキストエディタではなく、OS のファイラー（Windows の場合は `explorer.exe /select,"<フルパス>"`）で該当バイナリを選択状態でエクスプローラーを開くバックエンド API を呼び出す。

### タスク 5: コードプレビューのシンタックスハイライト言語自動切替 (UX-02)
- **対象**: `web/index.html`, `web/js/app.js` (`selectFinding`)
- **背景**: 詳細ビューのコード表示要素が `<code id="detail-code-block" class="language-python">` とハードコードされており、JS, Go, C++, バイナリ等の指摘であってもすべて Python の文法規則でハイライトされています。
- **改修要件**:
  - 対象ファイルの拡張子（`.js`, `.ts` -> `language-javascript`, `.c`, `.cpp` -> `language-clike`, `.go` -> `language-go`, `.java` -> `language-java` 等）に応じて、`code` 要素の Prism クラスを動的に切り替え。
  - バイナリ指摘の場合は `language-none`（または構造テキスト用スタイル）を適用し、不自然なハイライトを防止。

### タスク 6: 配布パッケージ生成スクリプトの同期 & Git コミット
- **対象**: `scripts/build_release.py`
- **改修要件**:
  - Phase 3 の修正完了後、`python scripts/build_release.py` を実行して `release/` ディレクトリを最新状態に同期。
  - `python -m unittest discover -s tests -v` で全テストが PASS することを確認後、Git にコミット・プッシュする。

---

## 4. 修正完了後の検証手順

1. **自動テストスイートの全件 PASS 確認**:
   ```bash
   python -m unittest discover -s tests -v
   ```
2. **完全オフラインでの起動・表示確認**:
   - PC のネットワークを切断（または機内モード）にした状態でアプリを起動し、Tailwind CSS、FontAwesome アイコン、Prism コードハイライト、Marked Markdown が正常に表示されることを確認。
3. **Zip Bomb 防御の確認**:
   - 制限値を超えるダミー ZIP ファイルを作成してスキャンを試行し、安全に例外が発生してアプリが保護されることをテストで確認。
4. **バイナリ指摘時の「ファイルの場所を開く」動作確認**:
   - `samples/sample_vulnerable.exe` をスキャンし、指摘選択時にボタンが「ファイルの場所を開く」となり、クリックでエクスプローラーが対象ファイルを選択して起動することを確認。
5. **Git コミットと同期確認**:
   - `git status` で差分を確認し、コミットおよび GitHub リモートへのプッシュを実施。
