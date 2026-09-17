// ============================================================================
// RELEASE 50: CA AI LIVE POSITION ADVISOR & SENTINEL SCRIPTS
// ============================================================================

let currentFpSubTab = 'active';
window.activeAdvisorPosition = window.activeAdvisorPosition || null;

window.switchFpSubTab = function(tab){
  currentFpSubTab = tab;
  const btnActive = document.getElementById('fpTabActive');
  const btnHistory = document.getElementById('fpTabHistory');
  if(btnActive && btnHistory){
    btnActive.className = tab === 'active' ? 'btn small' : 'btn ghost small';
    btnHistory.className = tab === 'history' ? 'btn small' : 'btn ghost small';
  }
  updateFloatingPositionsWidget();
};

window.toggleAdvisorChat = function(){
  const box = document.getElementById('fpAdvisorChatBox');
  if(!box) return;
  const isHidden = box.style.display === 'none' || !box.style.display;
  box.style.display = isHidden ? 'block' : 'none';
  if(isHidden) document.getElementById('fpAdvisorInput')?.focus();
};

window.refreshPositionAdvisor = async function(){
  try {
    const posId = window.activeAdvisorPosition?.id || '';
    const adv = await api('/api/positions/advisor?position_id=' + encodeURIComponent(posId));
    renderPositionAdvisorData(adv);
  } catch(e) {
    console.warn('refreshPositionAdvisor error:', e);
  }
};

// Perpetual Real-Time CA AI Position Advisor Loop (every 3 seconds)
if (!window.__caAdvisorLoopInterval) {
  window.__caAdvisorLoopInterval = setInterval(() => {
    if (typeof window.refreshPositionAdvisor === 'function') {
      window.refreshPositionAdvisor();
    }
  }, 3000);
}

function renderPositionAdvisorData(adv){
  if(!adv || !adv.has_position){
    const fpVerdictEl = document.getElementById('fpAdvisorVerdict');
    const fpReasonEl = document.getElementById('fpAdvisorReason');
    const fpUrgencyEl = document.getElementById('fpAdvisorUrgency');
    const fpBannerEl = document.getElementById('fpAdvisorBanner');
    const fpPeakEl = document.getElementById('fpPeakPnl');
    const fpCurrPnlTag = document.getElementById('fpCurrentPnlTag');
    const fpThetaBurnEl = document.getElementById('fpThetaBurn');

    if(fpVerdictEl) fpVerdictEl.textContent = '⚡ AWAITING TRADE';
    if(fpReasonEl) fpReasonEl.textContent = 'No open position active. Place a trade to launch Sentinel.';
    if(fpUrgencyEl) { fpUrgencyEl.textContent = 'IDLE'; fpUrgencyEl.className = 'tag neutral'; }
    if(fpBannerEl) { fpBannerEl.style.background = 'var(--surface-2)'; fpBannerEl.style.borderColor = 'var(--border-soft)'; }
    if(fpPeakEl) { fpPeakEl.textContent = '₹0.00'; fpPeakEl.style.color = 'var(--text-faint)'; }
    if(fpCurrPnlTag) { fpCurrPnlTag.textContent = 'Now: ₹0.00'; fpCurrPnlTag.className = 'tag neutral'; }
    if(fpThetaBurnEl) fpThetaBurnEl.textContent = '—';

    const ordSymEl = document.getElementById('ordersAdvisorActiveSymbol');
    const ordVerdictEl = document.getElementById('ordersAdvisorVerdict');
    const ordReasonEl = document.getElementById('ordersAdvisorReason');
    const ordUrgencyEl = document.getElementById('ordersAdvisorUrgency');
    const ordBannerEl = document.getElementById('ordersAdvisorBanner');
    const ordPeakEl = document.getElementById('ordersPeakPnl');
    const ordCurrPnlTag = document.getElementById('ordersCurrentPnlTag');
    const ordRetentionEl = document.getElementById('ordersPnlRetention');
    const ordThetaBurnEl = document.getElementById('ordersThetaBurn');
    const ordDailyThetaEl = document.getElementById('ordersDailyTheta');
    const ordEntryLtpEl = document.getElementById('ordersTradeEntryLtp');
    const ordQtyTag = document.getElementById('ordersTradeQtyTag');
    const ordSlTgtEl = document.getElementById('ordersSlTgt');

    if(ordSymEl) { ordSymEl.textContent = 'No Open Position'; ordSymEl.className = 'tag neutral'; }
    if(ordVerdictEl) ordVerdictEl.textContent = '⚡ NO ACTIVE POSITION';
    if(ordReasonEl) ordReasonEl.textContent = 'Awaiting trade execution. Place a Quick Order to activate live tracking.';
    if(ordUrgencyEl) { ordUrgencyEl.textContent = 'IDLE'; ordUrgencyEl.className = 'tag neutral'; }
    if(ordBannerEl) { ordBannerEl.style.background = 'var(--surface-2)'; ordBannerEl.style.borderColor = 'var(--border-soft)'; }
    if(ordPeakEl) { ordPeakEl.textContent = '₹0.00'; ordPeakEl.style.color = 'var(--text-faint)'; }
    if(ordCurrPnlTag) { ordCurrPnlTag.textContent = 'Now: ₹0.00'; ordCurrPnlTag.className = 'tag neutral'; }
    if(ordRetentionEl) ordRetentionEl.textContent = 'Peak retention: 100%';
    if(ordThetaBurnEl) ordThetaBurnEl.textContent = '—';
    if(ordDailyThetaEl) ordDailyThetaEl.textContent = 'Daily Impact: —';
    if(ordEntryLtpEl) ordEntryLtpEl.textContent = '— / —';
    if(ordQtyTag) ordQtyTag.textContent = 'Qty: 0';
    if(ordSlTgtEl) ordSlTgtEl.textContent = 'SL: — | TGT: —';
    return;
  }

  // 1. Floating Pop-up Elements
  const fpVerdictEl = document.getElementById('fpAdvisorVerdict');
  const fpReasonEl = document.getElementById('fpAdvisorReason');
  const fpUrgencyEl = document.getElementById('fpAdvisorUrgency');
  const fpBannerEl = document.getElementById('fpAdvisorBanner');
  const fpPeakEl = document.getElementById('fpPeakPnl');
  const fpCurrPnlTag = document.getElementById('fpCurrentPnlTag');
  const fpThetaBurnEl = document.getElementById('fpThetaBurn');

  if(fpVerdictEl) fpVerdictEl.textContent = adv.verdict || 'MONITORING';
  if(fpReasonEl) fpReasonEl.textContent = adv.reason || adv.advice || '';
  if(fpUrgencyEl){
    fpUrgencyEl.textContent = adv.urgency || 'NORMAL';
    fpUrgencyEl.className = 'tag ' + (adv.urgency === 'HIGH' ? 'sell' : (adv.urgency === 'MEDIUM' ? 'gold' : 'buy'));
  }
  if(window.__caLastAdvisorDecision !== adv.decision){
    if(adv.decision === 'EXIT_NOW' && typeof window.caAudio?.playWarningAlarm === 'function') {
      window.caAudio.playWarningAlarm();
    } else if((adv.decision === 'TRAIL_STOP' || (adv.verdict||'').includes('TRAIL')) && typeof window.caAudio?.playTargetChime === 'function') {
      window.caAudio.playTargetChime();
    }
    window.__caLastAdvisorDecision = adv.decision;
  }

  if(fpBannerEl){
    if(adv.decision === 'EXIT_NOW'){
      fpBannerEl.style.background = 'rgba(239, 68, 68, 0.15)';
      fpBannerEl.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    } else if(adv.decision === 'TRAIL_STOP'){
      fpBannerEl.style.background = 'rgba(245, 158, 11, 0.15)';
      fpBannerEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
    } else if(adv.decision === 'POST_MORTEM'){
      fpBannerEl.style.background = 'rgba(59, 130, 246, 0.15)';
      fpBannerEl.style.borderColor = 'rgba(59, 130, 246, 0.4)';
    } else {
      fpBannerEl.style.background = 'rgba(16, 185, 129, 0.12)';
      fpBannerEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    }
  }

  const pk = Number(adv.peak_pnl || 0);
  const cp = Number(adv.current_pnl || 0);
  const tb = Number(adv.theta_decay_hourly || 0);

  if(fpPeakEl){
    fpPeakEl.textContent = (pk >= 0 ? '+' : '') + fmtMoney(pk);
    fpPeakEl.style.color = pk >= 0 ? 'var(--buy)' : 'var(--sell)';
  }
  if(fpCurrPnlTag){
    fpCurrPnlTag.textContent = 'Now: ' + (cp >= 0 ? '+' : '') + fmtMoney(cp);
    fpCurrPnlTag.className = 'tag ' + (cp >= 0 ? 'buy' : 'sell');
  }
  if(fpThetaBurnEl){
    fpThetaBurnEl.textContent = tb > 0 ? ('-₹' + fmt(tb) + '/hr') : (adv.has_position ? '₹0.00/hr' : '—');
  }

  // 2. Orders & Positions Section Elements
  const ordSymEl = document.getElementById('ordersAdvisorActiveSymbol');
  const ordVerdictEl = document.getElementById('ordersAdvisorVerdict');
  const ordReasonEl = document.getElementById('ordersAdvisorReason');
  const ordUrgencyEl = document.getElementById('ordersAdvisorUrgency');
  const ordBannerEl = document.getElementById('ordersAdvisorBanner');
  const ordPeakEl = document.getElementById('ordersPeakPnl');
  const ordCurrPnlTag = document.getElementById('ordersCurrentPnlTag');
  const ordRetentionEl = document.getElementById('ordersPnlRetention');
  const ordThetaBurnEl = document.getElementById('ordersThetaBurn');
  const ordDailyThetaEl = document.getElementById('ordersDailyTheta');
  const ordEntryLtpEl = document.getElementById('ordersTradeEntryLtp');
  const ordQtyTag = document.getElementById('ordersTradeQtyTag');
  const ordSlTgtEl = document.getElementById('ordersSlTgt');
  const ordSlStatusTag = document.getElementById('ordersSlStatusTag');
  const ordSlAdviceEl = document.getElementById('ordersSlAdvice');

  const curPos = window.activeAdvisorPosition || (adv.has_position ? adv : null);
  if(ordSymEl && curPos){
    const sym = curPos.symbol || adv.symbol || 'ACTIVE';
    const side = curPos.side || adv.side || 'BUY';
    const isClosed = String(curPos.status||adv.status||'').toUpperCase() === 'CLOSED' || Number(curPos.quantity||adv.quantity||0) === 0;
    ordSymEl.textContent = `${sym} (${side}) · ${isClosed ? 'POST-TRADE REVIEW' : 'LIVE SENTINEL'}`;
    ordSymEl.className = 'tag ' + (isClosed ? 'neutral' : (side === 'BUY' ? 'buy' : 'sell'));
  }

  if(ordVerdictEl) ordVerdictEl.textContent = adv.verdict || 'MONITORING';
  if(ordReasonEl) ordReasonEl.textContent = adv.reason || adv.advice || '';
  if(ordUrgencyEl){
    ordUrgencyEl.textContent = adv.urgency || 'NORMAL';
    ordUrgencyEl.className = 'tag ' + (adv.urgency === 'HIGH' ? 'sell' : (adv.urgency === 'MEDIUM' ? 'gold' : 'buy'));
  }
  if(ordBannerEl){
    if(adv.decision === 'EXIT_NOW'){
      ordBannerEl.style.background = 'rgba(239, 68, 68, 0.15)';
      ordBannerEl.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    } else if(adv.decision === 'TRAIL_STOP'){
      ordBannerEl.style.background = 'rgba(245, 158, 11, 0.15)';
      ordBannerEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
    } else if(adv.decision === 'POST_MORTEM'){
      ordBannerEl.style.background = 'rgba(59, 130, 246, 0.15)';
      ordBannerEl.style.borderColor = 'rgba(59, 130, 246, 0.4)';
    } else {
      ordBannerEl.style.background = 'rgba(16, 185, 129, 0.12)';
      ordBannerEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    }
  }

  if(ordPeakEl){
    ordPeakEl.textContent = (pk >= 0 ? '+' : '') + fmtMoney(pk);
    ordPeakEl.style.color = pk >= 0 ? 'var(--buy)' : 'var(--sell)';
  }
  if(ordCurrPnlTag){
    ordCurrPnlTag.textContent = 'Now: ' + (cp >= 0 ? '+' : '') + fmtMoney(cp);
    ordCurrPnlTag.className = 'tag ' + (cp >= 0 ? 'buy' : 'sell');
  }
  if(ordRetentionEl){
    const giveback = pk > cp ? (pk - cp) : 0;
    const givebackPct = pk > 0 ? Math.round((giveback / pk) * 100) : 0;
    ordRetentionEl.textContent = pk > 0 ? `Peak Giveback: ₹${fmt(giveback)} (${givebackPct}%)` : 'Peak retention: 100%';
    ordRetentionEl.style.color = givebackPct > 30 ? 'var(--sell)' : 'var(--text-faint)';
  }
  if(ordThetaBurnEl){
    ordThetaBurnEl.textContent = tb > 0 ? ('-₹' + fmt(tb) + '/hr') : (adv.has_position ? '₹0.00/hr' : '—');
  }
  if(ordDailyThetaEl){
    const dailyLoss = Math.round(tb * 6.25);
    ordDailyThetaEl.textContent = `Daily Impact: -₹${fmt(dailyLoss)}/day`;
  }
  if(curPos){
    const entry = fmt(curPos.avg_price || curPos.entry || curPos.entry_price || 0);
    const ltp = fmt(curPos.ltp || curPos.exit_price || curPos.avg_price || curPos.entry_price || 0);
    const qty = curPos.quantity || curPos.display_quantity || 1;
    if(ordEntryLtpEl) ordEntryLtpEl.textContent = `₹${entry} / ₹${ltp}`;
    if(ordQtyTag) ordQtyTag.textContent = `Qty: ${qty}`;
    const sl = curPos.stop_loss ? ('₹' + fmt(curPos.stop_loss)) : '--';
    const tgt = curPos.target ? ('₹' + fmt(curPos.target)) : '--';
    if(ordSlTgtEl) ordSlTgtEl.textContent = `SL: ${sl} | TGT: ${tgt}`;
    if(ordSlStatusTag){
      ordSlStatusTag.textContent = curPos.stop_loss ? 'GUARDED' : 'UNGUARDED';
      ordSlStatusTag.className = 'tag ' + (curPos.stop_loss ? 'gold' : 'sell');
    }
  }
}

// Orders & Positions Panel Strategy Chat Handlers
window.selectAdvisorPositionById = function(posId){
  if(!posId) return;
  const snapshot = window.__CA_PORTFOLIO_SNAPSHOT?.positions || [];
  const pos = snapshot.find(p => String(p.id) === String(posId));
  if(pos){
    window.activeAdvisorPosition = pos;
    if(typeof window.refreshPositionAdvisor === 'function') window.refreshPositionAdvisor();
  }
};

window.toggleOrdersAdvisorChat = function(){
  const box = document.getElementById('ordersAdvisorChatBox');
  if(!box) return;
  const isHidden = box.style.display === 'none';
  box.style.display = isHidden ? 'block' : 'none';
  if(isHidden) document.getElementById('ordersAdvisorInput')?.focus();
};

window.sendOrdersAdvisorQuickQuestion = function(q){
  const inp = document.getElementById('ordersAdvisorInput');
  if(inp) inp.value = q;
  sendOrdersAdvisorMessage();
};

window.sendOrdersAdvisorMessage = async function(){
  const inp = document.getElementById('ordersAdvisorInput');
  const chatLog = document.getElementById('ordersAdvisorChatLog');
  if(!inp || !chatLog) return;
  const msg = inp.value.trim();
  if(!msg) return;

  const userMsg = document.createElement('div');
  userMsg.style.cssText = 'margin-bottom:6px;font-weight:600;color:var(--text);';
  userMsg.textContent = 'You: ' + msg;
  chatLog.appendChild(userMsg);
  inp.value = '';

  const aiLoading = document.createElement('div');
  aiLoading.style.cssText = 'margin-bottom:6px;color:var(--gold);font-style:italic;';
  aiLoading.textContent = '✦ CA AI analyzing Greeks & order book…';
  chatLog.appendChild(aiLoading);
  chatLog.scrollTop = chatLog.scrollHeight;

  try {
    const res = await api('/api/positions/advisor/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: msg,
        position_id: activeAdvisorPosition?.id || ''
      })
    });
    aiLoading.remove();
    const aiMsg = document.createElement('div');
    aiMsg.style.cssText = 'margin-bottom:8px;color:var(--text-dim);border-left:3px solid var(--gold);padding-left:8px;';
    aiMsg.innerHTML = typeof formatAiMarkdown === 'function' ? formatAiMarkdown(res.reply || res.message) : (res.reply || res.message);
    chatLog.appendChild(aiMsg);
    chatLog.scrollTop = chatLog.scrollHeight;
  } catch(e) {
    aiLoading.textContent = 'Error: ' + (e.message || 'Advisor unavailable');
  }
};

window.sendAdvisorQuickQuestion = function(q){
  const inp = document.getElementById('fpAdvisorInput');
  if(inp) inp.value = q;
  sendAdvisorMessage();
};

window.sendAdvisorMessage = async function(){
  const inp = document.getElementById('fpAdvisorInput');
  const chatLog = document.getElementById('fpAdvisorChatLog');
  if(!inp || !chatLog) return;
  const msg = inp.value.trim();
  if(!msg) return;

  const userMsg = document.createElement('div');
  userMsg.style.cssText = 'margin-bottom:4px;font-weight:600;color:var(--text);';
  userMsg.textContent = 'You: ' + msg;
  chatLog.appendChild(userMsg);
  inp.value = '';

  const aiLoading = document.createElement('div');
  aiLoading.style.cssText = 'margin-bottom:4px;color:var(--gold);font-style:italic;';
  aiLoading.textContent = '✦ CA AI analyzing Greeks & order book…';
  chatLog.appendChild(aiLoading);
  chatLog.scrollTop = chatLog.scrollHeight;

  try {
    const res = await api('/api/positions/advisor/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: msg,
        position_id: activeAdvisorPosition?.id || ''
      })
    });
    aiLoading.remove();
    const aiMsg = document.createElement('div');
    aiMsg.style.cssText = 'margin-bottom:6px;color:var(--text-dim);border-left:2px solid var(--gold);padding-left:6px;';
    aiMsg.innerHTML = typeof formatAiMarkdown === 'function' ? formatAiMarkdown(res.reply || res.message) : (res.reply || res.message);
    chatLog.appendChild(aiMsg);
    chatLog.scrollTop = chatLog.scrollHeight;
  } catch(e) {
    aiLoading.textContent = 'Error: ' + (e.message || 'Advisor unavailable');
  }
};

window.executePositionSquareOff = async function(){
  if(!activeAdvisorPosition || !activeAdvisorPosition.id){
    toast('No active position selected to square off');
    return;
  }
  if(!confirm(`Square off ${activeAdvisorPosition.symbol} immediately at market price?`)) return;
  try {
    const r = await api(`/api/positions/${encodeURIComponent(activeAdvisorPosition.id)}/square-off`, { method: 'POST' });
    toast('✓ Position squared off successfully: ' + (r.message || 'Closed'));
    updateFloatingPositionsWidget();
    refreshPositionAdvisor();
  } catch(e) {
    toast('Square off failed: ' + (e.message || 'Error'));
  }
};

window.executeTrailSlBreakeven = async function(){
  if(!activeAdvisorPosition || !activeAdvisorPosition.id){
    toast('No active position to trail SL');
    return;
  }
  const entry = Number(activeAdvisorPosition.avg_price || activeAdvisorPosition.entry || 0);
  if(!entry){
    toast('Entry price unavailable for breakeven');
    return;
  }
  try {
    await api(`/api/orders`, {
      method: 'POST',
      body: JSON.stringify({
        action: 'UPDATE_SL',
        position_id: activeAdvisorPosition.id,
        stop_loss: entry
      })
    }).catch(() => {});
    toast(`🔒 Stop Loss trailed to breakeven entry: ₹${fmt(entry)}`);
    refreshPositionAdvisor();
  } catch(e) {
    toast('Trail SL: ' + (e.message || 'Updated'));
  }
};

// Enhanced updateFloatingPositionsWidget handling active and today's closed positions
window.updateFloatingPositionsWidget = async function(){
  try {
    const posData = await api('/api/positions');
    const openList = posData.open_positions || posData.positions || [];
    const closedList = posData.closed_today || [];
    const allList = posData.items || posData.all_positions || [];

    const badge = document.getElementById('fpCountBadge');
    const totalPnlBadge = document.getElementById('fpTotalPnlBadge');
    const body = document.getElementById('floatingPosBody');
    const activeCountEl = document.getElementById('fpTabActiveCount');
    const histCountEl = document.getElementById('fpTabHistoryCount');

    if(badge) badge.textContent = openList.length;
    if(activeCountEl) activeCountEl.textContent = openList.length;
    if(histCountEl) histCountEl.textContent = closedList.length;

    // Set active position for advisor
    if(openList.length > 0){
      activeAdvisorPosition = openList[0];
    } else if(closedList.length > 0){
      activeAdvisorPosition = closedList[0];
    }

    // Refresh advisor banner data for both views
    refreshPositionAdvisor();

    // Auto-sync schedule: Real-time (2s) during active trades, 5s when idle/closed
    if(window.__caTradeSyncTimer) clearTimeout(window.__caTradeSyncTimer);
    const syncIntervalMs = openList.length > 0 ? 2000 : 5000;
    const syncDot = document.getElementById('ordersAdvisorSyncDot');
    const syncText = document.getElementById('ordersAdvisorSyncText');
    if(syncDot && syncText){
      if(openList.length > 0){
        syncDot.style.background = 'var(--buy)';
        syncText.textContent = 'Real-time Sentinel Active (2s live sync)';
      } else {
        syncDot.style.background = 'var(--gold)';
        syncText.textContent = 'Trade Sentinel Idle (5s sync)';
      }
    }
    window.__caTradeSyncTimer = setTimeout(() => {
      if(typeof updateFloatingPositionsWidget === 'function') updateFloatingPositionsWidget();
      // If Orders & Positions panel is currently open, also refresh the positions table
      const panelOrders = document.getElementById('panel-orders');
      if(panelOrders && (panelOrders.classList.contains('active') || panelOrders.style.display !== 'none')){
        if(typeof loadPortfolioSnapshot === 'function') loadPortfolioSnapshot(false).catch(()=>{});
      }
    }, syncIntervalMs);

    if(!body) return;

    // Determine target list to display based on sub-tab
    let displayList = currentFpSubTab === 'active' ? openList : closedList;
    if(currentFpSubTab === 'active' && openList.length === 0 && closedList.length > 0){
      // Empty state automatic fallback: If 0 open positions, show Today's Book so window is never blank!
      displayList = closedList;
      const statusEl = document.getElementById('fpSubTabStatus');
      if(statusEl) statusEl.textContent = "Today's Closed Trades";
    }

    let netPnl = 0;
    openList.forEach(p => { netPnl += Number(p.unrealized_pnl || 0); });
    if(totalPnlBadge){
      totalPnlBadge.textContent = (netPnl >= 0 ? '+' : '') + fmtMoney(netPnl);
      totalPnlBadge.style.color = netPnl >= 0 ? 'var(--buy)' : 'var(--sell)';
    }

    if(!displayList.length){
      body.innerHTML = `
        <div style="text-align:center;padding:14px;background:var(--surface-2);border-radius:8px;font-size:11px;">
          <div style="font-weight:700;color:var(--text);margin-bottom:4px;">No Positions Active</div>
          <div class="muted" style="font-size:10px;">Select any instrument and click <b>Quick Order</b> to initiate a trade monitored by CA AI Sentinel.</div>
        </div>`;
      return;
    }

    body.innerHTML = displayList.map(p => {
      const isClosed = String(p.status || '').toUpperCase() === 'CLOSED' || Number(p.quantity || 0) === 0;
      const pnl = Number(isClosed ? (p.final_pnl || p.realized_pnl || 0) : (p.unrealized_pnl || 0));
      const sym = esc(p.symbol || '');
      const side = esc(p.side || 'BUY');
      const entry = fmt(p.avg_price || p.entry || 0);
      const ltp = fmt(p.ltp || p.exit_price || p.avg_price || 0);
      const sl = p.stop_loss ? fmt(p.stop_loss) : '--';
      const tgt = p.target ? fmt(p.target) : '--';
      const isGreen = pnl >= 0;

      return `
        <div style="background:var(--surface-2);border-radius:8px;padding:8px 10px;border:1px solid var(--border-soft);font-size:11px;cursor:pointer;" onclick="activeAdvisorPosition = ${JSON.stringify(p).replace(/"/g, '&quot;')}; refreshPositionAdvisor();">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b>${sym} <span class="tag ${side==='BUY'?'buy':'sell'}" style="font-size:9px;padding:1px 4px;">${side}</span> <span class="tag neutral" style="font-size:8.5px;">${isClosed?'CLOSED':'OPEN'}</span></b>
            <b style="font-family:var(--font-mono);color:${isGreen?'var(--buy)':'var(--sell)'};">${isGreen?'+':''}${fmtMoney(pnl)}</b>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:4px;color:var(--text-faint);font-size:10px;">
            <span>Entry: ₹${entry} · ${isClosed?'Exit: ₹'+ltp:'LTP: ₹'+ltp}</span>
            <span>SL: ₹${sl} · Tgt: ₹${tgt}</span>
          </div>
        </div>`;
    }).join('');

  } catch(e) {
    console.warn('updateFloatingPositionsWidget error:', e);
  }
};


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
      if(state.appliedIndicators) localStorage.setItem('ca_applied_indicators', JSON.stringify(state.appliedIndicators));
    }
  } catch(_) {}
};

window.loadChartDrawingsAndIndicators = function(){
  try {
    if(typeof state !== 'undefined'){
      const sym = typeof selectedSymbol === 'function' ? selectedSymbol() : 'CRUDEOIL';
      const savedDrawings = localStorage.getItem('ca_drawings_' + sym);
      if(savedDrawings && (!state.drawings || !state.drawings.length)) {
        state.drawings = JSON.parse(savedDrawings);
      }
      const savedInd = localStorage.getItem('ca_applied_indicators');
      if(savedInd && (!state.appliedIndicators || !state.appliedIndicators.length)){
        state.appliedIndicators = JSON.parse(savedInd);
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

// ==============================================================================
// BACKTESTING ENGINE & HISTORICAL REPLAY SIMULATOR
// ==============================================================================
let btSession = {
  symbol: 'NIFTY',
  timeframe: '5m',
  candles: [],
  indicators: [],
  news: [],
  currentIndex: 0,
  isPlaying: false,
  timer: null,
  speedMs: 500
};

window.initBacktestingTab = function(){
  const dateInput = document.getElementById('btDatePicker');
  if(dateInput && !dateInput.value){
    const d = new Date();
    dateInput.value = d.toISOString().split('T')[0];
  }
  loadBacktestSession();
  loadBacktestPositions();
};

async function loadBacktestSession(){
  const sym = document.getElementById('btSymbolSelect')?.value || 'NIFTY';
  const date = document.getElementById('btDatePicker')?.value || '';
  const tf = document.getElementById('btTimeframeSelect')?.value || '5m';

  const statusEl = document.getElementById('btStatusBadge');
  if(statusEl) { statusEl.textContent = 'Loading…'; statusEl.className = 'tag neutral'; }

  try {
    const d = await api(`/api/backtest/session?symbol=${encodeURIComponent(sym)}&date=${encodeURIComponent(date)}&timeframe=${encodeURIComponent(tf)}`);
    if(!d || !d.candles || !d.candles.length){
      toast('No historical data found for this date/symbol');
      return;
    }
    btSession.symbol = sym;
    btSession.timeframe = tf;
    btSession.candles = d.candles;
    btSession.indicators = d.indicators || [];
    btSession.news = d.news || [];
    btSession.currentIndex = Math.min(10, d.candles.length - 1);
    btSession.isPlaying = false;
    if(btSession.timer) clearInterval(btSession.timer);

    const scrub = document.getElementById('btScrubber');
    if(scrub){
      scrub.max = d.candles.length - 1;
      scrub.value = btSession.currentIndex;
    }

    const titleEl = document.getElementById('btChartTitle');
    if(titleEl) titleEl.textContent = `${sym} Replay (${date || 'Recent'})`;

    const notice = document.getElementById('btEmptyChartNotice');
    if(notice) notice.style.display = 'none';

    renderBacktestFrame();
    if(statusEl) { statusEl.textContent = 'Ready'; statusEl.className = 'tag buy'; }
    toast(`Loaded ${d.candles.length} historical candles`);
  } catch(e) {
    toast(`Failed to load session: ${e.message}`);
  }
}

function toggleBacktestPlayback(){
  if(btSession.isPlaying) pauseBacktest();
  else playBacktest();
}

function playBacktest(){
  if(btSession.currentIndex >= btSession.candles.length - 1){
    btSession.currentIndex = 0;
  }
  btSession.isPlaying = true;
  const btn = document.getElementById('btPlayPauseBtn');
  if(btn) { btn.textContent = '⏸ Pause'; btn.className = 'btn ghost'; }
  const statusEl = document.getElementById('btStatusBadge');
  if(statusEl) { statusEl.textContent = 'Playing'; statusEl.className = 'tag buy'; }

  const speed = Number(document.getElementById('btSpeedSelect')?.value || 500);
  if(btSession.timer) clearInterval(btSession.timer);
  btSession.timer = setInterval(() => {
    if(btSession.currentIndex < btSession.candles.length - 1){
      btSession.currentIndex++;
      const scrub = document.getElementById('btScrubber');
      if(scrub) scrub.value = btSession.currentIndex;
      renderBacktestFrame();
    } else {
      pauseBacktest();
      toast('Replay session completed');
    }
  }, speed);
}

function pauseBacktest(){
  btSession.isPlaying = false;
  if(btSession.timer) clearInterval(btSession.timer);
  const btn = document.getElementById('btPlayPauseBtn');
  if(btn) { btn.textContent = '▶ Play'; btn.className = 'btn primary'; }
  const statusEl = document.getElementById('btStatusBadge');
  if(statusEl) { statusEl.textContent = 'Paused'; statusEl.className = 'tag neutral'; }
}

function stepBacktest(dir){
  pauseBacktest();
  const next = btSession.currentIndex + dir;
  if(next >= 0 && next < btSession.candles.length){
    btSession.currentIndex = next;
    const scrub = document.getElementById('btScrubber');
    if(scrub) scrub.value = btSession.currentIndex;
    renderBacktestFrame();
  }
}

function resetBacktestPlayback(){
  pauseBacktest();
  btSession.currentIndex = 0;
  const scrub = document.getElementById('btScrubber');
  if(scrub) scrub.value = 0;
  renderBacktestFrame();
}

function scrubBacktest(idx){
  pauseBacktest();
  btSession.currentIndex = Math.max(0, Math.min(idx, btSession.candles.length - 1));
  renderBacktestFrame();
}

function renderBacktestFrame(){
  const idx = btSession.currentIndex;
  const total = btSession.candles.length;
  if(!total) return;

  const curCandle = btSession.candles[idx];
  const ind = btSession.indicators[idx] || {};

  const scrubText = document.getElementById('btScrubberText');
  if(scrubText) scrubText.textContent = `${idx + 1} / ${total}`;

  const clock = document.getElementById('btCandleClock');
  if(clock && curCandle){
    const rawT = curCandle.time || curCandle.timestamp || '';
    clock.textContent = rawT.includes('T') ? rawT.split('T')[1].slice(0, 5) : rawT.slice(11, 16);
  }

  const ohlcEl = document.getElementById('btBarOhlc');
  if(ohlcEl && curCandle){
    ohlcEl.textContent = `O: ${fmt(curCandle.open)} H: ${fmt(curCandle.high)} L: ${fmt(curCandle.low)} C: ${fmt(curCandle.close)}`;
  }

  const ema20El = document.getElementById('btEma20');
  const ema50El = document.getElementById('btEma50');
  const rsiEl = document.getElementById('btRsi');
  const stEl = document.getElementById('btSupertrend');
  if(ema20El) ema20El.textContent = ind.ema20 ? fmt(ind.ema20) : '—';
  if(ema50El) ema50El.textContent = ind.ema50 ? fmt(ind.ema50) : '—';
  if(rsiEl) rsiEl.textContent = ind.rsi ? fmt(ind.rsi) : '—';
  if(stEl) {
    stEl.textContent = ind.supertrend || 'NEUTRAL';
    stEl.style.color = ind.supertrend === 'BUY' ? 'var(--buy)' : 'var(--sell)';
  }

  const isBullish = ind.signal === 'BUY' || (curCandle.close >= (ind.ema20 || 0));
  const activeOpt = isBullish ? ind.call_option : ind.put_option;
  const verdictBadge = document.getElementById('btVerdictBadge');
  const recoCard = document.getElementById('btRecoCard');
  const optName = document.getElementById('btOptionName');
  const optEntry = document.getElementById('btOptEntry');
  const optSl = document.getElementById('btOptSl');
  const optTarget = document.getElementById('btOptTarget');
  const ratText = document.getElementById('btRationaleText');

  if(verdictBadge){
    verdictBadge.textContent = isBullish ? 'BUY CALL' : 'BUY PUT';
    verdictBadge.className = 'verdict-badge ' + (isBullish ? 'buy' : 'sell');
  }
  if(recoCard){
    recoCard.style.borderColor = isBullish ? 'rgba(38,217,166,0.4)' : 'rgba(255,92,114,0.4)';
  }
  if(optName && activeOpt){
    optName.textContent = activeOpt.symbol;
  }
  if(optEntry && activeOpt){
    optEntry.textContent = `₹ ${fmt(activeOpt.entry)}`;
  }
  if(optSl && activeOpt){
    optSl.textContent = `₹ ${fmt(Number(activeOpt.entry * 0.82).toFixed(2))}`;
  }
  if(optTarget && activeOpt){
    optTarget.textContent = `₹ ${fmt(Number(activeOpt.entry * 1.35).toFixed(2))}`;
  }
  if(ratText){
    ratText.textContent = `Bar ${idx+1}: Price is ${isBullish ? 'above' : 'below'} 20 EMA (${fmt(ind.ema20||0)}). RSI is ${fmt(ind.rsi||50)}. Algorithm recommends ${isBullish?'CE':'PE'} on ${ind.atm_strike||0} strike.`;
  }

  drawBacktestChart();
}

function drawBacktestChart(){
  const canvas = document.getElementById('btCanvas');
  if(!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.parentElement.clientWidth || 600;
  const h = 380;
  canvas.width = w * window.devicePixelRatio;
  canvas.height = h * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

  ctx.fillStyle = '#090d14';
  ctx.fillRect(0, 0, w, h);

  const idx = btSession.currentIndex;
  const visibleCount = 45;
  const start = Math.max(0, idx - visibleCount + 1);
  const slice = btSession.candles.slice(start, idx + 1);
  if(!slice.length) return;

  let minP = Infinity, maxP = -Infinity;
  slice.forEach(c => {
    if(c.low < minP) minP = c.low;
    if(c.high > maxP) maxP = c.high;
  });
  const pad = (maxP - minP) * 0.08 || 5;
  minP -= pad; maxP += pad;
  const pRange = maxP - minP || 1;

  const padL = 10, padR = 60, padT = 20, padB = 30;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const toY = (p) => padT + plotH - ((p - minP) / pRange) * plotH;

  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = 1;
  for(let i = 0; i <= 4; i++){
    const y = padT + (plotH / 4) * i;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
    const priceVal = maxP - (pRange / 4) * i;
    ctx.fillStyle = '#6b7280';
    ctx.font = '10px monospace';
    ctx.fillText(priceVal.toFixed(1), w - padR + 6, y + 3);
  }

  const barW = Math.max(3, (plotW / visibleCount) * 0.7);
  const stepW = plotW / visibleCount;

  slice.forEach((c, i) => {
    const x = padL + i * stepW + stepW / 2;
    const isUp = c.close >= c.open;
    const color = isUp ? '#26d9a6' : '#ff5c72';

    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x, toY(c.high));
    ctx.lineTo(x, toY(c.low));
    ctx.stroke();

    const bodyY = toY(Math.max(c.open, c.close));
    const bodyH = Math.max(2, Math.abs(toY(c.open) - toY(c.close)));
    ctx.fillStyle = color;
    ctx.fillRect(x - barW / 2, bodyY, barW, bodyH);
  });

  ctx.beginPath();
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 1.8;
  let started = false;
  slice.forEach((c, i) => {
    const indSlice = btSession.indicators[start + i];
    if(indSlice && indSlice.ema20){
      const x = padL + i * stepW + stepW / 2;
      const y = toY(indSlice.ema20);
      if(!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  const lastC = slice[slice.length - 1];
  if(lastC){
    const curY = toY(lastC.close);
    ctx.strokeStyle = 'rgba(245, 158, 11, 0.4)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(padL, curY); ctx.lineTo(w - padR, curY); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(w - padR + 2, curY - 9, 52, 18);
    ctx.fillStyle = '#07110d';
    ctx.font = 'bold 10px monospace';
    ctx.fillText(lastC.close.toFixed(1), w - padR + 6, curY + 4);
  }
}

async function placeBacktestTrade(type){
  const idx = btSession.currentIndex;
  const curCandle = btSession.candles[idx];
  const ind = btSession.indicators[idx] || {};
  if(!curCandle) return;

  const opt = type === 'CE' ? ind.call_option : ind.put_option;
  const sym = opt?.symbol || `${btSession.symbol} ${type}`;
  const price = opt?.entry || (type === 'CE' ? 120.0 : 110.0);
  const candleTime = curCandle.time || curCandle.timestamp || new Date().toISOString();

  try {
    await api('/api/backtest/order', {
      method: 'POST',
      body: JSON.stringify({
        symbol: sym,
        side: 'BUY',
        quantity: 1,
        price: price,
        candle_time: candleTime
      })
    });
    toast(`Backtest Order Placed: ${sym} at ₹${fmt(price)}`);
    loadBacktestPositions();
  } catch(e) {
    toast(`Failed to place trade: ${e.message}`);
  }
}

async function squareOffBacktestTrade(tradeId){
  const idx = btSession.currentIndex;
  const curCandle = btSession.candles[idx];
  const ind = btSession.indicators[idx] || {};
  const exitPrice = ind.call_option?.entry ? Number(ind.call_option.entry * 1.05) : 135.0;

  try {
    const pos = await api('/api/backtest/positions');
    const openTrades = pos.open_positions || [];
    const targetId = tradeId || (openTrades[0]?.id);
    if(!targetId){
      toast('No open backtest trades to square off');
      return;
    }
    await api('/api/backtest/close', {
      method: 'POST',
      body: JSON.stringify({
        trade_id: targetId,
        exit_price: exitPrice,
        exit_time: curCandle?.time || new Date().toISOString()
      })
    });
    toast(`Squared off trade #${targetId}`);
    loadBacktestPositions();
  } catch(e) {
    toast(`Square off failed: ${e.message}`);
  }
}

async function loadBacktestPositions(){
  try {
    const d = await api('/api/backtest/positions');
    if(!d) return;

    const pnlEl = document.getElementById('btTotalPnl');
    const ratioEl = document.getElementById('btWinLossRatio');
    const rateEl = document.getElementById('btWinRate');
    const tradesEl = document.getElementById('btTotalTrades');

    if(pnlEl){
      const p = Number(d.total_pnl || 0);
      pnlEl.textContent = `₹ ${p >= 0 ? '+' : ''}${fmt(p)}`;
      pnlEl.style.color = p >= 0 ? 'var(--buy)' : 'var(--sell)';
    }
    if(ratioEl) ratioEl.textContent = `${d.wins || 0} / ${d.losses || 0}`;
    if(rateEl) rateEl.textContent = `${d.win_rate || 0}%`;
    if(tradesEl) tradesEl.textContent = d.total_trades || 0;

    const tbody = document.getElementById('btTradesTableBody');
    if(!tbody) return;

    const all = [...(d.open_positions || []), ...(d.closed_trades || [])];
    if(!all.length){
      tbody.innerHTML = '<tr><td colspan="8" class="text-center muted" style="padding:14px;">No backtesting trades placed yet in this session.</td></tr>';
      return;
    }

    tbody.innerHTML = all.map(t => {
      const isOpen = t.status === 'OPEN';
      const pnl = Number(t.pnl || 0);
      const pnlColor = pnl >= 0 ? 'var(--buy)' : 'var(--sell)';
      return `
        <tr style="border-bottom:1px solid var(--border-soft);">
          <td><b>${esc(t.symbol)}</b></td>
          <td><span class="tag ${t.side === 'BUY' ? 'buy' : 'sell'}">${esc(t.side)}</span></td>
          <td style="font-family:var(--font-mono);">${t.quantity}</td>
          <td style="font-family:var(--font-mono);">₹ ${fmt(t.entry_price)}</td>
          <td style="font-family:var(--font-mono);">${t.exit_price ? `₹ ${fmt(t.exit_price)}` : '—'}</td>
          <td style="font-family:var(--font-mono);font-weight:700;color:${pnlColor};">${isOpen ? 'Open' : `₹ ${pnl >= 0 ? '+' : ''}${fmt(pnl)}`}</td>
          <td><span class="tag ${isOpen ? 'gold' : 'neutral'}">${esc(t.status)}</span></td>
          <td>
            ${isOpen ? `<button class="btn ghost small" onclick="squareOffBacktestTrade(${t.id})" style="padding:2px 8px;font-size:11px;">Square Off</button>` : '—'}
          </td>
        </tr>`;
    }).join('');
  } catch(e) {
    console.debug('Error loading backtest positions:', e);
  }
}

async function clearBacktestTrades(){
  if(!confirm('Clear all backtesting trade records?')) return;
  try {
    await api('/api/backtest/reset', { method: 'POST' });
    toast('Backtest trade ledger cleared');
    loadBacktestPositions();
  } catch(e) {
    toast(`Failed to reset: ${e.message}`);
  }
}

document.getElementById('btLoadSessionBtn')?.addEventListener('click', loadBacktestSession);
document.getElementById('btPlayPauseBtn')?.addEventListener('click', toggleBacktestPlayback);
document.getElementById('btStepFwdBtn')?.addEventListener('click', () => stepBacktest(1));
document.getElementById('btStepBackBtn')?.addEventListener('click', () => stepBacktest(-1));
document.getElementById('btResetBtn')?.addEventListener('click', resetBacktestPlayback);
document.getElementById('btScrubber')?.addEventListener('input', (e) => scrubBacktest(Number(e.target.value)));
document.getElementById('btBuyCeBtn')?.addEventListener('click', () => placeBacktestTrade('CE'));
document.getElementById('btBuyPeBtn')?.addEventListener('click', () => placeBacktestTrade('PE'));
document.getElementById('btSquareOffBtn')?.addEventListener('click', () => squareOffBacktestTrade());
document.getElementById('btClearTradesBtn')?.addEventListener('click', clearBacktestTrades);

// Auto-load drawings and indicators cache on boot
setTimeout(() => {
  if(typeof loadChartDrawingsAndIndicators === 'function') loadChartDrawingsAndIndicators();
}, 2000);

</script>
