import sqlite3
import hashlib
import re
import pdfplumber
import easyocr
import io

# 全域初始化 OCR Reader (建議開啟 GPU，第一次執行會下載模型)
# 使用 'ch_tra' (繁體中文) 與 'en' (英文)
reader = easyocr.Reader(['ch_tra', 'en'], gpu=True)

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
    
    # 定義哪些摘要關鍵字屬於「收入」
    INCOME_KEYWORDS = ["薪資", "利息", "轉入", "存入", "退款"]

    # 匹配模式：日期、時間、摘要、序號(非貪婪)、金額
    item_pattern = re.compile(r"(\d{3}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*?)\s+([\d,]+)(?=\n|$)")
    
    transactions = []
    for match in item_pattern.finditer(full_text):
        date, time, summary, ref_no, amount = match.groups()
        amount_val = float(amount.replace(',', ''))

        # 修正正負號邏輯：若非收入關鍵字，預設為支出 (負值)
        if not any(kw in summary for kw in INCOME_KEYWORDS):
            amount_val = -abs(amount_val)
        
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
    
def recognize_screenshot(image_bytes):
    """
    新增功能：使用 EasyOCR 解析單筆交易截圖
    """
    # 使用 BeamSearch 解碼器解決 G/6 誤認問題
    # beamWidth=10 雖然稍慢但準確度較高
    result = reader.readtext(
        image_bytes, 
        detail=0, 
        decoder='beamsearch', 
        beamWidth=10, 
        paragraph=True,
        add_margin=0.2  # 增加邊距以識別 G 的開口
    )
    full_text = " ".join(result)
    
    # --- 1. 使用 Regex 提取資料 ---
    # 日期: 114/11/19
    date_match = re.search(r"(\d{3}/\d{2}/\d{2})", full_text)
    # 時間: 01:19:13
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", full_text)
    
    # 金額提取策略：找數字與逗號的組合，且長度大於2
    amounts = re.findall(r"[\d,]{2,}", full_text)
    print("Detected amounts:", amounts)
    # 過濾掉日期 (含斜線) 與時間 (含冒號)
    valid_amounts = [a for a in amounts if '/' not in a and ':' not in a]
    
    # 金額處理：取最長的一個 (通常金額位數較多)，或第一個
    amount_val = 0.0
    if valid_amounts:
        # 取看起來最像金額的 (最長的字串)
        raw_amount = max(valid_amounts, key=len)
        amount_val = float(raw_amount.replace(',', ''))

    # --- 2. 摘要智慧判斷 ---
    summary = "單筆匯入"
    if "薪" in full_text and "資" in full_text:
        summary = "薪資"
    elif "提款" in full_text:
        summary = "提款"
        # 提款通常是整數，且為支出
        amount_val = -abs(amount_val)
    elif "轉帳" in full_text:
        summary = "轉帳"
        amount_val = -abs(amount_val)
    
    # 若摘要是薪資，強制轉為正值
    if summary == "薪資":
        amount_val = abs(amount_val)

    # 交易序號 (如 GR-07871234)
    ref_match = re.search(r"([A-Z]{2}-[\d]+)", full_text)

    return {
        "date": date_match.group(1) if date_match else "",
        "time": time_match.group(1) if time_match else "00:00:00",
        "summary": summary,
        "amount": amount_val,
        "ref_no": ref_match.group(1) if ref_match else "IMG_IMPORT"
    }