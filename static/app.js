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
    const data = await res.json();

    // 計算統計
    let totalIncome = 0;
    let totalExpense = 0;

    const tbody = document.querySelector('#txTable tbody');
    tbody.innerHTML = data.map(tx => {
        if (tx.amount >= 0) totalIncome += tx.amount;
        else totalExpense += tx.amount;

        const amountClass = tx.amount >= 0 ? 'amount-pos' : 'amount-neg';
        const displayAmount = (tx.amount >= 0 ? '+' : '') + tx.amount.toLocaleString();
        
        return `
            <tr>
                <td>
                    <div style="font-weight:500;">${tx.trans_date}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${tx.trans_time}</div>
                </td>
                <td><b>${tx.summary}</b></td>
                <td class="${amountClass}">${displayAmount}</td>
                <td class="ref-text">${tx.ref_no || '-'}</td>
            </tr>
        `;
    }).join('');

    // 更新統計卡片
    document.getElementById('total-income').innerText = `$${totalIncome.toLocaleString()}`;
    document.getElementById('total-expense').innerText = `$${totalExpense.toLocaleString()}`;
}

// 初始化載入
document.addEventListener('DOMContentLoaded', fetchTransactions);