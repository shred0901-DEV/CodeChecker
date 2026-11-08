import requests
from typing import Dict, Any, List
from .base import BaseLLMProvider
from .prompts import create_remediation_prompt

class OllamaProvider(BaseLLMProvider):
    """Ollama ローカルLLMサーバー連携プロバイダ"""

    def __init__(self, host: str = "http://localhost:11434", model_name: str = "gemma4:12b-it-q4_K_M"):
        self.host = host.rstrip("/")
        self.model_name = model_name

    def is_available(self) -> bool:
        """Ollama サーバーが起動しているか確認"""
        try:
            res = requests.get(f"{self.host}/api/tags", timeout=3)
            return res.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """利用可能なモデル一覧を取得"""
        try:
            res = requests.get(f"{self.host}/api/tags", timeout=3)
            if res.status_code == 200:
                data = res.json()
                return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception:
            pass
        return []

    def generate_explanation(self, finding: Dict[str, Any], context_code: str) -> str:
        """Ollama API を呼び出して解説・修正提案を生成"""
        prompt = create_remediation_prompt(finding, context_code)

        try:
            res = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": -1  # 途切れを防止 (モデル完了EOSまで完全出力)
                    }
                },
                timeout=240
            )
            if res.status_code == 200:
                data = res.json()
                return data.get("response", "").strip()
            else:
                return f"**[Ollama エラー]** HTTP {res.status_code}: {res.text}"
        except requests.exceptions.Timeout:
            return "**[タイムアウト]** Ollama からの応答がタイムアウトしました (240秒)。モデルの初回読み込みに時間がかかった可能性があります。モデル展開完了後は高速に応答しますので、右上の「AI解説を再生成」を押して再試行してください。"
        except Exception as e:
            return f"**[Ollama 通信エラー]** {str(e)}\n\nOllama サーバー (`{self.host}`) が起動しているかご確認ください。"

    def unload_model(self):
        """Ollama にロードされているモデルをアンロードし、VRAM/RAM を即座に解放する"""
        try:
            requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model_name,
                    "keep_alive": 0
                },
                timeout=5
            )
        except Exception:
            pass

