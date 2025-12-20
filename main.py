#%% main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import parser
import os
import io

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

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...), password: str = Form(...)):
    try:
        # 1. 直接讀取檔案內容到記憶體
        file_content = await file.read()
        
        # 2. 將 bytes 轉化為記憶體中的檔案流 (file-like object)
        pdf_stream = io.BytesIO(file_content)
        
        # 3. 呼叫 parser (現在接收的是流而非路徑)
        added, total = parser.parse_and_save(pdf_stream, password)
        
        msg = f"成功解析 {total} 筆，新增 {added} 筆"
    except Exception as e:
        msg = f"解析失敗: {str(e)}"
    # 此處完全不需要 os.remove，因為根本沒寫入磁碟
    return {"message": msg}

#%%
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)