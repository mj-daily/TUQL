# parser.py
import sqlite3
from parsers.post import PostOfficeParser
from parsers.tbb import TBBParser

def init_db(db_name="finance.db"):
    # (保持原本的資料庫初始化程式碼不變，這裡省略以節省篇幅)
    # 請直接複製原本 parser.py 的 init_db 函式內容
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL UNIQUE,
            account_number TEXT NOT NULL,
            bank_code TEXT NOT NULL,
            initial_balance REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            trans_date TEXT NOT NULL,
            trans_time TEXT,
            summary TEXT,
            ref_no TEXT,
            amount REAL NOT NULL,
            trace_hash TEXT UNIQUE NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
        );
        """)

def get_parser(bank_code):
    """解析器工廠：根據銀行代碼回傳對應的解析器實例"""
    if bank_code == '050':
        return TBBParser()
    elif bank_code == '700':
        return PostOfficeParser()
    else:
        # 預設使用郵局 (兼容舊版)，或可拋出錯誤
        return PostOfficeParser()