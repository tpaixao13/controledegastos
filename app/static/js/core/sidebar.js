(() => {
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  const toggle   = document.getElementById('sidebarToggle');

  if (!sidebar || !overlay || !toggle) return;

  function open() {
    sidebar.classList.add('open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', () => {
    sidebar.classList.contains('open') ? close() : open();
  });

  overlay.addEventListener('click', close);

  // Fechar ao clicar em link (mobile)
  sidebar.querySelectorAll('.sidebar-link').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth < 992) close();
    });
  });

  // Fechar ao redimensionar para desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth >= 992) close();
  });
})();
