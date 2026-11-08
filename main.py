"""CodeChecker 起動スクリプト
"""
import sys
import os

# プロジェクトルートを Python パスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codechecker.app import run_app

if __name__ == "__main__":
    run_app()

