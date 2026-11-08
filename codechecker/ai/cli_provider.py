import subprocess
import shutil
import os
import sys
import re
import shlex
from typing import Dict, Any, List, Optional
from .base import BaseLLMProvider
from .prompts import create_remediation_prompt

# Codex CLI デフォルト定義
CLI_PROFILES = {
    "codex": {
        "id": "codex",
        "name": "Codex CLI",
        # ★Codexは対話モードだと "stdin is not a terminal" になるため、exec --skip-git-repo-check - が必須
        "command": "codex exec --skip-git-repo-check -",
        "default_command": "codex exec --skip-git-repo-check -",
        "description": "Codex CLI (非対話 exec モード)",
        "selected_model": "default",
        "model_flag": "--model",
        "suggested_models": ["default", "gpt-4o", "gpt-4o-mini", "o3-mini", "o1"]
    }
}

class DedicatedCLIProvider(BaseLLMProvider):
    """Codex 専用CLIプロバイダ"""

    def __init__(self):
        self.profiles: Dict[str, Dict[str, Any]] = {}
        for key, val in CLI_PROFILES.items():
            self.profiles[key] = dict(val)

    def _resolve_executable(self, cmd_name: str) -> Optional[str]:
        """システムのPATHまたは一般的なインストール場所から実行可能ファイルを解決"""
        found = shutil.which(cmd_name)
        if found:
            return found

        # Windows用：OpenAI Codex の一般的なインストール場所
        if cmd_name.lower().startswith("codex"):
            user_profile = os.environ.get("USERPROFILE", "")
            codex_path = os.path.join(user_profile, r"AppData\Local\Programs\OpenAI\Codex\bin\codex.exe")
            if os.path.exists(codex_path):
                return codex_path

        return None

    def is_available(self, cli_id: str = "codex") -> bool:
        profile = self.profiles.get(cli_id)
        if not profile:
            return False
        cmd_str = profile.get("command", "").strip()
        if not cmd_str:
            return False
        base_cmd = cmd_str.split()[0].strip('"\'')
        return bool(self._resolve_executable(base_cmd))

    def list_models(self) -> List[str]:
        return list(self.profiles.keys())

    def update_command(self, cli_id: str, new_command: str):
        if cli_id in self.profiles and new_command.strip():
            self.profiles[cli_id]["command"] = new_command.strip()

    def set_model(self, cli_id: str, model_name: str):
        if cli_id in self.profiles:
            clean_model = model_name.strip() if model_name else "default"
            self.profiles[cli_id]["selected_model"] = clean_model

    def detect_default_model(self, cli_id: str = "codex") -> Optional[str]:
        """CLI設定ファイルや環境変数から、現在設定されているデフォルトモデル名を自動取得"""
        user_profile = os.environ.get("USERPROFILE", "") or os.path.expanduser("~")

        if cli_id == "codex":
            # ~/.codex/config.toml 内の model = "..."
            config_toml = os.path.join(user_profile, ".codex", "config.toml")
            if os.path.exists(config_toml):
                try:
                    with open(config_toml, "r", encoding="utf-8") as f:
                        content = f.read()
                    m = re.search(r'model\s*=\s*["\']([^"\']+)["\']', content)
                    if m:
                        return m.group(1).strip()
                except Exception:
                    pass

        return None

    def get_profile(self, cli_id: str = "codex") -> Optional[Dict[str, Any]]:
        prof = self.profiles.get(cli_id)
        if not prof:
            return None
        detected = self.detect_default_model(cli_id)
        return {
            **prof,
            "available": self.is_available(cli_id),
            "detected_model": detected
        }

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for k in self.profiles.keys():
            result[k] = self.get_profile(k)
        return result

    def test_cli(self, cli_id: str = "codex") -> Dict[str, Any]:
        if not self.is_available(cli_id):
            cmd = self.profiles.get(cli_id, {}).get("command", "")
            return {
                "success": False,
                "message": f"コマンドが見つかりません: '{cmd}'\nインストールされているか、PATHが通っているかご確認ください。"
            }

        test_prompt = "Say OK in one word."
        try:
            output = self._execute_cli(cli_id, test_prompt, timeout=25)
            return {
                "success": True,
                "message": f"接続成功!\n応答: {output[:100]}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"実行エラー: {str(e)}"
            }

    def generate_explanation(self, finding: Dict[str, Any], context_code: str, cli_id: str = "codex") -> str:
        prompt = create_remediation_prompt(finding, context_code)

        if not self.is_available(cli_id):
            prof = self.profiles.get(cli_id, {})
            name = prof.get("name", cli_id)
            cmd = prof.get("command", "")
            return f"**[{name} 実行不可]**\nコマンド `{cmd}` が見つかりませんでした。\nターミナルで実行可能か、設定画面でパスが正しいかご確認ください。"

        try:
            return self._execute_cli(cli_id, prompt, timeout=120)
        except subprocess.TimeoutExpired:
            return f"**[タイムアウト]** {self.profiles.get(cli_id, {}).get('name')} からの応答がタイムアウトしました。"
        except Exception as e:
            return f"**[実行時エラー]** {str(e)}"

    def _execute_cli(self, cli_id: str, prompt: str, timeout: int = 120) -> str:
        profile = self.profiles.get(cli_id, {})
        raw_cmd = profile.get("command", "").strip()
        selected_model = profile.get("selected_model", "default")
        model_flag = profile.get("model_flag", "--model")

        # ★Codex 特有の正規化 (ユーザーが単に "codex" と設定していても自動で非対話 exec モードにする)
        if cli_id == "codex":
            # "exec" が含まれていなければ非対話モードフラグを付与
            if "exec" not in raw_cmd:
                raw_cmd = f"{raw_cmd} exec --skip-git-repo-check -"
            elif "--skip-git-repo-check" not in raw_cmd:
                raw_cmd = raw_cmd.replace("exec", "exec --skip-git-repo-check")
            if not raw_cmd.endswith("-") and "{prompt}" not in raw_cmd:
                raw_cmd = f"{raw_cmd} -"

        # モデルフラグの追加
        has_model_flag = bool(model_flag and f"{model_flag}" in raw_cmd)
        if selected_model and selected_model != "default" and not has_model_flag:
            raw_cmd = f"{raw_cmd} {model_flag} {selected_model}"

        # 引数をリスト形式に分解 (shell=False での安全な実行のため)
        try:
            raw_tokens = shlex.split(raw_cmd, posix=(os.name != "nt"))
        except Exception:
            raw_tokens = raw_cmd.split()

        cmd_tokens = [t.strip('"\'') for t in raw_tokens if t.strip()]
        if not cmd_tokens:
            raise ValueError(f"実行コマンドが空です: {raw_cmd}")

        # 実行可能ファイルのフルパス解決
        base_exe = cmd_tokens[0]
        resolved_exe = self._resolve_executable(base_exe)
        if resolved_exe:
            cmd_tokens[0] = resolved_exe

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        # 方式1: コマンドに {prompt} が明示されている場合
        if any("{prompt}" in t for t in cmd_tokens):
            args = []
            for t in cmd_tokens:
                if "{prompt}" in t:
                    args.append(t.replace("{prompt}", prompt))
                else:
                    args.append(t)

            process = subprocess.Popen(
                args,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                creationflags=creation_flags
            )
            stdout, stderr = process.communicate(timeout=timeout)

        # 方式2: 標準入力 (stdin) パイプ渡し (Codex exec - 等)
        else:
            process = subprocess.Popen(
                cmd_tokens,
                shell=False,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                creationflags=creation_flags
            )
            stdout, stderr = process.communicate(input=prompt, timeout=timeout)

        if process.returncode == 0 and stdout.strip():
            return stdout.strip()
        else:
            err = stderr.strip() or stdout.strip()
            raise RuntimeError(f"CLIがエラーコード {process.returncode} で終了しました:\n{err}")
