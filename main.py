#%% main.py
from typing import List
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

# --- 交易相關 API ---
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

@app.post("/api/pdf-preview")
async def pdf_preview(
    file: UploadFile = File(...), 
    password: str = Form(...),
    bank_code: str = Form(...) # [新增]
):
    try:
        content = await file.read()
        pdf_stream = io.BytesIO(content)
        
        # 使用工廠取得解析器
        parser_instance = parser.get_parser(bank_code)
        acc_num, txs = parser_instance.parse_pdf(pdf_stream, password)
        
        return {
            "success": True, 
            "data": {
                "account_number": acc_num,
                "transactions": txs,
                "count": len(txs)
            }
        }
    except Exception as e:
        return {"success": False, "message": f"解析失敗: {str(e)}"}
    
@app.post("/api/save-batch")
async def save_batch(payload: dict = Body(...)):
    """
    Payload 結構:
    {
        "account_id": 1,
        "transactions": [ ... ]
    }
    """
    account_id = payload.get("account_id")
    transactions = payload.get("transactions", [])
    
    if not account_id:
        return {"success": False, "message": "未指定匯入帳戶"}

    saved_count = 0
    with sqlite3.connect("finance.db") as conn:
        cursor = conn.cursor()
        
        for tx in transactions:
            # 這裡重新生成 hash，確保綁定的是正確的 account_id
            raw_id = f"BATCH|{account_id}|{tx['date']}|{tx['time']}|{tx['ref_no']}|{tx['amount']}"
            t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
            
            try:
                cursor.execute("""
                    INSERT INTO transactions (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (account_id, tx['date'], tx['time'], tx['summary'], tx['ref_no'], tx['amount'], t_hash))
                saved_count += 1
            except sqlite3.IntegrityError:
                continue # 忽略重複

    return {"success": True, "message": f"成功匯入 {saved_count} 筆 (共 {len(transactions)} 筆)"}

@app.post("/api/ocr-identify")
async def ocr_identify(
    files: List[UploadFile] = File(...),
    bank_code: str = Form(...) # [新增]
):
    results = []
    errors = []
    
    # 取得解析器 (假設批次上傳的都是同一家銀行)
    parser_instance = parser.get_parser(bank_code)
    
    for file in files:
        try:
            content = await file.read()
            data = parser_instance.recognize_screenshot(content)
            results.append(data)
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            
    if not results and errors:
        return {"success": False, "message": "; ".join(errors)}
        
    return {
        "success": True, 
        "data": results,
        "errors": errors
    }

@app.post("/api/save-manual")
async def save_manual(payload: dict = Body(...)):
    with sqlite3.connect("finance.db") as conn:
        cursor = conn.cursor()
        
        # [修改重點]：根據前端傳來的帳號號碼進行歸戶
        target_acc_num = payload.get('account_number', 'Manual-Import')
        
        # 1. 先嘗試找這個帳號是否存在
        cursor.execute("SELECT account_id FROM accounts WHERE account_number = ?", (target_acc_num,))
        row = cursor.fetchone()
        
        if row:
            account_id = row[0]
        else:
            # 2. 如果不存在 (例如第一次 OCR 某個新帳號)，則自動建立
            # 注意：這裡預設名稱給 "中華郵政(OCR)"，你可以手動進資料庫改名
            cursor.execute("INSERT INTO accounts (account_name, account_number) VALUES (?, ?)", 
                           ("中華郵政(OCR)", target_acc_num))
            account_id = cursor.lastrowid
        
        # 建立去重雜湊 (加入 account_id 確保不同帳號的相同交易不會衝突)
        raw_id = f"MANUAL|{account_id}|{payload['date']}|{payload['time']}|{payload['amount']}|{payload['ref_no']}"
        t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
        
        try:
            cursor.execute("""
                INSERT INTO transactions (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (account_id, payload['date'], payload['time'], payload['summary'], payload['ref_no'], payload['amount'], t_hash))
            return {"success": True}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "此筆資料已存在"}

# --- 帳戶管理 API ---
@app.get("/api/accounts")
async def get_accounts():
    conn = sqlite3.connect("finance.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.account_id, a.account_name, a.account_number, a.bank_code, a.initial_balance,
               (a.initial_balance + COALESCE(SUM(t.amount), 0)) as balance
        FROM accounts a
        LEFT JOIN transactions t ON a.account_id = t.account_id
        GROUP BY a.account_id
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.post("/api/account")
async def create_account(payload: dict = Body(...)):
    name = payload.get("name")
    number = payload.get("number")
    bank_code = payload.get("bank_code") # 必填
    init_balance = payload.get("init_balance", 0)

    # 驗證
    if not bank_code:
        return {"success": False, "message": "銀行代碼為必填欄位"}

    short_num = number[-5:] if number and len(number) >= 5 else number

    try:
        with sqlite3.connect("finance.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (account_name, account_number, bank_code, initial_balance)
                VALUES (?, ?, ?, ?)
            """, (name, short_num, bank_code, init_balance))
            return {"success": True, "id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "帳戶暱稱已存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/api/account/{acc_id}")
async def update_account(acc_id: int, payload: dict = Body(...)):
    name = payload.get("name")
    bank_code = payload.get("bank_code") # 必填
    number = payload.get("number")
    
    if not bank_code:
        return {"success": False, "message": "銀行代碼為必填欄位"}

    short_num = number[-5:] if number and len(number) >= 5 else number
    
    try:
        with sqlite3.connect("finance.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts 
                SET account_name = ?, account_number = ?, bank_code = ?, initial_balance = ?
                WHERE account_id = ?
            """, (name, short_num, bank_code, payload['init_balance'], acc_id))
            return {"success": True}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "帳戶暱稱已存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/api/account/{acc_id}")
async def delete_account(acc_id: int):
    try:
        with sqlite3.connect("finance.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE account_id = ?", (acc_id,))
            if cursor.fetchone()[0] > 0:
                return {"success": False, "message": "此帳戶尚有交易資料，無法刪除"}
            
            cursor.execute("DELETE FROM accounts WHERE account_id = ?", (acc_id,))
            return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
    
# [新增] 檢查重複 API
@app.post("/api/check-duplicates")
async def check_duplicates(payload: dict = Body(...)):
    """
    Payload: { "account_id": 1, "transactions": [ ... ] }
    回傳: [true, false, true...] (對應每一筆是否重複)
    """
    account_id = payload.get("account_id")
    transactions = payload.get("transactions", [])
    
    if not account_id:
        return {"success": False, "message": "未指定帳戶"}

    results = []
    
    with sqlite3.connect("finance.db") as conn:
        cursor = conn.cursor()
        
        for tx in transactions:
            # 使用與 save-batch 完全相同的 Hash 邏輯
            # 注意：必須確保欄位都存在，若無則給空字串
            date = tx.get('date', '')
            time = tx.get('time', '')
            ref_no = tx.get('ref_no', '')
            amount = tx.get('amount', 0)
            
            raw_id = f"BATCH|{account_id}|{date}|{time}|{ref_no}|{amount}"
            t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
            
            # 查詢雜湊是否存在
            cursor.execute("SELECT 1 FROM transactions WHERE trace_hash = ?", (t_hash,))
            exists = cursor.fetchone() is not None
            results.append(exists)

    return {"success": True, "duplicates": results}

#%%
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)