import json
import os
import subprocess
import sys
from typing import List, Dict, Any, Optional

class SemgrepRunner:
    """Semgrep CLI の実行および結果解析を行うラッパークラス"""

    def __init__(self, semgrep_cmd: str = "semgrep"):
        self.semgrep_cmd = semgrep_cmd

    def is_available(self) -> bool:
        """Semgrep が実行可能かどうかを確認する"""
        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            res = subprocess.run(
                [self.semgrep_cmd, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                creationflags=creation_flags
            )
            return res.returncode == 0
        except Exception:
            return False

    def run(self, target_dir: str, config: str = "auto") -> List[Dict[str, Any]]:
        """
        指定されたディレクトリに対して Semgrep スキャンを実行し、結果を正規化リストで返す。
        """
        target_dir = os.path.abspath(target_dir)
        cmd = [
            self.semgrep_cmd,
            "scan",
            "--json",
            "--quiet",
            f"--config={config}",
            target_dir
        ]

        try:
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=180,
                creationflags=creation_flags
            )
            if not process.stdout:
                return []

            data = json.loads(process.stdout)
            return self._parse_results(data, target_dir)
        except Exception as e:
            print(f"[SemgrepRunner] 実行エラー: {e}", file=sys.stderr)
            return []

    def _parse_results(self, data: Dict[str, Any], base_dir: str) -> List[Dict[str, Any]]:
        findings = []
        raw_results = data.get("results", [])

        for idx, item in enumerate(raw_results):
            check_id = item.get("check_id", "unknown-rule")
            path = item.get("path", "")
            
            # 相対パスの正規化
            if os.path.isabs(path):
                if os.path.isfile(base_dir) or path == base_dir:
                    rel_path = os.path.basename(path)
                else:
                    rel_path = os.path.relpath(path, base_dir).replace("\\", "/")
                full_path = path
            else:
                rel_path = path.replace("\\", "/")
                if os.path.isfile(base_dir):
                    full_path = base_dir
                else:
                    full_path = os.path.join(base_dir, path)

            start = item.get("start", {})
            end = item.get("end", {})
            start_line = start.get("line", 1)
            end_line = end.get("line", start_line)

            extra = item.get("extra", {})
            raw_severity = str(extra.get("severity", "WARNING")).upper()
            message = extra.get("message", "").strip()
            lines = extra.get("lines", "").strip()

            # ★重要: Semgrepが "requires login" を返した場合、実ファイルから該当行を読み取る
            if lines == "requires login" or not lines:
                lines = self._read_lines_from_file(full_path, start_line, end_line)

            metadata = extra.get("metadata", {})
            cwe = metadata.get("cwe", "")
            if isinstance(cwe, list):
                cwe = ", ".join(cwe)
            elif not cwe:
                cwe = "N/A"

            # Severity マッピング (HIGH, MEDIUM, LOW)
            if raw_severity in ["ERROR", "CRITICAL"]:
                severity = "HIGH"
            elif raw_severity in ["WARNING"]:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            # タイトルの生成
            rule_title = check_id.split(".")[-1].replace("-", " ").replace("_", " ").title()

            finding_id = f"semgrep-{check_id}-{rel_path}-{start_line}"
            findings.append({
                "id": finding_id,
                "rule_id": check_id,
                "title": rule_title,
                "severity": severity,
                "cwe": cwe,
                "file": rel_path,
                "full_path": full_path,
                "line": start_line,
                "end_line": end_line,
                "code": lines,
                "description": message,
                "source": "semgrep"
            })

        return findings

    def _read_lines_from_file(self, full_path: str, start_line: int, end_line: int) -> str:
        """ローカルファイルから指定行のソースコードを直接抽出する"""
        if not os.path.exists(full_path):
            return ""
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            
            s = max(0, start_line - 1)
            e = min(len(all_lines), end_line)
            extracted = "".join(all_lines[s:e]).strip()
            return extracted if extracted else ""
        except Exception:
            return ""
