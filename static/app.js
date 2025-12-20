// 頁面元素選取
const pdfFileInput = document.getElementById('pdfFile');
const pwdModal = document.getElementById('pwdModal');
const pdfPwdInput = document.getElementById('pdfPwd');
const btnSubmit = document.getElementById('btnSubmit');
const btnCancel = document.getElementById('btnCancel');
const statusMsg = document.getElementById('statusMsg');

// --- 事件監聽 ---
pdfFileInput.onchange = () => {
    if (pdfFileInput.files.length > 0) {
        openModal();
    }
};

btnSubmit.onclick = submitUpload;
btnCancel.onclick = closeModal;

pdfPwdInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitUpload();
    if (e.key === "Escape") closeModal();
});

// --- 核心功能 ---
function openModal() {
    pwdModal.style.display = 'block';
    pdfPwdInput.value = '';
    pdfPwdInput.focus();
}

function closeModal() {
    pwdModal.style.display = 'none';
    pdfPwdInput.value = ''; 
    pdfFileInput.value = ''; 
}

async function submitUpload() {
    const file = pdfFileInput.files[0];
    const password = pdfPwdInput.value;

    if (!password) return alert("請輸入密碼");

    const formData = new FormData();
    formData.append('file', file);
    formData.append('password', password);
    
    closeModal();
    statusMsg.innerText = "正在安全解析中...";

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const result = await res.json();
        statusMsg.innerText = result.message;
        await fetchTransactions(); 
    } catch (err) {
        statusMsg.innerText = "連線錯誤";
    }
}

async function fetchTransactions() {
    const res = await fetch('/api/transactions');
    const data = await res.json();
    const tbody = document.querySelector('#txTable tbody');
    tbody.innerHTML = data.map(tx => {
        // 判斷金額正負
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
}

// 初始化載入
document.addEventListener('DOMContentLoaded', fetchTransactions);