
// Resilient Storage Polyfill for restricted / iframe / file / cross-origin contexts
(function(){
  function makeMockStorage(){
    var mem = {};
    return {
      getItem: function(k){ return Object.prototype.hasOwnProperty.call(mem, k) ? mem[k] : null; },
      setItem: function(k, v){ mem[k] = String(v); },
      removeItem: function(k){ delete mem[k]; },
      clear: function(){ mem = {}; },
      key: function(i){ return Object.keys(mem)[i] || null; },
      get length(){ return Object.keys(mem).length; }
    };
  }
  try {
    var testKey = '__ca_test_storage__';
    window.localStorage.setItem(testKey, '1');
    window.localStorage.removeItem(testKey);
  } catch(e) {
    try {
      Object.defineProperty(window, 'localStorage', { value: makeMockStorage(), configurable: true, writable: true });
    } catch(_) {}
  }
  try {
    var testKey2 = '__ca_test_session__';
    window.sessionStorage.setItem(testKey2, '1');
    window.sessionStorage.removeItem(testKey2);
  } catch(e) {
    try {
      Object.defineProperty(window, 'sessionStorage', { value: makeMockStorage(), configurable: true, writable: true });
    } catch(_) {}
  }
})();
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
function extractUnderlying(sym){
  if(!sym) return 'NIFTY';
  let s = String(sym).trim();
  if(s.includes('Nifty 50') || s.includes('NIFTY 50')) return 'NIFTY';
  if(s.includes('Nifty Bank') || s.includes('BANKNIFTY')) return 'BANKNIFTY';
  if(s.includes('Fin Nifty') || s.includes('FINNIFTY')) return 'FINNIFTY';
  if(s.includes('Midcp Nifty') || s.includes('MIDCPNIFTY')) return 'MIDCPNIFTY';
  if(s.startsWith('NSE_INDEX|') || s.startsWith('NSE_EQ|') || s.startsWith('BSE_INDEX|') || s.startsWith('MCX_FO|')){
    s = s.split('|')[1] || s;
  }
  const mSpace = s.match(/^([A-Z0-9_\-]+)(?:\s+\d+|\s+[0-9]{2}[A-Z]{3}|\s+(?:CE|PE))/i);
  if(mSpace && mSpace[1]) return mSpace[1].toUpperCase();
  const mCompact = s.match(/^([A-Z]+)\d{2}[A-Z0-9]{3}\d+(?:CE|PE)$/i);
  if(mCompact && mCompact[1]) return mCompact[1].toUpperCase();
  return s.split(/\s+/)[0].toUpperCase();
}
window.extractUnderlying = extractUnderlying;
