
(() => {
  // --- ripple micro-interaction ---
  const rippleSel = '.btn,.icon-btn,.navtab,.chip-filter,.tf-btn,.add-btn,.mobile-menu-btn';
  document.addEventListener('click', (e) => {
    const target = e.target.closest(rippleSel);
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 1.4;
    const ripple = document.createElement('span');
    ripple.className = 'ca-ripple';
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    target.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  });

  // --- sidebar backdrop + scroll lock for the mobile drawer ---
  const sidebar = document.querySelector('.sidebar');
  const menuBtn = document.getElementById('mobileMenuBtn');
  if (sidebar && menuBtn) {
    const backdrop = document.createElement('div');
    backdrop.id = 'caSidebarBackdrop';
    document.body.appendChild(backdrop);
    const syncBackdrop = () => {
      const open = sidebar.classList.contains('mobile-open');
      backdrop.classList.toggle('show', open);
      document.body.style.overflow = open && window.innerWidth <= 760 ? 'hidden' : '';
    };
    const mo = new MutationObserver(syncBackdrop);
    mo.observe(sidebar, { attributes: true, attributeFilter: ['class'] });
    backdrop.addEventListener('click', () => sidebar.classList.remove('mobile-open'));
  }
})();
