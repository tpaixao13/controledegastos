// FinFam — Toast system
// Processa window._flashMessages e expõe window.showToast

const _TOAST_CFG = {
  success: { bg: '#198754', icon: 'bi-check-circle-fill',          dark: false },
  danger:  { bg: '#dc3545', icon: 'bi-x-circle-fill',              dark: false },
  error:   { bg: '#dc3545', icon: 'bi-x-circle-fill',              dark: false },
  warning: { bg: '#ffc107', icon: 'bi-exclamation-triangle-fill',  dark: true  },
  info:    { bg: '#0dcaf0', icon: 'bi-info-circle-fill',           dark: true  },
};

function showToast(message, category = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const cfg = _TOAST_CFG[category] || _TOAST_CFG.info;
  const textClass = cfg.dark ? 'text-dark' : 'text-white';
  const btnClass  = cfg.dark ? '' : 'btn-close-white';

  const el = document.createElement('div');
  el.className = `toast align-items-center ${textClass} border-0`;
  el.setAttribute('role', 'alert');
  el.style.cssText = `background:${cfg.bg};border-radius:8px;min-width:280px;max-width:400px`;

  el.innerHTML = `
    <div class="d-flex align-items-center gap-2 p-1">
      <i class="bi ${cfg.icon} ms-2 fs-5 flex-shrink-0"></i>
      <div class="toast-body flex-grow-1 ps-1">${message}</div>
      <button type="button" class="btn-close ${btnClass} me-1 flex-shrink-0"
              data-bs-dismiss="toast"></button>
    </div>`;

  container.appendChild(el);

  if (typeof bootstrap !== 'undefined') {
    const bsToast = new bootstrap.Toast(el, { delay: 4000 });
    bsToast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
  } else {
    setTimeout(() => el.remove(), 4500);
  }
}

// Expõe globalmente
window.showToast = showToast;

// Processa flash messages do Flask (on page load)
document.addEventListener('DOMContentLoaded', () => {
  const messages = window._flashMessages || [];
  messages.forEach(([cat, msg]) => showToast(msg, cat));
});
