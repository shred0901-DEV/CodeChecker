import os
import unittest
from codechecker.ai.manager import AIManager

class TestAIManager(unittest.TestCase):
    """AIマネージャーの単体テスト (TST-01, CLI-01)"""

    def setUp(self):
        self.ai = AIManager()

    def tearDown(self):
        self.ai.clear_cache()

    # ==========================================================
    # 1. 初期化とプロファイル取得 (CLI-01 規約検証含む)
    # ==========================================================
    def test_initial_status_and_cli_profiles(self):
        """ステータス取得と、許可されたCLI (Codex) のみの登録検証"""
        status = self.ai.get_status()
        self.assertIn("active_provider", status)
        self.assertIn("ollama", status)
        self.assertIn("clis", status)

        clis = status["clis"]
        self.assertIn("codex", clis, "Codex CLI がプロファイルに存在しません")

        # Phase 1 規約 CLI-01: 禁止された CLI が存在しないこと
        forbidden_clis = ["gemini", "antigravity", "claude"]
        for f in forbidden_clis:
            self.assertNotIn(f, clis, f"規約上使用不可の CLI ({f}) が残存しています")

    # ==========================================================
    # 2. プロバイダ切替
    # ==========================================================
    def test_provider_switching(self):
        """プロバイダの切り替えが正常に行えること"""
        # A. Codex CLI への切替
        self.ai.set_provider("codex")
        self.assertEqual(self.ai.active_provider, "codex")

        # B. AI無効 (disabled) への切替
        self.ai.set_provider("disabled")
        self.assertEqual(self.ai.active_provider, "disabled")

        # C. Ollama への切替
        self.ai.set_provider("ollama")
        self.assertEqual(self.ai.active_provider, "ollama")

        # D. 未知のプロバイダ指定時はデフォルト (ollama) にフォールバック
        self.ai.set_provider("unknown_provider_xyz")
        self.assertEqual(self.ai.active_provider, "ollama")

    # ==========================================================
    # 3. AI無効化モードの動作 (disabled)
    # ==========================================================
    def test_disabled_provider_explanation(self):
        """AI無効時 (disabled) は外部呼び出しを行わず、安全な案内メッセージを返すこと"""
        self.ai.set_provider("disabled")
        dummy_finding = {
            "id": "test-finding-1",
            "title": "ハードコードされたパスワード",
            "severity": "MEDIUM",
            "cwe": "CWE-259",
            "file": "config.py",
            "line": 5,
            "code": "password = 'secret'",
            "description": "平文パスワードの危険性"
        }
        res = self.ai.explain_finding(dummy_finding)
        self.assertIn("text", res)
        self.assertEqual(res["provider"], "disabled")
        self.assertIn("AI解説機能はオフになっています", res["text"])

    # ==========================================================
    # 4. キャッシュの動作
    # ==========================================================
    def test_cache_mechanism(self):
        """同一の指摘に対してキャッシュが機能し、clear_cache でリセットされること"""
        self.ai.set_provider("ollama")
        dummy_finding = {
            "id": "test-cache-id",
            "title": "SQL Injection",
            "severity": "HIGH",
            "cwe": "CWE-89",
            "file": "app.py",
            "line": 20,
            "code": "db.execute(query)"
        }
        current_model = self.ai.get_current_model_name()
        cache_key = f"ollama:{current_model}:{dummy_finding['id']}"

        # キャッシュにダミーデータを注入
        expected_result = {
            "text": "Cached AI explanation result",
            "provider": "ollama",
            "model": current_model
        }
        self.ai._cache[cache_key] = expected_result

        # キャッシュから即座に返却されること
        cached_res = self.ai.explain_finding(dummy_finding)
        self.assertEqual(cached_res["text"], "Cached AI explanation result")
        self.assertIn(cache_key, self.ai._cache)

        # キャッシュのクリア
        self.ai.clear_cache()
        self.assertEqual(len(self.ai._cache), 0)

    # ==========================================================
    # 5. Codex CLI のセキュリティ構成検証 (SEC-CLI)
    # ==========================================================
    def test_codex_cli_security_flags(self):
        """Codex CLI に読み取り専用サンドボックス & ephemeral フラグが設定・保証されていること"""
        status = self.ai.get_status()
        codex_profile = status["clis"].get("codex", {})
        command = codex_profile.get("command", "")

        # 読み取り専用サンドボックスの検証 (不必要なファイル書き込みやシェル実行の遮断)
        self.assertIn("--sandbox read-only", command, "Codex コマンドに --sandbox read-only が指定されていません")
        # セッション一時化の検証 (ディスクへの履歴残存防止)
        self.assertIn("--ephemeral", command, "Codex コマンドに --ephemeral が指定されていません")
        # 非対話実行 & Gitチェック除外の検証
        self.assertIn("exec", command)
        self.assertIn("--skip-git-repo-check", command)

    def test_codex_isolated_working_directory(self):
        """CLI実行時の作業ディレクトリがプロジェクトルートから隔離されていること"""
        cli_manager = self.ai.cli_manager
        isolated_cwd = cli_manager._get_isolated_cli_cwd()
        self.assertTrue(os.path.exists(isolated_cwd), "隔離作業ディレクトリが存在しません")
        # CodeChecker のルートと一致しないこと
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertNotEqual(os.path.abspath(isolated_cwd), os.path.abspath(app_dir), "作業ディレクトリがプロジェクトルートになっています")
        self.assertIn(".temp", isolated_cwd, "作業ディレクトリが .temp 配下に配置されていません")

if __name__ == "__main__":
    unittest.main()
