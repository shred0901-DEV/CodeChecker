import os
import re
import unittest

class TestWebOffline(unittest.TestCase):
    """外部CDN完全排除 & ローカルバンドル検証テスト (ARC-01)"""

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.web_dir = os.path.join(self.base_dir, "web")
        self.index_html = os.path.join(self.web_dir, "index.html")

    def test_no_external_cdn_in_index_html(self):
        """index.html の script/link タグに外部CDN(http/https)が存在しないこと"""
        self.assertTrue(os.path.exists(self.index_html), "index.html が存在しません")

        with open(self.index_html, "r", encoding="utf-8") as f:
            content = f.read()

        # <script src="..."> および <link rel="stylesheet" href="..."> を抽出
        script_srcs = re.findall(r'<script\s+[^>]*src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        link_hrefs = re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\']', content, re.IGNORECASE)

        all_refs = script_srcs + link_hrefs
        for ref in all_refs:
            self.assertFalse(
                ref.startswith("http://") or ref.startswith("https://") or ref.startswith("//"),
                f"外部CDNへの参照が残存しています: {ref}"
            )

    def test_all_local_vendor_assets_exist(self):
        """index.html で参照されているローカルアセットが全て存在し、正常なサイズであること"""
        with open(self.index_html, "r", encoding="utf-8") as f:
            content = f.read()

        script_srcs = re.findall(r'<script\s+[^>]*src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        link_hrefs = re.findall(r'<link\s+[^>]*href=["\']([^"\']+)["\']', content, re.IGNORECASE)

        all_refs = script_srcs + link_hrefs
        for ref in all_refs:
            clean_ref = ref.split("?")[0].split("#")[0]
            local_path = os.path.normpath(os.path.join(self.web_dir, clean_ref))
            self.assertTrue(os.path.exists(local_path), f"参照先ローカルアセットが見つかりません: {ref} -> {local_path}")
            self.assertGreater(os.path.getsize(local_path), 0, f"アセットが空ファイルです: {local_path}")

    def test_fontawesome_webfonts_exist(self):
        """FontAwesomeのCSSが参照するフォントファイルが全て存在すること"""
        webfonts_dir = os.path.join(self.web_dir, "vendor", "fontawesome", "webfonts")
        self.assertTrue(os.path.isdir(webfonts_dir))

        expected_fonts = [
            "fa-solid-900.woff2",
            "fa-solid-900.ttf",
            "fa-regular-400.woff2",
            "fa-regular-400.ttf",
            "fa-brands-400.woff2",
            "fa-brands-400.ttf"
        ]
        for font_name in expected_fonts:
            font_path = os.path.join(webfonts_dir, font_name)
            self.assertTrue(os.path.exists(font_path), f"フォントファイルが存在しません: {font_name}")
            self.assertGreater(os.path.getsize(font_path), 1024, f"フォントファイルが不正です: {font_name}")

if __name__ == "__main__":
    unittest.main()
