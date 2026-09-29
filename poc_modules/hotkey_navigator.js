/**
 * Feature 1 POC: Zerodha Kite Hotkey Navigator & Speed Trading HUD
 * Provides instant institutional keyboard shortcuts across CA Trader.
 */
(function() {
  'use strict';

  const hotkeysEnabled = true;

  window.addEventListener('keydown', function(e) {
    if (!hotkeysEnabled) return;
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable) {
      if (e.key === 'Escape') e.target.blur();
      return;
    }

    const key = e.key.toUpperCase();

    switch(key) {
      case 'B':
        e.preventDefault();
        if (typeof openOrder === 'function') openOrder('BUY');
        break;
      case 'S':
        e.preventDefault();
        if (typeof openOrder === 'function') openOrder('SELL');
        break;
      case 'O':
        e.preventDefault();
        if (typeof showTab === 'function') showTab('options');
        break;
      case 'C':
        e.preventDefault();
        if (typeof showTab === 'function') showTab('charts');
        break;
      case 'D':
        e.preventDefault();
        if (typeof showTab === 'function') showTab('dashboard');
        break;
      case 'N':
        e.preventDefault();
        if (typeof showTab === 'function') showTab('news');
        break;
      case 'M':
        e.preventDefault();
        if (typeof showTab === 'function') showTab('movers');
        break;
      case 'F':
        e.preventDefault();
        if (typeof showTab === 'function') showTab('fundamentals');
        break;
      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
        e.preventDefault();
        const wlSelect = document.getElementById('watchlistSelect');
        if (wlSelect && wlSelect.options[Number(key) - 1]) {
          wlSelect.selectedIndex = Number(key) - 1;
          wlSelect.dispatchEvent(new Event('change'));
        }
        break;
      case 'ESCAPE':
        document.querySelectorAll('.modal.active, .modal[style*="display: block"]').forEach(m => {
          m.classList.remove('active');
          m.style.display = 'none';
        });
        break;
      case '?':
        window.toggleHotkeyHUD && window.toggleHotkeyHUD();
        break;
    }
  });

  window.toggleHotkeyHUD = function() {
    let hud = document.getElementById('caHotkeyHudModal');
    if (!hud) {
      hud = document.createElement('div');
      hud.id = 'caHotkeyHudModal';
      hud.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:10000;background:rgba(12,18,28,0.95);border:1px solid #00f0ff;border-radius:12px;padding:20px;box-shadow:0 12px 40px rgba(0,0,0,0.8);color:#fff;font-family:sans-serif;width:400px;display:none;backdrop-filter:blur(16px);';
      hud.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:10px;margin-bottom:12px;">
          <b style="font-size:14px;color:#00f0ff;">⚡ Institutional Hotkey Commander</b>
          <button onclick="this.closest('#caHotkeyHudModal').style.display='none'" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:16px;">&times;</button>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;">
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;color:#00f0ff;">B</kbd> Quick Buy</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;color:#ff5c72;">S</kbd> Quick Sell</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;">O</kbd> Option Chain</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;">C</kbd> Candlestick Chart</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;">D</kbd> Main Dashboard</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;">N</kbd> News by Jarvis</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;">1-5</kbd> Watchlist Tabs</div>
          <div><kbd style="background:#222;padding:2px 6px;border-radius:4px;border:1px solid #444;">ESC</kbd> Close All Modals</div>
        </div>
      `;
      document.body.appendChild(hud);
    }
    hud.style.display = (hud.style.display === 'none' || !hud.style.display) ? 'block' : 'none';
  };
})();
