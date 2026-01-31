import { API } from './modules/api.js';
import { UI, els } from './modules/ui.js';
import { state, getFilteredTransactions } from './modules/state.js';
import * as Utils from './modules/utils.js';

// --- Initialization ---

document.addEventListener('DOMContentLoaded', async () => {
    await loadAccounts();
    await loadTransactions();
    
    // Global Event Listeners
    els.ocrBatchList.addEventListener('input', (e) => {
        if (e.target.tagName === 'INPUT') debouncedCheckBatchDuplicates();
    });

    els.editInputs.forEach(input => {
        input.addEventListener('input', () => {
            updateEditSaveState();
            debouncedCheckEdit();
        });
    });
});

// --- Debouncers ---

const debouncedCheckBatchDuplicates = Utils.debounce(() => checkBatchDuplicates(), 500);
const debouncedCheckEdit = Utils.debounce(() => checkEditDuplicate(), 500);

// --- Core Data Loading ---

async function loadAccounts() {
    try {
        const accounts = await API.getAccounts();
        UI.renderAccountCards(accounts, state.currentFilterAccountId);
        UI.updateImportSelect(accounts);
    } catch (e) {
        UI.showStatus("載入帳戶失敗", 'error');
    }
}

async function loadTransactions() {
    try {
        const txs = await API.getTransactions();
        // Normalize dates
        state.allTransactions = txs.map(tx => ({
            ...tx,
            trans_date: Utils.normalizeDate(tx.trans_date)
        }));
        
        // Sort
        state.allTransactions.sort((a, b) => {
            if (b.trans_date !== a.trans_date) return b.trans_date.localeCompare(a.trans_date);
            return (b.trans_time || "").localeCompare(a.trans_time || "");
        });

        if (!state.currentYearMonth) initMonthPicker();
        renderCurrentView();
    } catch (e) {
        UI.showStatus("載入交易失敗", 'error');
    }
}

// --- View & Navigation ---

function initMonthPicker() {
    const today = new Date();
    const currentYM = Utils.formatDateYM(today);
    
    const hasDataCurrentMonth = state.allTransactions.some(tx => {
        const txYearMonth = tx.trans_date.substring(0, 4) + '-' + tx.trans_date.substring(5, 7);
        return txYearMonth === currentYM;
    });

    if (hasDataCurrentMonth || state.allTransactions.length === 0) {
        state.currentYearMonth = currentYM;
    } else {
        const lastTxDate = state.allTransactions[0].trans_date;
        state.currentYearMonth = lastTxDate.substring(0, 4) + '-' + lastTxDate.substring(5, 7);
    }
    els.monthPicker.value = state.currentYearMonth;
}

window.handleMonthChange = () => {
    state.currentYearMonth = els.monthPicker.value;
    renderCurrentView();
};

window.changeMonth = (step) => {
    const [y, m] = state.currentYearMonth.split('-');
    const date = new Date(parseInt(y), parseInt(m) - 1 + step, 1);
    state.currentYearMonth = Utils.formatDateYM(date);
    els.monthPicker.value = state.currentYearMonth;
    renderCurrentView();
};

window.resetToCurrentMonth = () => {
    const today = new Date();
    state.currentYearMonth = Utils.formatDateYM(today);
    els.monthPicker.value = state.currentYearMonth;
    renderCurrentView();
};

window.filterByAccount = (accountId) => {
    state.currentFilterAccountId = accountId;
    loadAccounts(); // Refresh cards to show active state
    renderCurrentView();
};

window.switchView = (view) => {
    state.currentView = view;
    UI.toggleViewSpy(view);
    renderCurrentView();
};

function renderCurrentView() {
    const filtered = getFilteredTransactions();
    if (state.currentView === 'details') {
        UI.renderTxTable(filtered);
    } else {
        UI.renderStatsTable(filtered);
    }
}

// --- Account Management ---

window.openAccModal = async () => {
    UI.resetAccForm();
    els.accModal.style.display = 'block';
    const accounts = await API.getAccounts();
    UI.renderAccTable(accounts);
};

window.closeAccModal = () => {
    els.accModal.style.display = 'none';
    loadAccounts();
};

window.editAccount = (accStr) => {
    const acc = JSON.parse(decodeURIComponent(accStr));
    document.getElementById('accEditId').value = acc.account_id;
    document.getElementById('accName').value = acc.account_name;
    document.getElementById('accBankCode').value = acc.bank_code;
    document.getElementById('accNumber').value = acc.account_number;
    document.getElementById('accInitBalance').value = acc.initial_balance;
};

window.saveAccount = async () => {
    const id = document.getElementById('accEditId').value;
    const name = document.getElementById('accName').value;
    const number = document.getElementById('accNumber').value;
    const bankCode = document.getElementById('accBankCode').value;
    const initBalance = parseFloat(document.getElementById('accInitBalance').value);

    if (!name || !bankCode || !number || number.length !== 5 || isNaN(number)) {
        return alert("請檢查輸入資料");
    }

    const payload = { name, number, bank_code: bankCode, init_balance: initBalance };
    
    try {
        const result = id ? await API.updateAccount(id, payload) : await API.createAccount(payload);
        if (result.success) {
            UI.resetAccForm();
            const accounts = await API.getAccounts();
            UI.renderAccTable(accounts);
        } else {
            alert(result.message);
        }
    } catch (e) { alert("連線錯誤"); }
};

window.deleteAccount = async (id) => {
    if (!confirm("確定要刪除？")) return;
    const res = await API.deleteAccount(id);
    if (res.success) {
        const accounts = await API.getAccounts();
        UI.renderAccTable(accounts);
    } else {
        alert(res.message);
    }
};

// --- Transaction Management (Edit/Delete) ---

window.deleteTx = async (id) => {
    if (!confirm("確定刪除？")) return;
    const res = await API.deleteTransaction(id);
    if (res.success) {
        loadTransactions();
        loadAccounts(); // Recalculate balance
    } else {
        alert("刪除失敗");
    }
};

window.openEditModal = (txStr) => {
    const tx = JSON.parse(decodeURIComponent(txStr));
    UI.populateEditModal(tx);
    
    // Save original state for comparison
    state.editOriginal = {
        date: els.editDate.value,
        time: els.editTime.value,
        amount: els.editAmount.value,
        ref: els.editRef.value,
        summary: els.editSummary.value
    };
    
    state.editDuplicateFlag = false;
    UI.showEditDuplicateError(false);
    updateEditSaveState();
    
    els.editModal.style.display = 'block';
    // Immediate check
    setTimeout(() => { checkEditDuplicate(); }, 100);
};

window.closeEditModal = () => {
    els.editModal.style.display = 'none';
};

window.submitEdit = async () => {
    const form = UI.getEditFormData();
    
    // Date/Time logic
    const date = form.date.replace(/-/g, '/');
    let time = form.originalTime || '00:00:00';
    if (form.timeDisplay !== time.substring(0, 5)) {
        time = form.timeDisplay ? form.timeDisplay + ':00' : '00:00:00';
    }

    const payload = {
        date, time,
        summary: form.summary,
        amount: parseFloat(form.amount),
        ref_no: form.ref_no,
        account_id: parseInt(form.accountId)
    };

    if (!payload.date || isNaN(payload.amount)) return alert("資料不全");

    try {
        const res = await API.updateTransaction(form.id, payload);
        if (res.success) {
            window.closeEditModal();
            loadTransactions();
            loadAccounts();
        } else {
            alert(res.message);
        }
    } catch (e) { alert("更新失敗"); }
};

function isEditModified() {
    if (!state.editOriginal) return false;
    return (
        state.editOriginal.date !== els.editDate.value ||
        state.editOriginal.time !== els.editTime.value ||
        state.editOriginal.amount !== els.editAmount.value ||
        state.editOriginal.ref !== els.editRef.value ||
        state.editOriginal.summary !== els.editSummary.value
    );
}

function updateEditSaveState() {
    const shouldEnable = !state.editDuplicateFlag && isEditModified();
    UI.updateEditSaveButton(shouldEnable);
}

async function checkEditDuplicate() {
    const form = UI.getEditFormData();
    if (!form.accountId || !form.date || isNaN(form.amount)) return;

    const date = form.date.replace(/-/g, '/');
    let time = form.originalTime || '00:00:00';
    if (form.timeDisplay !== time.substring(0, 5)) time = form.timeDisplay + ':00';

    try {
        const res = await API.checkDuplicates({
            account_id: parseInt(form.accountId),
            transactions: [{ date, time, amount: parseFloat(form.amount), ref_no: form.ref_no }],
            exclude_transaction_id: parseInt(form.id)
        });
        
        state.editDuplicateFlag = (res.success && res.duplicates[0] === true);
        UI.showEditDuplicateError(state.editDuplicateFlag);
        updateEditSaveState();
    } catch (e) { console.error(e); }
}

// --- Imports (PDF / OCR) ---

els.fileInput.onchange = async (e) => {
    const files = e.target.files;
    if (files.length === 0) return;
    
    if (!els.importAccountSelect.value) {
        alert("請先選擇「匯入目標帳戶」");
        els.fileInput.value = '';
        return;
    }

    if (files[0].type === "application/pdf") {
        if (files.length > 1) return alert("PDF 請逐一上傳");
        els.pwdModal.style.display = 'block';
        document.getElementById('pdfPwd').value = '';
        document.getElementById('pdfPwd').focus();
    } else if (files[0].type.startsWith("image/")) {
        await handleBatchImageUpload(files);
    } else {
        alert("不支援格式");
    }
};

// PDF Logic
document.getElementById('btnSubmit').onclick = async () => {
    if (state.isPdfUploading) return;
    const pwd = document.getElementById('pdfPwd').value;
    if (!pwd) return alert("請輸入密碼");
    
    const accountSelect = els.importAccountSelect;
    const bankCode = accountSelect.options[accountSelect.selectedIndex].dataset.bankCode;

    state.isPdfUploading = true;
    const btn = document.getElementById('btnSubmit');
    btn.disabled = true; btn.innerText = "⏳處理中...";
    els.pwdModal.style.display = 'none';
    UI.showStatus("正在解析 PDF...");

    try {
        const formData = new FormData();
        formData.append('file', els.fileInput.files[0]);
        formData.append('password', pwd);
        formData.append('bank_code', bankCode);

        const res = await API.previewPdf(formData);
        if (res.success) {
            UI.showStatus("✅ 解析完成", 'success');
            openPdfConfirmModal(res.data);
        } else {
            UI.showStatus("❌ " + res.message, 'error');
        }
    } catch (e) {
        UI.showStatus("連線錯誤", 'error');
    } finally {
        state.isPdfUploading = false;
        btn.disabled = false; btn.innerText = "確認上傳";
    }
};

document.getElementById('btnCancel').onclick = () => {
    els.pwdModal.style.display = 'none'; els.fileInput.value = '';
};

// PDF Confirm Modal
async function openPdfConfirmModal(data) {
    const accountSelect = els.importAccountSelect;
    document.getElementById('pdfTargetAccountDisplay').innerText = accountSelect.options[accountSelect.selectedIndex].text;
    
    state.pendingPdfTransactions = data.transactions.map(tx => ({
        ...tx,
        date: Utils.normalizeDate(tx.date)
    }));

    // Auto-match removed since we now force user to select account upfront, 
    // but the modal logic remains for confirmation (simplified).
    els.pdfConfirmModal.style.display = 'block';
}

window.closePdfConfirmModal = () => {
    els.pdfConfirmModal.style.display = 'none';
    els.fileInput.value = '';
    state.pendingPdfTransactions = [];
};

window.savePdfBatch = async () => {
    const accountId = els.importAccountSelect.value;
    const btn = document.getElementById('btnPdfSave');
    btn.innerText = "⏳ 匯入中..."; btn.disabled = true;

    try {
        const res = await API.saveBatch({
            account_id: parseInt(accountId),
            transactions: state.pendingPdfTransactions
        });
        if (res.success) {
            window.closePdfConfirmModal();
            UI.showStatus("✅ " + res.message, 'success');
            loadAccounts();
            loadTransactions();
        } else {
            alert("匯入失敗: " + res.message);
        }
    } catch (e) { alert("連線錯誤"); }
    finally { btn.innerText = "確認匯入"; btn.disabled = false; }
};

// OCR Logic
async function handleBatchImageUpload(files) {
    const accountSelect = els.importAccountSelect;
    const bankCode = accountSelect.options[accountSelect.selectedIndex].dataset.bankCode;
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) formData.append('files', files[i]);
    formData.append('bank_code', bankCode);

    UI.showStatus(`⏳ 辨識中 (${files.length} 張)...`);
    
    try {
        const res = await API.identifyOcr(formData);
        if (res.success) {
            UI.showStatus("✅ 辨識完成", 'success');
            openOcrBatchModal(res.data);
        } else {
            UI.showStatus("❌ 辨識失敗: " + res.message, 'error');
        }
    } catch (e) { UI.showStatus("❌ 連線錯誤", 'error'); }
}

function openOcrBatchModal(items) {
    const accountSelect = els.importAccountSelect;
    document.getElementById('ocrTargetAccountDisplay').innerText = accountSelect.options[accountSelect.selectedIndex].text;
    
    items.forEach(item => item.date = Utils.normalizeDate(item.date));
    UI.renderBatchCards(items);
    checkBatchDuplicates();
    els.ocrBatchModal.style.display = 'block';
}

window.closeOcrBatchModal = () => {
    els.ocrBatchModal.style.display = 'none';
    els.fileInput.value = '';
    UI.clearStatus();
};

window.removeOcrCard = (btn) => {
    btn.closest('.ocr-card').remove();
};

async function checkBatchDuplicates() {
    const accountId = els.importAccountSelect.value;
    if (!accountId) return;

    const transactions = UI.getBatchTransactions();
    if (transactions.length === 0) return;

    try {
        const res = await API.checkDuplicates({
            account_id: accountId,
            transactions: transactions
        });
        if (res.success) {
            UI.updateBatchDuplicates(res.duplicates);
        }
    } catch (e) { console.error(e); }
}

window.saveOcrBatch = async () => {
    const accountId = els.importAccountSelect.value;
    const transactions = UI.getBatchTransactions().filter(t => t.date && !isNaN(t.amount));
    
    if (transactions.length === 0) return alert("無有效資料");

    const btn = document.getElementById('btnBatchSave');
    btn.innerText = "⏳ 匯入中..."; btn.disabled = true;

    try {
        const res = await API.saveBatch({
            account_id: parseInt(accountId),
            transactions: transactions
        });
        if (res.success) {
            window.closeOcrBatchModal();
            UI.showStatus("✅ " + res.message, 'success', true);
            loadTransactions();
            loadAccounts();
        } else {
            alert(res.message);
        }
    } catch (e) { alert("連線錯誤"); }
    finally { btn.innerText = "確認全部匯入"; btn.disabled = false; }
};