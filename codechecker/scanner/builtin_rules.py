import re
import os
from typing import List, Dict, Any

# 内蔵検出ルール定義
# 各ルールは regex, severity ("HIGH" / "MEDIUM" / "LOW"), cwe, title, description を持つ
PATTERNS = [
    {
        "id": "builtin-secrets-private-key",
        "title": "ハードコードされた秘密鍵",
        "severity": "HIGH",
        "cwe": "CWE-312",
        "regex": re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
        "description": "ソースコード内に暗号鍵（秘密鍵）が直接埋め込まれています。コミット履歴を含めて鍵が漏洩する危険があります。"
    },
    {
        "id": "builtin-secrets-aws-key",
        "title": "AWSアクセスキーのハードコード",
        "severity": "HIGH",
        "cwe": "CWE-798",
        "regex": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "description": "AWSアクセスキーIDがソースコード内に直接記載されています。環境変数やシークレットマネージャを利用してください。"
    },
    {
        "id": "builtin-secrets-generic-api-key",
        "title": "APIキー / シークレットトークンのハードコード",
        "severity": "HIGH",
        "cwe": "CWE-798",
        "regex": re.compile(r"""(?:api_key|apikey|secret_key|app_secret|auth_token|access_token)\s*[:=]\s*['"][a-zA-Z0-9_\-]{16,}['"]""", re.IGNORECASE),
        "description": "APIキーやシークレットトークンがハードコードされている可能性があります。"
    },
    {
        "id": "builtin-secrets-password",
        "title": "ハードコードされたパスワード",
        "severity": "MEDIUM",
        "cwe": "CWE-259",
        "regex": re.compile(r"""(?:password|passwd|pwd|db_pass)\s*[:=]\s*['"][^'"]{4,}['"]""", re.IGNORECASE),
        "description": "認証用パスワードが平文で直接コードに定義されている可能性があります。"
    },
    {
        "id": "builtin-rce-eval",
        "title": "危険なコード実行関数 (eval/exec)",
        "severity": "HIGH",
        "cwe": "CWE-95",
        "regex": re.compile(r"""\b(eval|exec)\s*\((?!['"][\w\s]+['"]\))"""),
        "description": "外部から渡された文字列をコードとして動的評価すると、任意のコード実行 (RCE) につながる危険があります。"
    },
    {
        "id": "builtin-cmdi-system",
        "title": "シェルコマンド実行の危険性",
        "severity": "HIGH",
        "cwe": "CWE-78",
        "regex": re.compile(r"""\b(?:os\.system|subprocess\.(?:call|Popen|run|check_call|check_output)|execSync|shell_exec|system)\s*\((?!['"][\w\s\-/]+['"]\s*\)|\s*\[(?!.*shell\s*=\s*True))"""),
        "description": "OSコマンド実行関数に変数を結合して渡すと、OSコマンドインジェクションが発生する危険があります。"
    },
    {
        "id": "builtin-sqli-concat",
        "title": "SQLインジェクションの兆候 (文字列連結)",
        "severity": "HIGH",
        "cwe": "CWE-89",
        "regex": re.compile(r"""(?:f['"][^'"]*(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\b.*\{|(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\s+.*(?:['"]\s*\+|\+\s*['"]|%s|\.format\())""", re.IGNORECASE),
        "description": "SQL文を文字列連結やフォーマット文字列で動的組み立てしている可能性があります。プレースホルダ（バインド機構）を使用してください。"
    },
    {
        "id": "builtin-deserialization-pickle",
        "title": "安全でないデシリアライズ (pickle)",
        "severity": "HIGH",
        "cwe": "CWE-502",
        "regex": re.compile(r"""\bpickle\.(loads?|Unpickler)\s*\("""),
        "description": "信頼できない入力に対して pickle をアンピックルすると、任意のコード実行が可能になります。JSONなど安全な形式を検討してください。"
    },
    {
        "id": "builtin-deserialization-yaml",
        "title": "安全でないYAMLロード (yaml.load)",
        "severity": "HIGH",
        "cwe": "CWE-502",
        "regex": re.compile(r"""\byaml\.load\s*\((?!.*Loader\s*=\s*(yaml\.)?(SafeLoader|BaseLoader))"""),
        "description": "yaml.load を SafeLoader なしで使用すると、任意のオブジェクト構築によりコード実行を招く恐れがあります。"
    },
    {
        "id": "builtin-debug-mode",
        "title": "本番環境でのデバッグモード有効化",
        "severity": "LOW",
        "cwe": "CWE-489",
        "regex": re.compile(r"""(?:DEBUG\s*=\s*True|debug\s*[:=]\s*true|app\.run\(.*debug\s*=\s*True)""", re.IGNORECASE),
        "description": "デバッグ機能が有効化されたまま本番公開されると、スタックトレースや内部情報が外部へ漏洩します。"
    },
    {
        "id": "builtin-crypto-weak-hash",
        "title": "強度の弱い暗号化/ハッシュアルゴリズム (MD5/SHA1)",
        "severity": "LOW",
        "cwe": "CWE-327",
        "regex": re.compile(r"""\b(?:hashlib\.(md5|sha1)|crypto\.createHash\(['"](md5|sha1)['"]\)|md5\(|sha1\()""", re.IGNORECASE),
        "description": "MD5 や SHA-1 は衝突攻撃耐性が破られており安全ではありません。SHA-256、SHA-3 やパスワードハッシュ用（Argon2, bcrypt）を使用してください。"
    }
]

class BuiltinScanner:
    """軽量内蔵ルールスキャナ"""

    def scan_file(self, file_path: str, base_dir: str) -> List[Dict[str, Any]]:
        findings = []
        if os.path.isfile(base_dir) or file_path == base_dir:
            rel_path = os.path.basename(file_path)
        else:
            rel_path = os.path.relpath(file_path, base_dir).replace("\\", "/")

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return findings

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # コメントアウト行の簡易スキップ（過剰検知防止）
            if stripped.startswith(("//", "#", "/*", "*", "<!--")):
                continue

            for rule in PATTERNS:
                if rule["regex"].search(line):
                    finding_id = f"{rule['id']}-{rel_path}-{line_num}"
                    findings.append({
                        "id": finding_id,
                        "rule_id": rule["id"],
                        "title": rule["title"],
                        "severity": rule["severity"],  # "HIGH", "MEDIUM", "LOW"
                        "cwe": rule["cwe"],
                        "file": rel_path,
                        "full_path": file_path,
                        "line": line_num,
                        "end_line": line_num,
                        "code": line.rstrip(),
                        "description": rule["description"],
                        "source": "builtin"
                    })

        return findings

    def scan_files(self, file_paths: List[str], base_dir: str) -> List[Dict[str, Any]]:
        all_findings = []
        for file_path in file_paths:
            all_findings.extend(self.scan_file(file_path, base_dir))
        return all_findings

