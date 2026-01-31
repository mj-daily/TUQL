// State Management
export const state = {
    allTransactions: [],
    currentFilterAccountId: null, // null represents 'All'
    pendingPdfTransactions: [],
    isPdfUploading: false,
    currentYearMonth: "",
    currentView: "details",
    editOriginal: null,
    editDuplicateFlag: false
};

// Helper: Get transactions based on current filters logic
export function getFilteredTransactions() {
    return state.allTransactions.filter(tx => {
        // 1. Account Filter
        const matchAccount = state.currentFilterAccountId === null || tx.account_id === state.currentFilterAccountId;
        // 2. Month Filter
        if (!tx.trans_date) return false;
        const txYearMonth = tx.trans_date.substring(0, 4) + '-' + tx.trans_date.substring(5, 7);
        const matchMonth = txYearMonth === state.currentYearMonth;
        
        return matchAccount && matchMonth;
    });
}