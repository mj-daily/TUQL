import sqlite3

DB_NAME = "finance.db"

def get_db_connection():
    """建立並回傳設有 row_factory 的資料庫連線"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫與資料表"""
    with sqlite3.connect(DB_NAME) as conn:
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
