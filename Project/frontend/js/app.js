// TicketMinds Global Client Application Library

// Toast notification helper
function showToast(message, type = 'success') {
    // Remove existing toast if any
    const existing = document.querySelector('.toast');
    if (existing) {
        existing.remove();
    }
    
    // Create new toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} glass-panel`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Trigger animation frame to slide in
    setTimeout(() => {
        toast.classList.add('active');
    }, 10);
    
    // Slide out and destroy after 4 seconds
    setTimeout(() => {
        toast.classList.remove('active');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}

// Global API Fetch wrapper with content type JSON and error handling
async function apiFetch(url, options = {}) {
    // Ensure headers has Content-Type if body is present
    if (options.body && typeof options.body === 'object') {
        options.headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };
        options.body = JSON.stringify(options.body);
    }
    
    // Include credentials (session cookies)
    options.credentials = 'same-origin';
    
    try {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        
        if (!response.ok) {
            const errorMsg = data.error || `HTTP error! status: ${response.status}`;
            throw new Error(errorMsg);
        }
        
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

// Session checking helper
async function checkSession() {
    try {
        const data = await apiFetch('/api/auth/session');
        return data;
    } catch (err) {
        return { logged_in: false };
    }
}

// Logout helper
async function performLogout() {
    try {
        await apiFetch('/api/auth/logout', { method: 'POST' });
        showToast('Logged out successfully.');
        setTimeout(() => {
            window.location.href = '/login';
        }, 800);
    } catch (err) {
        console.error('Logout failed:', err);
    }
}

// Setup common page UI actions when loaded
document.addEventListener('DOMContentLoaded', () => {
    // Bind any logout buttons dynamically
    const logoutBtns = document.querySelectorAll('.logout-btn-trigger');
    logoutBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            performLogout();
        });
    });
});
