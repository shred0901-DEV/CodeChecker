import unittest
from unittest.mock import patch, MagicMock
from codechecker.ai.api_providers import (
    BaseAPIProvider, OpenAIProvider, AnthropicProvider, GeminiProvider
)
from codechecker.ai.manager import AIManager

class TestAPIProviders(unittest.TestCase):
    """公式 AI API プロバイダの単体テスト"""

    def setUp(self):
        self.ai = AIManager()

    def tearDown(self):
        self.ai.clear_cache()

    def test_provider_availability(self):
        """APIキーの有無による利用可能状態の判定"""
        openai_p = OpenAIProvider(api_key="")
        self.assertFalse(openai_p.is_available())

        openai_p.api_key = "sk-test123456"
        self.assertTrue(openai_p.is_available())

    def test_provider_switching_apis(self):
        """ChatGPT / Claude / Gemini へのプロバイダ切り替え"""
        for prov in ["chatgpt", "claude", "gemini"]:
            self.ai.set_provider(prov, save=False)
            self.assertEqual(self.ai.active_provider, prov)

    def test_status_contains_apis(self):
        """get_status() に apis セクションが含まれていること"""
        status = self.ai.get_status()
        self.assertIn("apis", status)
        self.assertIn("chatgpt", status["apis"])
        self.assertIn("claude", status["apis"])
        self.assertIn("gemini", status["apis"])

    @patch("requests.post")
    def test_openai_provider_request(self, mock_post):
        """OpenAIProvider のリクエスト形式とレスポンス抽出の検証"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "OpenAI脆弱性解説"}}]
        }
        mock_post.return_value = mock_resp

        provider = OpenAIProvider(api_key="sk-openai-key", model_name="gpt-4o-mini")
        res = provider.generate_explanation({"title": "XSS", "id": "1"}, "code snippet")
        self.assertEqual(res, "OpenAI脆弱性解説")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-openai-key")
        self.assertEqual(kwargs["json"]["model"], "gpt-4o-mini")

    @patch("requests.post")
    def test_anthropic_provider_request(self, mock_post):
        """AnthropicProvider のリクエスト形式とレスポンス抽出の検証"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"text": "Claude脆弱性解説"}]
        }
        mock_post.return_value = mock_resp

        provider = AnthropicProvider(api_key="sk-ant-key", model_name="claude-3-7-sonnet-20250219")
        res = provider.generate_explanation({"title": "SQLi", "id": "2"}, "code snippet")
        self.assertEqual(res, "Claude脆弱性解説")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["x-api-key"], "sk-ant-key")
        self.assertEqual(kwargs["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(kwargs["json"]["model"], "claude-3-7-sonnet-20250219")
        self.assertIn("max_tokens", kwargs["json"])

    @patch("requests.post")
    def test_gemini_provider_request(self, mock_post):
        """GeminiProvider のリクエスト形式とレスポンス抽出の検証"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Gemini脆弱性解説"}]}}
            ]
        }
        mock_post.return_value = mock_resp

        provider = GeminiProvider(api_key="AIzaSyTestKey", model_name="gemini-3.8-flash")
        res = provider.generate_explanation({"title": "RCE", "id": "3"}, "code snippet")
        self.assertEqual(res, "Gemini脆弱性解説")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "AIzaSyTestKey")
        self.assertIn("gemini-3.8-flash", args[0])

    def test_api_key_masking(self):
        """APIキーがステータス取得時に適切にマスキングされること"""
        self.ai.update_api_settings("chatgpt", api_key="sk-1234567890abcdef", save=False)
        status = self.ai.get_status()
        masked = status["apis"]["chatgpt"]["masked_key"]
        self.assertTrue(masked.startswith("sk-1"))
        self.assertTrue(masked.endswith("cdef"))
        self.assertIn("...", masked)

if __name__ == "__main__":
    unittest.main()
