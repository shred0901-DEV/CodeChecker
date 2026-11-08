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

# 静的解析対象プログラミング言語の拡張子ホワイトリスト (PERF-01)
SOURCE_EXTENSIONS: Set[str] = {
    # Python
    ".py", ".pyw",
    # JavaScript / TypeScript
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    # Java / Kotlin / Scala
    ".java", ".jav", ".kt", ".kts", ".scala",
    # C / C++ / Objective-C
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx", ".m", ".mm",
    # C#
    ".cs",
    # Go
    ".go",
    # Rust
    ".rs",
    # PHP
    ".php", ".phtml", ".php4", ".php5", ".php7", ".phps",
    # Ruby
    ".rb", ".erb",
    # Shell / Script
    ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1",
    # Database / SQL
    ".sql",
    # Web markup / templates
    ".html", ".htm",
}

# 除外するファイル拡張子（メディア、アーカイブ、コンパイル中間成果物など）
EXCLUDED_EXTENSIONS: Set[str] = {
    ".so", ".dylib", ".bin",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".pyc", ".pyo", ".pyd", ".class", ".o", ".obj",
    ".woff", ".woff2", ".ttf", ".eot",
    ".lock", ".map", ".min.js", ".min.css",
    # データファイル・ログ等の除外 (PERF-01)
    ".json", ".csv", ".tsv", ".log", ".sqlite", ".db", ".xml", ".txt", ".md"
}

# Zip Bomb 防御定数 (SEC-03)
MAX_TOTAL_EXTRACT_SIZE: int = 200 * 1024 * 1024  # 展開後総サイズ上限: 200MB
MAX_EXTRACT_FILES: int = 1000                    # 総ファイル数上限: 1,000ファイル
MAX_SINGLE_FILE_SIZE: int = 100 * 1024 * 1024    # 単一ファイル上限: 100MB
MAX_COMPRESSION_RATIO: float = 200.0             # 圧縮比率上限 (10MB以上かつ200倍以上圧縮)

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

    def extract_zip_safely(
        self,
        zip_path: str,
        max_total_size: int = MAX_TOTAL_EXTRACT_SIZE,
        max_files: int = MAX_EXTRACT_FILES
    ) -> str:
        """
        Zip Slip脆弱性および Zip Bomb（サイズ爆発・ファイル数過多）を防ぎつつ、
        アプリ内一時フォルダ (.temp) に安全に解凍する (SEC-03)。
        """
        temp_root = get_temp_dir()
        unique_name = f"zip_{uuid.uuid4().hex[:8]}"
        target_dir = os.path.abspath(os.path.join(temp_root, unique_name))

        with zipfile.ZipFile(zip_path, 'r') as zf:
            members = zf.infolist()

            # 1. 総ファイル数チェック (Zip Bomb 防御)
            if len(members) > max_files:
                raise ValueError(
                    f"ZIP展開上限を超過しました: ファイル数 ({len(members):,}件) が上限 ({max_files:,}件) を超えています (Zip Bomb防御)"
                )

            # 2. メタデータに基づく展開前サイズ & 圧縮率事前チェック
            total_uncompressed_size = 0
            for member in members:
                # 安全なパス判定 (Zip Slip 防止)
                member_path = os.path.abspath(os.path.join(target_dir, member.filename))
                if not member_path.startswith(target_dir + os.sep) and member_path != target_dir:
                    continue  # パストラバーサルの危険があるエントリはスキップ

                if member.file_size < 0:
                    raise ValueError("ZIPヘッダーが不正です: 負のファイルサイズが指定されています")

                total_uncompressed_size += member.file_size
                if total_uncompressed_size > max_total_size:
                    raise ValueError(
                        f"ZIP展開上限を超過しました: 展開後総サイズが上限 ({max_total_size // (1024 * 1024)}MB) を超えています (Zip Bomb防御)"
                    )

                if member.file_size > MAX_SINGLE_FILE_SIZE:
                    raise ValueError(
                        f"ZIP展開上限を超過しました: 単一ファイルサイズ ({member.filename}) が上限 ({MAX_SINGLE_FILE_SIZE // (1024 * 1024)}MB) を超えています"
                    )

                # 異常圧縮率チェック (10MB以上かつ200倍以上圧縮)
                if member.file_size > 10 * 1024 * 1024 and member.compress_size > 0:
                    ratio = member.file_size / member.compress_size
                    if ratio > MAX_COMPRESSION_RATIO:
                        raise ValueError(
                            f"ZIP展開上限を超過しました: 異常な圧縮率 ({ratio:.1f}倍) を検出しました (Zip Bomb防御)"
                        )

            # 3. 実際の解凍処理 (展開中ストリームの実サイズ二重ガード)
            os.makedirs(target_dir, exist_ok=True)
            extracted_bytes = 0
            try:
                for member in members:
                    member_path = os.path.abspath(os.path.join(target_dir, member.filename))
                    if not member_path.startswith(target_dir + os.sep) and member_path != target_dir:
                        continue

                    if member.is_dir():
                        os.makedirs(member_path, exist_ok=True)
                        continue

                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    with zf.open(member) as source, open(member_path, "wb") as target:
                        while True:
                            chunk = source.read(64 * 1024)
                            if not chunk:
                                break
                            extracted_bytes += len(chunk)
                            if extracted_bytes > max_total_size:
                                raise ValueError(
                                    f"ZIP展開上限を超過しました: 展開中実データが上限 ({max_total_size // (1024 * 1024)}MB) を超えました (Zip Bomb防御)"
                                )
                            target.write(chunk)
            except Exception:
                shutil.rmtree(target_dir, ignore_errors=True)
                raise

        return target_dir

    def collect_files(self, base_dir: str) -> Tuple[List[str], List[str]]:
        """
        スキャン対象となるソースコードファイル一覧と、PEバイナリ一覧を収集する。
        対象言語の拡張子ホワイトリスト（SOURCE_EXTENSIONS）に基づいて高速収集 (PERF-01)。
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
            elif ext in SOURCE_EXTENSIONS:
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

                # PEバイナリ (EXE/DLL等) の収集 (100MB以下)
                if ext in PE_EXTENSIONS:
                    try:
                        if os.path.getsize(full_path) <= 100 * 1024 * 1024:
                            pe_files.append(full_path)
                    except OSError:
                        pass
                    continue

                # ソースコードホワイトリスト判定 (10MB以下) (PERF-01)
                if ext in SOURCE_EXTENSIONS:
                    try:
                        if os.path.getsize(full_path) <= 10 * 1024 * 1024:
                            source_files.append(full_path)
                    except OSError:
                        pass

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

