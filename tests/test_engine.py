import os
import unittest
from codechecker.scanner.engine import ScanEngine
from codechecker.scanner.file_manager import get_temp_dir

class TestScanEngine(unittest.TestCase):
    """統合スキャンエンジンの結合・単体テスト (TST-01, BUG-01, BUG-03, RES-01)"""

    def setUp(self):
        self.engine = ScanEngine(use_semgrep=False)  # CI/単体テストの高速安定化のためsemgrepはオフ
        self.sample_dir = os.path.abspath("tests/sample_target")
        self.sample_zip = os.path.abspath("tests/sample_target.zip")
        self.sample_py = os.path.abspath("tests/sample_target/vulnerable_app.py")
        self.sample_exe = os.path.abspath("samples/sample_vulnerable.exe")

    def tearDown(self):
        self.engine.cleanup()

    # ==========================================================
    # 1. ソースコードフォルダスキャン
    # ==========================================================
    def test_scan_directory(self):
        """ディレクトリ指定での正常スキャンとサマリー集計"""
        results = self.engine.scan(self.sample_dir)
        self.assertIn("summary", results)
        self.assertIn("findings", results)
        self.assertFalse(results["is_temp"])

        summary = results["summary"]
        self.assertGreater(summary["total"], 0)
        self.assertGreaterEqual(summary["high"], 1)

    # ==========================================================
    # 2. 単一ファイルスキャン時の元パス保持 (BUG-03)
    # ==========================================================
    def test_scan_single_file_preserves_path(self):
        """単一ファイルスキャン時に一時コピーでなく、元の実ファイルパスを記録すること (BUG-03)"""
        results = self.engine.scan(self.sample_py)
        self.assertFalse(results["is_temp"])
        self.assertEqual(results["target_path"], self.sample_py)

        findings = results["findings"]
        self.assertGreater(len(findings), 0)

        for f in findings:
            # full_path が元の実ファイルパスそのものであること
            self.assertEqual(os.path.abspath(f["full_path"]), self.sample_py)
            # 相対パス表記がファイル名であること
            self.assertEqual(f["file"], os.path.basename(self.sample_py))

    # ==========================================================
    # 3. ZIPファイルスキャン
    # ==========================================================
    def test_scan_zip_file(self):
        """ZIPアーカイブのスキャンと一時フォルダ識別"""
        results = self.engine.scan(self.sample_zip)
        self.assertTrue(results["is_temp"])
        self.assertGreater(results["summary"]["total"], 0)

    # ==========================================================
    # 4. PEバイナリスキャン & 重複排除 (BUG-01)
    # ==========================================================
    def test_pe_binary_scan_full_findings(self):
        """PEバイナリ診断で同一行指摘がロストせず全件 (15件) 検出されること (BUG-01)"""
        if not os.path.exists(self.sample_exe):
            self.skipTest(f"サンプルバイナリが存在しません: {self.sample_exe}")

        results = self.engine.scan(self.sample_exe)
        findings = results["findings"]

        # sample_vulnerable.exe の指摘件数は15件
        self.assertGreaterEqual(len(findings), 15, f"PE指摘件数が不足しています: {len(findings)}件")

        # PE指摘の source が 'pe-binary' であること
        pe_findings = [f for f in findings if f.get("source") == "pe-binary"]
        self.assertGreaterEqual(len(pe_findings), 15)

    # ==========================================================
    # 5. CWE 日本語タイトルの補完
    # ==========================================================
    def test_cwe_title_localization(self):
        """Semgrep等からの指摘に対し、CWE辞書による日本語タイトルが付与されること"""
        dummy_findings = [
            {
                "id": "semgrep-1",
                "rule_id": "generic.sql.injection",
                "title": "SQL Injection Warning",
                "severity": "HIGH",
                "cwe": "CWE-89: SQL Injection",
                "file": "test.py",
                "full_path": "test.py",
                "line": 10,
                "source": "semgrep"
            }
        ]
        localized = self.engine._deduplicate_and_localize(dummy_findings)
        self.assertEqual(len(localized), 1)
        self.assertIn("SQLインジェクションの脆弱性", localized[0]["title"])

    # ==========================================================
    # 6. 一時フォルダのリソースリーク防止 (RES-01)
    # ==========================================================
    def test_consecutive_scans_prevent_temp_leak(self):
        """連続してZIPスキャンを実行した際、直前の一時ディレクトリが削除され1件のみ維持されること (RES-01)"""
        temp_root = get_temp_dir()

        # 1回目のスキャン
        self.engine.scan(self.sample_zip)
        zip_dirs_1 = [d for d in os.listdir(temp_root) if d.startswith("zip_")]
        self.assertEqual(len(zip_dirs_1), 1, "1回目のスキャン後の一時ディレクトリ数が1ではありません")

        # 2回目のスキャン (直前の zip ディレクトリが破棄され、新しいものに置換される)
        self.engine.scan(self.sample_zip)
        zip_dirs_2 = [d for d in os.listdir(temp_root) if d.startswith("zip_")]
        self.assertEqual(len(zip_dirs_2), 1, "2回目のスキャン後に古い一時ディレクトリがリークしています")

if __name__ == "__main__":
    unittest.main()
