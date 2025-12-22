#%% main.py
from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import parser
import os
import io
import hashlib

app = FastAPI()

# 初始化資料庫
parser.init_db()

# 掛載靜態檔案
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/api/transactions")
async def get_transactions():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, a.account_name FROM transactions t 
        JOIN accounts a ON t.account_id = a.account_id 
        ORDER BY t.trans_date DESC, t.trans_time DESC
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.get("/api/accounts")
async def get_accounts():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 使用 LEFT JOIN 計算每個帳戶的餘額 (總收入 - 總支出)
    # COALESCE 確保沒有交易的帳戶餘額顯示為 0
    cursor.execute("""
        SELECT a.account_id, a.account_name, a.account_number, 
               COALESCE(SUM(t.amount), 0) as balance
        FROM accounts a
        LEFT JOIN transactions t ON a.account_id = t.account_id
        GROUP BY a.account_id
    """)
    
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), password: str = Form(...)):
    try:
        file_content = await file.read()
        pdf_stream = io.BytesIO(file_content)
        added, total = parser.parse_and_save(pdf_stream, password)
        msg = f"PDF 解析成功：共 {total} 筆，新增 {added} 筆"
    except Exception as e:
        msg = f"解析失敗: {str(e)}"
    return {"message": msg}

# --- 新增：圖片辨識 API ---
@app.post("/api/ocr-identify")
async def ocr_identify(file: UploadFile = File(...)):
    try:
        content = await file.read()
        # 呼叫 parser 裡的 EasyOCR 邏輯
        data = parser.recognize_screenshot(content)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "message": str(e)}
    
# --- 新增：手動/OCR 資料存入 API ---
@app.post("/api/save-manual")
async def save_manual(payload: dict = Body(...)):
    with sqlite3.connect("finance.db") as conn:
        cursor = conn.cursor()
        
        # 取得預設帳戶 ID (若無帳戶則先建立)
        cursor.execute("INSERT OR IGNORE INTO accounts (account_name, account_number) VALUES (?, ?)", ("中華郵政", "Manual-Import"))
        cursor.execute("SELECT account_id FROM accounts LIMIT 1")
        account_id = cursor.fetchone()[0]
        
        # 建立去重雜湊
        raw_id = f"MANUAL|{payload['date']}|{payload['time']}|{payload['amount']}|{payload['ref_no']}"
        t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
        
        try:
            cursor.execute("""
                INSERT INTO transactions (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (account_id, payload['date'], payload['time'], payload['summary'], payload['ref_no'], payload['amount'], t_hash))
            return {"success": True}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "此筆資料已存在 (重複匯入)"}

@app.delete("/api/transaction/{tx_id}")
async def delete_transaction(tx_id: int):
    try:
        with sqlite3.connect("finance.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", (tx_id,))
            if cursor.rowcount == 0:
                return {"success": False, "message": "找不到該筆交易"}
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/api/transaction/{tx_id}")
async def update_transaction(tx_id: int, payload: dict = Body(...)):
    try:
        with sqlite3.connect("finance.db") as conn:
            cursor = conn.cursor()
            # 這裡我們允許修改日期、時間、摘要、金額、序號
            # 注意：這裡不重新計算 hash，因為這只是修正資料
            cursor.execute("""
                UPDATE transactions 
                SET trans_date = ?, trans_time = ?, summary = ?, amount = ?, ref_no = ?
                WHERE transaction_id = ?
            """, (payload['date'], payload['time'], payload['summary'], payload['amount'], payload['ref_no'], tx_id))
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
#%%
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)