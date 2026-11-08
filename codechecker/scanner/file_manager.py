import os
import shutil
import uuid
import zipfile
from typing import List, Tuple, Optional, Set

def get_app_dir() -> str:
    """アプリケーションルートディレクトリの絶対パスを取得"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # current_dir is <app_root>/codechecker/scanner
    return os.path.dirname(os.path.dirname(current_dir))

def get_temp_dir() -> str:
    """アプリ内完結型の一時フォルダ (.temp) を取得・作成 (ポータブル設計)"""
    temp_root = os.path.join(get_app_dir(), ".temp")
    os.makedirs(temp_root, exist_ok=True)
    return temp_root

# 除外するディレクトリ名
DEFAULT_EXCLUDED_DIRS: Set[str] = {
    ".git", ".svn", ".hg",
    "node_modules", "bower_components", "vendor",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    ".venv", "venv", "env", "virtualenv",
    "dist", "build", "out", "target", ".next", ".nuxt",
    ".idea", ".vscode", ".vs", ".temp",
    "coverage", ".nyc_output"
}

# PEバイナリ拡張子
PE_EXTENSIONS: Set[str] = {".exe", ".dll", ".sys", ".ocx"}

# 除外するファイル拡張子（メディア、アーカイブ、コンパイル中間成果物など）
EXCLUDED_EXTENSIONS: Set[str] = {
    ".so", ".dylib", ".bin",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".pyd", ".class", ".o", ".obj",
    ".woff", ".woff2", ".ttf", ".eot",
    ".lock", ".map", ".min.js", ".min.css"
}

class FileManager:
    def __init__(self):
        self._temp_dirs: List[str] = []

    def prepare_target(self, path: str) -> Tuple[str, bool]:
        """
        指定されたパスを準備する。
        ZIPファイルの場合は安全に一時フォルダに解凍してそのパスを返す。
        フォルダの場合はそのまま返す。
        戻り値: (scan_dir_path, is_temp)
        """
        path = os.path.abspath(path.strip())
        if not os.path.exists(path):
            raise FileNotFoundError(f"指定されたパスが存在しません: {path}")

        if os.path.isfile(path):
            if path.lower().endswith(".zip"):
                temp_dir = self.extract_zip_safely(path)
                self._temp_dirs.append(temp_dir)
                return temp_dir, True
            else:
                # 単一ファイルスキャン時はコピーせず直接対象とし、実ファイルパスを保持 (BUG-03)
                return path, False

        return path, False

    def extract_zip_safely(self, zip_path: str) -> str:
        """
        Zip Slip脆弱性を防ぎつつ、アプリ内一時フォルダ (.temp) に安全に解凍する。
        """
        temp_root = get_temp_dir()
        unique_name = f"zip_{uuid.uuid4().hex[:8]}"
        target_dir = os.path.abspath(os.path.join(temp_root, unique_name))
        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.infolist():
                # 安全なパス判定（Zip Slip 防止）
                member_path = os.path.abspath(os.path.join(target_dir, member.filename))
                if not member_path.startswith(target_dir + os.sep) and member_path != target_dir:
                    continue  # パストラバーサルの危険があるエントリはスキップ

                zf.extract(member, target_dir)

        return target_dir

    def collect_files(self, base_dir: str) -> Tuple[List[str], List[str]]:
        """
        スキャン対象となるソースコードファイル一覧と、PEバイナリ一覧を収集する。
        単一ファイルパスまたはディレクトリパスのいずれにも対応 (BUG-03)。
        戻り値: (source_files, pe_files)
        """
        source_files = []
        pe_files = []
        base_dir = os.path.abspath(base_dir)

        # 単一ファイル指定の場合
        if os.path.isfile(base_dir):
            ext = os.path.splitext(base_dir)[1].lower()
            if ext in PE_EXTENSIONS:
                try:
                    if os.path.getsize(base_dir) <= 100 * 1024 * 1024:
                        pe_files.append(base_dir)
                except OSError:
                    pass
            elif ext not in EXCLUDED_EXTENSIONS:
                try:
                    if os.path.getsize(base_dir) <= 10 * 1024 * 1024:
                        source_files.append(base_dir)
                except OSError:
                    pass
            return source_files, pe_files

        for root, dirs, files in os.walk(base_dir):
            # 除外ディレクトリを探索リストから除外 (in-place変更)
            dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDED_DIRS and not d.startswith(".")]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)

                # PEバイナリ (EXE/DLL等) の収集
                if ext in PE_EXTENSIONS:
                    try:
                        # 100MB以下のバイナリをスキャン対象とする
                        if os.path.getsize(full_path) <= 100 * 1024 * 1024:
                            pe_files.append(full_path)
                    except OSError:
                        pass
                    continue

                # その他の除外ファイル
                if ext in EXCLUDED_EXTENSIONS:
                    continue

                # ソースコード (10MB以下)
                try:
                    if os.path.getsize(full_path) <= 10 * 1024 * 1024:
                        source_files.append(full_path)
                except OSError:
                    continue

        return source_files, pe_files

    def collect_source_files(self, base_dir: str) -> List[str]:
        """後方互換用: ソースコードファイルのみを返す"""
        sources, _ = self.collect_files(base_dir)
        return sources

    def collect_pe_files(self, base_dir: str) -> List[str]:
        """PEバイナリファイル (EXE/DLL) のみを返す"""
        _, pe_files = self.collect_files(base_dir)
        return pe_files

    def cleanup(self):
        """作成した一時ディレクトリをすべて削除する (RES-01)。"""
        for temp_dir in list(self._temp_dirs):
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        self._temp_dirs.clear()

        # .temp フォルダ自体が空であれば削除
        temp_root = os.path.join(get_app_dir(), ".temp")
        if os.path.exists(temp_root):
            try:
                if not os.listdir(temp_root):
                    os.rmdir(temp_root)
            except Exception:
                pass

    def cleanup_all_temp(self):
        """アプリ内一時フォルダ (.temp) 配下の全残骸ディレクトリを完全に清掃する"""
        self.cleanup()
        temp_root = os.path.join(get_app_dir(), ".temp")
        if os.path.exists(temp_root):
            try:
                for item in os.listdir(temp_root):
                    item_path = os.path.join(temp_root, item)
                    if os.path.isdir(item_path) and (item.startswith("zip_") or item.startswith("file_")):
                        shutil.rmtree(item_path, ignore_errors=True)
                if not os.listdir(temp_root):
                    os.rmdir(temp_root)
            except Exception:
                pass

    def __del__(self):
        self.cleanup()

