/* app.js — shared utilities loaded on every page */

const API_BASE = '';

/**
 * Generic fetch wrapper around the /api prefix.
 * Throws an Error with the server's detail message on non-2xx responses.
 * Returns parsed JSON on success.
 */
async function apiFetch(path, options = {}) {
    const url = API_BASE + '/api' + path;

    // Set Content-Type to JSON for object bodies (not FormData)
    const headers = Object.assign({}, options.headers || {});
    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, Object.assign({}, options, { headers }));

    if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
            const err = await response.json();
            if (err.detail) {
                // FastAPI validation errors return detail as an array of objects
                detail = Array.isArray(err.detail)
                    ? err.detail.map(e => e.msg || JSON.stringify(e)).join('; ')
                    : String(err.detail);
            } else {
                detail = JSON.stringify(err);
            }
        } catch (_) { /* ignore parse failures */ }
        throw new Error(detail);
    }

    return response.json();
}

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = [
            'position:fixed', 'bottom:1.5rem', 'right:1.5rem',
            'z-index:9999', 'display:flex', 'flex-direction:column', 'gap:0.5rem'
        ].join(';');
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = [
        'padding:0.75rem 1.25rem',
        'border-radius:0.5rem',
        'font-size:0.9rem',
        'max-width:320px',
        'box-shadow:0 2px 8px rgba(0,0,0,0.18)',
        'transition:opacity 0.4s ease',
        'opacity:1',
        type === 'error'   ? 'background:#fee2e2;color:#b91c1c;border:1px solid #fca5a5' :
        type === 'success' ? 'background:#dcfce7;color:#15803d;border:1px solid #86efac' :
                             'background:#e0f2fe;color:#0369a1;border:1px solid #7dd3fc'
    ].join(';');

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 420);
    }, 4000);
}

// ---------------------------------------------------------------------------
// Loading overlay
// ---------------------------------------------------------------------------

function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const msg = document.getElementById('loading-message');
    if (msg) msg.textContent = message;
    if (overlay) overlay.removeAttribute('hidden');
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.setAttribute('hidden', '');
}

// ---------------------------------------------------------------------------
// Date / time helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
        // Parse as local date to avoid UTC offset shifts
        const [year, month, day] = String(dateStr).split('-').map(Number);
        const d = new Date(year, month - 1, day);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
    } catch (_) {
        return dateStr;
    }
}

function formatTime(timeStr) {
    if (!timeStr) return '—';
    try {
        const parts = String(timeStr).split(':');
        const hours = parseInt(parts[0], 10);
        const minutes = parseInt(parts[1] || '0', 10);
        if (isNaN(hours) || isNaN(minutes)) return timeStr;
        const ampm = hours < 12 ? 'AM' : 'PM';
        const h = hours % 12 || 12;
        return `${h}:${String(minutes).padStart(2, '0')} ${ampm}`;
    } catch (_) {
        return timeStr;
    }
}

// ---------------------------------------------------------------------------
// Health check — runs on every page load
// ---------------------------------------------------------------------------

async function checkHealth() {
    try {
        const data = await apiFetch('/health');
        if (!data.ai_available) {
            const banner = document.getElementById('ai-banner');
            if (banner) banner.removeAttribute('hidden');
        }
    } catch (_) {
        // Silently ignore — server may not be up yet during static browsing
    }
}

checkHealth();
