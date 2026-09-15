
window.$ = window.$ || (id => document.getElementById(id));
window.esc = window.esc || (v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
window.fmtMoney = window.fmtMoney || (v => '₹' + Number(v||0).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2}));
window.formatTime = window.formatTime || (v => { try { const d = new Date(v); return isNaN(d) ? String(v||'') : d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}); } catch(_) { return String(v||''); } });
window.toast = window.toast || ((m) => {
  try {
    const el = document.getElementById('toast') || (() => {
      const x = document.createElement('div');
      x.id = 'toast';
      x.style.cssText = 'position:fixed;right:18px;bottom:18px;z-index:300;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:9px 12px;font-size:11px;box-shadow:0 12px 30px rgba(0,0,0,.25);opacity:0;transition:.2s';
      document.body.appendChild(x);
      return x;
    })();
    el.textContent = m;
    el.style.opacity = '1';
    clearTimeout(el._t);
    el._t = setTimeout(() => el.style.opacity = '0', 2200);
  } catch(_) { console.log(m); }
});
window.selectedSymbol = window.selectedSymbol || (() => document.querySelector('.wl-item.selected')?.dataset.symbol || window.CATraderSymbol || window.state?.symbol || 'RELIANCE');
