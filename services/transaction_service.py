import hashlib
import sqlite3
from database import get_db_connection

def compute_transaction_hash(account_id, date, time, ref_no, amount, source_type="MANUAL"):
    """
    Computes a standardized hash for a transaction.
    Format: source_type|account_id|date|time|ref_no|amount
    """
    # Ensure standard string representation and order: ref_no BEFORE amount
    # Ensure ref_no is string (handle None)
    ref_str = str(ref_no) if ref_no is not None else ""
    # Ensure amount is string representation of number
    amount_str = str(amount)
    
    raw_id = f"{source_type}|{account_id}|{date}|{time}|{ref_str}|{amount_str}"
    return hashlib.sha256(raw_id.encode()).hexdigest()

def check_duplicates(account_id, transactions, exclude_tx_id=None):
    """
    Checks if provided transactions already exist in the database.
    Returns a list of booleans.
    
    transactions: list of dicts with keys 'date', 'time', 'ref_no', 'amount'
    """
    results = []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for tx in transactions:
            date = tx.get('date', '')
            time = tx.get('time', '')
            ref_no = tx.get('ref_no', '')
            amount = tx.get('amount', 0)
            
            # Check against BATCH format (source_type='BATCH')
            hash_batch = compute_transaction_hash(account_id, date, time, ref_no, amount, "BATCH")
            # Check against MANUAL format (source_type='MANUAL')
            hash_manual = compute_transaction_hash(account_id, date, time, ref_no, amount, "MANUAL")
            
            query = """
                SELECT 1 FROM transactions 
                WHERE (trace_hash = ? OR trace_hash = ?)
            """
            params = [hash_batch, hash_manual]
            
            if exclude_tx_id:
                query += " AND transaction_id != ?"
                params.append(exclude_tx_id)
            
            cursor.execute(query, tuple(params))
            exists = cursor.fetchone() is not None
            results.append(exists)
    return results

def create_transactions_batch(account_id, transactions, source_type="BATCH"):
    """
    Inserts a list of transactions into the database.
    Ignores duplicates silently (via integrity error or check).
    Returns count of successfully inserted records.
    """
    saved_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for tx in transactions:
            t_hash = compute_transaction_hash(
                account_id, 
                tx['date'], 
                tx['time'], 
                tx.get('ref_no', ''), 
                tx['amount'], 
                source_type
            )
            try:
                cursor.execute("""
                    INSERT INTO transactions (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (account_id, tx['date'], tx['time'], tx.get('summary', ''), tx.get('ref_no', ''), tx['amount'], t_hash))
                saved_count += 1
            except sqlite3.IntegrityError:
                continue
        conn.commit()
    return saved_count

def create_transaction(account_id, date, time, summary, ref_no, amount, source_type="MANUAL"):
    """
    Inserts a single transaction.
    """
    t_hash = compute_transaction_hash(account_id, date, time, ref_no, amount, source_type)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO transactions (account_id, trans_date, trans_time, summary, ref_no, amount, trace_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (account_id, date, time, summary, ref_no, amount, t_hash))
            conn.commit()
            return True, None
        except sqlite3.IntegrityError:
            return False, "Transaction already exists"

def update_transaction(tx_id, account_id, date, time, summary, ref_no, amount):
    """
    Updates an existing transaction and re-calculates hash.
    Checks for collisions.
    """
    # Standardize on consistent hashing (treat edits as MANUAL)
    new_hash = compute_transaction_hash(account_id, date, time, ref_no, amount, "MANUAL")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if the OTHER transaction already has this hash
        cursor.execute("""
            SELECT transaction_id FROM transactions 
            WHERE trace_hash = ? AND transaction_id != ?
        """, (new_hash, tx_id))
        
        if cursor.fetchone():
            return False, "Modification results in a duplicate transaction."

        cursor.execute("""
            UPDATE transactions 
            SET trans_date=?, trans_time=?, summary=?, amount=?, ref_no=?, trace_hash=?
            WHERE transaction_id=?
        """, (date, time, summary, amount, ref_no, new_hash, tx_id))
        
        if cursor.rowcount == 0:
            return False, "Transaction not found."
        
        conn.commit()
    return True, "Update successful."
