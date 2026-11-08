# CodeChecker コード監査結果 & 作業引き継ぎ書 (AUDIT & HANDOVER)

本ドキュメントは、CodeChecker プロジェクト全体のコード監査結果、フェーズ別の改修状況、および次回作業（Phase 2: 短期改善推奨）を引き継ぐための詳細仕様をまとめたものです。

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
  - **TST-01**: Python 標準 `unittest` に準拠した包括的テストスイート（全29テストケース）を構築。
  - **BUG-03**: 単一ファイルスキャン時にコピーを廃止して元の実パスを保持し、「エディタで開く」連携を正常化。
  - **RES-01**: スキャン開始時の一時フォルダ安全解放と `cleanup_all_temp` により、`.temp` 内のリソース蓄積（リーク）を完全防止。
  - **BUG-04**: 内蔵コマンド実行ルール（`builtin-cmdi-system`）の正規表現を改善し、リスト引数（配列渡し）の安全な呼び出しを誤検知除外。
  - **BUG-05**: 進捗通知（`on_progress`）で `json.dumps` による完全エスケープを適用し、JS 構文エラーを防止。
- **Phase 3（中長期改善候補）**: **【次回対応対象 (Current Target)】**
  - Zip Bomb 防御（SEC-03）、外部 CDN アセットのローカルバンドル化（ARC-01）、ファイル拡張子走査の最適化（PERF-01）、バイナリ指摘時の「エディタで開く」制御（UX-01）、コードプレビューのハイライト言語自動切替（UX-02）。

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
| **SEC-03** | **Medium** | Probable | `scanner/file_manager.py` | ZIP 展開処理における Zip Bomb（展開サイズ・ファイル数爆発）防御の欠落 | Phase 3 (中長期) |
| **ARC-01** | **Medium** | Confirmed | `web/index.html` | Tailwind, FontAwesome, Prism, Marked の外部 CDN 依存によるオフライン動作不能 | Phase 3 (中長期) |
| **PERF-01**| **Medium** | Probable | `scanner/file_manager.py` | 拡張子フィルタ不足により巨大なデータファイルやログも走査対象になる | Phase 3 (中長期) |
| **ARC-02** | **Low** | Confirmed | `codechecker/app.py`, `codechecker/api.py` | PyWebView 内部非公開 API（`_dnd_state`）への直接依存 | 現状維持推奨 |
| **UX-01** | **Enhancement** | Probable | `web/js/app.js`, `codechecker/api.py` | バイナリ指摘に対しても「エディタで開く」が実行され文字化けする | Phase 3 (中長期) |
| **UX-02** | **Enhancement** | Probable | `web/index.html`, `web/js/app.js` | コードプレビュー欄のシンタックスハイライトが `language-python` 固定 | Phase 3 (中長期) |

---

## 3. Phase 2 で実施した短期改善実績 (完了)

Phase 2 では、アプリケーションの信頼性・安定性・リソース管理を強化するため、以下の **5項目（Phase 2）** の実装および検証を完了しました。

### 実績 1: 自動テストスイートの構築 (TST-01) - 完了
- **対象**: `tests/` ディレクトリ
- **内容**:
  - アドホックスクリプトを整理・移行し、Python 標準の `unittest` に準拠した4つのテストモジュール（全29テストケース）を構築。
  - `test_engine.py`: フォルダ/ZIP/単一ファイルスキャン、PEバイナリ全15件検出（BUG-01）、CWE日本語タイトル補完、連続スキャン時のリソースリーク防止（RES-01）を検証。
  - `test_builtin_rules.py`: コマンドインジェクションの安全なリスト引数除外（BUG-04）および危険な呼び出し検知、シークレット漏洩、SQLi（文字列連結・f-string）、RCE、デシリアライズ、コメントスキップを検証。
  - `test_file_manager.py`: 単一ファイルの元パス保持（BUG-03）、安全なZIP解凍（Zip Slip防御）、除外ディレクトリ判定、一時フォルダの完全クリーンアップ（RES-01）を検証。
  - `test_ai_manager.py`: ステータス取得、Codex CLI プロファイル確認、CLI-01 規約検証（禁止CLIの完全排除）、プロバイダ切替、AI無効化モードの安全性、キャッシュ動作を検証。
- **検証**: `python -m unittest discover -s tests -v` で29件全件 PASS を確認。

### 実績 2: 単一ファイルスキャン時の元パス保持とエディタ連携改善 (BUG-03) - 完了
- **対象**: `codechecker/scanner/file_manager.py`, `codechecker/scanner/engine.py`, `codechecker/api.py`
- **内容**:
  - 単一ファイル指定時は一時フォルダ `.temp/file_xxxx/` へのコピーを行わず、元の実ファイルパスを直接スキャン対象として `is_temp=False` を維持するよう改修。
  - `FileManager.collect_files` に単一ファイル判定を追加し、単一ファイルのみを正確にスキャナへ渡すよう対応。
  - スキャナ側（`builtin_rules`, `pe_scanner`, `semgrep_runner`）で `base_dir` がファイルパスの場合に相対パスが `.` とならずファイル名となるよう改善。
  - `AppAPI.open_source_file` で元の実ファイルが VS Code / 既定エディタで直接開かれ、変更が元ファイルに即時反映されることを確認。

### 実績 3: スキャン一時フォルダのリソースリーク防止 (RES-01) - 完了
- **対象**: `codechecker/scanner/engine.py`, `codechecker/scanner/file_manager.py`, `codechecker/api.py`
- **内容**:
  - `ScanEngine.scan` 開始時および `AppAPI.__init__` 時に `file_manager.cleanup()` / `cleanup_all_temp()` を実行。
  - 連続して ZIP ファイルをスキャンしても直前の一時ディレクトリが自動解放され、常に最新スキャンの一時ディレクトリ1件のみが保持されるライフサイクル管理を確立。

### 実績 4: リスト形式コマンド呼び出しの誤検知修正 (BUG-04) - 完了
- **対象**: `codechecker/scanner/builtin_rules.py` (`builtin-cmdi-system`)
- **内容**:
  - 正規表現にリスト引数形式の否定先読み `(?!.*shell\s*=\s*True)\s*\[` を導入。
  - `subprocess.Popen(["cmd", "arg"])` や `subprocess.run(["git", "status"])` 等の安全な配列渡し呼び出しを誤検知から除外。
  - 一方で `subprocess.Popen("cmd " + arg, shell=True)` や `subprocess.Popen(["cmd", arg], shell=True)` などの危険な呼び出しは確実に検知。
  - 併せて `builtin-sqli-concat` の f-string (`f"SELECT ... {var}"`) 正規表現も補正し検知精度を向上。

### 実績 5: 進捗通知メッセージの完全エスケープ (BUG-05) - 完了
- **対象**: `codechecker/api.py` (`on_progress` コールバック)
- **内容**:
  - `json.dumps(message)` による完全な JSON エスケープを適用。
  - バックスラッシュ、シングルクォート、ダブルクォート、改行を含むパス名やメッセージでも JS 構文エラーを防止。

### 実績 6: 配布パッケージの同期 - 完了
- **内容**: `python scripts/build_release.py` を実行し、Phase 1 & Phase 2 の全修正内容が `release/` ディレクトリに正常反映されたことを確認。

---

## 4. 次回チャットで実施する中長期改善タスク (Phase 3 詳細仕様)

次回以降の作業（Phase 3）では、アプリケーションの堅牢性・オフライン完全対応・パフォーマンス・UI/UX の向上を目的として、以下の課題に対応することを推奨します。

1. **ZIP展開処理における Zip Bomb 防御 (SEC-03)**:
   - 対象: `codechecker/scanner/file_manager.py`
   - 内容: 解凍後の総展開ファイルサイズ上限（例: 200MB）および展開ファイル数上限（例: 1,000件）を設け、Zip Bomb 攻撃によるディスク枯渇やフリーズを防御。
2. **外部 CDN アセットのローカルバンドル化 (ARC-01)**:
   - 対象: `web/index.html`, `web/css/`, `web/js/`
   - 内容: Tailwind CSS, FontAwesome, Prism.js, Marked.js などの外部 CDN 依存をローカルアセットとして同梱し、完全オフライン環境（セキュアな隔離環境）での動作を保証。
3. **拡張子フィルタとファイル収集の最適化 (PERF-01)**:
   - 対象: `codechecker/scanner/file_manager.py`
   - 内容: 解析対象拡張子のホワイトリスト化や走査深度制限により、巨大なログやバイナリデータファイルの走査を早期除外してスキャン速度を向上。
4. **バイナリ指摘時の「エディタで開く」制御 (UX-01)**:
   - 対象: `web/js/app.js`, `codechecker/api.py`
   - 内容: PE バイナリ由来の指摘（`source == 'pe-binary'`）については「エディタで開く」ボタンを非活性（またはバイナリビューア案内）とし、エディタでの文字化け表示を防止。
5. **コードプレビューのハイライト言語自動切替 (UX-02)**:
   - 対象: `web/index.html`, `web/js/app.js`
   - 内容: 現在 `language-python` 固定となっているシンタックスハイライトを、対象ファイルの拡張子（`.js`, `.c`, `.cpp`, `.java`, `.go` 等）に応じて動的切り替え。

---

## 5. 検証手順まとめ

1. **自動テストスイートの全件 PASS 確認**:
   ```bash
   python -m unittest discover -s tests -v
   ```
   （29 tests 全件 OK）
2. **単一ファイルの元パス保持確認**:
   - `tests/sample_target/vulnerable_app.py` スキャン時に `is_temp == False` かつ `full_path` が実パスであることを確認。
3. **リリースパッケージ生成**:
   ```bash
   python scripts/build_release.py
   ```
