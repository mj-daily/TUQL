from fastapi import APIRouter, Body
import sqlite3
from database import get_db_connection

router = APIRouter()

@router.get("/api/accounts")
async def get_accounts():
    conn = get_db_connection()
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

@router.post("/api/account")
async def create_account(payload: dict = Body(...)):
    name = payload.get("name")
    number = payload.get("number")
    bank_code = payload.get("bank_code") 
    init_balance = payload.get("init_balance", 0)

    if not bank_code:
        return {"success": False, "message": "銀行代碼為必填欄位"}

    short_num = number[-5:] if number and len(number) >= 5 else number

    try:
        with get_db_connection() as conn:
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

@router.put("/api/account/{acc_id}")
async def update_account(acc_id: int, payload: dict = Body(...)):
    name = payload.get("name")
    bank_code = payload.get("bank_code") 
    number = payload.get("number")
    
    if not bank_code:
        return {"success": False, "message": "銀行代碼為必填欄位"}

    short_num = number[-5:] if number and len(number) >= 5 else number
    
    try:
        with get_db_connection() as conn:
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

@router.delete("/api/account/{acc_id}")
async def delete_account(acc_id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE account_id = ?", (acc_id,))
            if cursor.fetchone()[0] > 0:
                return {"success": False, "message": "此帳戶尚有交易資料，無法刪除"}
            
            cursor.execute("DELETE FROM accounts WHERE account_id = ?", (acc_id,))
            return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
