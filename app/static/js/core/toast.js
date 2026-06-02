(() => {
  const messages = window._flashMessages || [];
  if (!messages.length) return;

  const container = document.getElementById('toastContainer');
  if (!container) return;

  const COLOR = {
    success: { bg: '#198754', icon: 'bi-check-circle-fill' },
    danger:  { bg: '#dc3545', icon: 'bi-x-circle-fill' },
    error:   { bg: '#dc3545', icon: 'bi-x-circle-fill' },
    warning: { bg: '#ffc107', icon: 'bi-exclamation-triangle-fill', dark: true },
    info:    { bg: '#0dcaf0', icon: 'bi-info-circle-fill',           dark: true },
  };

  messages.forEach(([category, message]) => {
    const cfg = COLOR[category] || COLOR.info;
    const textClass = cfg.dark ? 'text-dark' : 'text-white';
    const btnClass  = cfg.dark ? '' : 'btn-close-white';

    const el = document.createElement('div');
    el.className = `toast align-items-center ${textClass} border-0`;
    el.setAttribute('role', 'alert');
    el.style.cssText = `background:${cfg.bg};border-radius:8px;min-width:280px`;

    el.innerHTML = `
      <div class="d-flex align-items-center gap-2 p-1">
        <i class="bi ${cfg.icon} ms-2 fs-5 flex-shrink-0"></i>
        <div class="toast-body flex-grow-1 ps-1">${message}</div>
        <button type="button" class="btn-close ${btnClass} me-1" data-bs-dismiss="toast"></button>
      </div>`;

    container.appendChild(el);

    const bsToast = new bootstrap.Toast(el, { delay: 4000 });
    bsToast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
  });
})();
