#%% main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import database
from routers import transactions, accounts, imports

app = FastAPI()

# 初始化資料庫
database.init_db()

# 掛載靜態檔案
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 註冊 Routers
app.include_router(transactions.router, tags=["Transactions"])
app.include_router(accounts.router, tags=["Accounts"])
app.include_router(imports.router, tags=["Imports"])

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

#%%
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
