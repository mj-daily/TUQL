import sqlite3
import hashlib
import re
import pdfplumber
import easyocr
import cv2
import numpy as np

# 全域初始化 OCR Reader (建議開啟 GPU，第一次執行會下載模型)
# 使用 'ch_tra' (繁體中文) 與 'en' (英文)
reader = easyocr.Reader(['ch_tra', 'en'], gpu=True)

def init_db(db_name="finance.db"):
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;") # 啟用外鍵約束
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL UNIQUE, -- 暱稱唯一
            account_number TEXT NOT NULL,      -- 帳號只存末 5 碼
            bank_code TEXT NOT NULL,           -- 銀行代碼
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
    raw_acc = acc_match.group(1).strip() if acc_match else "Unknown"
    account_no_5 = raw_acc[-5:] if len(raw_acc) >= 5 else raw_acc
    
    # 定義哪些摘要關鍵字屬於「收入」
    INCOME_KEYWORDS = ["薪資", "利息", "轉入", "存入", "退款"]
    item_pattern = re.compile(r"(\d{3}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*?)\s+([\d,]+)(?=\n|$)")
    
    transactions = []
    for match in item_pattern.finditer(full_text):
        date, time, summary, ref_no, amount = match.groups()
        amount_val = float(amount.replace(',', ''))

        # 修正正負號邏輯：若非收入關鍵字，預設為支出 (負值)
        if not any(kw in summary for kw in INCOME_KEYWORDS):
            amount_val = -abs(amount_val)
        
        # 生成唯一雜湊
        raw_id = f"{account_no_5}|{date}|{time}|{ref_no}|{amount_val}"
        t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
        transactions.append((date, time, summary, ref_no.strip(), amount_val, t_hash))

    # 3. 寫入資料庫
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        # 嘗試尋找帳戶
        cursor.execute("SELECT account_id FROM accounts WHERE account_number = ?", (account_no_5,))
        row = cursor.fetchone()
        if row:
            account_id = row[0]
        else:
            # 若不存在，建立一個預設帳戶，名稱為「未知帳戶_末5碼」，並指定銀行代碼為 "000"
            # 使用者可後續再修改帳戶名稱
            acc_name = f"未知帳戶_{account_no_5}"
            try:
                cursor.execute("INSERT INTO accounts (account_name, account_number, bank_code) VALUES (?, ?, ?)", 
                               (acc_name, account_no_5, "000"))
                account_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor.execute("SELECT account_id FROM accounts WHERE account_name = ?", (acc_name,))
                account_id = cursor.fetchone()[0]
        
        cursor.executemany(f"""
            INSERT OR IGNORE INTO transactions 
            (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
            VALUES ({account_id}, ?, ?, ?, ?, ?, ?)
        """, transactions)
        return cursor.rowcount, len(transactions)

def preprocess_image(image_bytes):
    """
    圖像前處理：強化特徵以區分 G/6
    """
    # 1. 將 bytes 轉換為 OpenCV 圖像格式
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 2. 轉為灰階 (去除色彩雜訊)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. CLAHE (限制對比度自適應直方圖均衡化)
    # 這步是關鍵：它會增強局部細節，讓 G 的中間橫槓更明顯，避免被誤認為 6
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_img = clahe.apply(gray)
    
    # (可選) 二值化：若背景真的很雜，可開啟下面這行
    # _, binary_img = cv2.threshold(enhanced_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return enhanced_img

def recognize_screenshot(image_bytes):
    """
    OCR 辨識入口
    """
    # 1. 執行前處理
    processed_img = preprocess_image(image_bytes)
    
    # 2. 執行 OCR
    # paragraph=True: 利用上下文來輔助判定 (例如看到 Pay 知道前面是 G 而不是 6)
    # decoder='beamsearch': 使用更聰明的解碼搜尋
    result = reader.readtext(
        processed_img, 
        detail=0, 
        decoder='beamsearch', 
        beamWidth=10, 
        paragraph=True,
        add_margin=0.2
    )
    full_text = " ".join(result)
    print("OCR 辨識結果：", full_text)  # 除錯用
    
    # --- 資料提取邏輯 ---
    
    # [帳號] 抓取 "帳號" 最後 5 碼
    acc_match = re.search(r"(?:帳號|轉出帳號)[:：\s]*[\d\*]*(\d{5})", full_text)
    account_number = acc_match.group(1) if acc_match else ""

    # [序號] 使用錨點定位 (Anchor: 交易資訊/交易序號)
    # 找關鍵字後面接的 5碼以上英數字
    ref_match = re.search(r"(?:交易資訊|交易序號|附言)[:：\s]*([A-Z0-9-]{5,})", full_text)
    final_ref = ref_match.group(1) if ref_match else "IMG_IMPORT"
    
    # [金額] 優先找千分位逗號
    comma_matches = re.findall(r"(?<![\d.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?)", full_text)
    amount_val = 0.0
    if comma_matches:
        best_match = max(comma_matches, key=len)
        amount_val = float(best_match.replace(',', ''))
    else:
        # 備用：找關鍵字後的數字
        kw_amount = re.search(r"(?:金額|薪\s*資|存入|支出|NT\$)[^0-9\-]*([-\d]+(?:\.\d+)?)", full_text)
        if kw_amount:
            try: amount_val = float(kw_amount.group(1))
            except: pass

    # [日期] & [時間]
    date_match = re.search(r"(\d{3}/\d{2}/\d{2})", full_text)
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", full_text)
    
    # [摘要] 根據關鍵字判斷
    summary = "單筆匯入"
    if "薪" in full_text and "資" in full_text:
        summary = "薪資"
        amount_val = abs(amount_val)
    elif "提款" in full_text:
        summary = "提款"
        amount_val = -abs(amount_val)
    elif "轉帳" in full_text:
        summary = "轉帳"
        amount_val = -abs(amount_val)

    return {
        "date": date_match.group(1) if date_match else "",
        "time": time_match.group(1) if time_match else "00:00:00",
        "summary": summary,
        "amount": amount_val,
        "ref_no": final_ref,
        "account_number": account_number
    }