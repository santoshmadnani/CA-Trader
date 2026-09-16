import sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

# Backup
shutil.copyfile('terminal.html', 'terminal.html.bak')
print('Backup created: terminal.html.bak')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# ==============================================================================
# 1. Inject Orders & Positions Advisor Card
# ==============================================================================
target_banner_end = """        <div id="positionAdvisoryText" style="font-size:12px;line-height:1.4;color:var(--text-dim);"></div>
      </div>"""

orders_advisor_html = """        <div id="positionAdvisoryText" style="font-size:12px;line-height:1.4;color:var(--text-dim);"></div>
      </div>

      <!-- CA AI During & Post Trade Live Advisor (Release 51) -->
      <div class="card" id="ordersAdvisorCard" style="margin-bottom:16px;border:1px solid var(--border);border-left:4px solid var(--gold);background:linear-gradient(180deg, rgba(245,158,11,0.05) 0%, var(--surface) 100%);">
        <div class="card-head" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--buy);box-shadow:0 0 8px var(--buy);" id="ordersAdvisorPulse"></span>
            <b style="font-size:13px;color:var(--text);letter-spacing:0.3px;">✦ CA AI During &amp; Post-Trade Advisor</b>
            <span id="ordersAdvisorActiveSymbol" class="tag neutral" style="font-size:10px;font-weight:700;">No Open Position Selected</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span id="ordersAdvisorSyncStatus" style="font-size:10.5px;color:var(--text-dim);display:flex;align-items:center;gap:4px;">
              <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--buy);" id="ordersAdvisorSyncDot"></span> <span id="ordersAdvisorSyncText">Real-time Sync Active (2s)</span>
            </span>
            <button type="button" class="btn ghost small" style="padding:2px 8px;height:24px;font-size:11px;" onclick="refreshPositionAdvisor()">↻ Sync</button>
          </div>
        </div>

        <!-- Verdict Banner -->
        <div id="ordersAdvisorBanner" style="padding:10px 14px;border-radius:8px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">
            <b id="ordersAdvisorVerdict" style="font-size:13px;color:var(--gold);">⚡ ANALYZING TRADE HEALTH…</b>
            <span id="ordersAdvisorUrgency" class="tag gold" style="font-size:10px;">MONITORING</span>
          </div>
          <div id="ordersAdvisorReason" style="font-size:11.5px;color:var(--text);margin-top:6px;line-height:1.4;">
            Evaluating real-time option Theta decay, peak P&L retention, and technical exit triggers.
          </div>
        </div>

        <!-- Comprehensive 4-Column Metrics Grid -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:10px;margin-bottom:12px;">
          <!-- Metric 1: Peak P&L vs Current P&L -->
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10.5px;margin-bottom:2px;">Peak vs Current MTM P&L:</div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
              <b id="ordersPeakPnl" style="color:var(--buy);font-family:var(--font-mono);font-size:14px;">+₹--</b>
              <span id="ordersCurrentPnlTag" class="tag neutral" style="font-size:10px;">Now: ₹--</span>
            </div>
            <div id="ordersPnlRetention" class="muted" style="font-size:9.5px;margin-top:2px;">Peak Giveback: ₹-- (0%)</div>
          </div>

          <!-- Metric 2: Theta Decay Burn Rate -->
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10.5px;margin-bottom:2px;">Theta Decay Burn Rate:</div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
              <b id="ordersThetaBurn" style="color:var(--sell);font-family:var(--font-mono);font-size:14px;">-₹--/hr</b>
              <span class="tag sell" style="font-size:9.5px;">TIME DECAY</span>
            </div>
            <div id="ordersDailyTheta" class="muted" style="font-size:9.5px;margin-top:2px;">Daily Impact: -₹--/day</div>
          </div>

          <!-- Metric 3: Trade Status / Entry & LTP -->
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10.5px;margin-bottom:2px;">Entry / LTP / Qty:</div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
              <b id="ordersTradeEntryLtp" style="font-family:var(--font-mono);font-size:13px;color:var(--text);">-- / --</b>
              <span id="ordersTradeQtyTag" class="tag neutral" style="font-size:9.5px;">Qty: --</span>
            </div>
            <div id="ordersTradeDuration" class="muted" style="font-size:9.5px;margin-top:2px;">Mode: Paper Live Sentinel</div>
          </div>

          <!-- Metric 4: Stop-Loss & Target Guard -->
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10.5px;margin-bottom:2px;">Stop-Loss &amp; Target Guard:</div>
            <div style="display:flex;justify-content:space-between;align-items:baseline;">
              <b id="ordersSlTgt" style="font-family:var(--font-mono);font-size:13px;color:var(--text);">SL: -- | TGT: --</b>
              <span class="tag gold" style="font-size:9.5px;" id="ordersSlStatusTag">GUARD ACTIVE</span>
            </div>
            <div id="ordersSlAdvice" class="muted" style="font-size:9.5px;margin-top:2px;">Recommended Trail: Breakeven</div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px;">
          <button type="button" class="btn sell" style="flex:1;min-width:180px;font-size:12px;padding:7px 12px;" onclick="executePositionSquareOff()">⚡ Square Off Position at Market</button>
          <button type="button" class="btn gold" style="flex:1;min-width:180px;font-size:12px;padding:7px 12px;" onclick="executeTrailSlBreakeven()">🔒 Trail Stop-Loss to Breakeven</button>
          <button type="button" class="btn ghost" style="padding:7px 14px;font-size:12px;" onclick="toggleOrdersAdvisorChat()" title="Expand CA AI Trade Chat">💬 Ask CA AI Advisor</button>
        </div>

        <!-- Expandable Two-Way Chat Box in Orders Panel -->
        <div id="ordersAdvisorChatBox" style="background:var(--surface-2);border-radius:8px;padding:12px;border:1px solid var(--border-soft);">
          <div style="font-size:11.5px;font-weight:700;color:var(--text);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
            <span>✦ Interactive Position Strategy Advisor</span>
            <span class="muted" style="font-size:10px;">Greeks &amp; Real-time Sentinel Chat</span>
          </div>

          <!-- Quick Query Chips -->
          <div style="display:flex;gap:6px;overflow-x:auto;padding-bottom:6px;margin-bottom:8px;" class="custom-scroll">
            <button type="button" class="btn ghost small" style="font-size:10.5px;white-space:nowrap;padding:3px 8px;" onclick="sendOrdersAdvisorQuickQuestion('Why should I exit now?')">Why exit now?</button>
            <button type="button" class="btn ghost small" style="font-size:10.5px;white-space:nowrap;padding:3px 8px;" onclick="sendOrdersAdvisorQuickQuestion('Is Theta decay critical for this strike?')">Is Theta decay critical?</button>
            <button type="button" class="btn ghost small" style="font-size:10.5px;white-space:nowrap;padding:3px 8px;" onclick="sendOrdersAdvisorQuickQuestion('Where should I trail my Stop Loss?')">Where to trail SL?</button>
            <button type="button" class="btn ghost small" style="font-size:10.5px;white-space:nowrap;padding:3px 8px;" onclick="sendOrdersAdvisorQuickQuestion('Explain post-trade lesson and mistake')">Post-trade lesson</button>
          </div>

          <!-- Chat Conversation Log -->
          <div id="ordersAdvisorChatLog" style="max-height:180px;overflow-y:auto;background:var(--surface);border-radius:6px;padding:10px;font-size:11.5px;line-height:1.45;margin-bottom:8px;border:1px solid var(--border-soft);">
            <div style="color:var(--text-dim);font-style:italic;">
              CA AI Advisor ready. Ask any question about this trade's MTM, Greeks, Theta decay risk, or exit recommendations.
            </div>
          </div>

          <!-- Chat Input Row -->
          <div style="display:flex;gap:8px;">
            <input type="text" id="ordersAdvisorInput" placeholder="Ask CA AI: e.g., Should I hold through this retracement?" style="flex:1;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:7px 12px;color:var(--text);font-size:11.5px;" onkeydown="if(event.key==='Enter') sendOrdersAdvisorMessage()">
            <button type="button" class="btn gold small" style="padding:7px 14px;font-size:11.5px;" onclick="sendOrdersAdvisorMessage()">Send</button>
          </div>
        </div>
      </div>"""

if target_banner_end in text:
    text = text.replace(target_banner_end, orders_advisor_html, 1)
    print('[OK] Injected ordersAdvisorCard into #panel-orders')
else:
    print('[FAIL] target_banner_end not found')
    sys.exit(1)

# ==============================================================================
# 2. Fix Floating Pop-up Window Minimize Button in HTML
# ==============================================================================
target_fp_min_btn = '<button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:11px;line-height:1;" id="fpMinBtn" onclick="toggleFloatingPositionsWidget()">_</button>'
replacement_fp_min_btn = '<button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:11px;line-height:1;" id="fpMinBtn" onclick="toggleFloatingPositionsWidget(event)" title="Minimize / Expand Sentinel">_</button>'

if target_fp_min_btn in text:
    text = text.replace(target_fp_min_btn, replacement_fp_min_btn, 1)
    print('[OK] Updated fpMinBtn onclick in HTML')
else:
    print('[FAIL] target_fp_min_btn not found')
    sys.exit(1)

# ==============================================================================
# 3. Fix toggleFloatingPositionsWidget in JS
# ==============================================================================
target_toggle_js = """  // Item 13: Floating Mini-Position Sentinel Widget
  let isFloatingPosMinimized = false;
  window.toggleFloatingPositionsWidget = function(){
    isFloatingPosMinimized = !isFloatingPosMinimized;
    const body = document.getElementById('floatingPosBody');
    const btn = document.getElementById('fpMinBtn');
    if(body){
      body.style.display = isFloatingPosMinimized ? 'none' : 'flex';
      if(btn) btn.textContent = isFloatingPosMinimized ? '▢' : '_';
    }
  };"""

replacement_toggle_js = """  // Item 13: Floating Mini-Position Sentinel Widget (Release 51 Fix)
  let isFloatingPosMinimized = false;
  window.toggleFloatingPositionsWidget = function(e){
    if(e && e.stopPropagation) e.stopPropagation();
    isFloatingPosMinimized = !isFloatingPosMinimized;
    const bodyWrapper = document.getElementById('floatingPosBodyWrapper');
    const btn = document.getElementById('fpMinBtn');
    const widget = document.getElementById('floatingPositionWidget');
    if(bodyWrapper){
      bodyWrapper.style.display = isFloatingPosMinimized ? 'none' : 'flex';
    }
    if(btn){
      btn.textContent = isFloatingPosMinimized ? '▢' : '_';
      btn.title = isFloatingPosMinimized ? 'Expand Sentinel' : 'Minimize Sentinel';
    }
    if(widget){
      widget.style.boxShadow = isFloatingPosMinimized ? '0 4px 16px rgba(0,0,0,0.4)' : '0 14px 44px rgba(0,0,0,0.55)';
    }
  };"""

if target_toggle_js in text:
    text = text.replace(target_toggle_js, replacement_toggle_js, 1)
    print('[OK] Replaced toggleFloatingPositionsWidget implementation')
else:
    print('[FAIL] target_toggle_js not found')
    sys.exit(1)

# ==============================================================================
# 4. Update renderPositionAdvisorData, add Orders Chat handlers, and Adaptive Real-time Auto-Sync
# ==============================================================================
target_render_fn = """function renderPositionAdvisorData(adv){
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
}"""

replacement_render_fn = """function renderPositionAdvisorData(adv){
  if(!adv) return;
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
    fpThetaBurnEl.textContent = '-₹' + fmt(tb) + '/hr';
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

  if(ordSymEl && activeAdvisorPosition){
    const sym = activeAdvisorPosition.symbol || 'ACTIVE';
    const side = activeAdvisorPosition.side || 'BUY';
    const isClosed = String(activeAdvisorPosition.status||'').toUpperCase() === 'CLOSED' || Number(activeAdvisorPosition.quantity||0) === 0;
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
    ordThetaBurnEl.textContent = '-₹' + fmt(tb) + '/hr';
  }
  if(ordDailyThetaEl){
    const dailyLoss = Math.round(tb * 6.25);
    ordDailyThetaEl.textContent = `Daily Impact: -₹${fmt(dailyLoss)}/day`;
  }
  if(activeAdvisorPosition){
    const entry = fmt(activeAdvisorPosition.avg_price || activeAdvisorPosition.entry || 0);
    const ltp = fmt(activeAdvisorPosition.ltp || activeAdvisorPosition.exit_price || activeAdvisorPosition.avg_price || 0);
    const qty = activeAdvisorPosition.quantity || activeAdvisorPosition.display_quantity || 1;
    if(ordEntryLtpEl) ordEntryLtpEl.textContent = `₹${entry} / ₹${ltp}`;
    if(ordQtyTag) ordQtyTag.textContent = `Qty: ${qty}`;
    const sl = activeAdvisorPosition.stop_loss ? ('₹' + fmt(activeAdvisorPosition.stop_loss)) : '--';
    const tgt = activeAdvisorPosition.target ? ('₹' + fmt(activeAdvisorPosition.target)) : '--';
    if(ordSlTgtEl) ordSlTgtEl.textContent = `SL: ${sl} | TGT: ${tgt}`;
    if(ordSlStatusTag){
      ordSlStatusTag.textContent = activeAdvisorPosition.stop_loss ? 'GUARDED' : 'UNGUARDED';
      ordSlStatusTag.className = 'tag ' + (activeAdvisorPosition.stop_loss ? 'gold' : 'sell');
    }
  }
}

// Orders & Positions Panel Strategy Chat Handlers
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
};"""

if target_render_fn in text:
    text = text.replace(target_render_fn, replacement_render_fn, 1)
    print('[OK] Updated renderPositionAdvisorData and added Orders Chat handlers')
else:
    print('[FAIL] target_render_fn not found')
    sys.exit(1)

# ==============================================================================
# 5. Update updateFloatingPositionsWidget for Real-time Adaptive Auto-Sync
# ==============================================================================
target_update_fp = """    // Refresh advisor banner data
    refreshPositionAdvisor();"""

replacement_update_fp = """    // Refresh advisor banner data for both views
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
    }, syncIntervalMs);"""

if target_update_fp in text:
    text = text.replace(target_update_fp, replacement_update_fp, 1)
    print('[OK] Injected real-time auto-sync loop into updateFloatingPositionsWidget')
else:
    print('[FAIL] target_update_fp not found')
    sys.exit(1)

# Write updated file
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Successfully applied all changes to terminal.html')

