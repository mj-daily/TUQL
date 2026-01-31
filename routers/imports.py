from fastapi import APIRouter, UploadFile, File, Form, Body
from typing import List
import sqlite3
import hashlib
import io
import parser
from database import get_db_connection

router = APIRouter()

@router.post("/api/pdf-preview")
async def pdf_preview(
    file: UploadFile = File(...), 
    password: str = Form(...),
    bank_code: str = Form(...) 
):
    try:
        content = await file.read()
        pdf_stream = io.BytesIO(content)
        
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
    
@router.post("/api/save-batch")
async def save_batch(payload: dict = Body(...)):
    account_id = payload.get("account_id")
    transactions = payload.get("transactions", [])
    
    if not account_id:
        return {"success": False, "message": "未指定匯入帳戶"}

    saved_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for tx in transactions:
            raw_id = f"BATCH|{account_id}|{tx['date']}|{tx['time']}|{tx['ref_no']}|{tx['amount']}"
            t_hash = hashlib.sha256(raw_id.encode()).hexdigest()
            
            try:
                cursor.execute("""
                    INSERT INTO transactions (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (account_id, tx['date'], tx['time'], tx['summary'], tx['ref_no'], tx['amount'], t_hash))
                saved_count += 1
            except sqlite3.IntegrityError:
                continue 

    return {"success": True, "message": f"成功匯入 {saved_count} 筆 (共 {len(transactions)} 筆)"}

@router.post("/api/ocr-identify")
async def ocr_identify(
    files: List[UploadFile] = File(...),
    bank_code: str = Form(...) 
):
    results = []
    errors = []
    
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

@router.post("/api/save-manual")
async def save_manual(payload: dict = Body(...)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        target_acc_num = payload.get('account_number', 'Manual-Import')
        
        cursor.execute("SELECT account_id FROM accounts WHERE account_number = ?", (target_acc_num,))
        row = cursor.fetchone()
        
        if row:
            account_id = row[0]
        else:
            cursor.execute("INSERT INTO accounts (account_name, account_number) VALUES (?, ?)", 
                           ("中華郵政(OCR)", target_acc_num))
            account_id = cursor.lastrowid
        
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
