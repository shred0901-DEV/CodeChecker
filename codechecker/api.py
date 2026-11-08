import os
import sys
import re
import json
import html
import shutil
import subprocess
import webbrowser
import urllib.parse
import webview
from typing import Dict, Any, Optional
from .scanner.engine import ScanEngine
from .ai.manager import AIManager

class AppAPI:
    """PyWebView JavaScript-Python 双方向通信ブリッジ API"""

    def __init__(self):
        self.engine = ScanEngine(use_semgrep=True)
        self.ai = AIManager()
        self.current_results: Optional[Dict[str, Any]] = None
        self._window = None
        # 起動時に前回の残骸一時フォルダを安全に清掃 (ポータブル設計 & RES-01)
        self.engine.file_manager.cleanup_all_temp()

    def _get_window(self):
        if self._window:
            return self._window
        if len(webview.windows) > 0:
            return webview.windows[0]
        return None

    def select_folder(self) -> Optional[str]:
        """ネイティブフォルダ選択ダイアログ"""
        win = self._get_window()
        if not win:
            return None
        result = win.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return result[0] if isinstance(result, (tuple, list)) else result
        return None

    def select_file(self) -> Optional[str]:
        """ネイティブファイル選択ダイアログ (ZIP / EXE / DLL 対応)"""
        win = self._get_window()
        if not win:
            return None
        try:
            # PyWebView の file_types は説明欄に英数字・スペースのみ許可 (スラッシュ記号は不可)
            file_types = (
                'Supported Files (*.zip;*.exe;*.dll)',
                'ZIP Archive (*.zip)',
                'Executable Files (*.exe;*.dll)',
                'All files (*.*)'
            )
            result = win.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
            if result and len(result) > 0:
                return result[0] if isinstance(result, (tuple, list)) else result
        except Exception as e:
            print(f"[AppAPI] select_file error: {e}")
            # フォールバック (フィルタなし)
            try:
                result = win.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False)
                if result and len(result) > 0:
                    return result[0] if isinstance(result, (tuple, list)) else result
            except Exception as e2:
                print(f"[AppAPI] fallback select_file error: {e2}")
        return None

    def resolve_dropped_path(self, filename_or_path: str) -> Optional[str]:
        """ドラッグ＆ドロップされたファイル名から実際の絶対パスを解決する"""
        if not filename_or_path:
            return None
        # 既に絶対パスとして存在していればそのまま返す
        if os.path.isabs(filename_or_path) and os.path.exists(filename_or_path):
            return os.path.abspath(filename_or_path)

        basename = os.path.basename(filename_or_path).lower()

        # 0. 直近でPython側DOMリスナーがキャッチしたドロップパスと照合
        last_path = getattr(self, '_last_dropped_path', None)
        if last_path and os.path.exists(last_path):
            if os.path.basename(last_path).lower() == basename:
                return os.path.abspath(last_path)

        # 1. WebView2 の _dnd_state['paths'] から逆引き
        try:
            from webview.dom import _dnd_state
            for item in reversed(_dnd_state.get('paths', [])):
                # item は (basename, full_path)
                if item and len(item) >= 2:
                    name_candidate = item[0].lower()
                    unquoted_name = urllib.parse.unquote(item[0]).lower()
                    if (name_candidate == basename or unquoted_name == basename) and os.path.exists(item[1]):
                        return os.path.abspath(item[1])
        except Exception as e:
            print(f"[resolve_dropped_path] _dnd_state error: {e}")

        # 2. 直近の親ディレクトリやカレントディレクトリ等に存在するか確認
        if os.path.exists(filename_or_path):
            return os.path.abspath(filename_or_path)

        return None

    def open_external_url(self, url: str) -> bool:
        """システム既定のブラウザでURLを開く (アプリ画面遷移防止)"""
        if not url:
            return False
        if url.startswith(("http://", "https://")):
            webbrowser.open(url)
            return True
        return False

    def _resolve_target_file(self, target_ref: str) -> Optional[str]:
        """target_ref から実ファイルパスを解決する共通ヘルパー"""
        if not target_ref:
            return None

        # 参照文字列から行番号やスキームをクリーンアップ
        clean_ref = re.sub(r"[:#]L?\d+.*$", "", target_ref)
        if clean_ref.startswith("file:///"):
            clean_ref = clean_ref[8:]
        elif clean_ref.startswith("file://"):
            clean_ref = clean_ref[7:]
        clean_ref = urllib.parse.unquote(clean_ref).replace("/", os.sep)

        # 既に絶対パスで存在する場合
        if os.path.isabs(clean_ref) and os.path.exists(clean_ref):
            return clean_ref

        if self.current_results:
            findings = self.current_results.get("findings", [])
            base_target = self.current_results.get("target_path", "")

            # A. スキャン結果の findings からファイル名・相対パスで照合
            for f in findings:
                full_path = f.get("full_path")
                rel_path = f.get("file", "")
                if full_path and os.path.exists(full_path):
                    if clean_ref.endswith(os.path.basename(full_path)) or clean_ref == rel_path.replace("/", os.sep):
                        return full_path

            # B. ターゲットディレクトリ / 単一ファイルからの照合
            if os.path.isdir(base_target):
                candidate = os.path.join(base_target, clean_ref)
                if os.path.exists(candidate):
                    return candidate
            elif os.path.isfile(base_target):
                if os.path.basename(base_target).lower() == os.path.basename(clean_ref).lower() or base_target == clean_ref:
                    return base_target

        return None

    def open_source_file(self, target_ref: str) -> Dict[str, Any]:
        """
        AI解説内のファイルリンクから、該当ソースコードを既定エディタ(またはVS Code)で開く。
        ZIP一時展開ファイルかどうかも判定して返す。
        バイナリファイル（EXE/DLL）が渡された場合は文字化け防止のため open_file_location に自動委譲 (UX-01)。
        """
        if not target_ref:
            return {"success": False, "error": "ファイル指定が空です"}

        # 1. 行番号の抽出 (例: file.py#L42, file.py:42)
        line_num = None
        line_match = re.search(r"[:#]L?(\d+)", target_ref, re.IGNORECASE)
        if line_match:
            try:
                line_num = int(line_match.group(1))
            except ValueError:
                pass

        # 2. 実ファイルパスの解決
        resolved_path = self._resolve_target_file(target_ref)
        if not resolved_path or not os.path.exists(resolved_path):
            clean_ref = re.sub(r"[:#]L?\d+.*$", "", target_ref)
            return {
                "success": False,
                "error": f"該当のファイルが見つかりませんでした: {clean_ref}"
            }

        # 3. PEバイナリ (EXE/DLL) の場合はエクスプローラー起動へ委譲 (UX-01)
        ext = os.path.splitext(resolved_path)[1].lower()
        if ext in {".exe", ".dll", ".sys", ".ocx"}:
            return self.open_file_location(target_ref)

        # 4. ZIP一時展開ファイルかどうかの判定
        is_temp = False
        if self.current_results:
            is_temp = self.current_results.get("is_temp", False)
        if not is_temp and (".temp" in resolved_path or "codechecker_zip_" in resolved_path or "zip_" in resolved_path):
            is_temp = True

        # 5. エディタで起動 (VS Codeがあれば行番号ジャンプ、なければOS関連付けで開く)
        code_cli = shutil.which("code") or shutil.which("code.cmd")
        opened_via_vscode = False

        if code_cli:
            try:
                if line_num:
                    subprocess.Popen([code_cli, "-g", f"{resolved_path}:{line_num}"], shell=False)
                else:
                    subprocess.Popen([code_cli, resolved_path], shell=False)
                opened_via_vscode = True
            except Exception:
                opened_via_vscode = False

        if not opened_via_vscode:
            try:
                # Windowsの既定エディタ(メモ帳、VSCode等)で開く
                os.startfile(resolved_path)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"エディタの起動に失敗しました: {str(e)}"
                }

        return {
            "success": True,
            "path": resolved_path,
            "file_name": os.path.basename(resolved_path),
            "line": line_num,
            "is_temp": is_temp,
            "editor": "VS Code" if opened_via_vscode else "既定エディタ"
        }

    def open_file_location(self, target_ref: str) -> Dict[str, Any]:
        """
        対象ファイル（特にPEバイナリ等）が存在する場所をOSのファイラー（エクスプローラー）で開き、
        該当ファイルを選択状態にする (UX-01)。
        """
        if not target_ref:
            return {"success": False, "error": "ファイル指定が空です"}

        resolved_path = self._resolve_target_file(target_ref)
        if not resolved_path or not os.path.exists(resolved_path):
            clean_ref = re.sub(r"[:#]L?\d+.*$", "", target_ref)
            return {
                "success": False,
                "error": f"該当のファイルが見つかりませんでした: {clean_ref}"
            }

        try:
            if sys.platform == "win32":
                # Windows エクスプローラーで選択状態で表示
                subprocess.Popen(["explorer.exe", f"/select,{resolved_path}"], shell=False)
            elif sys.platform == "darwin":
                # macOS Finder で選択状態で表示
                subprocess.Popen(["open", "-R", resolved_path], shell=False)
            else:
                # Linux は親ディレクトリを開く
                subprocess.Popen(["xdg-open", os.path.dirname(resolved_path)], shell=False)
        except Exception as e:
            return {
                "success": False,
                "error": f"ファイラーの起動に失敗しました: {str(e)}"
            }

        return {
            "success": True,
            "path": resolved_path,
            "file_name": os.path.basename(resolved_path),
            "directory": os.path.dirname(resolved_path)
        }

    def start_scan(self, target_path: str) -> Dict[str, Any]:
        """指定されたパス（フォルダ、ZIP、またはEXE/DLL）のスキャンを実行する"""
        if not target_path:
            return {"error": "スキャン対象のパスが指定されていません"}

        target_path = target_path.strip().strip('"').strip("'")

        # パスが存在しない場合、WebView2でドロップされたファイルからの自動解決を試行
        if not os.path.exists(target_path):
            resolved = self.resolve_dropped_path(target_path)
            if resolved:
                target_path = resolved

        if not os.path.exists(target_path):
            return {"error": f"指定されたパスが存在しません: {target_path}"}

        win = self._get_window()

        def on_progress(message: str, percent: int):
            if win:
                # json.dumps で文字列を完全エスケープ (BUG-05)
                js_code = f"window.onScanProgress && window.onScanProgress({json.dumps(message)}, {percent});"
                try:
                    win.evaluate_js(js_code)
                except Exception:
                    pass

        try:
            self.ai.clear_cache()
            results = self.engine.scan(target_path, progress_callback=on_progress)
            self.current_results = results
            return results
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"スキャン中にエラーが発生しました: {str(e)}"}

    def explain_finding(self, finding_id: str, provider: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """特定の脆弱性に対するAI解説を取得 (モデル名付き)"""
        if not self.current_results:
            return {"error": "スキャン結果がありません"}

        findings = self.current_results.get("findings", [])
        target = next((f for f in findings if f["id"] == finding_id), None)
        if not target:
            return {"error": f"該当の指摘 (ID: {finding_id}) が見つかりません"}

        result = self.ai.explain_finding(target, provider=provider, force=force)
        return {
            "finding_id": finding_id,
            "explanation": result["text"],
            "provider": result["provider"],
            "model": result["model"]
        }

    def get_ai_status(self) -> Dict[str, Any]:
        """AIプロバイダの状態を取得"""
        return self.ai.get_status()

    def update_ai_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """AIプロバイダの設定を更新"""
        provider = settings.get("active_provider")
        if provider:
            self.ai.set_provider(provider)

        ollama_settings = settings.get("ollama", {})
        self.ai.update_ollama_settings(
            host=ollama_settings.get("host"),
            model=ollama_settings.get("selected_model")
        )

        clis_settings = settings.get("clis", {})
        for cli_id, cli_data in clis_settings.items():
            if "command" in cli_data:
                self.ai.update_cli_command(cli_id, cli_data["command"])
            if "selected_model" in cli_data:
                self.ai.set_cli_model(cli_id, cli_data["selected_model"])

        return self.ai.get_status()

    def test_cli(self, cli_id: str) -> Dict[str, Any]:
        """指定のCLI導通テストを実行"""
        return self.ai.test_cli(cli_id)

    def export_report(self, format_type: str = "markdown") -> Dict[str, Any]:
        """スキャン結果レポートをファイルに保存 (タプル返却対応)"""
        win = self._get_window()
        if not self.current_results or not win:
            return {"error": "エクスポート可能なスキャン結果がありません"}

        file_types = ('Markdown (*.md)',) if format_type == "markdown" else ('HTML (*.html)',)
        ext = "md" if format_type == "markdown" else "html"
        save_result = win.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=f"vulnerability_report.{ext}",
            file_types=file_types
        )

        if not save_result:
            return {"status": "cancelled"}

        if isinstance(save_result, (tuple, list)):
            if len(save_result) == 0:
                return {"status": "cancelled"}
            save_path = save_result[0]
        else:
            save_path = save_result

        if not save_path:
            return {"status": "cancelled"}

        try:
            summary = self.current_results.get("summary", {})
            findings = self.current_results.get("findings", [])

            if format_type == "markdown":
                content = f"# ソースコード脆弱性診断レポート\n\n"
                content += f"**対象**: `{self.current_results.get('target_path')}`\n\n"
                content += f"## 診断サマリー\n"
                content += f"- 🔴 危険度[高]: {summary.get('high', 0)} 件\n"
                content += f"- 🟡 危険度[中]: {summary.get('medium', 0)} 件\n"
                content += f"- 🟢 危険度[低]: {summary.get('low', 0)} 件\n"
                content += f"- 合計検出数: {summary.get('total', 0)} 件 (対象ファイル数: {summary.get('total_files', 0)})\n\n"
                content += f"## 検出一覧\n\n"

                for idx, f in enumerate(findings, 1):
                    content += f"### {idx}. [{f['severity']}] {f['title']} ({f['cwe']})\n"
                    content += f"- **ファイル**: `{f['file']}` (L{f['line']})\n"
                    content += f"- **説明**: {f['description']}\n\n"
                    content += f"```\n{f.get('code', '').strip()}\n```\n\n"

                    for k, v in self.ai._cache.items():
                        if k.endswith(f":{f['id']}"):
                            content += f"#### AI解説 & 修正提案 ({v['provider']} / {v['model']})\n\n{v['text']}\n\n"
                            break
                    content += "---\n\n"
            else:
                esc_target = html.escape(str(self.current_results.get('target_path', '')))
                content = f"<html><head><meta charset='utf-8'><title>脆弱性診断レポート</title>"
                content += "<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:24px;max-width:960px;margin:auto;line-height:1.6;color:#1e293b}"
                content += ".high{color:#ef4444;font-weight:bold}.medium{color:#f59e0b;font-weight:bold}.low{color:#10b981;font-weight:bold}"
                content += "pre{background:#f8fafc;border:1px solid #e2e8f0;padding:12px;border-radius:6px;overflow-x:auto;font-family:monospace}"
                content += ".ai-box{background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #16a34a;border-radius:6px;padding:12px 16px;margin:12px 0}"
                content += ".ai-box h4{margin:0 0 8px 0;color:#15803d;font-size:14px}"
                content += ".ai-box pre{background:#ffffff;border:1px solid #dcfce7;white-space:pre-wrap;font-family:inherit;line-height:1.5}"
                content += "</style></head><body>"
                content += f"<h1>ソースコード脆弱性診断レポート</h1>"
                content += f"<p>対象: <code>{esc_target}</code></p>"
                content += f"<p>🔴 高: {summary.get('high', 0)} | 🟡 中: {summary.get('medium', 0)} | 🟢 低: {summary.get('low', 0)}</p><hr>"
                for f in findings:
                    sev_class = f['severity'].lower()
                    esc_title = html.escape(str(f.get('title', '')))
                    esc_cwe = html.escape(str(f.get('cwe', '')))
                    esc_file = html.escape(str(f.get('file', '')))
                    esc_desc = html.escape(str(f.get('description', '')))
                    esc_code = html.escape(str(f.get('code', '')))
                    content += f"<div><h3 class='{sev_class}'>[{f['severity']}] {esc_title} ({esc_cwe})</h3>"
                    content += f"<p>ファイル: <code>{esc_file}:{f['line']}</code></p>"
                    content += f"<p>{esc_desc}</p>"
                    content += f"<pre><code>{esc_code}</code></pre>"

                    for k, v in self.ai._cache.items():
                        if k.endswith(f":{f['id']}"):
                            esc_ai_prov = html.escape(str(v.get('provider', '')))
                            esc_ai_mod = html.escape(str(v.get('model', '')))
                            esc_ai_text = html.escape(str(v.get('text', '')))
                            content += f"<div class='ai-box'><h4>🤖 AI解説 &amp; 修正提案 ({esc_ai_prov} / {esc_ai_mod})</h4>"
                            content += f"<pre>{esc_ai_text}</pre></div>"
                            break

                    content += "</div><hr>"
                content += "</body></html>"

            with open(save_path, "w", encoding="utf-8") as out_f:
                out_f.write(content)

            return {"status": "success", "saved_path": save_path}
        except Exception as e:
            return {"error": f"保存失敗: {str(e)}"}

    def cleanup(self):
        """アプリケーション終了処理 (一時ファイル削除 & Ollama VRAM/RAM 解放)"""
        try:
            self.engine.cleanup()
        except Exception:
            pass
        try:
            self.ai.cleanup()
        except Exception:
            pass
