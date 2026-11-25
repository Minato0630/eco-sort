/* ==========================================================================
   EcoSort Core Client Library (Theme, Toasts, Auth Headers, Helpers)
   ========================================================================== */

// 1. THEME MANAGEMENT (Light / Dark Mode)
function initTheme() {
    const savedTheme = localStorage.getItem('eco_theme') || 'dark';
    setTheme(savedTheme);
}

function setTheme(theme) {
    if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('eco_theme', theme);

    // Update any theme toggler icons if present
    const icons = document.querySelectorAll('.theme-toggle-icon');
    icons.forEach(icon => {
        if (theme === 'light') {
            icon.className = 'fa-solid fa-moon theme-toggle-icon';
        } else {
            icon.className = 'fa-solid fa-sun theme-toggle-icon';
        }
    });
}

function toggleTheme() {
    const currentTheme = localStorage.getItem('eco_theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    showToast(`Switched to ${nextTheme === 'dark' ? 'Dark' : 'Light'} Mode`, 'info');
}

// 2. TOAST NOTIFICATION SYSTEM
function showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-solid fa-circle-info';
    if (type === 'success') iconClass = 'fa-solid fa-circle-check';
    if (type === 'error') iconClass = 'fa-solid fa-triangle-exclamation';

    toast.innerHTML = `
        <i class="${iconClass}" style="font-size:1.1rem; flex-shrink:0;"></i>
        <div style="flex:1; line-height:1.35;">${message}</div>
        <button onclick="this.parentElement.remove()" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:0.9rem;">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(30px)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// 3. AUTHENTICATION & HEADERS HELPER
function getAuthHeaders(includeJson = true) {
    const token = localStorage.getItem('eco_token');
    const headers = {};
    if (includeJson) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = "Bearer " + token;
    return headers;
}

// 4. MOBILE SIDEBAR DRAWER TOGGLING
function toggleMobileNav() {
    const sidebar = document.querySelector('.app-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('mobile-open');
    }
}

// 5. ACCESSIBLE MODALS
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

// Initialize theme on script evaluation
document.addEventListener('DOMContentLoaded', initTheme);
