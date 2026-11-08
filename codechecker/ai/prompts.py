from typing import Dict, Any

def create_remediation_prompt(finding: Dict[str, Any], context_code: str) -> str:
    """
    脆弱性情報と周辺コードから、解説・修正提案を求めるプロンプトを構築する。
    """
    rule_title = finding.get("title", "脆弱性")
    cwe = finding.get("cwe", "N/A")
    severity = finding.get("severity", "MEDIUM")
    description = finding.get("description", "")
    file_path = finding.get("file", "unknown")
    line = finding.get("line", 1)
    is_binary = finding.get("source") == "pe-binary" or file_path.lower().endswith((".exe", ".dll", ".sys", ".ocx"))

    if is_binary:
        return f"""あなたは高度なWindowsバイナリおよびシステムセキュリティの専門家です。
以下の実行可能バイナリ（EXE/DLL）静的セキュリティ診断によって検出された脆弱性・セキュリティリスクを分析し、開発者・運用者向けにわかりやすい解説と具体的な修正提案を行ってください。

### 検出情報
- **対象バイナリ**: {file_path}
- **検出された脆弱性/リスク**: {rule_title}
- **CWE / 識別子**: {cwe}
- **危険度判定**: {severity}
- **検出詳細**: {context_code}
- **検出ツールの指摘**: {description}

### 回答フォーマット要件
必ず以下の構成に従い、丁寧かつ簡潔な日本語のMarkdownで回答してください。

## 1. 脆弱性の要約とリスク
- この脆弱性・緩和策の不備によって、攻撃者がどのような攻撃（例: ROPエクスプロイト、バッファオーバーフロー、DLLインジェクション、機密情報窃取等）を実行可能になるのか、2〜4行で要約してください。

## 2. 修正方針
- コンパイラ・リンカーオプション（Visual Studio等）の設定変更、またはソースコード側（C/C++等）の改修方針を説明してください。

## 3. 推奨修正例
- Visual Studioのプロジェクト設定やコンパイルオプション（例: `/DYNAMICBASE`, `/NXCOMPAT`, `/GS`, `/guard:cf` 等）、または安全な代替API（例: `strcpy_s` 等）への書き換えコード例を提示してください。
"""

    return f"""あなたは高度なセキュリティエンジニアです。
以下のソースコード静的解析ツールによって検出された脆弱性を分析し、開発者向けにわかりやすい解説と具体的な修正提案を行ってください。

### 検出情報
- **脆弱性名**: {rule_title}
- **CWE / 識別子**: {cwe}
- **危険度判定**: {severity}
- **対象ファイル**: {file_path} (該当行: {line}行目)
- **検出ツールの指摘**: {description}

### 該当箇所のソースコード (周辺行含む)
```
{context_code}
```

### 回答フォーマット要件
必ず以下の構成に従い、丁寧かつ簡潔な日本語のMarkdownで回答してください。

## 1. 脆弱性の要約とリスク
- なぜこれが問題なのか、どのような攻撃（悪用）が可能になるのかを2〜4行で要約してください。

## 2. 修正方針
- どのようにコードや設計を改修すべきか、安全な実装アプローチを説明してください。

## 3. 推奨修正コード
- 脆弱性を解消した安全な修正後コード（可能であれば修正前後のDiffまたは書き換え例）をコードブロックで提示してください。
"""

