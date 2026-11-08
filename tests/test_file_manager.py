import os
import shutil
import tempfile
import unittest
import zipfile
from codechecker.scanner.file_manager import FileManager, get_temp_dir

class TestFileManager(unittest.TestCase):
    """ファイル管理 & 一時領域ライフサイクルテスト (TST-01, BUG-03, RES-01)"""

    def setUp(self):
        self.fm = FileManager()
        self.sample_py = os.path.abspath("tests/sample_target/vulnerable_app.py")
        self.sample_zip = os.path.abspath("tests/sample_target.zip")

    def tearDown(self):
        self.fm.cleanup()

    # ==========================================================
    # 1. 単一ファイルパスの保持 (BUG-03)
    # ==========================================================
    def test_single_file_preserves_original_path(self):
        """単一ファイル指定時はコピーせず、元の実ファイルパスを返すこと (BUG-03)"""
        scan_path, is_temp = self.fm.prepare_target(self.sample_py)
        self.assertEqual(scan_path, self.sample_py)
        self.assertFalse(is_temp, "単一ファイルスキャンで is_temp が True になっています")

    def test_collect_files_single_python_file(self):
        """単一Pythonファイル指定時にそのファイルのみを収集すること"""
        sources, pes = self.fm.collect_files(self.sample_py)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0], self.sample_py)
        self.assertEqual(len(pes), 0)

    def test_collect_files_single_pe_file(self):
        """単一EXEファイル指定時にそのファイルのみをPEバイナリとして収集すること"""
        sample_exe = os.path.abspath("samples/sample_vulnerable.exe")
        if os.path.exists(sample_exe):
            sources, pes = self.fm.collect_files(sample_exe)
            self.assertEqual(len(sources), 0)
            self.assertEqual(len(pes), 1)
            self.assertEqual(pes[0], sample_exe)

    # ==========================================================
    # 2. 安全な ZIP 解凍 (Zip Slip 防御)
    # ==========================================================
    def test_zip_extraction_and_zip_slip_prevention(self):
        """正常なZIPの解凍と、Zip Slipパストラバーサルの防御"""
        # A. 正常なZIPの解凍
        target_dir, is_temp = self.fm.prepare_target(self.sample_zip)
        self.assertTrue(is_temp)
        self.assertTrue(os.path.isdir(target_dir))
        extracted_file = os.path.join(target_dir, "vulnerable_app.py")
        self.assertTrue(os.path.exists(extracted_file))

        # B. Zip Slip攻撃ZIPの安全なスキップ
        with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".zip") as tf:
            malicious_zip = tf.name

        try:
            with zipfile.ZipFile(malicious_zip, "w") as zf:
                zf.writestr("../../evil_escape.txt", "MALICIOUS")
                zf.writestr("normal.txt", "NORMAL")

            safe_out = self.fm.extract_zip_safely(malicious_zip)
            self.fm._temp_dirs.append(safe_out)

            # 正常ファイルのみ解凍され、上位階層へのトラバーサルファイルは存在しないこと
            self.assertTrue(os.path.exists(os.path.join(safe_out, "normal.txt")))
            parent_evil = os.path.abspath(os.path.join(safe_out, "..", "..", "evil_escape.txt"))
            self.assertFalse(os.path.exists(parent_evil), "Zip Slip による不正ファイル書き込みが発生しました")
        finally:
            if os.path.exists(malicious_zip):
                os.remove(malicious_zip)

    # ==========================================================
    # 3. 除外ディレクトリ判定
    # ==========================================================
    def test_excluded_directories(self):
        """除外対象ディレクトリ (.git, node_modules, __pycache__ 等) が無視されること"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 探索対象ファイル
            os.makedirs(os.path.join(temp_dir, "src"))
            good_file = os.path.join(temp_dir, "src", "app.py")
            with open(good_file, "w") as f:
                f.write("print('hello')\n")

            # 除外対象ディレクトリ
            for excluded in [".git", "node_modules", "__pycache__", ".venv"]:
                ex_path = os.path.join(temp_dir, excluded)
                os.makedirs(ex_path)
                with open(os.path.join(ex_path, "ignored.py"), "w") as f:
                    f.write("print('ignore me')\n")

            sources, _ = self.fm.collect_files(temp_dir)
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0], os.path.abspath(good_file))

    # ==========================================================
    # 4. 一時フォルダのクリーンアップ & リーク防止 (RES-01)
    # ==========================================================
    def test_cleanup_releases_temp_directories(self):
        """cleanup() 呼び出しで生成された一時フォルダが完全消去されること (RES-01)"""
        target_dir, is_temp = self.fm.prepare_target(self.sample_zip)
        self.assertTrue(os.path.exists(target_dir))

        self.fm.cleanup()
        self.assertFalse(os.path.exists(target_dir), "cleanup() 後も一時ディレクトリが残存しています")
        self.assertEqual(len(self.fm._temp_dirs), 0)

    def test_cleanup_all_temp(self):
        """cleanup_all_temp() で残存する zip_* フォルダが一括削除されること"""
        temp_root = get_temp_dir()
        dummy_zip_dir = os.path.join(temp_root, "zip_dummy12345")
        os.makedirs(dummy_zip_dir, exist_ok=True)
        with open(os.path.join(dummy_zip_dir, "test.txt"), "w") as f:
            f.write("dummy")

        self.assertTrue(os.path.exists(dummy_zip_dir))
        self.fm.cleanup_all_temp()
        self.assertFalse(os.path.exists(dummy_zip_dir))

if __name__ == "__main__":
    unittest.main()
