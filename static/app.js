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
const ocrErrorMsg = document.getElementById('ocrErrorMsg');

// 編輯交易彈窗元素
const editModal = document.getElementById('editModal');
const accModal = document.getElementById('accModal');

// 全域變數，存儲所有交易資料 (方便前端篩選，不用一直 call API)
let allTransactions = [];
let currentFilterAccountId = null; // null 代表顯示全部

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    await fetchAccounts();     // 先載入帳戶
    await fetchTransactions(); // 再載入交易
});

// --- 帳戶管理功能 (Phase 1) ---
function openAccModal() {
    renderAccTable();
    resetAccForm();
    accModal.style.display = 'block';
}

function closeAccModal() {
    accModal.style.display = 'none';
    fetchAccounts(); 
}

function resetAccForm() {
    document.getElementById('accEditId').value = '';
    document.getElementById('accName').value = '';
    document.getElementById('accBankCode').value = '';
    document.getElementById('accNumber').value = '';
    document.getElementById('accInitBalance').value = 0;
}

async function renderAccTable() {
    const res = await fetch('/api/accounts');
    const accounts = await res.json();
    const tbody = document.querySelector('#accTable tbody');
    tbody.innerHTML = accounts.map(acc => {
        const accStr = encodeURIComponent(JSON.stringify(acc));
        return `
            <tr>
                <td>
                    <div style="font-weight:bold">${acc.account_name}</div>
                    <small style="color:#888">${acc.bank_code || '-'}</small>
                </td>
                <td>
                    <span style="font-family:monospace; background:#f1f5f9; padding:2px 6px; border-radius:4px;">
                        ${acc.account_number}
                    </span>
                </td>
                <td>$${acc.balance.toLocaleString()}</td>
                <td>
                    <button class="btn-icon edit" onclick="editAccount('${accStr}')">✎</button>
                    <button class="btn-icon delete" onclick="deleteAccount(${acc.account_id})">🗑️</button>
                </td>
            </tr>
        `;
    }).join('');
}

function editAccount(accStr) {
    const acc = JSON.parse(decodeURIComponent(accStr));
    document.getElementById('accEditId').value = acc.account_id;
    document.getElementById('accName').value = acc.account_name;
    document.getElementById('accBankCode').value = acc.bank_code;
    document.getElementById('accNumber').value = acc.account_number;
    document.getElementById('accInitBalance').value = acc.initial_balance;
}

async function saveAccount() {
    const id = document.getElementById('accEditId').value;
    const name = document.getElementById('accName').value;
    const number = document.getElementById('accNumber').value;
    const bankCode = document.getElementById('accBankCode').value;
    const initBalance = parseFloat(document.getElementById('accInitBalance').value);

    if (!name) return alert("請輸入帳戶暱稱");
    if (!bankCode) return alert("請輸入銀行代碼");
    if (!number || number.length !== 5 || isNaN(number)) return alert("請輸入 5 碼數字帳號");

    const payload = { name, number, bank_code: bankCode, init_balance: initBalance };
    const url = id ? `/api/account/${id}` : '/api/account';
    const method = id ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    const result = await res.json();
    if (result.success) {
        renderAccTable();
        resetAccForm();
    } else {
        alert("錯誤: " + result.message);
    }
}

async function deleteAccount(id) {
    if (!confirm("確定要刪除此帳戶？(若有交易資料將無法刪除)")) return;
    const res = await fetch(`/api/account/${id}`, { method: 'DELETE' });
    const result = await res.json();
    if (result.success) renderAccTable();
    else alert(result.message);
}

// --- 首頁帳戶卡片 ---
async function fetchAccounts() {
    const res = await fetch('/api/accounts');
    const accounts = await res.json();
    const container = document.getElementById('account-list');
    let netWorth = 0;
    
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
        let cardClass = acc.bank_code === '' ? 'acc-card-manual' : '';
        if (acc.account_name === 'Manual-Import') cardClass = 'acc-card-manual';

        html += `
            <div class="account-card ${cardClass} ${currentFilterAccountId === acc.account_id ? 'active' : ''}" 
                 onclick="filterByAccount(${acc.account_id})">
                <div class="acc-name">${acc.account_name}</div>
                <div class="acc-balance">$${acc.balance.toLocaleString()}</div>
                <div class="acc-number">${acc.account_number}</div>
            </div>
        `;
    });
    container.innerHTML = html;
    // 更新總資產
    const nw = document.getElementById('net-worth');
    nw.innerText = `$${netWorth.toLocaleString()}`;
    nw.style.color = netWorth >= 0 ? 'var(--text-main)' : 'var(--danger-color)';
}

// 切換帳戶篩選
function filterByAccount(accountId) {
    currentFilterAccountId = accountId;
    // document.querySelectorAll('.account-card').forEach(card => card.classList.remove('active'));
    // 這裡可以用 event.currentTarget 來加 active，或重新 render fetchAccounts (較簡單但較慢)
    // 為了效能，我們直接重新 fetchAccounts 其實也很快，因為它會重新計算餘額
    fetchAccounts();
    renderTable(); // 重新渲染表格
}

// --- 交易列表 ---
async function fetchTransactions() {
    const res = await fetch('/api/transactions');
    allTransactions = await res.json(); // 存入全域變數
    renderTable(); // 執行渲染
}

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

// --- 編輯交易 ---
function openEditModal(txStr) {
    const tx = JSON.parse(decodeURIComponent(txStr));
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

// --- PDF & OCR 上傳 ---
fileInput.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.type === "application/pdf") {
        pwdModal.style.display = 'block';
        pdfPwdInput.value = '';
        pdfPwdInput.focus();
    } else if (file.type.startsWith("image/")) {
        await handleImageUpload(file);
    } else {
        alert("不支援的檔案格式");
    }
};

btnSubmit.onclick = submitPdfUpload;
btnCancel.onclick = () => { pwdModal.style.display = 'none'; fileInput.value = ''; };
pdfPwdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitPdfUpload();
    if (e.key === "Escape") btnCancel.click();
});

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
            document.getElementById('ocrAccount').value = result.data.account_number || "";
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

// OCR 校對框操作
btnOcrSave.onclick = saveOcrResult;
btnOcrCancel.onclick = () => { ocrModal.style.display = 'none'; fileInput.value = ''; };

// btnSubmit.onclick = submitUpload;
// btnCancel.onclick = closeModal;

pdfPwdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitPdfUpload();
    if (e.key === "Escape") closeModal();
});

async function closeModal() {
    ocrModal.style.display = 'none';
    fileInput.value = '';
}

// --- 核心功能函數 ---

async function saveOcrResult() {
    const data = {
        account_number: document.getElementById('ocrAccount').value,
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

// 初始化載入
document.addEventListener('DOMContentLoaded', fetchTransactions);