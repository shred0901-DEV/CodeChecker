import os
import re
from typing import List, Dict, Any, Callable, Optional
from .file_manager import FileManager
from .builtin_rules import BuiltinScanner
from .semgrep_runner import SemgrepRunner
from .pe_scanner import PEScanner

# CWE番号から日本語タイトルへの対応辞書 (Semgrep単独検出時の親切化)
CWE_TITLES = {
    "798": "認証情報・APIキーのハードコード",
    "259": "パスワードのハードコード",
    "312": "平文での機密情報保持・秘密鍵漏洩",
    "89": "SQLインジェクションの脆弱性",
    "78": "OSコマンドインジェクションの脆弱性",
    "95": "危険なコード実行 (Eval Injection)",
    "502": "安全でないデシリアライズの脆弱性",
    "79": "クロスサイトスクリプティング (XSS)",
    "22": "パストラバーサル (ディレクトリ巡回)",
    "327": "安全でない暗号アルゴリズムの使用",
    "489": "デバッグ機能・開発用機能の露出",
    "352": "クロスサイトリクエストフォージェリ (CSRF)",
    "918": "SSRF (サーバーサイドリクエストフォージェリ)"
}

class ScanEngine:
    """統合脆弱性スキャンエンジン"""

    def __init__(self, use_semgrep: bool = True):
        self.file_manager = FileManager()
        self.builtin_scanner = BuiltinScanner()
        self.pe_scanner = PEScanner()
        self.use_semgrep = use_semgrep
        self.semgrep_runner = SemgrepRunner() if use_semgrep else None

    def scan(self, target_path: str, progress_callback: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        """
        フォルダ、単一ファイル、またはZIPファイルをスキャンし、結果オブジェクトを返す。
        """
        # 新規スキャン開始時に前回の一時ディレクトリを安全に解放 (RES-01)
        self.file_manager.cleanup()

        if progress_callback:
            progress_callback("ターゲットファイルを展開・準備中...", 10)

        scan_dir, is_temp = self.file_manager.prepare_target(target_path)
        all_findings: List[Dict[str, Any]] = []

        try:
            source_files, pe_files = self.file_manager.collect_files(scan_dir)
            total_source = len(source_files)
            total_pe = len(pe_files)
            total_files = total_source + total_pe

            # 1. 内蔵ルールスキャン (ソースコード)
            if progress_callback:
                progress_callback(f"ソースコード解析中... ({total_source} ファイル)", 25)

            if source_files:
                builtin_findings = self.builtin_scanner.scan_files(source_files, scan_dir)
                all_findings.extend(builtin_findings)

            # 2. PEバイナリスキャン (EXE / DLL)
            if pe_files:
                if progress_callback:
                    progress_callback(f"EXE/DLL バイナリを包括診断中... ({total_pe} ファイル)", 50)
                pe_findings = self.pe_scanner.scan_files(pe_files, scan_dir)
                all_findings.extend(pe_findings)

            # 3. Semgrep スキャン
            if self.use_semgrep and self.semgrep_runner and self.semgrep_runner.is_available() and source_files:
                if progress_callback:
                    progress_callback("Semgrep による多言語静的解析を実行中...", 75)
                try:
                    semgrep_findings = self.semgrep_runner.run(scan_dir)
                    all_findings.extend(semgrep_findings)
                except Exception as e:
                    print(f"[ScanEngine] Semgrepスキップ: {e}")

            if progress_callback:
                progress_callback("解析結果を集計・重複排除中...", 90)

            # 重複排除と日本語タイトルの補完
            unique_findings = self._deduplicate_and_localize(all_findings)
            sorted_findings = self._sort_findings(unique_findings)

            # 統計サマリー
            summary = {
                "total": len(sorted_findings),
                "high": sum(1 for f in sorted_findings if f["severity"] == "HIGH"),
                "medium": sum(1 for f in sorted_findings if f["severity"] == "MEDIUM"),
                "low": sum(1 for f in sorted_findings if f["severity"] == "LOW"),
                "total_files": total_files
            }

            if progress_callback:
                progress_callback("スキャン完了", 100)

            return {
                "target_path": target_path,
                "summary": summary,
                "findings": sorted_findings,
                "is_temp": is_temp
            }

        finally:
            pass

    def _extract_cwe_id(self, cwe_str: str) -> Optional[str]:
        """CWE文字列から番号部分を取り出す (例: 'CWE-798: ...' -> '798')"""
        if not cwe_str:
            return None
        m = re.search(r"CWE-(\d+)", cwe_str, re.IGNORECASE)
        return m.group(1) if m else None

    def _deduplicate_and_localize(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        同一箇所・同一脆弱性の重複を排除し、内蔵ルールの日本語を優先統合する。
        また、Semgrep単独の指摘についてもCWE辞書に基づいて日本語タイトルを付与する。
        PEバイナリ指摘はソースコードと重複しないため、ユニーク性を保ちつつ全件保持する。
        """
        pe_findings = []
        builtin_findings = []
        semgrep_findings = []
        other_findings = []

        seen_pe_ids = set()
        for f in findings:
            source = f.get("source", "")
            if source == "pe-binary":
                fid = f.get("id") or f"{f.get('file')}:{f.get('rule_id')}:{f.get('code')}"
                if fid not in seen_pe_ids:
                    seen_pe_ids.add(fid)
                    pe_findings.append(f)
            elif source == "builtin":
                builtin_findings.append(f)
            elif source == "semgrep":
                semgrep_findings.append(f)
            else:
                other_findings.append(f)

        # builtin と semgrep の重複統合
        # builtin の指摘をベースに、同一ファイル・近傍行（±1行）・同一CWEの semgrep 指摘をペアリング
        used_semgrep_indices = set()
        merged_source_findings = []

        for b in builtin_findings:
            b_item = dict(b)
            b_cwe_id = self._extract_cwe_id(b.get("cwe", ""))

            # 対応する semgrep 指摘を探す
            matched_s_idx = None
            for idx, s in enumerate(semgrep_findings):
                if idx in used_semgrep_indices:
                    continue
                if b["file"] == s["file"] and abs(b["line"] - s["line"]) <= 1:
                    s_cwe_id = self._extract_cwe_id(s.get("cwe", ""))
                    if b_cwe_id and s_cwe_id and b_cwe_id == s_cwe_id:
                        matched_s_idx = idx
                        break

            if matched_s_idx is not None:
                used_semgrep_indices.add(matched_s_idx)
                s_item = semgrep_findings[matched_s_idx]
                b_item["rule_id"] = f"{b_item['rule_id']} / {s_item['rule_id']}"
                if "N/A" in b_item.get("cwe", ""):
                    b_item["cwe"] = s_item.get("cwe")

            merged_source_findings.append(b_item)

        # マージされなかった semgrep 指摘を追加（CWE辞書から日本語化）
        for idx, s in enumerate(semgrep_findings):
            if idx not in used_semgrep_indices:
                s_item = dict(s)
                cwe_id = self._extract_cwe_id(s_item.get("cwe", ""))
                if cwe_id and cwe_id in CWE_TITLES:
                    s_item["title"] = f"{CWE_TITLES[cwe_id]} ({s_item['title']})"
                merged_source_findings.append(s_item)

        result = pe_findings + merged_source_findings + other_findings
        return result

    def _sort_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        return sorted(
            findings,
            key=lambda x: (
                severity_order.get(x["severity"], 3),
                x["file"],
                x["line"]
            )
        )

    def cleanup(self):
        self.file_manager.cleanup()
