import sqlite3
import hashlib
import re
import pdfplumber

def init_db(db_name="finance.db"):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            account_number TEXT UNIQUE
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
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        );
        """)

# 定義哪些摘要關鍵字屬於「收入」
INCOME_KEYWORDS = ["薪資", "利息", "轉入", "存入", "退款"]

def parse_and_save(pdf_source, password, db_name="finance.db"):
    # pdf_source 現在可以是檔案路徑字串，也可以是 BytesIO 記憶體流
    try:
        with pdfplumber.open(pdf_source, password=password) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages])
    except Exception as e:
        # 如果密碼錯誤或 PDF 損壞，pdfplumber 會噴錯
        raise Exception(f"PDF 開啟失敗: {str(e)}")

    # 2. 正則解析 Header 與 Body
    acc_match = re.search(r"帳\s+號：([\d\*\-]+)", full_text)
    account_no = acc_match.group(1).strip() if acc_match else "Unknown"
    
    # 匹配模式：日期、時間、摘要、序號(非貪婪)、金額
    item_pattern = re.compile(r"(\d{3}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*?)\s+([\d,]+)(?=\n|$)")
    
    transactions = []
    for match in item_pattern.finditer(full_text):
        date, time, summary, ref_no, amount = match.groups()
        amount_val = float(amount.replace(',', ''))

        # --- 修正正負號邏輯 ---
        # 預設為支出 (負值) 除非摘要中包含收入關鍵字
        is_income = any(keyword in summary for keyword in INCOME_KEYWORDS)
        
        if not is_income:
            amount_val = -abs(amount_val)  # 強制轉為負值
        else:
            amount_val = abs(amount_val)   # 強制轉為正值
        # ----------------------
        
        # 生成唯一雜湊
        raw_id = f"{account_no}|{date}|{time}|{ref_no}|{amount_val}"
        t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
        
        transactions.append((date, time, summary, ref_no.strip(), amount_val, t_hash))

    # 3. 寫入資料庫
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO accounts (account_name, account_number) VALUES (?, ?)", ("中華郵政", account_no))
        cursor.execute("SELECT account_id FROM accounts WHERE account_number = ?", (account_no,))
        account_id = cursor.fetchone()[0]
        
        cursor.executemany(f"""
            INSERT OR IGNORE INTO transactions 
            (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
            VALUES ({account_id}, ?, ?, ?, ?, ?, ?)
        """, transactions)
        return cursor.rowcount, len(transactions)