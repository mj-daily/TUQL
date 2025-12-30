import sqlite3
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

def parse_pdf(pdf_stream, password):
    """
    只負責解析 PDF，回傳帳號字串與交易列表 (不寫入 DB)
    """
    try:
        with pdfplumber.open(pdf_stream, password=password) as pdf:
            full_text = "\n".join([page.extract_text() for page in pdf.pages])
    except Exception as e:
        raise Exception(f"PDF 開啟失敗: {str(e)}")

    # [修改] 帳號提取邏輯
    # 支援： "帳號：12345", "帳號：***345", "帳號 12345"
    acc_match = re.search(r"帳\s+號[:：\s]*([\d\*\-]+)", full_text)
    raw_acc = acc_match.group(1).strip() if acc_match else "Unknown"
    
    # 移除星號與橫槓，只留數字
    last_5_acc = raw_acc[-5:] if len(raw_acc) >= 5 else raw_acc
    account_no_parsed = last_5_acc.replace('*', '').replace('-', '')
    
    INCOME_KEYWORDS = ["薪資", "利息", "轉入", "存入", "退款"]
    item_pattern = re.compile(r"(\d{3}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(.*?)\s+([\d,]+)(?=\n|$)")
    
    transactions = []
    for match in item_pattern.finditer(full_text):
        date, time, summary, ref_no, amount = match.groups()
        amount_val = float(amount.replace(',', ''))
        
        if not any(kw in summary for kw in INCOME_KEYWORDS):
            amount_val = -abs(amount_val)
        
        transactions.append({
            "date": date,
            "time": time,
            "summary": summary,
            "ref_no": ref_no.strip(),
            "amount": amount_val
        })
        
    return account_no_parsed, transactions

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
    full_text = " ".join(result).split("交易") # 以 "交易" 分割為三段
    
    # --- 資料提取邏輯 ---
    
    # [帳號] 抓取 "帳號" 最後 5 碼
    account_match = re.search(r"帳\s*號\s*[\*\d\-]*?(\d{5})", full_text[0])
    account_number = account_match.group(1) if account_match else ""

    # [序號] 抓取 "資訊" 後的編號
    final_ref = full_text[2].split()[1]
    
    # [金額] 抓取 full_text[0] 最後一組數字
    amount_val = full_text[0].split()[-1]
    amount_val = float(amount_val.replace(',', ''))

    # [日期] & [時間]
    date_match = re.search(r"(\d{3}/\d{2}/\d{2})", full_text[1])
    time_match = re.search(r"(\d{2}:\d{2}:\d{2})", full_text[1])
    
    # [摘要] 剝離 "帳號" 後，取 full_text[0] 中的所有中文字作為摘要
    summary = "".join(re.findall(r"[\u4e00-\u9fff]", full_text[0].replace("帳號", "")))

    return {
        "date": date_match.group(1) if date_match else "",
        "time": time_match.group(1) if time_match else "00:00:00",
        "summary": summary,
        "amount": amount_val,
        "ref_no": final_ref,
        "account_number": account_number
    }