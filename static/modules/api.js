// API Interaction Layer
const API_BASE = '/api';

async function request(url, options = {}) {
    try {
        const res = await fetch(url, options);
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("API Error:", e);
        throw e;
    }
}

export const API = {
    getAccounts: () => request(`${API_BASE}/accounts`),
    
    createAccount: (payload) => request(`${API_BASE}/account`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }),

    updateAccount: (id, payload) => request(`${API_BASE}/account/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }),

    deleteAccount: (id) => request(`${API_BASE}/account/${id}`, { method: 'DELETE' }),

    getTransactions: () => request(`${API_BASE}/transactions`),

    deleteTransaction: (id) => request(`${API_BASE}/transaction/${id}`, { method: 'DELETE' }),

    updateTransaction: (id, payload) => request(`${API_BASE}/transaction/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }),

    checkDuplicates: (payload) => request(`${API_BASE}/check-duplicates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }),

    previewPdf: (formData) => request(`${API_BASE}/pdf-preview`, {
        method: 'POST',
        body: formData
    }),

    saveBatch: (payload) => request(`${API_BASE}/save-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }),

    identifyOcr: (formData) => request(`${API_BASE}/ocr-identify`, {
        method: 'POST',
        body: formData
    }),

    saveManual: (payload) => request(`${API_BASE}/save-manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
};