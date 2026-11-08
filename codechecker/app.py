import os
import sys
import json
import atexit
import webview
from webview.dom import _dnd_state
from .api import AppAPI

def run_app():
    """PyWebView アプリケーションを初期化・起動する"""
    api = AppAPI()
    atexit.register(api.cleanup)

    # WebView2 の DnD ファイルパス取得リスナーを有効化
    try:
        _dnd_state['num_listeners'] = max(_dnd_state.get('num_listeners', 0), 1)
    except Exception:
        pass

    # フロントエンドの index.html のパスを解決
    base_dir = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.abspath(os.path.join(base_dir, "..", "web"))
    index_html = os.path.join(web_dir, "index.html")

    if not os.path.exists(index_html):
        raise FileNotFoundError(f"フロントエンドファイルが見つかりません: {index_html}")

    # ウィンドウ作成 (background_color はWebView2との互換性のため省略)
    window = webview.create_window(
        title="CodeChecker - ソースコード脆弱性診断 & AI修正提案",
        url=f"file:///{index_html.replace(os.sep, '/')}",
        js_api=api,
        width=1280,
        height=860,
        min_size=(960, 640)
    )

    api._window = window

    def on_loaded():
        try:
            drop_zone = window.dom.get_element('#drop-zone')
            if drop_zone:
                def on_drop(e):
                    try:
                        data_transfer = e.get('dataTransfer', {})
                        files = data_transfer.get('files', [])
                        if files:
                            full_path = files[0].get('pywebviewFullPath')
                            if full_path:
                                api._last_dropped_path = full_path
                                window.evaluate_js(f"window.setSelectedPath && window.setSelectedPath({json.dumps(full_path)});")
                    except Exception as err:
                        print(f"[app.py] on_drop error: {err}")
                drop_zone.on('drop', on_drop)
        except Exception as ex:
            print(f"[app.py] DND bind error: {ex}")

    window.events.loaded += on_loaded

    try:
        webview.start(debug=False)
    finally:
        # アプリ終了時に一時フォルダ削除 & Ollama VRAM/RAM 解放
        api.cleanup()

if __name__ == "__main__":
    run_app()
