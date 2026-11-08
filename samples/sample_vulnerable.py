import sqlite3
import os
import subprocess

# 1. ハードコードされたシークレット
AWS_ACCESS_KEY = "AKIA1234567890ABCDEF"
DB_PASSWORD = "SuperSecretPassword123!"

def search_user(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # 2. SQLインジェクション (文字列連結)
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()

def run_ping(host):
    # 3. コマンドインジェクション
    os.system("ping -c 1 " + host)

def parse_input(user_data):
    # 4. 危険なeval
    return eval(user_data)

