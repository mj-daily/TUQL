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
const ocrBatchModal = document.getElementById('ocrBatchModal');
const ocrBatchList = document.getElementById('ocrBatchList');

// 編輯交易彈窗元素
const editModal = document.getElementById('editModal');
const accModal = document.getElementById('accModal');

// PDF 確認匯入彈窗元素
const pdfConfirmModal = document.getElementById('pdfConfirmModal');

// [新增] 狀態訊息管理工具
const UI = {
    timer: null,
    showStatus: (msg, type = 'info', autoHide = false) => {
        if (UI.timer) clearTimeout(UI.timer);
        statusMsg.innerText = msg;
        statusMsg.style.color = type === 'error' ? 'var(--danger-color)' : 
                                type === 'success' ? 'var(--success-color)' : 'blue';
        
        if (autoHide) {
            UI.timer = setTimeout(() => {
                statusMsg.innerText = '';
            }, 5000); // 5秒後自動消失
        }
    },
    clearStatus: () => {
        if (UI.timer) clearTimeout(UI.timer);
        statusMsg.innerText = '';
    }
};

// 全域變數，存儲所有交易資料 (方便前端篩選，不用一直 call API)
let allTransactions = [];
let currentFilterAccountId = null; // null 代表顯示全部
let pendingPdfTransactions = []; // 暫存 PDF 解析出來的交易資料
let isPdfUploading = false; // 防止重複上傳

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
    const files = e.target.files;
    if (files.length === 0) return;

    // 判斷邏輯：如果是 PDF (通常一次傳一個)，走舊流程
    // 如果是圖片 (可能多張)，走新流程
    if (files[0].type === "application/pdf") {
        if (files.length > 1) alert("PDF 請逐一上傳，目前僅支援單檔解析");
        pwdModal.style.display = 'block';
        pdfPwdInput.value = '';
        pdfPwdInput.focus();
    } else if (files[0].type.startsWith("image/")) {
        // [修改] 改為呼叫批次處理
        await handleBatchImageUpload(files);
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
    if (isPdfUploading) return;

    const password = pdfPwdInput.value;
    if (!password) return alert("請輸入密碼"); // 簡易防呆

    isPdfUploading = true;

    btnSubmit.disabled = true;
    btnSubmit.innerText = "⏳ 處理中...";

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('password', pdfPwdInput.value);
    
    pwdModal.style.display = 'none';
    statusMsg.innerText = "正在解析 PDF...";

    try {
        // 1. 呼叫預覽 API
        const res = await fetch('/api/pdf-preview', { method: 'POST', body: formData });
        const result = await res.json();
        
        if (result.success) {
            statusMsg.innerText = "✅ 解析完成，請確認歸戶";
            openPdfConfirmModal(result.data);
        } else {
            statusMsg.innerText = "❌ " + result.message;
        }
    } catch (err) {
        statusMsg.innerText = "連線錯誤";
    } finally {
        // 3. 解除鎖定 (無論成功失敗都要解除，並恢復按鈕)
        isPdfUploading = false;
        btnSubmit.disabled = false;
        btnSubmit.innerText = "確認上傳";
    }
}

async function openPdfConfirmModal(data) {
    pendingPdfTransactions = data.transactions;
    
    // UI 顯示偵測結果
    document.getElementById('pdfDetectedAcc').innerText = data.account_number || "未知";
    document.getElementById('pdfTxCount').innerText = `共 ${data.count} 筆交易`;

    // 準備下拉選單
    const select = document.getElementById('pdfTargetAccount');
    select.innerHTML = '<option value="">-- 請選擇歸戶帳戶 --</option>';
    
    // 取得最新帳戶列表 (為了確保資料同步，這裡可以再 fetch 一次，或者用全域變數)
    const res = await fetch('/api/accounts');
    const accounts = await res.json();
    
    let matchedId = "";

    accounts.forEach(acc => {
        const option = document.createElement('option');
        option.value = acc.account_id;
        // 顯示格式： 暱稱 (末5碼) - 銀行代碼
        option.text = `${acc.account_name} (${acc.account_number}) - ${acc.bank_code}`;
        select.appendChild(option);

        // [關鍵邏輯] 自動匹配
        // 如果 PDF 偵測到的號碼 (例如 "345") 是帳戶號碼 (例如 "12345") 的結尾
        if (data.account_number && acc.account_number.endsWith(data.account_number)) {
            matchedId = acc.account_id;
        }
    });

    // 如果有匹配到，自動選取
    if (matchedId) {
        select.value = matchedId;
    }

    pdfConfirmModal.style.display = 'block';
}

function closePdfConfirmModal() {
    pdfConfirmModal.style.display = 'none';
    fileInput.value = '';
    pendingPdfTransactions = [];
}

async function savePdfBatch() {
    const accountId = document.getElementById('pdfTargetAccount').value;
    
    if (!accountId) {
        alert("請選擇一個匯入目標帳戶！若無帳戶請先至「帳戶管理」新增。");
        return;
    }

    const btn = document.getElementById('btnPdfSave');
    btn.innerText = "⏳ 匯入中..."; btn.disabled = true;

    try {
        const payload = {
            account_id: parseInt(accountId),
            transactions: pendingPdfTransactions
        };

        const res = await fetch('/api/save-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await res.json();
        
        if (result.success) {
            closePdfConfirmModal();
            statusMsg.innerText = "✅ " + result.message;
            fetchAccounts();     // 更新餘額
            fetchTransactions(); // 更新列表
        } else {
            alert("匯入失敗: " + result.message);
        }
    } catch (e) {
        alert("連線錯誤");
    } finally {
        btn.innerText = "確認匯入"; btn.disabled = false;
    }
}
// [修改] handleBatchImageUpload：優化進度提示
async function handleBatchImageUpload(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    // 即時提示
    UI.showStatus(`⏳ 正在上傳並辨識 ${files.length} 張圖片...`, 'info');
    
    try {
        const res = await fetch('/api/ocr-identify', { method: 'POST', body: formData });
        
        if (!res.ok) {
           // ... (原本的錯誤處理邏輯) ...
           UI.showStatus(`❌ 請求失敗: ${res.statusText}`, 'error');
           return;
        }

        const result = await res.json();
        
        if (result.success) {
            UI.showStatus("✅ 辨識完成，請在視窗中校對", 'success');
            openOcrBatchModal(result.data);
        } else {
            const msg = result.message || JSON.stringify(result);
            UI.showStatus("❌ 辨識失敗：" + msg, 'error');
        }
    } catch (err) {
        console.error(err);
        UI.showStatus("❌ 連線錯誤", 'error');
    }
    // 注意：這裡不設 autoHide，因為使用者還在操作，直到他關閉視窗或完成
}
// [修改] openOcrBatchModal：加入監聽器
async function openOcrBatchModal(items) {
    const select = document.getElementById('ocrBatchAccount');
    select.innerHTML = '<option value="">-- 請選擇歸戶帳戶 --</option>';
    
    // ... (取得帳戶列表與自動匹配邏輯保持不變) ...
    const res = await fetch('/api/accounts');
    const accounts = await res.json();
    
    // ... (填入 options) ...
    let detectedAccNum = items.length > 0 ? items[0].account_number : null;
    let matchedId = "";
    accounts.forEach(acc => {
        const option = document.createElement('option');
        option.value = acc.account_id;
        option.text = `${acc.account_name} (${acc.account_number}) - ${acc.bank_code}`;
        select.appendChild(option);
        if (detectedAccNum && acc.account_number.endsWith(detectedAccNum)) {
            matchedId = acc.account_id;
        }
    });
    if (matchedId) select.value = matchedId;

    // 渲染卡片
    renderBatchCards(items);

    // [新增] 綁定事件：當帳戶改變時，重新檢查重複
    // 先移除舊的監聽器以免重複綁定
    const newSelect = select.cloneNode(true);
    select.parentNode.replaceChild(newSelect, select);
    newSelect.addEventListener('change', () => checkBatchDuplicates());

    ocrBatchModal.style.display = 'block';

    // 如果已經有選中帳戶，直接執行一次檢查
    if (newSelect.value) {
        checkBatchDuplicates();
    }
}

// [新增] 渲染卡片獨立函數 (方便重繪)
function renderBatchCards(items) {
    ocrBatchList.innerHTML = '';
    items.forEach((item, index) => {
        const card = createOcrCard(item, index);
        ocrBatchList.appendChild(card);
    });
}

// [新增] 檢查重複功能
async function checkBatchDuplicates() {
    const accountId = document.getElementById('ocrBatchAccount').value;
    if (!accountId) return; // 沒選帳戶無法計算 Hash

    // 1. 收集目前畫面上的資料
    const cards = document.querySelectorAll('.ocr-card');
    const transactions = [];
    cards.forEach(card => {
        transactions.push({
            date: card.querySelector('.inp-date').value,
            time: card.querySelector('.inp-time').value,
            // summary 不影響 hash 但為了完整性
            amount: parseFloat(card.querySelector('.inp-amount').value),
            ref_no: card.querySelector('.inp-ref').value
        });
    });

    if (transactions.length === 0) return;

    try {
        const res = await fetch('/api/check-duplicates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ account_id: accountId, transactions: transactions })
        });
        const result = await res.json();

        if (result.success) {
            // 2. 根據結果更新 UI
            const duplicates = result.duplicates; // [true, false, ...]
            cards.forEach((card, index) => {
                if (duplicates[index]) {
                    card.classList.add('duplicate');
                    if (!card.querySelector('.duplicate-badge')) {
                        const badge = document.createElement('div');
                        badge.className = 'duplicate-badge';
                        badge.innerText = '⚠️ 已存在';
                        card.appendChild(badge);
                    }
                } else {
                    card.classList.remove('duplicate');
                    const badge = card.querySelector('.duplicate-badge');
                    if (badge) badge.remove();
                }
            });
        }
    } catch (e) {
        console.error("Check duplicate failed", e);
    }
}

// [修改] 關閉 Modal 時清除狀態
function closeOcrBatchModal() {
    ocrBatchModal.style.display = 'none';
    fileInput.value = '';
    UI.clearStatus(); // 清除提示
}

// 建立單張卡片的 HTML
function createOcrCard(item, index) {
    const div = document.createElement('div');
    div.className = 'ocr-card';
    div.dataset.index = index; // 用於標記

    // 刪除按鈕
    div.innerHTML = `
        <button class="ocr-card-del" onclick="removeOcrCard(this)" title="移除此筆">✕</button>
        <div class="ocr-grid">
            <div>
                <label>日期</label>
                <input type="text" class="inp-date" value="${item.date || ''}" placeholder="YYYY/MM/DD">
            </div>
            <div>
                <label>時間</label>
                <input type="text" class="inp-time" value="${item.time || ''}" placeholder="HH:MM:SS">
            </div>
            <div class="ocr-full-width">
                <label>摘要</label>
                <input type="text" class="inp-summary" value="${item.summary || ''}">
            </div>
            <div>
                <label>金額 (支出為負)</label>
                <input type="number" class="inp-amount" value="${item.amount || 0}">
            </div>
            <div>
                <label>交易序號</label>
                <input type="text" class="inp-ref" value="${item.ref_no || ''}">
            </div>
        </div>
    `;
    return div;
}

// 移除卡片
window.removeOcrCard = function(btn) {
    const card = btn.closest('.ocr-card');
    card.remove();
};

// 確認全部匯入
async function saveOcrBatch() {
    const accountId = document.getElementById('ocrBatchAccount').value;
    if (!accountId) return alert("請選擇匯入目標帳戶！");

    const cards = document.querySelectorAll('.ocr-card');
    if (cards.length === 0) return alert("沒有可匯入的交易資料");

    // 收集資料
    const transactions = [];
    cards.forEach(card => {
        const date = card.querySelector('.inp-date').value;
        const time = card.querySelector('.inp-time').value;
        const summary = card.querySelector('.inp-summary').value;
        const amount = parseFloat(card.querySelector('.inp-amount').value);
        const ref_no = card.querySelector('.inp-ref').value;

        // 簡單驗證
        if (date && !isNaN(amount)) {
            transactions.push({ date, time, summary, amount, ref_no });
        }
    });

    const btn = document.getElementById('btnBatchSave');
    btn.innerText = "⏳ 匯入中..."; btn.disabled = true;

    try {
        // 重用 PDF 的批次儲存 API
        const payload = {
            account_id: parseInt(accountId),
            transactions: transactions
        };

        const res = await fetch('/api/save-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (result.success) {
            closeOcrBatchModal();
            // 使用自動隱藏的成功訊息
            UI.showStatus("✅ " + result.message, 'success', true);
            fetchTransactions();
            fetchAccounts();
        } else {
            alert("匯入失敗: " + result.message);
        }
    } catch (e) {
        alert("連線錯誤");
    } finally {
        btn.innerText = "確認全部匯入"; btn.disabled = false;
    }
}

// OCR 校對框操作
btnOcrSave.onclick = saveOcrResult;
btnOcrCancel.onclick = () => { ocrModal.style.display = 'none'; fileInput.value = ''; };

pdfPwdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        // [關鍵修正] 阻止瀏覽器預設行為 (避免 Enter 同時觸發按鈕點擊)
        e.preventDefault(); 
        submitPdfUpload(); 
    }
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