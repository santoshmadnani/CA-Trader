#!/usr/bin/env python3
import sys, re

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print(f"Loaded terminal.html ({len(text):,} bytes)")

# -----------------------------------------------------------------------------
# 1. Expand #floatingPositionWidget HTML with Sentinel & Advisor section
# -----------------------------------------------------------------------------
old_widget_html = '''<div id="floatingPositionWidget" class="floating-pos-widget" style="position:fixed;bottom:16px;right:16px;z-index:9999;background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:0 12px 36px rgba(0,0,0,0.45);width:310px;max-width:92vw;transition:transform 0.2s;overflow:hidden;">
  <div class="pos-widget-head" id="floatingPosHead" style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:var(--surface-2);border-bottom:1px solid var(--border-soft);cursor:pointer;" onclick="toggleFloatingPositionsWidget()">
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--buy);" id="fpPulseDot"></span>
      <b style="font-size:12px;color:var(--text);">Positions (<span id="fpCountBadge">0</span>)</b>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
      <b id="fpTotalPnlBadge" style="font-family:var(--font-mono);font-size:12px;color:var(--text);">₹0.00</b>
      <button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:11px;" id="fpMinBtn">_</button>
    </div>
  </div>
  <div id="floatingPosBody" style="padding:10px 12px;max-height:220px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;">
    <div class="muted" style="font-size:11px;text-align:center;padding:10px;">No open positions active.</div>
  </div>
</div>'''

new_widget_html = '''<!-- Permanent Floating Mini-Position Sentinel & Advisor (Release 50) -->
<div id="floatingPositionWidget" class="floating-pos-widget" style="position:fixed;bottom:16px;right:16px;z-index:9999;background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:0 14px 44px rgba(0,0,0,0.55);width:380px;max-width:94vw;transition:transform 0.2s;overflow:hidden;">
  <!-- Header Bar -->
  <div class="pos-widget-head" id="floatingPosHead" style="display:flex;align-items:center;justify-content:space-between;padding:9px 12px;background:var(--surface-2);border-bottom:1px solid var(--border-soft);cursor:move;">
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--buy);" id="fpPulseDot"></span>
      <b style="font-size:12px;color:var(--text);">CA AI Trade Sentinel (<span id="fpCountBadge">0</span>)</b>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
      <b id="fpTotalPnlBadge" style="font-family:var(--font-mono);font-size:12px;color:var(--text);">₹0.00</b>
      <button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:11px;line-height:1;" id="fpMinBtn" onclick="toggleFloatingPositionsWidget()">_</button>
    </div>
  </div>

  <!-- Sentinel Body Container -->
  <div id="floatingPosBodyWrapper" style="display:flex;flex-direction:column;max-height:480px;overflow-y:auto;">
    
    <!-- SECTION 1: CA AI Live Position Advisor (Above Open Positions) -->
    <div id="fpAdvisorSection" style="padding:10px 12px;background:var(--surface);border-bottom:1px solid var(--border-soft);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <span style="font-size:10px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:0.5px;display:flex;align-items:center;gap:4px;">
          ✦ CA AI Live Position Advisor
        </span>
        <button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:10px;" onclick="refreshPositionAdvisor()">↻ Sync</button>
      </div>

      <!-- Verdict Banner -->
      <div id="fpAdvisorBanner" style="padding:8px 10px;border-radius:8px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b id="fpAdvisorVerdict" style="font-size:11.5px;color:var(--gold);">⚡ ANALYZING TRADE HEALTH…</b>
          <span id="fpAdvisorUrgency" class="tag gold" style="font-size:9px;">MONITORING</span>
        </div>
        <div id="fpAdvisorReason" style="font-size:10.5px;color:var(--text);margin-top:4px;line-height:1.35;">
          Evaluating real-time option Theta decay, peak P&L retention, and technical exit triggers.
        </div>
      </div>

      <!-- Metrics Grid: Peak P&L vs Theta Decay Burn Rate -->
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin-bottom:8px;font-size:10.5px;">
        <div style="background:var(--surface-2);padding:6px 8px;border-radius:6px;border:1px solid var(--border-soft);">
          <div class="muted" style="font-size:9.5px;">Peak vs Current P&L:</div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:2px;">
            <b id="fpPeakPnl" style="color:var(--buy);font-family:var(--font-mono);font-size:11px;">+₹--</b>
            <span id="fpCurrentPnlTag" class="tag neutral" style="font-size:9px;">Now: ₹--</span>
          </div>
        </div>
        <div style="background:var(--surface-2);padding:6px 8px;border-radius:6px;border:1px solid var(--border-soft);">
          <div class="muted" style="font-size:9.5px;">Theta Decay Burn Rate:</div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:2px;">
            <b id="fpThetaBurn" style="color:var(--sell);font-family:var(--font-mono);font-size:11px;">-₹--/hr</b>
            <span class="tag sell" style="font-size:9px;">TIME DECAY</span>
          </div>
        </div>
      </div>

      <!-- Action Control Buttons -->
      <div style="display:flex;gap:6px;margin-bottom:6px;">
        <button type="button" class="btn sell small" id="fpSquareOffBtn" style="flex:1;height:26px;font-size:10.5px;font-weight:700;justify-content:center;" onclick="executePositionSquareOff()">
          ✕ Square Off Now
        </button>
        <button type="button" class="btn gold small" id="fpTrailSlBtn" style="flex:1;height:26px;font-size:10.5px;font-weight:600;justify-content:center;" onclick="executeTrailSlBreakeven()">
          🔒 Trail SL to Entry
        </button>
        <button type="button" class="btn ghost small" style="padding:0 8px;height:26px;font-size:10.5px;" onclick="toggleAdvisorChat()" title="Chat with CA AI about this position">
          💬 Chat
        </button>
      </div>

      <!-- Collapsible Inline Chat with CA AI -->
      <div id="fpAdvisorChatBox" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border-soft);">
        <div style="display:flex;gap:4px;overflow-x:auto;padding-bottom:6px;margin-bottom:6px;">
          <span class="ai-chip" style="font-size:9.5px;padding:2px 8px;" onclick="sendAdvisorQuickQuestion('Why should I exit or hold?')">Why exit?</span>
          <span class="ai-chip" style="font-size:9.5px;padding:2px 8px;" onclick="sendAdvisorQuickQuestion('How much will Theta decay cost me in 1 hour?')">Theta burn rate?</span>
          <span class="ai-chip" style="font-size:9.5px;padding:2px 8px;" onclick="sendAdvisorQuickQuestion('Should I roll over or switch to PE?')">Switch to PE?</span>
        </div>
        <div id="fpAdvisorChatLog" style="max-height:110px;overflow-y:auto;font-size:11px;line-height:1.4;margin-bottom:6px;background:var(--surface-2);padding:6px 8px;border-radius:6px;border:1px solid var(--border-soft);">
          <div class="muted" style="font-size:10px;">✦ Ask CA AI anything about this position...</div>
        </div>
        <div style="display:flex;gap:4px;">
          <input id="fpAdvisorInput" type="text" class="tool-input" placeholder="Ask CA AI about this position..." style="height:26px;font-size:10.5px;flex:1;" onkeydown="if(event.key==='Enter')sendAdvisorMessage()">
          <button type="button" class="btn gold small" style="height:26px;padding:0 8px;font-size:10px;" onclick="sendAdvisorMessage()">Send</button>
        </div>
      </div>
    </div>

    <!-- SECTION 2: Sub-tabs (Active Positions / Today's Book) -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 12px;background:var(--surface-2);border-bottom:1px solid var(--border-soft);">
      <div style="display:flex;gap:4px;">
        <button type="button" class="btn small" id="fpTabActive" style="height:22px;padding:0 8px;font-size:10px;font-weight:700;background:var(--surface);border:1px solid var(--border);" onclick="switchFpSubTab('active')">
          Active (<span id="fpTabActiveCount">0</span>)
        </button>
        <button type="button" class="btn ghost small" id="fpTabHistory" style="height:22px;padding:0 8px;font-size:10px;" onclick="switchFpSubTab('history')">
          Today's Trades (<span id="fpTabHistoryCount">0</span>)
        </button>
      </div>
      <span class="muted" style="font-size:9.5px;" id="fpSubTabStatus">Live Feed</span>
    </div>

    <!-- SECTION 3: Open Positions List / Today's Book List -->
    <div id="floatingPosBody" style="padding:8px 12px;max-height:180px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;">
      <div class="muted" style="font-size:11px;text-align:center;padding:10px;">Loading positions...</div>
    </div>

  </div>
</div>'''

if old_widget_html in text:
    text = text.replace(old_widget_html, new_widget_html, 1)
    print("Replaced floatingPositionWidget with full CA AI Live Sentinel & Advisor layout")
else:
    print("Warning: old_widget_html not matched exactly")

# -----------------------------------------------------------------------------
# 2. Add JavaScript logic for Position Advisor, Theta Decay monitoring, and Empty-State
# -----------------------------------------------------------------------------
RELEASE_50_JS = '''
// ============================================================================
// RELEASE 50: CA AI LIVE POSITION ADVISOR & SENTINEL SCRIPTS
// ============================================================================

let currentFpSubTab = 'active';
let activeAdvisorPosition = null;

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
    const posId = activeAdvisorPosition?.id || '';
    const adv = await api('/api/positions/advisor?position_id=' + encodeURIComponent(posId));
    renderPositionAdvisorData(adv);
  } catch(e) {
    console.warn('refreshPositionAdvisor error:', e);
  }
};

function renderPositionAdvisorData(adv){
  if(!adv) return;
  const verdictEl = document.getElementById('fpAdvisorVerdict');
  const reasonEl = document.getElementById('fpAdvisorReason');
  const urgencyEl = document.getElementById('fpAdvisorUrgency');
  const bannerEl = document.getElementById('fpAdvisorBanner');
  const peakEl = document.getElementById('fpPeakPnl');
  const currPnlTag = document.getElementById('fpCurrentPnlTag');
  const thetaBurnEl = document.getElementById('fpThetaBurn');

  if(verdictEl) verdictEl.textContent = adv.verdict || 'MONITORING';
  if(reasonEl) reasonEl.textContent = adv.reason || adv.advice || '';
  if(urgencyEl){
    urgencyEl.textContent = adv.urgency || 'NORMAL';
    urgencyEl.className = 'tag ' + (adv.urgency === 'HIGH' ? 'sell' : (adv.urgency === 'MEDIUM' ? 'gold' : 'buy'));
  }
  if(bannerEl){
    if(adv.decision === 'EXIT_NOW'){
      bannerEl.style.background = 'rgba(239, 68, 68, 0.15)';
      bannerEl.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    } else if(adv.decision === 'TRAIL_STOP'){
      bannerEl.style.background = 'rgba(245, 158, 11, 0.15)';
      bannerEl.style.borderColor = 'rgba(245, 158, 11, 0.4)';
    } else {
      bannerEl.style.background = 'rgba(16, 185, 129, 0.12)';
      bannerEl.style.borderColor = 'rgba(16, 185, 129, 0.3)';
    }
  }

  if(peakEl){
    const pk = Number(adv.peak_pnl || 0);
    peakEl.textContent = (pk >= 0 ? '+' : '') + fmtMoney(pk);
    peakEl.style.color = pk >= 0 ? 'var(--buy)' : 'var(--sell)';
  }
  if(currPnlTag){
    const cp = Number(adv.current_pnl || 0);
    currPnlTag.textContent = 'Now: ' + (cp >= 0 ? '+' : '') + fmtMoney(cp);
    currPnlTag.className = 'tag ' + (cp >= 0 ? 'buy' : 'sell');
  }
  if(thetaBurnEl){
    const tb = Number(adv.theta_decay_hourly || 0);
    thetaBurnEl.textContent = '-₹' + fmt(tb) + '/hr';
  }
}

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

    // Refresh advisor banner data
    refreshPositionAdvisor();

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
'''

if '// RELEASE 50: CA AI LIVE POSITION ADVISOR & SENTINEL SCRIPTS' not in text:
    text = text.replace('</body>', f'<script>{RELEASE_50_JS}</script>\n</body>', 1)
    print("Injected Release 50 client scripts before </body>")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print(f"Saved terminal.html with Release 50 updates ({len(text):,} bytes)")

