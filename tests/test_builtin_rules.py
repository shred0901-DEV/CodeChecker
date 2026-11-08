import unittest
import os
import tempfile
from codechecker.scanner.builtin_rules import BuiltinScanner, PATTERNS

class TestBuiltinRules(unittest.TestCase):
    """内蔵脆弱性検出ルールの単体テスト (TST-01, BUG-04)"""

    def setUp(self):
        self.scanner = BuiltinScanner()
        self.rules_by_id = {r["id"]: r for r in PATTERNS}

    def _match_rule(self, rule_id: str, line: str) -> bool:
        rule = self.rules_by_id[rule_id]
        return bool(rule["regex"].search(line))

    # ==========================================================
    # 1. コマンドインジェクション (BUG-04 & CWE-78)
    # ==========================================================
    def test_cmdi_safe_list_arguments_excluded(self):
        """引数が安全なリスト形式（配列渡し）の場合に誤検知されないこと (BUG-04)"""
        safe_lines = [
            'subprocess.Popen(["cmd", "arg"])',
            'subprocess.Popen(["ls", "-la", target_dir])',
            'subprocess.run(["git", "status"])',
            'subprocess.run(["pytest", "-v"])',
            'subprocess.call(["curl", "-s", url])',
            'subprocess.check_call(["npm", "test"])',
            'subprocess.check_output(["whoami"])',
        ]
        for line in safe_lines:
            with self.subTest(line=line):
                self.assertFalse(
                    self._match_rule("builtin-cmdi-system", line),
                    f"安全なリスト引数が誤検知されました: {line}"
                )

    def test_cmdi_safe_static_strings_excluded(self):
        """固定の単一文字列引数の場合に誤検知されないこと"""
        safe_lines = [
            'os.system("ls -l")',
            'os.system("clear")',
            'system("cls")',
            'subprocess.call("uptime")',
        ]
        for line in safe_lines:
            with self.subTest(line=line):
                self.assertFalse(
                    self._match_rule("builtin-cmdi-system", line),
                    f"安全な固定文字列コマンドが誤検知されました: {line}"
                )

    def test_cmdi_dangerous_calls_detected(self):
        """変数結合や shell=True を伴う危険な呼び出しを正確に検知すること"""
        dangerous_lines = [
            'os.system("cat " + user_input)',
            'os.system(f"rm -rf {path}")',
            'subprocess.Popen("cmd " + arg, shell=True)',
            'subprocess.run("dir " + query, shell=True)',
            'subprocess.call(user_cmd, shell=True)',
            'shell_exec($user_input)',
            'execSync("git checkout " + branch)',
            'subprocess.Popen(["cmd", arg], shell=True)',
        ]
        for line in dangerous_lines:
            with self.subTest(line=line):
                self.assertTrue(
                    self._match_rule("builtin-cmdi-system", line),
                    f"危険なコマンド呼び出しが検知されませんでした: {line}"
                )

    # ==========================================================
    # 2. ハードコードされた秘密情報 (CWE-798, CWE-312, CWE-259)
    # ==========================================================
    def test_secrets_aws_key_detected(self):
        """AWSアクセスキーのハードコードを検知"""
        line = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'
        self.assertTrue(self._match_rule("builtin-secrets-aws-key", line))

    def test_secrets_private_key_detected(self):
        """秘密鍵の直接記載を検知"""
        line = '-----BEGIN RSA PRIVATE KEY-----'
        self.assertTrue(self._match_rule("builtin-secrets-private-key", line))
        line_ec = '-----BEGIN EC PRIVATE KEY-----'
        self.assertTrue(self._match_rule("builtin-secrets-private-key", line_ec))

    def test_secrets_generic_api_key_detected(self):
        """一般的なAPIキーのハードコードを検知"""
        line = 'api_key = "abcdef1234567890abcdef"'
        self.assertTrue(self._match_rule("builtin-secrets-generic-api-key", line))

    def test_secrets_password_detected(self):
        """平文パスワードのハードコードを検知"""
        line = 'db_password = "supersecretpassword123"'
        self.assertTrue(self._match_rule("builtin-secrets-password", line))

    # ==========================================================
    # 3. SQL インジェクション (CWE-89)
    # ==========================================================
    def test_sqli_concatenation_detected(self):
        """文字列連結や f-string による動的 SQL 構築を検知"""
        lines = [
            'query = "SELECT * FROM users WHERE name = \'" + user_name + "\'"',
            'query = f"SELECT * FROM items WHERE id = {item_id}"',
            'query = "UPDATE accounts SET balance = %s" % new_balance',
            'query = "DELETE FROM logs WHERE date = {}".format(date_str)',
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertTrue(
                    self._match_rule("builtin-sqli-concat", line),
                    f"SQLiの兆候が検知されませんでした: {line}"
                )

    # ==========================================================
    # 4. 危険なコード実行 / デシリアライズ (CWE-95, CWE-502)
    # ==========================================================
    def test_rce_eval_detected(self):
        """動的な eval / exec を検知"""
        self.assertTrue(self._match_rule("builtin-rce-eval", 'eval(user_expression)'))
        self.assertTrue(self._match_rule("builtin-rce-eval", 'exec(dynamic_code)'))

    def test_deserialization_pickle_detected(self):
        """pickle.loads の安全でないデシリアライズを検知"""
        self.assertTrue(self._match_rule("builtin-deserialization-pickle", 'data = pickle.loads(untrusted_payload)'))

    def test_deserialization_yaml_safeloader(self):
        """SafeLoader を用いた安全な yaml.load は誤検知しないこと"""
        safe_line = 'yaml.load(payload, Loader=yaml.SafeLoader)'
        self.assertFalse(self._match_rule("builtin-deserialization-yaml", safe_line))

        dangerous_line = 'yaml.load(payload)'
        self.assertTrue(self._match_rule("builtin-deserialization-yaml", dangerous_line))

    # ==========================================================
    # 5. コメント行のスキップ検証
    # ==========================================================
    def test_comment_lines_skipped(self):
        """コメント行に書かれた脆弱パターンはスキップされること"""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", encoding="utf-8") as f:
            f.write("# eval(user_input)\n")
            f.write("// os.system('rm -rf ' + path)\n")
            f.write("/* AKIAIOSFODNN7EXAMPLE */\n")
            temp_path = f.name

        try:
            findings = self.scanner.scan_file(temp_path, os.path.dirname(temp_path))
            self.assertEqual(len(findings), 0, "コメント行が誤って検知されました")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
