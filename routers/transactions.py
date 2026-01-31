from fastapi import APIRouter, Body
from database import get_db_connection
from services import transaction_service

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

    try:
        success, msg = transaction_service.update_transaction(
            tx_id, account_id, date, time, summary, ref_no, amount
        )
        if success:
            return {"success": True, "message": msg}
        else:
            return {"success": False, "message": msg}
    except Exception as e:
        return {"success": False, "message": f"資料庫錯誤: {str(e)}"}

@router.post("/api/check-duplicates")
async def check_duplicates(payload: dict = Body(...)):
    account_id = payload.get("account_id")
    transactions = payload.get("transactions", [])
    exclude_id = payload.get("exclude_transaction_id") 
    
    if not account_id:
        return {"success": False, "message": "未指定帳戶"}

    try:
        results = transaction_service.check_duplicates(account_id, transactions, exclude_id)
        return {"success": True, "duplicates": results}
    except Exception as e:
        return {"success": False, "message": str(e)}
