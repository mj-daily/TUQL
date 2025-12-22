// 頁面元素選取
const fileInput = document.getElementById('fileInput'); // 注意這裡 ID 改為通用名稱
const statusMsg = document.getElementById('statusMsg');

// PDF 相關元素
const pwdModal = document.getElementById('pwdModal');
const pdfPwdInput = document.getElementById('pdfPwd');
const btnSubmit = document.getElementById('btnSubmit');
const btnCancel = document.getElementById('btnCancel');

// OCR 相關元素
const ocrModal = document.getElementById('ocrModal');
const btnOcrSave = document.getElementById('btnOcrSave');
const btnOcrCancel = document.getElementById('btnOcrCancel');

// 全域變數，存儲所有交易資料 (方便前端篩選，不用一直 call API)
let allTransactions = [];
let currentFilterAccountId = null; // null 代表顯示全部

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    await fetchAccounts();     // 先載入帳戶
    await fetchTransactions(); // 再載入交易
});

// 取得並渲染帳戶
async function fetchAccounts() {
    const res = await fetch('/api/accounts');
    const accounts = await res.json();
    
    const container = document.getElementById('account-list');
    let netWorth = 0;
    
    // 加入「全部帳戶」的選項卡片
    let html = `
        <div class="account-card ${currentFilterAccountId === null ? 'active' : ''}" 
             onclick="filterByAccount(null)" style="background: linear-gradient(135deg, #6366f1, #4338ca);">
            <div class="acc-name">總覽</div>
            <div class="acc-balance">ALL</div>
            <div class="acc-number">所有帳戶</div>
        </div>
    `;

    accounts.forEach(acc => {
        netWorth += acc.balance;
        
        // 判斷樣式 (如果是 Manual-Import 給灰色)
        let cardClass = '';
        if (acc.account_name === 'Manual-Import') cardClass = 'acc-card-manual';
        
        // 格式化帳號 (只顯示後4碼)
        const displayNum = acc.account_number.length > 4 
            ? '•••• ' + acc.account_number.slice(-4) 
            : acc.account_number;

        html += `
            <div class="account-card ${cardClass} ${currentFilterAccountId === acc.account_id ? 'active' : ''}" 
                 onclick="filterByAccount(${acc.account_id})">
                <div class="acc-name">${acc.account_name}</div>
                <div class="acc-balance">$${acc.balance.toLocaleString()}</div>
                <div class="acc-number">${displayNum}</div>
            </div>
        `;
    });

    container.innerHTML = html;
    document.getElementById('net-worth').innerText = `$${netWorth.toLocaleString()}`;
    
    // 根據淨值變色
    document.getElementById('net-worth').style.color = netWorth >= 0 ? 'var(--text-main)' : 'var(--danger-color)';
}

// --- 事件監聽 ---

// 檔案選擇變更
fileInput.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.type === "application/pdf") {
        // PDF 流程：開密碼框
        pwdModal.style.display = 'block';
        pdfPwdInput.value = '';
        pdfPwdInput.focus();
    } else if (file.type.startsWith("image/")) {
        // 圖片流程：直接辨識
        await handleImageUpload(file);
    } else {
        alert("不支援的檔案格式");
    }
};

// PDF 密碼框操作
btnSubmit.onclick = submitPdfUpload;
btnCancel.onclick = () => { pwdModal.style.display = 'none'; fileInput.value = ''; };
pdfPwdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitPdfUpload();
    if (e.key === "Escape") btnCancel.click();
});

// OCR 校對框操作
btnOcrSave.onclick = saveOcrResult;
btnOcrCancel.onclick = () => { ocrModal.style.display = 'none'; fileInput.value = ''; };

// btnSubmit.onclick = submitUpload;
// btnCancel.onclick = closeModal;

pdfPwdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitUpload();
    if (e.key === "Escape") closeModal();
});

// --- 核心功能函數 ---
async function submitPdfUpload() {
    const file = fileInput.files[0];
    const password = pdfPwdInput.value;

    if (!password) return alert("請輸入密碼");

    const formData = new FormData();
    formData.append('file', file);
    formData.append('password', password);
    
    pwdModal.style.display = 'none';
    statusMsg.innerText = "正在解析 PDF...";

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const result = await res.json();
        statusMsg.innerText = result.message;
        await fetchTransactions(); 
    } catch (err) {
        statusMsg.innerText = "PDF 上傳失敗";
    }
}

async function handleImageUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    statusMsg.innerText = "⏳ 正在進行 OCR 辨識...";
    
    try {
        const res = await fetch('/api/ocr-identify', { method: 'POST', body: formData });
        const result = await res.json();
        
        if (result.success) {
            statusMsg.innerText = "✅ 辨識完成，請校對資料";
            // 填入校對視窗
            document.getElementById('ocrDate').value = result.data.date;
            document.getElementById('ocrTime').value = result.data.time;
            document.getElementById('ocrSummary').value = result.data.summary;
            document.getElementById('ocrAmount').value = result.data.amount;
            document.getElementById('ocrRef').value = result.data.ref_no;
            
            ocrModal.style.display = 'block';
        } else {
            statusMsg.innerText = "❌ 辨識失敗：" + result.message;
        }
    } catch (err) {
        statusMsg.innerText = "連線錯誤";
    }
}

// 新增選取錯誤訊息元素
const ocrErrorMsg = document.getElementById('ocrErrorMsg');

async function saveOcrResult() {
    const data = {
        date: document.getElementById('ocrDate').value,
        time: document.getElementById('ocrTime').value,
        summary: document.getElementById('ocrSummary').value,
        amount: parseFloat(document.getElementById('ocrAmount').value),
        ref_no: document.getElementById('ocrRef').value
    };

    // 1. UX 優化：鎖定按鈕並顯示處理中
    const btnSave = document.getElementById('btnOcrSave');
    const originalText = btnSave.innerText;
    btnSave.innerText = "⏳ 儲存中...";
    btnSave.disabled = true;
    ocrErrorMsg.innerText = ""; // 清空舊的錯誤訊息

    try {
        const res = await fetch('/api/save-manual', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if (result.success) {
            // 成功：關閉 Modal 並刷新
            ocrModal.style.display = 'none';
            fileInput.value = ''; 
            statusMsg.innerText = "✅ 單筆交易存入成功！";
            fetchTransactions();
        } else {
            // 失敗：顯示錯誤在 Modal 內，不關閉視窗
            // 這樣使用者可以看到 "重複匯入" 的訊息，決定要取消還是改序號
            ocrErrorMsg.innerText = "❌ " + result.message;
        }
    } catch (err) {
        ocrErrorMsg.innerText = "❌ 連線錯誤，請稍後再試";
    } finally {
        // 2. 恢復按鈕狀態
        btnSave.innerText = originalText;
        btnSave.disabled = false;
    }
}

async function fetchTransactions() {
    const res = await fetch('/api/transactions');
    allTransactions = await res.json(); // 存入全域變數
    renderTable(); // 執行渲染
}

// 渲染表格與統計 (核心邏輯分離)
function renderTable() {
    // 根據目前選中的帳戶 ID 篩選資料
    const filteredData = currentFilterAccountId 
        ? allTransactions.filter(tx => tx.account_id === currentFilterAccountId)
        : allTransactions;

    // 計算本頁面(或本帳戶)的收支統計
    let inc = 0, exp = 0;
    
    const tbody = document.querySelector('#txTable tbody');
    tbody.innerHTML = filteredData.map(tx => {
        if (tx.amount >= 0) inc += tx.amount; else exp += tx.amount;
        
        // ... (原本的表格渲染邏輯，含按鈕) ...
        const amountClass = tx.amount >= 0 ? 'amount-pos' : 'amount-neg';
        const displayAmount = (tx.amount >= 0 ? '+' : '') + tx.amount.toLocaleString();
        const txStr = encodeURIComponent(JSON.stringify(tx));

        return `
            <tr>
                <td>
                    <div style="font-weight:500;">${tx.trans_date}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${tx.trans_time}</div>
                </td>
                <td><b>${tx.summary}</b></td>
                <td class="${amountClass}">${displayAmount}</td>
                <td class="ref-text">${tx.ref_no || '-'}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-icon edit" onclick="openEditModal('${txStr}')" title="編輯">✎</button>
                        <button class="btn-icon delete" onclick="deleteTx(${tx.transaction_id})" title="刪除">🗑️</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    // 更新下方統計卡片
    document.getElementById('total-income').innerText = `$${inc.toLocaleString()}`;
    document.getElementById('total-expense').innerText = `$${exp.toLocaleString()}`;
}

// 切換帳戶篩選
function filterByAccount(accountId) {
    currentFilterAccountId = accountId;
    
    // 更新卡片選中狀態 UI
    document.querySelectorAll('.account-card').forEach(card => card.classList.remove('active'));
    // 這裡可以用 event.currentTarget 來加 active，或重新 render fetchAccounts (較簡單但較慢)
    // 為了效能，我們直接重新 fetchAccounts 其實也很快，因為它會重新計算餘額
    fetchAccounts(); 
    
    renderTable(); // 重新渲染表格
}

// 刪除功能
async function deleteTx(id) {
    if (!confirm("確定要刪除這筆交易嗎？此操作無法復原。")) return;

    try {
        const res = await fetch(`/api/transaction/${id}`, { method: 'DELETE' });
        const result = await res.json();
        if (result.success) {
            fetchTransactions(); // 重新整理列表
        } else {
            alert("刪除失敗: " + result.message);
        }
    } catch (e) {
        alert("連線錯誤");
    }
}

// 編輯功能相關
const editModal = document.getElementById('editModal');

function openEditModal(txStr) {
    const tx = JSON.parse(decodeURIComponent(txStr));
    
    // 填入資料到編輯彈窗
    document.getElementById('editTxId').value = tx.transaction_id;
    document.getElementById('editDate').value = tx.trans_date;
    document.getElementById('editTime').value = tx.trans_time;
    document.getElementById('editSummary').value = tx.summary;
    document.getElementById('editAmount').value = tx.amount;
    document.getElementById('editRef').value = tx.ref_no;
    
    editModal.style.display = 'block';
}

function closeEditModal() {
    editModal.style.display = 'none';
}

async function submitEdit() {
    const id = document.getElementById('editTxId').value;
    const payload = {
        date: document.getElementById('editDate').value,
        time: document.getElementById('editTime').value,
        summary: document.getElementById('editSummary').value,
        amount: parseFloat(document.getElementById('editAmount').value),
        ref_no: document.getElementById('editRef').value
    };

    try {
        const res = await fetch(`/api/transaction/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        
        if (result.success) {
            closeEditModal();
            fetchTransactions(); // 刷新列表
        } else {
            alert("更新失敗: " + result.message);
        }
    } catch (e) {
        alert("連線錯誤");
    }
}

// 初始化載入
document.addEventListener('DOMContentLoaded', fetchTransactions);