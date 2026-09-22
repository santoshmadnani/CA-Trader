# Script to fix terminal.html
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()
    content = f.read()

# 1. Remove duplicate Ask CA AI button and duplicate editUIBtn in profile dropdown
old_profile_btn = '<button class="btn ghost small mobile-profile-ai" id="caAiOpenMobile" style="margin-top:10px;width:100%;justify-content:center;">Ask CA AI</button>'
if old_profile_btn in text:
    text = text.replace(old_profile_btn, '')
    print("Replaced old_profile_btn")
# 1. Replace topbar buttons block
topbar_pattern = re.compile(
    r'<button class="btn gold small" id="caAiOpen".*?</div>\s*</div>\s*</div>\s*<div class="user-chip"',
    re.DOTALL
)

clean_topbar = '''<button class="btn gold small" id="caAiOpen" onclick="openModal('caAiModal'); document.getElementById('aiChatInput')?.focus();" style="display:inline-flex;align-items:center;gap:5px;font-weight:700;padding:3px 9px;height:26px;font-size:11px;cursor:pointer;border-radius:4px;" title="Chat with CA AI">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z"/></svg>
      <span class="ai-btn-text">Ask CA AI</span>
    </button>
    
    <button class="icon-btn" id="moveTopBtn" title="Move to top"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20V4M5 12l7-8 7 8"/></svg></button>
    <button class="btn small sell" id="panicKillSwitchBtn" title="EMERGENCY PANIC BUTTON: Square off ALL open positions & cancel all pending orders immediately" style="display:inline-flex;align-items:center;gap:4px;font-size:10.5px;padding:2px 8px;height:26px;font-weight:700;margin-right:4px;background:rgba(239,68,68,0.2);color:var(--sell);border:1px solid var(--sell);cursor:pointer;border-radius:4px;">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <span class="panic-btn-text">Panic Exit</span>
    </button>
    <div class="top-icon-wrap">
      <button class="icon-btn" id="notificationBtn" title="Notifications"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a2 2 0 0 0 3.4 0"/></svg><span class="badge" id="notificationBadge">0</span></button>
      <div class="notification-menu" id="notificationMenu">
        <div class="notification-tabs" id="notifTabs" style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border-soft);padding:4px 8px;">
          <div style="display:flex;gap:4px;">
            <button type="button" class="notif-tab active" data-notif-filter="all" onclick="window.selectNotifFilter(this, 'all')">All</button>
            <button type="button" class="notif-tab" data-notif-filter="news" onclick="window.selectNotifFilter(this, 'news')">News</button>
            <button type="button" class="notif-tab" data-notif-filter="orders_reco" onclick="window.selectNotifFilter(this, 'orders_reco')">Orders &amp; Recos</button>
          </div>
          <div style="display:flex;align-items:center;gap:4px;">
            <button type="button" class="btn ghost small" onclick="window.markAllNotifsRead()" style="font-size:10px;padding:2px 6px;height:22px;display:inline-flex;align-items:center;gap:3px;" title="Mark all notifications as read"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg> Read</button>
            <button type="button" class="btn ghost small" onclick="window.openNotifSettingsModal()" style="font-size:10px;padding:2px 6px;height:22px;display:inline-flex;align-items:center;gap:3px;" title="Notification settings"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></button>
            <button class="icon-btn" id="soundToggleBtn" title="Audio alerts active" style="font-size:12px;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;border-radius:4px;" onclick="window.toggleAudioAlerts(event)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
            </button>
          </div>
        </div>
        <div class="notification-list" id="notificationListBody" style="max-height:360px;overflow-y:auto;"></div>
      </div>
    </div>
  </div>
  <div class="user-chip"'''

if topbar_pattern.search(content):
    content = topbar_pattern.sub(clean_topbar, content, count=1)
    print("Cleaned topbar successfully.")
else:
    print("old_profile_btn not found")
    print("WARNING: Topbar pattern not found!")

# Remove duplicate editUIBtn if present
duplicate_edit_ui = '<button class="btn ghost small" id="editUIBtn" style="margin-top:7px;width:100%;justify-content:center;">Edit UI</button>\n        <button class="btn ghost small" id="editUIBtn" style="margin-top:10px;width:100%;justify-content:center;">Edit UI</button>'
if duplicate_edit_ui in text:
    text = text.replace(duplicate_edit_ui, '<button class="btn ghost small" id="editUIBtn" style="margin-top:10px;width:100%;justify-content:center;">Edit UI</button>')
    print("Removed duplicate editUIBtn")
# 2. Replace user menu buttons block
user_menu_pattern = re.compile(
    r'<div style="margin-top:8px;padding-top:8px;border-top:1px solid var\(--border-soft\);display:flex;flex-direction:column;gap:6px;">\s*<button class="btn small gold" id="turboLoadBtn".*?</div>\s*<button class="btn ghost small" id="fitnessSwitchBtn"',
    re.DOTALL
)

# 2. Fix the fatal syntax error at lines 8314-8316 in Script #4
# Find the broken section:
broken_fmt = """  const fmt = v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+N
... [truncated for diff preview]
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0});"""
clean_user_menu = '''<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border-soft);display:flex;flex-direction:column;gap:6px;">
          <button class="btn small gold" id="turboLoadBtn" title="Turbo Refresh (Immediate instant live reload of all data feeds)" style="width:100%;justify-content:center;font-size:11px;padding:5px 8px;font-weight:600;display:inline-flex;align-items:center;gap:5px;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>Turbo Refresh</span>
          </button>
          <button class="btn small" id="telegramAlertsBtn" onclick="window.openTelegramModal()" title="Telegram Alert Bot (Mobile alerts for signals, SL &amp; news)" style="width:100%;justify-content:center;font-size:11px;padding:5px 9px;font-weight:600;background:rgba(0,136,204,0.18);color:#29b6f6;border:1px solid rgba(0,136,204,0.45);cursor:pointer;border-radius:4px;display:inline-flex;align-items:center;gap:5px;">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.52 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
            <span>Telegram Bot Alerts</span>
          </button>
          <button type="button" class="btn ghost small" id="openClearCacheModalBtn" onclick="window.openClearCacheModal()" style="width:100%;justify-content:center;font-size:11px;padding:5px 8px;color:var(--text-muted);border:1px dashed var(--border);display:inline-flex;align-items:center;gap:5px;" title="Clear transient cached data">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18m-2 0v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            <span>Clear Cache</span>
          </button>
        </div>
        <button class="btn ghost small" id="fitnessSwitchBtn"'''

clean_fmt = """  const fmt = v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0});"""

if broken_fmt in text:
    text = text.replace(broken_fmt, clean_fmt)
    print("Fixed broken_fmt in Script #4")
if user_menu_pattern.search(content):
    content = user_menu_pattern.sub(clean_user_menu, content, count=1)
    print("Cleaned user menu successfully.")
else:
    print("Searching with regex for broken fmtMoney...")
    import re
    text = re.sub(
        r"const fmtMoney = v => v == null \|\| !isFinite\(Number\(v\)\) \? '—' : '₹'\+N\s*\.\.\.\s*\[truncated for diff preview\]\s*",
        "",
        text
    )
    print("Regex replacement applied")
    print("WARNING: User menu pattern not found!")

# 3. Enhance api timeout default to 8000ms instead of 4500ms
text = text.replace(
    "const timeoutMs = Math.max(1200, Number(options.timeoutMs || 4500));",
    "const timeoutMs = Math.max(1200, Number(options.timeoutMs || 8000));"
)
# 3. Add CSS block right before </style>
css_injection = '''
/* --- COMPACT CONTROLS & METRICS HARMONIZATION --- */
/* All Metric Clickable Boxes (Spot, CE, PE) strictly identical & responsive */
.dash-reco-grid .metric-clickable-box,
#dashCardSpot .metric-clickable-box,
#dashCardUnderlying .metric-clickable-box,
#dashCardCe .metric-clickable-box,
#dashCardPe .metric-clickable-box {
  padding: 5px 2px !important;
  min-width: 0 !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: center !important;
  box-sizing: border-box !important;
}
.dash-reco-grid .metric-clickable-box div:first-child,
#dashCardSpot .metric-clickable-box div:first-child,
#dashCardUnderlying .metric-clickable-box div:first-child,
#dashCardCe .metric-clickable-box div:first-child,
#dashCardPe .metric-clickable-box div:first-child {
  font-size: 8.5px !important;
  font-weight: 700 !important;
  letter-spacing: 0.2px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  width: 100% !important;
  text-align: center !important;
  line-height: 1.2 !important;
}
.dash-reco-grid .metric-clickable-box div:last-child,
#dashCardSpot .metric-clickable-box div:last-child,
#dashCardUnderlying .metric-clickable-box div:last-child,
#dashCardCe .metric-clickable-box div:last-child,
#dashCardPe .metric-clickable-box div:last-child {
  font-family: var(--font-mono) !important;
  font-size: 11.5px !important;
  font-weight: 700 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  width: 100% !important;
  text-align: center !important;
  line-height: 1.2 !important;
}

# 4. Enhance loadChartAiSuggestions in Script #3
old_load_ai = """    if(S){
      try {
        const d = await A(`/api/analysis/chart-ai-suggestions/${encodeURIComponent(S)}?timeframe=${encodeURIComponent(state.tf)}&days=${state.history || 7}`, {timeoutMs: 12000});"""
@media (max-width: 768px) {
  .dash-reco-grid .metric-clickable-box div:first-child,
  #dashCardSpot .metric-clickable-box div:first-child,
  #dashCardUnderlying .metric-clickable-box div:first-child,
  #dashCardCe .metric-clickable-box div:first-child,
  #dashCardPe .metric-clickable-box div:first-child {
    font-size: 7.5px !important;
    letter-spacing: 0 !important;
  }
  .dash-reco-grid .metric-clickable-box div:last-child,
  #dashCardSpot .metric-clickable-box div:last-child,
  #dashCardUnderlying .metric-clickable-box div:last-child,
  #dashCardCe .metric-clickable-box div:last-child,
  #dashCardPe .metric-clickable-box div:last-child {
    font-size: 10.5px !important;
  }
}

new_load_ai = """    const activeSym = S || (typeof selectedSymbol === 'function' ? selectedSymbol() : null) || window.CATraderSymbol || 'NIFTY';
    if(activeSym){
      try {
        const d = await A(`/api/analysis/chart-ai-suggestions/${encodeURIComponent(activeSym)}?timeframe=${encodeURIComponent(state.tf || '5m')}&days=${state.history || 5}`, {timeoutMs: 6000});"""
@media (max-width: 480px) {
  .dash-reco-grid .metric-clickable-box,
  #dashCardSpot .metric-clickable-box,
  #dashCardUnderlying .metric-clickable-box,
  #dashCardCe .metric-clickable-box,
  #dashCardPe .metric-clickable-box {
    padding: 3px 1px !important;
  }
  .dash-reco-grid .metric-clickable-box div:first-child,
  #dashCardSpot .metric-clickable-box div:first-child,
  #dashCardUnderlying .metric-clickable-box div:first-child,
  #dashCardCe .metric-clickable-box div:first-child,
  #dashCardPe .metric-clickable-box div:first-child {
    font-size: 7px !important;
  }
  .dash-reco-grid .metric-clickable-box div:last-child,
  #dashCardSpot .metric-clickable-box div:last-child,
  #dashCardUnderlying .metric-clickable-box div:last-child,
  #dashCardCe .metric-clickable-box div:last-child,
  #dashCardPe .metric-clickable-box div:last-child {
    font-size: 9.5px !important;
  }
}

if old_load_ai in text:
    text = text.replace(old_load_ai, new_load_ai)
    print("Updated loadChartAiSuggestions with activeSym fallback")
else:
    print("old_load_ai pattern not matched directly, searching...")
/* Compact Table Controls, Inputs, and Selects */
#dashExcelMatrixTable select,
#dashExcelMatrixTable input,
#dashExcelMatrixTable .matrix-weight-input,
.matrix-weight-input {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  font-size: 10.5px !important;
  height: 22px !important;
  min-height: 22px !important;
  max-height: 22px !important;
  line-height: 20px !important;
  padding: 1px 4px !important;
  border-radius: 4px !important;
  box-sizing: border-box !important;
}

# 5. Enhance sendAiChat in Script #4 to provide instant typing indicator and robust error handling
old_send_ai = """  async function sendAiChat(){ const input=$('aiChatInput'); const text=(input?.value||'').trim(); if(!text)return; addAiMessage(text,'user'); input.value=''; try{const sym=String(window.CATraderSymbol||selectedSymbol()||'NIFTY').toUpperCase(); const q=await api('/api/market/quote/'+encodeURIComponent(sym)).catch(()=>null); const r=await api('/api/ai/chat',{method:'POST',body:JSON.stringify({message:text,symbol:sym,current_setup:window.__caCurrentChartReco||{},context:{symbol:sym,quote:q}})}); addAiMessage(r.message||r.reply||r.response||r.reason||'CA AI response received.','ai');}catch(e){addAiMessage('CA AI Error: '+(e.message||'Service unavailable'),'ai')} }"""
select, .tool-input select, select.tool-input, select.form-input {
  font-family: var(--font-body) !important;
  font-size: 11.5px !important;
  height: 26px !important;
  min-height: 26px !important;
  padding: 2px 6px !important;
  border-radius: 5px !important;
  box-sizing: border-box !important;
}

new_send_ai = """  async function sendAiChat(){
    const input = $('aiChatInput');
    const text = (input?.value || '').trim();
    if(!text) return;
    addAiMessage(text, 'user');
    input.value = '';
    const placeholder = addAiMessage('✦ CA AI thinking…', 'ai');
    try {
      const sym = String(window.CATraderSymbol || selectedSymbol() || 'NIFTY').toUpperCase();
      const q = await api('/api/market/quote/' + encodeURIComponent(sym), {timeoutMs: 3000}).catch(() => null);
      const r = await api('/api/ai/chat', {
        method: 'POST',
        timeoutMs: 12000,
        body: JSON.stringify({
          message: text,
          symbol: sym,
          current_setup: window.__caCurrentChartReco || {},
          context: {symbol: sym, quote: q}
        })
      });
      if(placeholder && placeholder.parentNode) placeholder.remove();
      addAiMessage(r.message || r.reply || r.response || r.reason || 'CA AI response received.', 'ai');
    } catch(e) {
      if(placeholder && placeholder.parentNode) placeholder.remove();
      addAiMessage('CA AI Error: ' + (e.message || 'Service unavailable'), 'ai');
    }
  }"""
.btn.small,
button.btn.small,
.btn-sm,
.btn.gold.small,
.btn.buy.small,
.btn.sell.small,
.btn.ghost.small {
  min-height: 24px !important;
  height: 24px !important;
  font-size: 11px !important;
  padding: 2px 8px !important;
  line-height: 20px !important;
  box-sizing: border-box !important;
}
</style>'''

if old_send_ai in text:
    text = text.replace(old_send_ai, new_send_ai)
    print("Enhanced sendAiChat with thinking indicator and timeout")
else:
    print("old_send_ai not matched directly")
content = content.replace('</style>', css_injection, 1)
print("Injected CSS successfully.")

# 4. In JS: Update cardUnd to check both dashCardSpot and dashCardUnderlying
content = content.replace(
    "const cardUnd = document.getElementById('dashCardUnderlying');",
    "const cardUnd = document.getElementById('dashCardSpot') || document.getElementById('dashCardUnderlying');"
)
print("Updated cardUnd lookup.")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)
    f.write(content)

print("terminal.html updated successfully")

print("Saved terminal.html successfully.")
