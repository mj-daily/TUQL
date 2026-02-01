// UI Rendering and DOM Manipulation
import { state } from './state.js';

// DOM Element Cache
export const els = {
    fileInput: document.getElementById('fileInput'),
    statusMsg: document.getElementById('statusMsg'),
    accountList: document.getElementById('account-list'),
    accountSummary: document.getElementById('account-summary'),
    txTableBody: document.querySelector('#txTable tbody'),
    noDataMsg: document.getElementById('noDataMsg'),
    statsIncomeTotal: document.getElementById('stats-income-total'),
    statsExpenseTotal: document.getElementById('stats-expense-total'),
    statsTableIncome: document.querySelector('#statsTableIncome tbody'),
    statsTableExpense: document.querySelector('#statsTableExpense tbody'),
    monthPicker: document.getElementById('monthPicker'),
    btnViewDetails: document.getElementById('btnViewDetails'),
    btnViewStats: document.getElementById('btnViewStats'),
    viewDetails: document.getElementById('view-details'),
    viewStats: document.getElementById('view-stats'),
    
    // Modals
    accModal: document.getElementById('accModal'),
    editModal: document.getElementById('editModal'),
    pwdModal: document.getElementById('pwdModal'),
    ocrBatchModal: document.getElementById('ocrBatchModal'),
    ocrModal: document.getElementById('ocrModal'),
    fileSelectionModal: document.getElementById('fileSelectionModal'),
    selectedFileList: document.getElementById('selectedFileList'),
    btnConfirmImport: document.getElementById('btnConfirmImport'),

    // Edit Form
    editId: document.getElementById('editId'),
    editAccountId: document.getElementById('editAccountId'),
    editDate: document.getElementById('editDate'),
    editTime: document.getElementById('editTime'),
    editSummary: document.getElementById('editSummary'),
    editAmount: document.getElementById('editAmount'),
    editRef: document.getElementById('editRef'),
    btnSaveEdit: document.getElementById('btnSaveEdit'),
    editDuplicateAlert: document.getElementById('editDuplicateAlert'),
    editInputs: document.querySelectorAll('#editModal input:not([type="hidden"])'),

    // OCR Batch
    ocrBatchList: document.getElementById('ocrBatchList'),
};

export const UI = {
    timer: null,
    
    showStatus: (msg, type = 'info', autoHide = false) => {
        if (UI.timer) clearTimeout(UI.timer);
        els.statusMsg.innerText = msg;
        els.statusMsg.style.color = type === 'error' ? 'var(--danger-color)' : 
                                    type === 'success' ? 'var(--success-color)' : 'blue';
        if (autoHide) {
            UI.timer = setTimeout(() => { els.statusMsg.innerText = ''; }, 5000);
        }
    },
    
    clearStatus: () => {
        if (UI.timer) clearTimeout(UI.timer);
        els.statusMsg.innerText = '';
    },

    toggleAccountList: (event) => {
        if (event) event.stopPropagation();
        if (els.accountList) els.accountList.classList.toggle('expanded');
        const icon = document.querySelector('.summary-icon');
        if (icon) icon.classList.toggle('rotate');
    },

    // --- Account Rendering ---
    renderAccountCards: (accounts, currentFilterId) => {
        let netWorth = 0;
        accounts.forEach(acc => netWorth += acc.balance);
        
        // 1. Render Summary Info Bar (Total Overview)
        const summaryActive = currentFilterId === null ? 'active' : '';
        const summaryHtml = `
            <div class="summary-content ${summaryActive}">
                <div class="summary-left" onclick="window.filterByAccount(null)">
                    <span class="summary-label">總資產淨值</span>
                    <span class="summary-value">$${netWorth.toLocaleString()}</span>
                </div>
                <div class="summary-right" onclick="UI.toggleAccountList(event)">
                    <span class="summary-hint">檢視帳戶</span>
                    <span class="summary-icon">▼</span>
                </div>
            </div>
        `;
        if (els.accountSummary) els.accountSummary.innerHTML = summaryHtml;

        // 2. Render Account Cards
        let html = '';
        accounts.forEach(acc => {
            let cardClass = (acc.bank_code === '' || acc.account_name === 'Manual-Import') ? 'acc-card-manual' : '';
            html += `
                <div class="account-card ${cardClass} ${currentFilterId === acc.account_id ? 'active' : ''}" 
                     onclick="window.filterByAccount(${acc.account_id})">
                    <button class="btn-import-icon" title="匯入交易 (PDF 對帳單 或 截圖)" onclick="event.stopPropagation(); window.openFileSelectionModal(${acc.account_id})">+</button>
                    <div class="acc-name">${acc.account_name}</div>
                    <div class="acc-balance">$${acc.balance.toLocaleString()}</div>
                    <div class="acc-number">${acc.account_number}</div>
                </div>
            `;
        });
        els.accountList.innerHTML = html;
    },

    renderAccTable: (accounts) => {
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
                        <button class="btn-icon edit" onclick="window.editAccount('${accStr}')">✎</button>
                        <button class="btn-icon delete" onclick="window.deleteAccount(${acc.account_id})">🗑️</button>
                    </td>
                </tr>
            `;
        }).join('');
    },

    resetAccForm: () => {
        document.getElementById('accEditId').value = '';
        document.getElementById('accName').value = '';
        document.getElementById('accBankCode').value = '';
        document.getElementById('accNumber').value = '';
        document.getElementById('accInitBalance').value = 0;
    },

    // --- Transaction Rendering ---
    renderTxTable: (transactions) => {
        if (transactions.length === 0) {
            els.txTableBody.innerHTML = '';
            els.noDataMsg.style.display = 'block';
            return;
        }
        
        els.noDataMsg.style.display = 'none';
        els.txTableBody.innerHTML = transactions.map(tx => {
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
                            <button class="btn-icon edit" onclick="window.openEditModal('${txStr}')" title="編輯">✎</button>
                            <button class="btn-icon delete" onclick="window.deleteTx(${tx.transaction_id})" title="刪除">🗑️</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    renderStatsTable: (filteredData) => {
        const incomeMap = {};
        const expenseMap = {};
        let inc = 0, exp = 0;
        
        filteredData.forEach(tx => {
            const name = tx.summary.trim(); 
            const amt = tx.amount;
            if (amt >= 0) {
                inc += amt;
                if (!incomeMap[name]) incomeMap[name] = { count: 0, total: 0 };
                incomeMap[name].count++;
                incomeMap[name].total += amt;
            } else {
                exp += amt;
                if (!expenseMap[name]) expenseMap[name] = { count: 0, total: 0 };
                expenseMap[name].count++;
                expenseMap[name].total += amt; 
            }
        });

        if (els.statsIncomeTotal) els.statsIncomeTotal.textContent = `總計：$${inc.toLocaleString()}`;
        if (els.statsExpenseTotal) els.statsExpenseTotal.textContent = `總計：$${exp.toLocaleString()}`;

        const renderRows = (map, isNeg, sortDesc) => {
            const list = Object.entries(map).map(([name, stat]) => ({ name, ...stat }));
            list.sort((a, b) => sortDesc ? (b.total - a.total) : (a.total - b.total));
            if (list.length === 0) return `<tr><td colspan="3" style="text-align:center;color:#999;padding:15px;">無資料</td></tr>`;
            return list.map(item => `
                <tr>
                    <td style="font-weight:bold;">${item.name}</td>
                    <td style="color:#666;">${item.count} 筆</td>
                    <td style="text-align:right; font-family:monospace; font-weight:bold;" class="${isNeg ? 'amount-neg' : 'amount-pos'}">
                        ${item.total.toLocaleString()}
                    </td>
                </tr>
            `).join('');
        };

        els.statsTableIncome.innerHTML = renderRows(incomeMap, false, true);
        els.statsTableExpense.innerHTML = renderRows(expenseMap, true, false);
    },

    // --- View Logic ---
    toggleViewSpy: (view) => {
        els.btnViewDetails.classList.toggle('active', view === 'details');
        els.btnViewStats.classList.toggle('active', view === 'stats');
        els.viewDetails.style.display = view === 'details' ? 'block' : 'none';
        els.viewStats.style.display = view === 'stats' ? 'block' : 'none';
    },

    // --- Edit Modal Logic ---
    populateEditModal: (tx) => {
        els.editId.value = tx.transaction_id;
        els.editAccountId.value = tx.account_id;
        els.editDate.value = tx.trans_date.replace(/\//g, '-');
        
        const timeDisplay = (tx.trans_time || '00:00:00').substring(0, 5);
        els.editTime.value = timeDisplay;
        els.editTime.dataset.originalTime = tx.trans_time || '00:00:00';
        
        els.editSummary.value = tx.summary;
        els.editAmount.value = tx.amount;
        els.editRef.value = tx.ref_no || '';
    },

    showEditDuplicateError: (isDuplicate) => {
        if (isDuplicate) {
            els.editDuplicateAlert.style.display = 'block';
            els.btnSaveEdit.innerText = "重複資料";
            [els.editDate, els.editTime, els.editAmount, els.editRef].forEach(el => el.style.borderColor = 'var(--danger-color)');
        } else {
            els.editDuplicateAlert.style.display = 'none';
            els.btnSaveEdit.innerText = "儲存";
            els.editInputs.forEach(inp => inp.style.borderColor = '#e2e8f0');
        }
    },

    updateEditSaveButton: (isEnabled) => {
        els.btnSaveEdit.disabled = !isEnabled;
        els.btnSaveEdit.classList.toggle('btn-disabled', !isEnabled);
    },

    getEditFormData: () => {
        return {
            id: els.editId.value,
            accountId: els.editAccountId.value,
            date: els.editDate.value,
            timeDisplay: els.editTime.value,
            originalTime: els.editTime.dataset.originalTime,
            summary: els.editSummary.value,
            amount: els.editAmount.value,
            ref_no: els.editRef.value
        };
    },

    // --- OCR Batch Logic ---
    renderBatchCards: (items) => {
        els.ocrBatchList.innerHTML = '';
        items.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'ocr-card';
            div.dataset.index = index;
            div.innerHTML = `
                <button class="ocr-card-del" onclick="window.removeOcrCard(this)" title="移除此筆">✕</button>
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
            els.ocrBatchList.appendChild(div);
        });
    },

    getBatchTransactions: () => {
        const cards = document.querySelectorAll('.ocr-card');
        const transactions = [];
        cards.forEach(card => {
            transactions.push({
                date: card.querySelector('.inp-date').value,
                time: card.querySelector('.inp-time').value,
                summary: card.querySelector('.inp-summary').value,
                amount: parseFloat(card.querySelector('.inp-amount').value),
                ref_no: card.querySelector('.inp-ref').value
            });
        });
        return transactions;
    },

    updateBatchDuplicates: (duplicates) => {
        const cards = document.querySelectorAll('.ocr-card');
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
};window.UI = UI;
