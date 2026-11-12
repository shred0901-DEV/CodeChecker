import requests
from typing import Dict, Any, List, Optional
from .base import BaseLLMProvider
from .prompts import create_remediation_prompt

DEFAULT_SYSTEM_PROMPT = "あなたはセキュリティ専門家です。静的解析ツールの指摘情報に対して、簡潔で実用的なMarkdown形式の日本語解説と修正提案を出力してください。"

class BaseAPIProvider(BaseLLMProvider):
    """クラウド REST API 共通基底プロバイダ (requests 直接呼び出し)"""

    def __init__(self, api_key: str = "", model_name: str = "", timeout: int = 60):
        self.api_key = (api_key or "").strip()
        self.model_name = (model_name or "").strip()
        self.timeout = timeout

    def is_available(self) -> bool:
        """APIキーが設定されているか確認"""
        return bool(self.api_key)

    def list_models(self) -> List[str]:
        return getattr(self, "DEFAULT_MODELS", [])

    def test_connection(self) -> Dict[str, Any]:
        """接続確認テスト（軽量なpingリクエスト）"""
        if not self.is_available():
            return {
                "success": False,
                "message": "APIキーが設定されていません。設定画面でAPIキーを入力してください。"
            }
        try:
            test_prompt = "Hello"
            res = self._send_request(test_prompt, system_prompt="Respond with 'OK'")
            return {
                "success": True,
                "message": f"接続成功 (モデル: {self.model_name or self.list_models()[0]})\n応答: {res[:50].strip()}"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": f"接続タイムアウト: サーバーからの応答が制限時間 ({self.timeout}秒) を超えました。"
            }
        except requests.exceptions.HTTPError as e:
            err_msg = self._format_http_error(e)
            return {
                "success": False,
                "message": err_msg
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"通信エラー: {str(e)}"
            }

    def generate_explanation(self, finding: Dict[str, Any], context_code: str) -> str:
        """脆弱性情報と周辺コードを受け取り、Markdown形式の解説・修正提案を生成"""
        if not self.is_available():
            return f"**[{self.__class__.__name__} 設定エラー]** APIキーが設定されていません。右上の歯車アイコン（設定）からAPIキーを入力してください。"

        prompt = create_remediation_prompt(finding, context_code)
        try:
            return self._send_request(prompt, system_prompt=DEFAULT_SYSTEM_PROMPT)
        except requests.exceptions.Timeout:
            return f"**[タイムアウト]** {self.__class__.__name__} からの応答がタイムアウトしました ({self.timeout}秒)。右上の「AI解説を再生成」を押して再試行してください。"
        except requests.exceptions.HTTPError as e:
            return self._format_http_error(e)
        except Exception as e:
            return f"**[{self.__class__.__name__} 通信エラー]** {str(e)}"

    def _format_http_error(self, e: requests.exceptions.HTTPError) -> str:
        """HTTPエラーコードに応じた親切なエラーメッセージ整形"""
        status = e.response.status_code if e.response is not None else 0
        detail = ""
        try:
            err_json = e.response.json()
            if isinstance(err_json, dict):
                # OpenAI / Anthropic / Gemini 各社のエラー構造に対応
                if "error" in err_json:
                    err_obj = err_json["error"]
                    if isinstance(err_obj, dict):
                        detail = err_obj.get("message", str(err_obj))
                    else:
                        detail = str(err_obj)
                elif "message" in err_json:
                    detail = err_json["message"]
        except Exception:
            detail = e.response.text[:200] if e.response is not None else ""

        if status in (401, 403):
            return f"**[認証エラー (HTTP {status})]** APIキーが無効であるか、アクセス権限がありません。\n設定画面でAPIキーをご確認ください。\n> {detail}"
        elif status == 429:
            return f"**[利用制限 (HTTP 429)]** クォータ上限またはレートリミットに達しました。\nアカウントの残高・請求設定または利用上限をご確認ください。\n> {detail}"
        elif status >= 500:
            return f"**[サーバーエラー (HTTP {status})]** AIプロバイダ側で一時的なサーバー障害が発生しています。\n> {detail}"
        return f"**[API エラー (HTTP {status})]** {detail or e}"

    def _send_request(self, user_prompt: str, system_prompt: str) -> str:
        """各プロバイダ固有のHTTP呼び出し (オーバーライド必須)"""
        raise NotImplementedError


class OpenAIProvider(BaseAPIProvider):
    """ChatGPT API (OpenAI 公式) プロバイダ"""
    ENDPOINT = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODELS = ["gpt-4o-mini", "gpt-4o", "o3-mini"]

    def _send_request(self, user_prompt: str, system_prompt: str) -> str:
        model = self.model_name or "gpt-4o-mini"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        is_reasoning_model = model.startswith(("o1", "o3"))
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system" if not is_reasoning_model else "user", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        # 推論モデル (o1, o3-mini) は temperature 非対応の場合がある
        if not is_reasoning_model:
            payload["temperature"] = 0.2

        res = requests.post(self.ENDPOINT, headers=headers, json=payload, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()


class AnthropicProvider(BaseAPIProvider):
    """Claude API (Anthropic 公式) プロバイダ"""
    ENDPOINT = "https://api.anthropic.com/v1/messages"
    DEFAULT_MODELS = ["claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"]

    def _send_request(self, user_prompt: str, system_prompt: str) -> str:
        model = self.model_name or "claude-3-7-sonnet-20250219"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        res = requests.post(self.ENDPOINT, headers=headers, json=payload, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        return data["content"][0]["text"].strip()


class GeminiProvider(BaseAPIProvider):
    """Gemini API (Google 公式) プロバイダ"""
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODELS = ["gemini-3.8-flash", "gemini-3.8-pro", "gemini-2.5-flash"]

    def _send_request(self, user_prompt: str, system_prompt: str) -> str:
        model = self.model_name or "gemini-3.8-flash"
        url = f"{self.BASE_URL}/{model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        }
        res = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"].strip()
        return ""
