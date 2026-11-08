import os
import unittest
from unittest.mock import patch, MagicMock
from codechecker.api import AppAPI

class TestAppAPI(unittest.TestCase):
    """PyWebView APIブリッジ & UX機能テスト (UX-01, BUG-03)"""

    def setUp(self):
        self.api = AppAPI()
        self.sample_exe = os.path.abspath("samples/sample_vulnerable.exe")
        self.sample_py = os.path.abspath("tests/sample_target/vulnerable_app.py")

    def tearDown(self):
        self.api.engine.cleanup()

    @patch("subprocess.Popen")
    def test_open_file_location_success(self, mock_popen):
        """open_file_location で既存ファイルの場所を開く処理が成功すること (UX-01)"""
        if not os.path.exists(self.sample_exe):
            self.skipTest(f"サンプルEXEが存在しません: {self.sample_exe}")

        res = self.api.open_file_location(self.sample_exe)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], self.sample_exe)
        self.assertEqual(res["file_name"], os.path.basename(self.sample_exe))
        self.assertEqual(res["directory"], os.path.dirname(self.sample_exe))
        mock_popen.assert_called_once()

    def test_open_file_location_not_found(self):
        """存在しないファイルパス指定時に安全にエラーを返すこと"""
        res = self.api.open_file_location("C:/non_existent_folder/file.exe")
        self.assertFalse(res["success"])
        self.assertIn("見つかりませんでした", res["error"])

    @patch("codechecker.api.AppAPI.open_file_location")
    def test_open_source_file_delegates_binary_to_location(self, mock_open_loc):
        """open_source_file にEXE/DLLが指定された場合、自動的に open_file_location へ委譲すること (UX-01)"""
        if not os.path.exists(self.sample_exe):
            self.skipTest(f"サンプルEXEが存在しません: {self.sample_exe}")

        mock_open_loc.return_value = {"success": True, "path": self.sample_exe}
        res = self.api.open_source_file(self.sample_exe)
        mock_open_loc.assert_called_once_with(self.sample_exe)
        self.assertTrue(res["success"])

if __name__ == "__main__":
    unittest.main()
