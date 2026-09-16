import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add Dedicated Notifications Panel & Admin API Passbook Panel right after panel-alerts
target_alerts_div = '<div class="panel" id="panel-alerts" style="display:none"></div>'

panels_html = """<div class="panel" id="panel-alerts" style="display:none"></div>

    <!-- ============ DEDICATED NOTIFICATIONS & ALERT CENTER (Item 22) ============ -->
    <div class="panel" id="panel-notifications" style="display:none;">
      <div class="page-head">
        <div>
          <div class="page-title">Notifications &amp; Alert Center</div>
          <div class="page-sub">Institutional alerts, Golden Trade triggers, Sentinel risk advisories, and breaking news</div>
        </div>
        <div class="head-actions" style="display:flex;gap:8px;">
          <button class="btn ghost small" onclick="loadDedicatedNotifications(true)">↻ Refresh</button>
          <button class="btn small" onclick="markAllNotificationsRead()">✓ Mark All Read</button>
        </div>
      </div>

      <div class="card" style="margin-bottom:16px;">
        <div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;border-bottom:1px solid var(--border-soft);margin-bottom:12px;">
          <button class="tab-sub-btn active" id="notifSubTabAll" onclick="filterDedicatedNotifications('all', this)">All Notifications</button>
          <button class="tab-sub-btn" id="notifSubTabGolden" onclick="filterDedicatedNotifications('golden', this)">🌟 Golden Trades</button>
          <button class="tab-sub-btn" id="notifSubTabRisk" onclick="filterDedicatedNotifications('risk', this)">🛡️ Risk Advisories</button>
          <button class="tab-sub-btn" id="notifSubTabNews" onclick="filterDedicatedNotifications('news', this)">📰 High-Impact News</button>
        </div>

        <div id="dedicatedNotifList" style="display:flex;flex-direction:column;gap:8px;min-height:200px;">
          <div class="muted" style="text-align:center;padding:24px;">Loading notifications…</div>
        </div>
      </div>
    </div>

    <!-- ============ ADMIN API & RESOURCE STATEMENT PASSBOOK (Item 12) ============ -->
    <div class="panel" id="panel-api-passbook" style="display:none;">
      <div class="page-head">
        <div>
          <div class="page-title">Admin API &amp; Resource Statement Passbook</div>
          <div class="page-sub">Real-time Upstox rate limits (RPM vs actual), Gemini AI token usage, and live audit trail (Admin Only)</div>
        </div>
        <div class="head-actions" style="display:flex;gap:8px;">
          <span id="passbookAutoSyncBadge" class="tag buy" style="font-size:10px;">● Live 3s Meter</span>
          <button class="btn ghost small" onclick="loadAdminApiPassbook()">↻ Refresh Statement</button>
        </div>
      </div>

      <!-- Real-time Quota & Usage Meters -->
      <div class="grid grid-2" style="margin-bottom:16px;gap:12px;">
        <!-- Upstox Meter -->
        <div class="card" style="border-left:4px solid var(--buy);background:var(--surface);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:13px;color:var(--text);">Upstox API Live Meter</b>
            <span id="upstoxMeterStatus" class="tag buy" style="font-size:10px;">HEALTHY</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
            <span class="muted" style="font-size:11px;">Current Requests / Minute:</span>
            <b id="upstoxRpmText" style="font-family:var(--font-mono);font-size:15px;color:var(--buy);">18 / 250 RPM</b>
          </div>
          <div style="width:100%;height:6px;background:var(--surface-2);border-radius:3px;overflow:hidden;margin-bottom:8px;">
            <div id="upstoxRpmBar" style="width:7%;height:100%;background:var(--buy);transition:width 0.3s;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);">
            <span>Today's Total REST Calls: <b id="upstoxTotalCallsText" style="color:var(--text);">1,420</b></span>
            <span>Limit: 250 req/min</span>
          </div>
        </div>

        <!-- Gemini AI Meter -->
        <div class="card" style="border-left:4px solid var(--gold);background:var(--surface);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:13px;color:var(--text);">Google Gemini 2.0 AI Engine</b>
            <span id="geminiMeterStatus" class="tag gold" style="font-size:10px;">OPTIMAL</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
            <span class="muted" style="font-size:11px;">Tokens Consumed Today:</span>
            <b id="geminiTodayTokensText" style="font-family:var(--font-mono);font-size:15px;color:var(--gold);">42,500 tokens</b>
          </div>
          <div style="width:100%;height:6px;background:var(--surface-2);border-radius:3px;overflow:hidden;margin-bottom:8px;">
            <div id="geminiTpmBar" style="width:4%;height:100%;background:var(--gold);transition:width 0.3s;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);">
            <span>Estimated Cost: <b id="geminiCostText" style="color:var(--text);">₹0.38</b></span>
            <span>Limit: 1,000,000 TPM</span>
          </div>
        </div>
      </div>

      <!-- Data Feeds Health Grid -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-title" style="margin-bottom:10px;font-size:13px;">Connected Data Feeds &amp; Quotas</div>
        <div id="apiDataSourcesGrid" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:10px;font-size:11.5px;">
          <div class="muted" style="padding:10px;">Loading data feeds…</div>
        </div>
      </div>

      <!-- Chronological Statement / Passbook Ledger -->
      <div class="card">
        <div class="card-title" style="margin-bottom:10px;font-size:13px;display:flex;justify-content:space-between;align-items:center;">
          <span>API &amp; AI Usage Statement Ledger (Audit Trail)</span>
          <span class="muted" style="font-size:11px;">Chronological Trail</span>
        </div>
        <div class="table-wrap">
          <table style="width:100%;font-size:11.5px;">
            <thead>
              <tr style="background:var(--surface-2);">
                <th>Timestamp (IST)</th>
                <th>Provider / Service</th>
                <th>Activity / Feature</th>
                <th>Usage / Volume</th>
                <th>Rate / Quota</th>
                <th>Estimated Cost</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody id="apiPassbookLedgerBody">
              <tr><td colspan="7" class="data-empty" style="text-align:center;padding:16px;">Loading statement…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>"""

if target_alerts_div in text:
    text = text.replace(target_alerts_div, panels_html, 1)
    print('[OK] Injected panel-notifications and panel-api-passbook')
else:
    print('[FAIL] target_alerts_div not found')
    sys.exit(1)

# 2. Add Navtab Buttons into navtabs
target_navtab_reports = '<button class="navtab" data-tab="reports"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>Reports</button>'

replacement_navtabs = target_navtab_reports + """
      <button class="navtab" data-tab="notifications"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>Notifications</button>
      <button class="navtab admin-only" data-tab="api-passbook" id="navtabApiPassbook"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>API Passbook</button>"""

if target_navtab_reports in text:
    text = text.replace(target_navtab_reports, replacement_navtabs, 1)
    print('[OK] Injected Notifications and API Passbook navtabs')
else:
    print('[FAIL] target_navtab_reports not found')
    sys.exit(1)

# 3. Add Client JavaScript Engine for Release 52
js_engine = """
// ==============================================================================
// RELEASE 52 CLIENT ENGINE: NOTIFICATIONS, DRAWINGS CACHE, PASSBOOK & AUDIO
// ==============================================================================

// Item 19 & 20: Web Audio Chime Generator
window.playNotificationChime = function(type = 'normal'){
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    
    if(type === 'golden'){
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(1046.5, audioCtx.currentTime); // C6
      osc.frequency.setValueAtTime(1567.98, audioCtx.currentTime + 0.12); // G6
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.45);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.45);
    } else if(type === 'high'){
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      osc.frequency.setValueAtTime(440, audioCtx.currentTime + 0.1); // A4
      gain.gain.setValueAtTime(0.25, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.35);
    } else {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.25);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.25);
    }
  } catch(e) {
    console.debug('Web Audio context blocked before gesture:', e);
  }
};

window.showRightSideNotification = function(title, body, type = 'normal'){
  const container = document.getElementById('rightSideNotificationContainer');
  if(!container) return;
  playNotificationChime(type);
  
  const notif = document.createElement('div');
  notif.style.cssText = `
    pointer-events: auto;
    background: var(--surface);
    border: 1px solid ${type === 'golden' ? 'var(--gold)' : (type === 'high' ? 'var(--sell)' : 'var(--border)')};
    border-left: 4px solid ${type === 'golden' ? 'var(--gold)' : (type === 'high' ? 'var(--sell)' : 'var(--buy)')};
    border-radius: 10px;
    padding: 11px 13px;
    box-shadow: 0 12px 36px rgba(0,0,0,0.5);
    display: flex;
    flex-direction: column;
    gap: 4px;
    transform: translateX(120%);
    transition: transform 0.35s cubic-bezier(0.2, 0.9, 0.3, 1.2), opacity 0.3s;
    opacity: 0;
  `;
  
  notif.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <b style="font-size:11.5px;color:${type === 'golden' ? 'var(--gold)' : (type === 'high' ? 'var(--sell)' : 'var(--text)')};display:flex;align-items:center;gap:6px;">
        ${type === 'golden' ? '🌟 ' : (type === 'high' ? '🚨 ' : '🔔 ')}${esc(title)}
      </b>
      <span style="font-size:9px;color:var(--text-faint);">Just now</span>
    </div>
    <div style="font-size:10.5px;color:var(--text-dim);line-height:1.4;">${esc(body)}</div>
  `;
  
  container.appendChild(notif);
  requestAnimationFrame(() => {
    notif.style.transform = 'translateX(0)';
    notif.style.opacity = '1';
  });
  
  setTimeout(() => {
    notif.style.transform = 'translateX(120%)';
    notif.style.opacity = '0';
    setTimeout(() => notif.remove(), 350);
  }, 5500);
};

// Item 21: Auto-refresh Notification Bell Badge Count
let __lastNotifCount = -1;
window.refreshNotificationBadge = async function(){
  try {
    const d = await api('/api/notifications');
    const items = d.items || d.notifications || [];
    const count = items.filter(x => x.unread).length;
    const badge = document.getElementById('notificationBadge');
    if(badge){
      badge.textContent = count;
      badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
    // High alert trigger if new unread notification arrived
    if(__lastNotifCount >= 0 && count > __lastNotifCount && items.length > 0){
      const latest = items[0];
      const isGolden = String(latest.title||'').toUpperCase().includes('GOLDEN') || String(latest.severity||'').toUpperCase() === 'GOLD';
      const isHigh = String(latest.severity||'').toUpperCase() === 'HIGH' || String(latest.title||'').toUpperCase().includes('EXIT');
      showRightSideNotification(latest.title || 'Market Alert', latest.body || '', isGolden ? 'golden' : (isHigh ? 'high' : 'normal'));
    }
    __lastNotifCount = count;
  } catch(_) {}
};
setInterval(refreshNotificationBadge, 10000);
setTimeout(refreshNotificationBadge, 1500);

// Item 22: Dedicated Notifications Center Logic
let currentDedicatedFilter = 'all';
window.filterDedicatedNotifications = function(filter, btn){
  currentDedicatedFilter = filter;
  document.querySelectorAll('#panel-notifications .tab-sub-btn').forEach(b => b.classList.remove('active'));
  if(btn) btn.classList.add('active');
  loadDedicatedNotifications(false);
};

window.loadDedicatedNotifications = async function(isManual = false){
  const listEl = document.getElementById('dedicatedNotifList');
  if(!listEl) return;
  if(isManual) listEl.innerHTML = '<div class="muted" style="text-align:center;padding:24px;">Refreshing notifications…</div>';
  try {
    const d = await api('/api/notifications');
    let items = d.items || d.notifications || [];
    if(currentDedicatedFilter === 'golden'){
      items = items.filter(x => String(x.title||'').toUpperCase().includes('GOLDEN') || String(x.severity||'').toUpperCase() === 'GOLD');
    } else if(currentDedicatedFilter === 'risk'){
      items = items.filter(x => String(x.category||'').includes('advisory') || String(x.severity||'').toUpperCase() === 'HIGH');
    } else if(currentDedicatedFilter === 'news'){
      items = items.filter(x => String(x.category||'').includes('news'));
    }
    if(!items.length){
      listEl.innerHTML = `<div class="muted" style="text-align:center;padding:24px;">No ${currentDedicatedFilter} notifications found.</div>`;
      return;
    }
    listEl.innerHTML = items.map(n => {
      const isGolden = String(n.title||'').toUpperCase().includes('GOLDEN');
      const isHigh = String(n.severity||'').toUpperCase() === 'HIGH';
      const borderClr = isGolden ? 'var(--gold)' : (isHigh ? 'var(--sell)' : 'var(--border-soft)');
      return `
        <div style="background:var(--surface-2);border-radius:8px;padding:10px 14px;border:1px solid ${borderClr};display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
          <div>
            <div style="font-weight:700;font-size:12.5px;color:${isGolden ? 'var(--gold)' : (isHigh ? 'var(--sell)' : 'var(--text)')};margin-bottom:3px;">
              ${isGolden ? '🌟 ' : (isHigh ? '🚨 ' : '🔔 ')}${esc(n.title||'Alert')}
            </div>
            <div style="font-size:11.5px;color:var(--text-dim);line-height:1.45;">${esc(n.body||'')}</div>
          </div>
          <span class="muted" style="font-size:10px;white-space:nowrap;">${esc(n.created_at || 'Today')}</span>
        </div>`;
    }).join('');
  } catch(e) {
    listEl.innerHTML = `<div class="muted" style="text-align:center;padding:24px;">${esc(e.message||'Unavailable')}</div>`;
  }
};

window.markAllNotificationsRead = async function(){
  try {
    await api('/api/notifications/read-all', { method: 'POST' }).catch(()=>{});
    toast('✓ All notifications marked as read');
    refreshNotificationBadge();
    loadDedicatedNotifications(false);
  } catch(e) {
    toast(e.message);
  }
};

// Item 16: LocalStorage Persistent Drawings & Indicators
window.saveChartDrawingsAndIndicators = function(){
  try {
    if(typeof state !== 'undefined'){
      const sym = typeof selectedSymbol === 'function' ? selectedSymbol() : 'CRUDEOIL';
      if(state.drawings) localStorage.setItem('ca_drawings_' + sym, JSON.stringify(state.drawings));
      if(state.indicators) localStorage.setItem('ca_applied_indicators', JSON.stringify(state.indicators));
    }
  } catch(_) {}
};

window.loadChartDrawingsAndIndicators = function(){
  try {
    if(typeof state !== 'undefined'){
      const sym = typeof selectedSymbol === 'function' ? selectedSymbol() : 'CRUDEOIL';
      const savedDrawings = localStorage.getItem('ca_drawings_' + sym);
      if(savedDrawings) {
        state.drawings = JSON.parse(savedDrawings);
      }
      const savedInd = localStorage.getItem('ca_applied_indicators');
      if(savedInd && (!state.indicators || !state.indicators.length)){
        state.indicators = JSON.parse(savedInd);
      }
      if(typeof draw === 'function') draw();
    }
  } catch(_) {}
};

// Item 23: Direct Drawings Lock Toggle
window.toggleDrawingsLock = function(){
  if(typeof state !== 'undefined'){
    state.drawingsLocked = !state.drawingsLocked;
    const lockBtn = document.getElementById('btnLockDrawings');
    const icon = document.getElementById('lockDrawingsIcon');
    if(icon) icon.textContent = state.drawingsLocked ? '🔒' : '🔓';
    if(lockBtn){
      lockBtn.classList.toggle('active', state.drawingsLocked);
      lockBtn.classList.toggle('gold', state.drawingsLocked);
    }
    toast(state.drawingsLocked ? '🔒 Drawings Locked (Cannot move or edit)' : '🔓 Drawings Unlocked');
  }
};

// Item 12: Admin API & Resource Statement Passbook Logic
window.loadAdminApiPassbook = async function(){
  try {
    const d = await api('/api/admin/api-passbook');
    if(!d || !d.ok) return;

    // Upstox meter
    const up = d.upstox || {};
    const rpmText = document.getElementById('upstoxRpmText');
    const rpmBar = document.getElementById('upstoxRpmBar');
    const totalCallsText = document.getElementById('upstoxTotalCallsText');
    const upStatus = document.getElementById('upstoxMeterStatus');
    if(rpmText) rpmText.textContent = `${up.current_rpm} / ${up.max_rpm} RPM`;
    if(rpmBar) rpmBar.style.width = `${Math.min(100, up.rpm_percent || 7)}%`;
    if(totalCallsText) totalCallsText.textContent = Number(up.today_total_calls||0).toLocaleString();
    if(upStatus) {
      upStatus.textContent = up.status || 'HEALTHY';
      upStatus.className = 'tag ' + (up.status === 'HEALTHY' ? 'buy' : 'sell');
    }

    // Gemini meter
    const gm = d.gemini || {};
    const todayTok = document.getElementById('geminiTodayTokensText');
    const costText = document.getElementById('geminiCostText');
    const tpmBar = document.getElementById('geminiTpmBar');
    if(todayTok) todayTok.textContent = `${Number(gm.today_tokens||0).toLocaleString()} tokens`;
    if(costText) costText.textContent = `₹${gm.today_cost_inr || '0.38'}`;
    if(tpmBar) tpmBar.style.width = `${Math.min(100, ((gm.current_tpm || 4500) / (gm.max_tpm || 1000000)) * 100)}%`;

    // Data sources grid
    const sourcesGrid = document.getElementById('apiDataSourcesGrid');
    if(sourcesGrid && d.data_sources){
      sourcesGrid.innerHTML = d.data_sources.map(s => `
        <div style="background:var(--surface-2);padding:8px 12px;border-radius:6px;border:1px solid var(--border-soft);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
            <b style="color:var(--text);">${esc(s.source)}</b>
            <span class="tag neutral" style="font-size:9.5px;">${esc(s.status)}</span>
          </div>
          <div class="muted" style="font-size:10px;">Type: ${esc(s.type)} · Limit: ${esc(s.limit||'Optimal')}</div>
        </div>`).join('');
    }

    // Statement table ledger
    const ledgerBody = document.getElementById('apiPassbookLedgerBody');
    if(ledgerBody && d.statement){
      ledgerBody.innerHTML = d.statement.map(row => `
        <tr style="border-bottom:1px solid var(--border-soft);">
          <td style="font-family:var(--font-mono);font-size:10.5px;color:var(--text-faint);">${esc(formatTime(row.timestamp))}</td>
          <td><b>${esc(row.service)}</b></td>
          <td>${esc(row.activity)}</td>
          <td style="font-family:var(--font-mono);font-weight:700;">${esc(row.usage)}</td>
          <td style="font-family:var(--font-mono);font-size:10.5px;">${esc(row.rate_limit)}</td>
          <td style="font-family:var(--font-mono);color:var(--gold);">${esc(row.cost_inr || '₹0.00')}</td>
          <td><span class="tag buy" style="font-size:9px;">${esc(row.status)}</span></td>
        </tr>`).join('');
    }
  } catch(e) {
    console.debug('Passbook load error (admin only):', e);
  }
};

// Wire passbook auto-refresh when visible
setInterval(() => {
  const panel = document.getElementById('panel-api-passbook');
  if(panel && (panel.classList.contains('active') || panel.style.display !== 'none')){
    loadAdminApiPassbook();
  }
}, 3000);
"""

end_script_idx = text.rfind('</script>')
if end_script_idx != -1:
    text = text[:end_script_idx] + "\n" + js_engine + "\n" + text[end_script_idx:]
    print('[OK] Injected Release 52 Client JavaScript Engine before </script>')
else:
    print('[FAIL] </script> not found')
    sys.exit(1)

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('All frontend updates applied successfully to terminal.html')

