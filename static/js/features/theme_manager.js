// Theme dropdown (desktop)
const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeMenu = document.getElementById('themeMenu');
const themeOptions = document.querySelectorAll('.theme-option');

if(themeToggleBtn) themeToggleBtn.addEventListener('click', ()=>{
  themeMenu.classList.toggle('open');
});

document.addEventListener('click', (e)=>{
  if(!e.target.closest('.theme-dropdown')){
    if(themeMenu) themeMenu.classList.remove('open');
  }
});

const THEMES = [
  {name:'ivory',label:'White',bg:'#FFFFFF'},
  {name:'mint',label:'Mint',bg:'rgba(76,206,149,0.15)'},
  {name:'cream',label:'Cream',bg:'#F6F4EE'},
  {name:'powder',label:'Powder',bg:'#F8F6FB'},
  {name:'peach',label:'Peach',bg:'#FFF9F5'},
  {name:'midnight',label:'Dark',bg:'#0A0D12'},
  {name:'slate',label:'Slate',bg:'#0E1826'},
];

function setTheme(name){
  document.body.setAttribute('data-theme', name);
  document.querySelectorAll('.theme-option').forEach(opt=>opt.classList.toggle('active', opt.dataset.theme===name));
  document.querySelectorAll('.user-menu-theme-swatch').forEach(s=>s.classList.toggle('active', s.dataset.theme===name));
  if(themeMenu) themeMenu.classList.remove('open');
  const um = document.getElementById('userMenu');
  if(um) um.classList.remove('open');
  localStorage.setItem('selectedTheme', name);
}

if(themeOptions) themeOptions.forEach(opt=>{
  opt.addEventListener('click', ()=>setTheme(opt.dataset.theme));
});

// Populate user-menu theme swatches
const umThemes = document.getElementById('userMenuThemes');
if(umThemes){
  THEMES.forEach(t=>{
    const s = document.createElement('div');
    s.className = 'user-menu-theme-swatch';
    s.dataset.theme = t.name;
    s.title = t.label;
    s.style.cssText = `background:${t.bg};border:1.5px solid rgba(0,0,0,.15);`;
    s.addEventListener('click', ()=>setTheme(t.name));
    umThemes.appendChild(s);
  });
}

const savedTheme = localStorage.getItem('selectedTheme') || 'ivory';
setTheme(savedTheme);

// Core Market Hours Helpers (available globally)
window.isAnyMarketOpen = function() {
  const d = new Date();
  const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
  const ist = new Date(utc + (3600000 * 5.5));
  const day = ist.getDay();
  if (day === 0 || day === 6) return false;
  const mins = ist.getHours() * 60 + ist.getMinutes();
  const nseOpen = mins >= 555 && mins <= 930;
  const mcxOpen = mins >= 540 && mins <= 1410;
  return nseOpen || mcxOpen;
};

window.isInstrumentMarketOpen = function(sym) {
  const d = new Date();
  const utc = d.getTime() + (d.getTimezoneOffset() * 60000);
  const ist = new Date(utc + (3600000 * 5.5));
  const day = ist.getDay();
  if (day === 0 || day === 6) return false;
  const mins = ist.getHours() * 60 + ist.getMinutes();
  const s = String(sym || '').toUpperCase();
  if (s.includes('CRUDE') || s.includes('GOLD') || s.includes('SILVER') || s.includes('NATURALGAS') || s.includes('COPPER')) {
    return mins >= 540 && mins <= 1410;
  }
  return mins >= 555 && mins <= 930;
};

function showTab(name){
  if(!name) return;
  if(window.navIsDragging) { window.navIsDragging = false; return; }
  const panelName = name; // 'reco' and 'notes' map directly to their panels
  document.querySelectorAll('.navtab').forEach(t=>t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.mobile-dock-item').forEach(btn=>btn.classList.toggle('active', btn.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active', p.id==='panel-'+panelName));
  // Ensure active panels are visible
  document.querySelectorAll('.panel.active').forEach(p=>{
    p.style.minHeight = p.style.minHeight || '';
    p.style.display = '';
  });
  try {
    if(name === 'reco'){
      if(typeof loadRecommendations === 'function') loadRecommendations(false);
      if(typeof loadRecommendationHistory === 'function') loadRecommendationHistory();
    } else if(name === 'backtesting'){
      if(typeof initBacktestingTab === 'function') initBacktestingTab();
    } else if(name === 'dashboard'){
      if(typeof loadDashboard === 'function') loadDashboard();
    } else if(name === 'charts'){
      if(typeof loadChart === 'function') loadChart();
    } else if(name === 'options'){
      if(typeof loadOptions === 'function') loadOptions();
    } else if(name === 'news'){
      if(typeof loadNewsByCaAi === 'function') loadNewsByCaAi();
    } else if(name === 'fundamentals'){
      if(typeof loadFundamentals === 'function') loadFundamentals();
    } else if(name === 'other-factors'){
      if(typeof loadOtherFactorsSuite === 'function') loadOtherFactorsSuite(false);
    } else if(name === 'movers'){
      if(typeof loadMovers === 'function') loadMovers();
    } else if(name === 'orders'){
      if(typeof loadPortfolioSnapshot === 'function') loadPortfolioSnapshot(false);
    } else if(name === 'funds'){
      if(typeof loadFundsTab === 'function') loadFundsTab();
    } else if(name === 'notifications'){
      if(typeof loadDedicatedNotifications === 'function') loadDedicatedNotifications(false);
    } else if(name === 'api-passbook'){
      if(typeof loadAdminApiPassbook === 'function') loadAdminApiPassbook();
    } else if(name === 'console'){
      if(typeof loadServerConsole === 'function') loadServerConsole();
    } else if(name === 'reports'){
      if(typeof loadReports === 'function') loadReports();
    } else if(name === 'quiz'){
      if(typeof loadQuiz === 'function') loadQuiz();
    } else if(name === 'tutorial'){
      if(typeof setupTutorialTrees === 'function') setupTutorialTrees();
    }
  } catch(_) {}
  try { document.querySelector('.sidebar')?.classList.remove('mobile-open'); } catch(_) {}
}
window.showTab = showTab;
['click', 'pointerdown'].forEach(evtName => {
  document.querySelectorAll('.navtab').forEach(t=>{
    t.addEventListener(evtName, (e)=>{
      const targetTab = t.dataset.tab || e.target.closest('.navtab')?.dataset.tab;
      if(targetTab) showTab(targetTab);
    }, {passive: true});
  });
});
document.querySelectorAll('.wl-item').forEach(item=>{
  item.addEventListener('click', ()=>{
    document.querySelectorAll('.wl-item').forEach(i=>i.classList.remove('selected'));
    item.classList.add('selected');
  });
});
document.querySelectorAll('.switch').forEach(s=>{
  s.addEventListener('click', ()=>s.classList.toggle('on'));
});
document.querySelectorAll('.chip-filter').forEach(c=>{
  c.addEventListener('click', ()=>{
    c.parentElement.querySelectorAll('.chip-filter').forEach(x=>x.classList.remove('active'));
    c.classList.add('active');
  });
});

// Global Early State Definitions
window.optionState = window.optionState || {expiry: null, chain: null};
var optionState = window.optionState;

// ===== EDIT UI SYSTEM =====
let caEditMode = false;
const caEditBar = document.createElement('div');
caEditBar.className = 'ca-edit-bar';
caEditBar.innerHTML = `
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
    <span style="font-weight:700;color:var(--gold);">✦ Edit UI Mode</span>
    <span class="muted" style="font-size:11px;">Drag cards (⠿) to reposition stacked layout</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <button id="caResetLayout" class="btn ghost small" style="font-size:11px;">↺ Reset Layout</button>
    <button id="caEditDone" style="background:var(--primary);color:#ffffff;border:none;padding:4px 12px;border-radius:5px;font-weight:700;cursor:pointer;font-size:11.5px;">✓ Done</button>
  </div>
`;
document.body.appendChild(caEditBar);

// Initialize compact buttons mode from localStorage
if(localStorage.getItem('ca_compact_buttons') === '1'){
  document.body.classList.add('compact-ui-buttons');
  const btn = document.getElementById('caToggleCompactButtons');
  if(btn) btn.textContent = '⊙ Normal Buttons';
}

function applySavedCardLayouts(){
  try {
    const saved = JSON.parse(localStorage.getItem('ca_card_layouts') || '{}');
    document.querySelectorAll('.card[id]').forEach(card => {
      const info = saved[card.id];
      if(info){
        card.classList.remove('ca-col-1', 'ca-col-2', 'ca-col-full', 'card-compact');
        if(info.colClass) card.classList.add(info.colClass);
        if(info.isCompact) card.classList.add('card-compact');
      }
    });
  } catch(_) {}
}

function saveCardLayouts(){
  try {
    const saved = {};
    document.querySelectorAll('.card[id]').forEach(card => {
      let colClass = '';
      if(card.classList.contains('ca-col-1')) colClass = 'ca-col-1';
      else if(card.classList.contains('ca-col-2')) colClass = 'ca-col-2';
      else if(card.classList.contains('ca-col-full')) colClass = 'ca-col-full';
      const isCompact = card.classList.contains('card-compact');
      if(colClass || isCompact){
        saved[card.id] = { colClass, isCompact };
      }
    });
    localStorage.setItem('ca_card_layouts', JSON.stringify(saved));
  } catch(_) {}
}

function enableEditMode(){
  caEditMode = true;
  document.body.classList.add('ca-edit-mode');
  caEditBar.classList.add('active');

  const btn = document.getElementById('caToggleCompactButtons');
  if(btn){
    btn.textContent = document.body.classList.contains('compact-ui-buttons') ? '⊙ Normal Buttons' : '⊙ Compact Buttons';
  }

  // Add drag handles & resize controls to cards
  document.querySelectorAll('.panel.active .card, #panel-charts .card').forEach((card, idx) => {
    if(!card.id) card.id = 'ca-card-auto-' + idx;

    if(!card.querySelector('.ca-drag-handle')){
      const handle = document.createElement('div');
      handle.className = 'ca-drag-handle';
      handle.title = 'Drag to reposition card';
      handle.innerHTML = '⠿';
      handle.draggable = true;

      handle.ondragstart = (e) => {
        e.dataTransfer.setData('text/plain', card.id);
        card.classList.add('ca-card-dragging');
      };
      handle.ondragend = () => {
        card.classList.remove('ca-card-dragging');
        saveCardLayouts();
      };
      card.appendChild(handle);
    }

    // Cards stack full width by default (Item 36 & 37)

    card.ondragover = (e) => { e.preventDefault(); };
    card.ondrop = (e) => {
      e.preventDefault();
      const dragging = document.querySelector('.ca-card-dragging');
      if(dragging && dragging !== card && card.parentNode === dragging.parentNode){
        card.parentNode.insertBefore(dragging, card);
        saveCardLayouts();
      }
    };
  });

  document.getElementById('userMenu')?.classList.remove('open');
}

function disableEditMode(){
  caEditMode = false;
  document.body.classList.remove('ca-edit-mode');
  caEditBar.classList.remove('active');
  saveCardLayouts();
  toast('Edit UI mode closed · Layout saved');
}

document.getElementById('caEditDone')?.addEventListener('click', disableEditMode);
document.getElementById('editUIBtn')?.addEventListener('click', enableEditMode);

document.getElementById('caToggleCompactButtons')?.addEventListener('click', () => {
  const isCompact = document.body.classList.toggle('compact-ui-buttons');
  localStorage.setItem('ca_compact_buttons', isCompact ? '1' : '0');
  const btn = document.getElementById('caToggleCompactButtons');
  if(btn) btn.textContent = isCompact ? '⊙ Normal Buttons' : '⊙ Compact Buttons';
  toast(isCompact ? 'Compact buttons enabled across UI' : 'Standard button sizing restored');
});

document.getElementById('caResetLayout')?.addEventListener('click', () => {
  if(!confirm('Reset all customized card sizes and layouts to default?')) return;
  localStorage.removeItem('ca_card_layouts');
  document.querySelectorAll('.card').forEach(card => {
    card.classList.remove('ca-col-1', 'ca-col-2', 'ca-col-full', 'card-compact');
    card.style.width = '';
    card.style.height = '';
  });
  toast('UI layouts reset to defaults');
});

// Auto-restore saved card layouts on load
applySavedCardLayouts();

// ===== SIDEBAR RESIZE =====
const sidebarResizer = document.getElementById('sidebarResizer');
const mainSidebar = document.getElementById('mainSidebar');
if(sidebarResizer && mainSidebar){
  let isResizing = false;
  sidebarResizer.addEventListener('mousedown', e=>{
    isResizing = true;
    sidebarResizer.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', e=>{
    if(!isResizing) return;
    const rect = mainSidebar.getBoundingClientRect();
    const newW = Math.max(180, Math.min(420, e.clientX - rect.left));
    mainSidebar.style.width = newW + 'px';
    mainSidebar.style.flexShrink = '0';
  });
  document.addEventListener('mouseup', ()=>{
    if(!isResizing) return;
    isResizing = false;
    sidebarResizer.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    localStorage.setItem('ca_sidebar_width', mainSidebar.style.width);
  });
  // Restore saved width
  const savedW = localStorage.getItem('ca_sidebar_width');
  if(savedW) { const pw = parseInt(savedW); mainSidebar.style.width = Math.min(320, Math.max(220, isNaN(pw)?266:pw)) + 'px'; }
}

// ===== MCX Option Chain Selector =====
const mcxOptLoadBtn = document.getElementById('mcxOptLoadBtn');
const mcxOptExpiry = document.getElementById('mcxOptExpiry');
const mcxOptYear = document.getElementById('mcxOptYear');
if(mcxOptExpiry && mcxOptYear){
  const months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  const now = new Date();
  // Populate expiry months (current + 6)
  for(let i=0;i<6;i++){
    const d = new Date(now.getFullYear(), now.getMonth()+i, 1);
    const opt = document.createElement('option');
    const yr = String(d.getFullYear()).slice(-2);
    const mo = months[d.getMonth()];
    opt.value = yr+mo;
    opt.textContent = mo + ' ' + d.getFullYear();
    mcxOptExpiry.appendChild(opt);
  }
  // Year options
  for(let y=now.getFullYear();y<=now.getFullYear()+2;y++){
    const opt = document.createElement('option');
    opt.value = String(y).slice(-2);
    opt.textContent = y;
    mcxOptYear.appendChild(opt);
  }
  mcxOptLoadBtn?.addEventListener('click', async()=>{
    const comm = (document.getElementById('mcxOptSymbol')?.value || S || 'CRUDEOIL').trim().toUpperCase();
    const exp = document.getElementById('mcxOptExpiry')?.value || '';
    if(!comm){ alert('Enter an MCX commodity symbol'); return; }
    mcxOptLoadBtn.textContent = '⏳ Loading…';
    mcxOptLoadBtn.disabled = true;
    try{
      window.optionState = window.optionState || {expiry: null, chain: null};
      window.optionState.expiry = exp || null;
      S = comm;
      window.CATraderSymbol = comm;
      if(typeof loadOptions === 'function') {
        await loadOptions();
      } else if(window.loadOptions) {
        await window.loadOptions();
      }
      if(typeof toast === 'function') toast('Loaded MCX option chain for ' + comm);
    }catch(err){
      alert('MCX Options lookup: ' + err.message);
    }finally{
      mcxOptLoadBtn.textContent = 'Load Chain';
      mcxOptLoadBtn.disabled = false;
    }
  });
}

// ===== MAX PROFIT RECOMMENDATION =====
document.getElementById('maxProfitRecommendationBtn')?.addEventListener('click', async()=>{
  const sym = window.__CA_CURRENT_SYMBOL || '';
  if(!sym){alert('Select an instrument first');return;}
  const btn = document.getElementById('maxProfitRecommendationBtn');
  btn.textContent = '⏳ Analyzing…';
  btn.disabled = true;
  try{
    const res = await fetch('/api/recommendations/on-demand',{
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({symbol:sym,timeframe:'5m',max_profit_mode:true,ask_ai:false})
    });
    const data = await res.json();
    // Render in the first consensus card
    const cards = document.querySelectorAll('#recommendationCards .consensus');
    if(cards[0]){
      const v = cards[0].querySelector('.verdict-badge');
      const side = (data.recommendation||'').toUpperCase();
      if(v){
        v.textContent = side==='BUY'?'MAX PROFIT ↑':side==='SELL'?'MAX PROFIT ↓':'NO TRADE';
        v.className = 'verdict-badge ' + (side==='BUY'?'buy':side==='SELL'?'sell':'mixed');
        v.style.background = 'linear-gradient(145deg,#26D9A6,#00bfff)';
        v.style.color = '#0B2A1E';
      }
      const foot = cards[0].querySelector('.consensus-foot');
      if(foot && data.entry){
        foot.innerHTML = `<span>Entry <b>${data.entry?.toFixed?data.entry.toFixed(2):data.entry}</b></span><span>SL <b>${data.stop_loss?.toFixed?data.stop_loss.toFixed(2):data.stop_loss||'—'}</b></span><span>Tgt <b>${data.target?.toFixed?data.target.toFixed(2):data.target||'—'}</b></span>`;
      }
      const muted = cards[0].querySelector('.muted');
      if(muted) muted.textContent = data.rationale||data.reason||'Max profit mode analysis complete.';
    }
  }catch(err){
    alert('Max Profit analysis failed: '+err.message);
  }finally{
    btn.textContent = '⚡ Max Profit';
    btn.disabled = false;
  }
});
</script>
