from fastapi import APIRouter, Body
import sqlite3
import hashlib
from database import get_db_connection

router = APIRouter()

@router.get("/api/transactions")
async def get_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, a.account_name FROM transactions t 
        JOIN accounts a ON t.account_id = a.account_id 
        ORDER BY t.trans_date DESC, t.trans_time DESC
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@router.delete("/api/transaction/{tx_id}")
async def delete_transaction(tx_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE transaction_id = ?", (tx_id,))
            if cursor.rowcount == 0:
                return {"success": False, "message": "找不到該筆交易"}
            conn.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.put("/api/transaction/{tx_id}")
async def edit_transaction(tx_id: int, item: dict = Body(...)):
    date = item.get("date")
    time = item.get("time", "00:00:00")
    summary = item.get("summary")
    amount = item.get("amount")
    ref_no = item.get("ref_no", "")
    account_id = item.get("account_id") 

    raw_id = f"MANUAL|{account_id}|{date}|{time}|{amount}|{ref_no}"
    new_hash = hashlib.sha256(raw_id.encode()).hexdigest()

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT transaction_id FROM transactions 
                WHERE trace_hash = ? AND transaction_id != ?
            """, (new_hash, tx_id))
            collision = cursor.fetchone()
            
            if collision:
                return {"success": False, "message": "修改後的資料與現有交易重複，無法儲存。"}

            cursor.execute("""
                UPDATE transactions 
                SET trans_date=?, trans_time=?, summary=?, amount=?, ref_no=?, trace_hash=?
                WHERE transaction_id=?
            """, (date, time, summary, amount, ref_no, new_hash, tx_id))
            
            if cursor.rowcount == 0:
                return {"success": False, "message": "找不到該筆交易"}
                
            conn.commit()
            return {"success": True, "message": "更新成功"}
    except Exception as e:
        return {"success": False, "message": f"資料庫錯誤: {str(e)}"}

@router.post("/api/check-duplicates")
async def check_duplicates(payload: dict = Body(...)):
    account_id = payload.get("account_id")
    transactions = payload.get("transactions", [])
    exclude_id = payload.get("exclude_transaction_id") 
    
    if not account_id:
        return {"success": False, "message": "未指定帳戶"}

    results = []
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for tx in transactions:
            date = tx.get('date', '')
            time = tx.get('time', '')
            ref_no = tx.get('ref_no', '')
            amount = tx.get('amount', 0)
            
            raw_id_batch = f"BATCH|{account_id}|{date}|{time}|{ref_no}|{amount}"
            hash_batch = hashlib.sha256(raw_id_batch.encode()).hexdigest()

            raw_id_manual = f"MANUAL|{account_id}|{date}|{time}|{amount}|{ref_no}"
            hash_manual = hashlib.sha256(raw_id_manual.encode()).hexdigest()
            
            query = """
                SELECT 1 FROM transactions 
                WHERE (trace_hash = ? OR trace_hash = ?)
            """
            params = [hash_batch, hash_manual]
            
            if exclude_id:
                query += " AND transaction_id != ?"
                params.append(exclude_id)
            
            cursor.execute(query, tuple(params))
            exists = cursor.fetchone() is not None
            results.append(exists)

    return {"success": True, "duplicates": results}
