import os
import json
from typing import Dict, Any, List, Optional
from .ollama_provider import OllamaProvider
from .cli_provider import DedicatedCLIProvider
from .api_providers import OpenAIProvider, AnthropicProvider, GeminiProvider

def get_app_dir() -> str:
    """アプリケーションルートディレクトリの絶対パスを取得"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

class AIManager:
    """AI プロバイダ管理マネージャー (Ollama / Codex / ChatGPT API / Claude API / Antigravity Agent API / AI無効)"""

    def __init__(self):
        self.active_provider: str = "ollama"
        self.ollama = OllamaProvider()
        self.cli_manager = DedicatedCLIProvider()
        self.api_providers = {
            "chatgpt": OpenAIProvider(model_name="gpt-4o-mini"),
            "claude": AnthropicProvider(model_name="claude-3-7-sonnet-20250219"),
            "gemini": GeminiProvider(model_name="gemini-3.8-flash")
        }
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.settings_file = os.path.join(get_app_dir(), "settings.json")
        self.load_settings()

    def load_settings(self):
        """アプリ内 settings.json から設定を復元 (完全ポータブル設計)"""
        if not os.path.exists(self.settings_file):
            return
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "active_provider" in data:
                self.set_provider(data["active_provider"], save=False)
            if "ollama" in data:
                self.update_ollama_settings(
                    host=data["ollama"].get("host"),
                    model=data["ollama"].get("selected_model"),
                    save=False
                )
            if "clis" in data:
                for cli_id, cdata in data["clis"].items():
                    if "command" in cdata:
                        self.update_cli_command(cli_id, cdata["command"], save=False)
                    if "selected_model" in cdata:
                        self.set_cli_model(cli_id, cdata["selected_model"], save=False)
            if "apis" in data:
                for api_id, adata in data["apis"].items():
                    if api_id in self.api_providers:
                        self.update_api_settings(
                            api_id=api_id,
                            api_key=adata.get("api_key"),
                            model=adata.get("selected_model"),
                            save=False
                        )
        except Exception as e:
            print(f"[AIManager] settings.json 読み込み失敗: {e}")

    def save_settings(self):
        """アプリ内 settings.json に設定を自己完結保存"""
        try:
            data = {
                "active_provider": self.active_provider,
                "ollama": {
                    "host": self.ollama.host,
                    "selected_model": self.ollama.model_name
                },
                "clis": {
                    k: {
                        "command": v.get("command"),
                        "selected_model": v.get("selected_model", "default")
                    }
                    for k, v in self.cli_manager.profiles.items()
                },
                "apis": {
                    k: {
                        "api_key": v.api_key,
                        "selected_model": v.model_name or (v.list_models()[0] if v.list_models() else "")
                    }
                    for k, v in self.api_providers.items()
                }
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[AIManager] settings.json 保存失敗: {e}")

    def set_provider(self, provider_id: str, save: bool = True):
        valid_providers = ["ollama", "codex", "chatgpt", "claude", "gemini", "disabled"]
        if provider_id not in valid_providers:
            provider_id = "ollama"
        prev = self.active_provider
        self.active_provider = provider_id
        # Ollamaから他のプロバイダに切り替えた場合はVRAMを即時解放
        if prev == "ollama" and provider_id != "ollama":
            self.ollama.unload_model()
        if save:
            self.save_settings()

    def update_ollama_settings(self, host: Optional[str] = None, model: Optional[str] = None, save: bool = True):
        if host:
            self.ollama.host = host.rstrip("/")
        if model:
            self.ollama.model_name = model
        if save:
            self.save_settings()

    def update_cli_command(self, cli_id: str, command: str, save: bool = True):
        self.cli_manager.update_command(cli_id, command)
        if save:
            self.save_settings()

    def set_cli_model(self, cli_id: str, model_name: str, save: bool = True):
        self.cli_manager.set_model(cli_id, model_name)
        if save:
            self.save_settings()

    def update_api_settings(self, api_id: str, api_key: Optional[str] = None, model: Optional[str] = None, save: bool = True):
        """APIキーおよび使用モデルを更新"""
        if api_id in self.api_providers:
            prov = self.api_providers[api_id]
            if api_key is not None:
                # 前後の空白をトリム
                key_clean = api_key.strip()
                # フロントエンドからのマスキング文字列 ("sk-...****" や 空文字列など) で既存キーを誤上書きしない保護
                if key_clean and not key_clean.startswith(("••••", "****")):
                    prov.api_key = key_clean
            if model:
                prov.model_name = model.strip()
            if save:
                self.save_settings()

    def test_api(self, api_id: str) -> Dict[str, Any]:
        """指定のAPI接続テストを実行"""
        if api_id in self.api_providers:
            return self.api_providers[api_id].test_connection()
        return {"success": False, "message": f"未知のAPIプロバイダです: {api_id}"}

    def test_cli(self, cli_id: str) -> Dict[str, Any]:
        return self.cli_manager.test_cli(cli_id)

    def get_current_model_name(self) -> str:
        """現在選択されているプロバイダの使用中モデル名を返す"""
        if self.active_provider == "ollama":
            return self.ollama.model_name or "gemma4:12b-it-q4_K_M"
        elif self.active_provider in self.cli_manager.profiles:
            profile = self.cli_manager.profiles[self.active_provider]
            sel = profile.get("selected_model", "default")
            if sel == "default":
                detected = self.cli_manager.detect_default_model(self.active_provider)
                if detected:
                    return detected
            return sel
        elif self.active_provider in self.api_providers:
            prov = self.api_providers[self.active_provider]
            return prov.model_name or (prov.list_models()[0] if prov.list_models() else "default")
        return "N/A"

    def get_status(self) -> Dict[str, Any]:
        """各プロバイダの稼働状態とモデル選択状況を返す"""
        ollama_avail = self.ollama.is_available()
        ollama_models = self.ollama.list_models() if ollama_avail else []

        cli_profiles = self.cli_manager.get_all_profiles()

        api_profiles = {}
        for k, v in self.api_providers.items():
            masked = ""
            if v.api_key:
                masked = f"{v.api_key[:4]}...{v.api_key[-4:]}" if len(v.api_key) >= 10 else "••••••••"
            api_profiles[k] = {
                "available": v.is_available(),
                "selected_model": v.model_name or (v.list_models()[0] if v.list_models() else ""),
                "models": v.list_models(),
                "has_key": bool(v.api_key),
                "masked_key": masked
            }

        if self.active_provider == "ollama":
            active_available = ollama_avail
        elif self.active_provider in cli_profiles:
            active_available = cli_profiles[self.active_provider]["available"]
        elif self.active_provider in self.api_providers:
            active_available = self.api_providers[self.active_provider].is_available()
        else:
            active_available = False

        return {
            "active_provider": self.active_provider,
            "active_available": active_available,
            "active_model": self.get_current_model_name(),
            "ollama": {
                "available": ollama_avail,
                "host": self.ollama.host,
                "selected_model": self.ollama.model_name,
                "models": ollama_models
            },
            "clis": cli_profiles,
            "apis": api_profiles
        }

    def explain_finding(self, finding: Dict[str, Any], provider: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        指定の指摘に対して解説と修正提案を生成。
        戻り値: {"text": "...", "provider": "...", "model": "..."}
        """
        if provider:
            self.set_provider(provider)

        finding_id = finding.get("id", "")
        current_model = self.get_current_model_name()
        cache_key = f"{self.active_provider}:{current_model}:{finding_id}"

        if not force and cache_key in self._cache:
            return self._cache[cache_key]
        elif force and cache_key in self._cache:
            del self._cache[cache_key]

        if self.active_provider == "disabled":
            return {
                "text": "AI解説機能はオフになっています。上部の選択メニューから Ollama、Codex CLI または各種公式APIを選択してください。",
                "provider": "disabled",
                "model": "none"
            }

        context_code = self._extract_context_code(finding)

        if self.active_provider == "ollama":
            if not self.ollama.is_available():
                text = f"**[Ollama 接続不可]**\nOllama サーバー ({self.ollama.host}) に接続できませんでした。\n`ollama serve` が実行されているかご確認ください。"
            else:
                text = self.ollama.generate_explanation(finding, context_code)

        elif self.active_provider == "codex":
            text = self.cli_manager.generate_explanation(finding, context_code, cli_id="codex")

        elif self.active_provider in self.api_providers:
            prov = self.api_providers[self.active_provider]
            text = prov.generate_explanation(finding, context_code)

        else:
            text = f"未対応のプロバイダです: {self.active_provider}"

        result = {
            "text": text,
            "provider": self.active_provider,
            "model": current_model
        }

        # 対策1: エラーやタイムアウト時はキャッシュに保存しない (再試行を可能にする)
        is_error = (
            text.startswith("**[タイムアウト]") or 
            text.startswith("**[Ollama エラー]") or 
            text.startswith("**[Ollama 通信エラー]") or
            text.startswith("**[Ollama 接続不可]") or
            text.startswith("**[実行時エラー]") or
            text.startswith("**[CLIがエラー") or
            ("エラー" in text and text.startswith("**["))
        )

        if finding_id and not is_error:
            self._cache[cache_key] = result

        return result

    def _extract_context_code(self, finding: Dict[str, Any], context_lines: int = 15) -> str:
        # PEバイナリ (EXE/DLL) 指摘の場合はバイナリファイルを直接テキスト読み込みせず、finding["code"] を返す
        if finding.get("source") == "pe-binary":
            return finding.get("code", "")

        full_path = finding.get("full_path")
        line = finding.get("line", 1)

        if not full_path or not os.path.exists(full_path):
            return finding.get("code", "")

        ext = os.path.splitext(full_path)[1].lower()
        if ext in [".exe", ".dll", ".sys", ".ocx"]:
            return finding.get("code", "")

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            start_idx = max(0, line - 1 - context_lines)
            end_idx = min(len(lines), line + context_lines)

            snippet_lines = []
            for i in range(start_idx, end_idx):
                curr_line_num = i + 1
                prefix = ">> " if curr_line_num == line else "   "
                snippet_lines.append(f"{prefix}{curr_line_num:4d} | {lines[i].rstrip()}")

            return "\n".join(snippet_lines)
        except Exception:
            return finding.get("code", "")

    def clear_cache(self):
        self._cache.clear()

    def cleanup(self):
        """アプリ終了時のリソース解放 (Ollama のモデルをアンロードして VRAM/RAM を即座に解放)"""
        try:
            self.ollama.unload_model()
        except Exception:
            pass
