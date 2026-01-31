// Utility Functions
export function debounce(func, delay) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}

export function normalizeDate(dateStr) {
    if (!dateStr) return "";
    const parts = dateStr.replace(/[^\d]/g, '/').split('/');
    
    if (parts.length >= 3) {
        let year = parseInt(parts[0], 10);
        const month = parts[1].padStart(2, '0');
        const day = parts[2].padStart(2, '0');
        
        if (year < 1911) {
            year += 1911;
        }
        return `${year}/${month}/${day}`;
    }
    return dateStr;
}

export function formatDateYM(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    return `${y}-${m}`;
}