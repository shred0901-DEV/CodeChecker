# CodeChecker コード監査結果 & 作業引き継ぎ書 (AUDIT & HANDOVER)

本ドキュメントは、CodeChecker プロジェクト全体のコード監査結果、フェーズ別の改修完了状況、現在の到達点、および今後の配布パッケージ化に向けた検討事項をまとめた総括書です。

---

## 【重要】開発・運用作業ルール (WORKFLOW RULES)

1. **調査と作業実施の分離（事前調査ファースト）**:
   - **ユーザーからの明確な指示があるまでは調査・検証のみを実施し、勝手なコード改修・ファイル変更等の作業実施は行わない。**
   - 不具合や課題発生時は、原因調査・メカニズム特定・改修方針の策定を行い、ユーザーに報告して指示・承認を得てから実装に着手する。
2. **Git コミットおよびリモートプッシュの運用ルール**:
   - **エージェントはローカルコミット（`git commit`）のみを実施し、リモートへのプッシュ（`git push`）は行わない。**
   - GitHub リモートリポジトリ（`origin/main`）へのプッシュは、ユーザー自身がコミット内容を確認のうえ手動で実施する。
   - 詳細は `docs/WORKFLOW_RULES.md` を参照。

---

## 1. プロジェクト概要と開発進捗総括

CodeChecker は、ソースコードおよび Windows PE バイナリ（EXE/DLL）のセキュリティ脆弱性を静的解析（Built-in ルール / Semgrep / pefile）で検出し、LLM（Ollama / Codex CLI）と連携して日本語の解説と修正提案を提示する完全オフライン・ポータブル対応のデスクトップアプリケーション（PyWebView / Python 3.10+）です。

### 全フェーズ完了ステータス (全改修完了・テスト100%合格)

- **Phase 1（即時対応 & 規約対応）**: **【完了済 (Completed)】**
  - **BUG-01**: 重複排除キーの改修により、バイナリ全指摘（15件）の完全出力に成功。
  - **SEC-01**: AI 解説描画部での DOMPurify サニタイズ適用による XSS 脆弱性の排除。
  - **SEC-02**: `cli_provider.py` の `shell=True` を廃止し、引数リスト形式の安全な `shell=False` 実行へ改修。
  - **BUG-02**: HTML レポート出力時に AI 解説・修正提案を含めるように改修。
  - **CLI-01**: 規約上使用不可の 3大CLI（Gemini, Antigravity, Claude）を全削除し、「Ollama」「Codex CLI」「AI無効」に集約。
- **Phase 2（短期改善推奨）**: **【完了済 (Completed)】**
  - **TST-01**: Python 標準 `unittest` に準拠した包括的テストスイートを構築。
  - **BUG-03**: 単一ファイルスキャン時にコピーを廃止して元の実パスを保持し、「エディタで開く」連携を正常化。
  - **RES-01**: スキャン開始時の一時フォルダ安全解放と `cleanup_all_temp` により、`.temp/` 内のリソース蓄積（リーク）を完全防止。
  - **BUG-04**: 内蔵コマンド実行ルール（`builtin-cmdi-system`）の正規表現を改善し、リスト引数（配列渡し）の安全な呼び出しを誤検知除外。
  - **BUG-05**: 進捗通知（`on_progress`）で `json.dumps` による完全エスケープを適用し、JS 構文エラーを防止。
- **Phase 3（中長期改善）**: **【完了済 (Completed)】**
  - **SEC-03**: ZIP 展開処理における Zip Bomb 防御（展開サイズ200MB / ファイル数1,000件 / 異常圧縮比率 / 実ストリーム二重検査）を実装。
  - **ARC-01**: 外部 CDN アセット（Tailwind, FontAwesome, Prism, Marked, DOMPurify）をローカルバンドル化し、閉域網・完全オフライン対応を達成。
  - **PERF-01**: 対象プログラミング言語の拡張子ホワイトリスト導入により、巨大データファイルやログの走査を排除し高速化。
  - **UX-01**: PE バイナリ指摘時の「ファイルの場所を開く」機能（OS エクスプローラー連携）を実装し、エディタでの文字化けを防止。
  - **UX-02**: 対象ファイルの拡張子に応じた Prism シンタックスハイライト言語の動的自動切替を実装。
  - **BUG-06**: Prism 依存読み込み順の修正によるスクリプト例外の完全解消。
- **SEC-CLI（Codex CLI セキュリティ多層防御）**: **【完了済 (Completed)】**
  - `--sandbox read-only` による書き込み・シェル実行の強制遮断。
  - `--ephemeral` によるセッション履歴のディスク残存防止。
  - `cwd = .temp/cli_sandbox/`（空の独立ディレクトリ）による CodeChecker 本体のファイル探索遮断。
  - プロンプトでのツール実行禁止制約の徹底。
- **全件ユニットテスト検証**: **【40/40 PASS (100%)】**
  - `python -m unittest discover -s tests -v`: 全40テストが 0.20秒で成功（エラー 0 / 失敗 0）。

---

## 2. 課題一覧と最終対応ステータス

| ID | 優先度 | 区分 | 対象ファイル | 概要 | 最終ステータス |
|---|---|---|---|---|:---:|
| **BUG-01** | **Critical** | バグ | `scanner/engine.py` | 重複排除ロジックの不備により、同一行の指摘がロストする | **完了 (Phase 1)** |
| **SEC-01** | **High** | セキュリティ | `web/js/app.js` | AI解説描画時のサニタイズ欠如による XSS 脆弱性 | **完了 (Phase 1)** |
| **SEC-02** | **High** | セキュリティ | `ai/cli_provider.py` | CLI 実行時の `shell=True` による OS コマンドインジェクションリスク | **完了 (Phase 1)** |
| **BUG-02** | **High** | バグ | `codechecker/api.py` | HTML レポートエクスポート時に AI 解説の出力処理が欠落している | **完了 (Phase 1)** |
| **CLI-01** | **High** | 規約遵守 | 全般 | 規約上使用不可となった Gemini / Antigravity / Claude CLI の残存 | **完了 (Phase 1)** |
| **TST-01** | **High** | 品質管理 | `tests/` 全般 | 標準 `unittest` による包括的自動テストスイートの構築 | **完了 (Phase 2)** |
| **BUG-03** | **Medium** | バグ | `scanner/file_manager.py`<br>`codechecker/api.py` | 単一ファイルスキャン時に一時コピー先のパスが記録され元ファイルを開けない | **完了 (Phase 2)** |
| **RES-01** | **Medium** | 資源管理 | `scanner/engine.py`<br>`file_manager.py` | 複数回スキャン実行時に `.temp/` 内の一時フォルダが蓄積し続ける | **完了 (Phase 2)** |
| **BUG-04** | **Medium** | 誤検知 | `scanner/builtin_rules.py` | コマンド実行ルールで推奨のリスト配列渡しが誤検知される | **完了 (Phase 2)** |
| **BUG-05** | **Low** | バグ | `codechecker/api.py` | `on_progress` 内の文字列エスケープ不備による JS 構文エラーリスク | **完了 (Phase 2)** |
| **SEC-03** | **Medium** | セキュリティ | `scanner/file_manager.py` | ZIP 展開処理における Zip Bomb（展開サイズ・ファイル数爆発）防御 | **完了 (Phase 3)** |
| **ARC-01** | **Medium** | 閉域網対応 | `web/index.html`<br>`web/vendor/` | 外部 CDN 全廃とローカルバンドル化（完全オフライン・閉域網動作） | **完了 (Phase 3)** |
| **PERF-01**| **Medium** | 性能改善 | `scanner/file_manager.py` | 拡張子ホワイトリスト導入による不要データ・ログ除外とスキャン高速化 | **完了 (Phase 3)** |
| **UX-01** | **Enhancement** | 操作性 | `web/js/app.js`<br>`codechecker/api.py` | バイナリ指摘時の「ファイルの場所を開く」（OSエクスプローラー連携） | **完了 (Phase 3)** |
| **UX-02** | **Enhancement** | 操作性 | `web/index.html`<br>`web/js/app.js` | コードプレビュー欄のシンタックスハイライト言語自動切替 | **完了 (Phase 3)** |
| **BUG-06** | **High** | バグ | `web/index.html`<br>`web/js/app.js` | Prism依存読み込み順序に起因するAI解説描画停止の解消 | **完了 (Phase 3)** |
| **SEC-CLI**| **High** | セキュリティ | `ai/cli_provider.py`<br>`prompts.py` | Codex CLI における読み取り専用サンドボックス・一時セッション・隔離作業ディレクトリ | **完了 (SEC-CLI)** |

---

## 3. 配布パッケージ化に向けた検討事項（今後のロードマップ）

開発フェーズの区切りを迎え、今後は第三者や社内環境へ安全かつ手軽に配布可能なパッケージ化の検討・検証に進みます。

### 検討アプローチの比較

| 方式 | 概要 | メリット | デメリット / 考慮点 |
| :--- | :--- | :--- | :--- |
| **① ポータブル版（現行拡張）**<br>`scripts/build_release.py` | Pythonインストール済み環境向けの配布パッケージ（`run.bat` / `setup.bat` 同梱） | ・コード変更が不要で軽量<br・構造が透過的で保守性が高い | ・ユーザーPCに Python 3.10+ が必要 |
| **② 単一実行ファイル化 (PyInstaller / Nuitka)** | Pythonインタプリタおよび全依存パッケージを `.exe` にパッケージング | ・ユーザー側での Python インストールが不要<br>・ダブルクリックだけで即起動 | ・アンチウイルスソフト（EDR/Windows Defender）による誤検知対策が必要<br>・Semgrep CLIバイナリやルール定義の同梱パス解決の検証が必要 |
| **③ 組み込みPython（Embedded Python）同梱型** | Windows用公式 Embeddable Python を `python/` フォルダに同梱してZIP配布 | ・Python事前インストール不要<br>・PyInstaller特有の誤検知や解凍オーバーヘッドを回避可能<br>・完全ポータブルで最も安定 | ・配布パッケージ容量が約50MB〜80MB程度増加する |

### パッケージ化における技術検証チェックリスト
1. **Semgrep のバンドル性**:
   - Semgrep がPythonパッケージ版またはスタンドアロンバイナリとして配布先で外部接続なしに動作するか。
2. **Microsoft Edge WebView2 ランタイム**:
   - Windows 10/11 に標準搭載されている WebView2 の依存確認（未導入環境でのフォールバック案内）。
3. **PEバイナリ診断（`pefile`）**:
   - パッケージ化後もWindows PE解析が自己完結して動作することの確認。
4. **Ollama / Codex CLI の外部ツール連携**:
   - 配布パッケージ内からローカルの `localhost:11434` や環境変数の `codex` コマンドが問題なく呼び出せることの確認。
