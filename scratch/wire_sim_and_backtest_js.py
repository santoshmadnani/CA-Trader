# -*- coding: utf-8 -*-
"""
Add JS wiring for Price Sensitivity Simulator & Backtesting Dual Synchronized Charts
"""
with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

sim_js = '''
  // ==========================================
  // PRICE SENSITIVITY SIMULATOR LOGIC (Item 10)
  // ==========================================
  function updatePriceSensitivitySim(prefix){
    const rawSym = selectedSymbol() || 'NIFTY';
    const sym = extractUnderlying(rawSym);
    const q = (window.__CA_WL_QUOTES || {})[sym.toUpperCase()] || (window.__CA_WL_QUOTES || {})[rawSym.toUpperCase()] || {};
    const cmp = Number(q.ltp || state.latestLive || (state.candles.length ? state.candles[state.candles.length-1].close : 23450));
    const slider = document.getElementById(`${prefix}SimSlider`);
    if(!slider || !cmp) return;

    const cmpBadge = document.getElementById(`${prefix}SimCmpBadge`);
    if(cmpBadge) cmpBadge.textContent = `CMP: ₹${fmt(cmp)}`;

    const pct = Number(slider.value) / 10; // e.g. -5.0 to +5.0%
    const diff = (cmp * pct) / 100;
    const simPrice = cmp + diff;

    const disp = document.getElementById(`${prefix}SimSliderDisplay`);
    if(disp) disp.textContent = `Simulated Price: ₹${fmt(simPrice)} (${pct>=0?'+':''}${pct.toFixed(1)}%)`;

    const diffBadge = document.getElementById(`${prefix}SimDiffBadge`);
    if(diffBadge){
      diffBadge.textContent = `Diff: ${diff>=0?'+':''}₹${fmt(diff)} (${pct>=0?'+':''}${pct.toFixed(2)}%)`;
      diffBadge.className = `tag ${pct > 0 ? 'buy' : pct < 0 ? 'sell' : 'neutral'}`;
    }

    const priceVal = document.getElementById(`${prefix}SimPriceVal`);
    if(priceVal) priceVal.textContent = `₹${fmt(simPrice)}`;

    const priceDiff = document.getElementById(`${prefix}SimPriceDiff`);
    if(priceDiff){
      priceDiff.textContent = `${pct>=0?'+':''}${pct.toFixed(2)}% vs CMP`;
      priceDiff.style.color = pct > 0 ? 'var(--buy)' : pct < 0 ? 'var(--sell)' : 'var(--text-faint)';
    }

    // Call / Put Option Greeks impact
    const callImpact = diff * 0.52 + 0.5 * 0.0012 * diff * diff;
    const putImpact = -diff * 0.48 + 0.5 * 0.0012 * diff * diff;

    const callEl = document.getElementById(`${prefix}SimCallDelta`);
    if(callEl){
      callEl.textContent = `${callImpact>=0?'+':''}₹${fmt(callImpact)}`;
      callEl.style.color = callImpact >= 0 ? 'var(--buy)' : 'var(--sell)';
    }

    const putEl = document.getElementById(`${prefix}SimPutDelta`);
    if(putEl){
      putEl.textContent = `${putImpact>=0?'+':''}₹${fmt(putImpact)}`;
      putEl.style.color = putImpact >= 0 ? 'var(--buy)' : 'var(--sell)';
    }

    const threshEl = document.getElementById(`${prefix}SimThreshold`);
    const threshDet = document.getElementById(`${prefix}SimThresholdDetail`);
    if(threshEl && threshDet){
      if(pct >= 2.0){
        threshEl.textContent = 'Bullish Resistance Breakout';
        threshEl.style.color = 'var(--buy)';
        threshDet.textContent = `Breaches +2% band · Projected target acceleration`;
      } else if(pct <= -2.0){
        threshEl.textContent = 'Bearish Support Breakdown';
        threshEl.style.color = 'var(--sell)';
        threshDet.textContent = `Breaches -2% support · Dynamic stop-loss trigger`;
      } else {
        threshEl.textContent = 'Consolidation / Range-Bound';
        threshEl.style.color = 'var(--gold)';
        threshDet.textContent = `Within normal volatility band (±2.0%)`;
      }
    }
  }

  function wirePriceSensitivitySim(prefix){
    const slider = document.getElementById(`${prefix}SimSlider`);
    if(slider && !slider.dataset.wired){
      slider.dataset.wired = '1';
      slider.addEventListener('input', () => updatePriceSensitivitySim(prefix));
    }
    updatePriceSensitivitySim(prefix);
  }

  function updateAllPriceSensitivitySimulators(){
    ['chart', 'reco'].forEach(prefix => updatePriceSensitivitySim(prefix));
  }
  window.updateAllPriceSensitivitySimulators = updateAllPriceSensitivitySimulators;
'''

# Find place to insert sim_js (e.g. before drawBacktestCanvas)
anchor_bt_draw = "  function drawBacktestCanvas(){"
if anchor_bt_draw in c and "updatePriceSensitivitySim" not in c:
    c = c.replace(anchor_bt_draw, sim_js + "\n" + anchor_bt_draw)
    print("1. Added Price Sensitivity Simulator JS")

# Now add Option Chart rendering & Option Chain loading in backtest
bt_opt_js = '''
  // ==========================================
  // BACKTEST DUAL SYNCHRONIZED CHARTS (Item 15)
  // ==========================================
  let btOptionStrikes = [];
  let btSelectedOptionStrike = null;
  let btSelectedOptionType = 'CE';

  async function loadBacktestOptionChain(){
    const sel = $('btOptionContractSelect');
    if(!sel) return;
    try {
      const sym = btState.symbol || 'NIFTY';
      const d = await api('/api/options/' + encodeURIComponent(sym) + '/chain');
      const strikes = d?.strikes || [];
      btOptionStrikes = strikes;
      if(!strikes.length){
        sel.innerHTML = `<option value="">No options chain available</option>`;
        return;
      }
      // Populate strikes around ATM
      const currPrice = Number(d.underlying_price || d.spot_price || (btState.allCandles.length ? btState.allCandles[0].close : 23500));
      let optOptionsHtml = '';
      strikes.slice(0, 25).forEach(s => {
        const diff = Number(s.strike) - currPrice;
        const tag = Math.abs(diff) < 100 ? '(ATM)' : diff > 0 ? '(OTM)' : '(ITM)';
        optOptionsHtml += `<option value="${s.strike}|CE" ${Math.abs(diff) < 50 ? 'selected' : ''}>${sym} ${s.strike} CE ${tag}</option>`;
        optOptionsHtml += `<option value="${s.strike}|PE">${sym} ${s.strike} PE ${Math.abs(diff) < 100 ? '(ATM)' : diff < 0 ? '(OTM)' : '(ITM)'}</option>`;
      });
      sel.innerHTML = optOptionsHtml;
      if(sel.value){
        const [stk, type] = sel.value.split('|');
        btSelectedOptionStrike = Number(stk);
        btSelectedOptionType = type || 'CE';
        updateBacktestOptionHeader();
      }
    } catch(e) {
      console.debug('loadBacktestOptionChain error:', e);
    }
  }

  function updateBacktestOptionHeader(){
    const sym = btState.symbol || 'NIFTY';
    const stk = btSelectedOptionStrike || 23500;
    const type = btSelectedOptionType || 'CE';
    const name = `${sym} ${stk} ${type}`;
    if($('btOptionNameBadge')) $('btOptionNameBadge').textContent = name;

    const curr = btState.allCandles[btState.currentIndex];
    const spot = curr ? Number(curr.close) : stk;
    const diff = type === 'CE' ? (spot - stk) : (stk - spot);
    const timeToExpiry = 7 / 365; // ~7 days
    const iv = 0.145;
    const delta = type === 'CE' ? Math.max(0.05, Math.min(0.95, 0.5 + (diff / (spot * iv * Math.sqrt(timeToExpiry))))) : -Math.max(0.05, Math.min(0.95, 0.5 - (diff / (spot * iv * Math.sqrt(timeToExpiry)))));
    const gamma = Math.max(0.0005, (1 / (spot * iv * Math.sqrt(timeToExpiry) * 2.5)));
    const theta = -((spot * iv) / (2 * Math.sqrt(timeToExpiry * 365)) * 0.05);
    const vega = spot * Math.sqrt(timeToExpiry) * 0.01;

    if($('btOptionGreeksBadge')){
      $('btOptionGreeksBadge').textContent = `Δ: ${delta.toFixed(2)} | Γ: ${gamma.toFixed(4)} | Θ: ${theta.toFixed(1)} | ν: ${vega.toFixed(1)} | IV: ${(iv*100).toFixed(1)}%`;
    }
  }

  function drawBacktestOptionCanvas(){
    const canvas = $('btOptionCanvas');
    if(!canvas) return;
    const parent = canvas.parentElement;
    if(!parent) return;

    const dpr = window.devicePixelRatio || 1;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    if(w <= 0 || h <= 0) return;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const pad = { t: 16, b: 20, l: 12, r: 60 };
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b;

    const viewCount = 45;
    const startIdx = Math.max(0, btState.currentIndex - viewCount + 1);
    const visibleCandles = btState.allCandles.slice(startIdx, btState.currentIndex + 1);
    if(!visibleCandles.length) return;

    const stk = btSelectedOptionStrike || 23500;
    const isCall = (btSelectedOptionType || 'CE') === 'CE';

    // Calculate synthetic option candles strictly from underlying candles (Black-Scholes approximation)
    const optCandles = visibleCandles.map(c => {
      const calcOptPrice = (spot) => {
        const moneyness = isCall ? (spot - stk) : (stk - spot);
        const timeVal = Math.max(25, spot * 0.012);
        const intrinsic = Math.max(0, moneyness);
        return Math.max(2.5, intrinsic + timeVal * Math.exp(-Math.abs(moneyness) / (spot * 0.03)));
      };
      return {
        open: calcOptPrice(Number(c.open)),
        high: Math.max(calcOptPrice(Number(c.high)), calcOptPrice(Number(c.open))),
        low: Math.min(calcOptPrice(Number(c.low)), calcOptPrice(Number(c.close))),
        close: calcOptPrice(Number(c.close)),
        timestamp: c.timestamp
      };
    });

    const lows = optCandles.map(c => c.low);
    const highs = optCandles.map(c => c.high);
    let minP = Math.min(...lows);
    let maxP = Math.max(...highs);
    const range = (maxP - minP) || 1;
    minP -= range * 0.08;
    maxP += range * 0.08;

    const yFromP = p => pad.t + ((maxP - p) / (maxP - minP)) * plotH;
    const step = plotW / Math.max(viewCount, optCandles.length);

    const isLightMode = document.documentElement.getAttribute('data-theme') === 'light' || document.body.classList.contains('light-theme');
    ctx.fillStyle = isLightMode ? '#ffffff' : '#0f141c';
    ctx.fillRect(0, 0, w, h);

    // Gridlines
    ctx.strokeStyle = isLightMode ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.font = '9px IBM Plex Mono, monospace';
    ctx.fillStyle = isLightMode ? 'rgba(0,0,0,0.55)' : 'rgba(255,255,255,0.4)';

    for(let i = 0; i <= 4; i++){
      const yy = pad.t + (i * plotH) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.l, yy);
      ctx.lineTo(w - pad.r, yy);
      ctx.stroke();

      const val = maxP - ((maxP - minP) * i) / 4;
      ctx.fillText(`₹${fmt(val)}`, w - pad.r + 6, yy + 3);
    }

    // Render Option Candles
    optCandles.forEach((c, idx) => {
      const cx = pad.l + (idx + 0.5) * step;
      const isUp = c.close >= c.open;
      const bodyTop = yFromP(Math.max(c.open, c.close));
      const bodyBottom = yFromP(Math.min(c.open, c.close));
      const bodyH = Math.max(1.5, bodyBottom - bodyTop);

      ctx.strokeStyle = isUp ? 'var(--buy)' : 'var(--sell)';
      ctx.fillStyle = isUp ? 'var(--buy)' : 'var(--sell)';
      ctx.lineWidth = 1;

      // Wick
      ctx.beginPath();
      ctx.moveTo(cx, yFromP(c.high));
      ctx.lineTo(cx, yFromP(c.low));
      ctx.stroke();

      // Body
      const bw = Math.max(2, step * 0.7);
      ctx.fillRect(cx - bw / 2, bodyTop, bw, bodyH);
    });

    // Update Option OHLC bar
    const lastOpt = optCandles[optCandles.length - 1];
    if(lastOpt){
      if($('btOptO')) $('btOptO').textContent = `₹${fmt(lastOpt.open)}`;
      if($('btOptH')) $('btOptH').textContent = `₹${fmt(lastOpt.high)}`;
      if($('btOptL')) $('btOptL').textContent = `₹${fmt(lastOpt.low)}`;
      if($('btOptC')) $('btOptC').textContent = `₹${fmt(lastOpt.close)}`;
      if($('btOptLtp')) $('btOptLtp').textContent = `₹${fmt(lastOpt.close)}`;
    }
  }
'''

# Find end of drawBacktestCanvas to hook drawBacktestOptionCanvas
anchor_end_draw = "  function drawBacktestCanvas(){"
if anchor_end_draw in c and "drawBacktestOptionCanvas" not in c:
    c = c.replace(anchor_end_draw, bt_opt_js + "\n" + anchor_end_draw)
    print("2. Added Backtest Option Canvas rendering JS")

# Ensure drawBacktestCanvas calls drawBacktestOptionCanvas
if "drawBacktestOptionCanvas();" not in c:
    c = c.replace("updateFastForward(view);", "updateFastForward(view);\n    if(typeof drawBacktestOptionCanvas === 'function') drawBacktestOptionCanvas();\n    if(typeof updateBacktestOptionHeader === 'function') updateBacktestOptionHeader();")
    print("3. Hooked option canvas redraw into main redraw")

# Wire Step Back button in initBacktest
step_back_wire = """    $('btStepBtn')?.addEventListener('click', stepBacktestForward);
    $('btStepBackBtn')?.addEventListener('click', () => {
      if(btState.currentIndex > 0){
        btState.currentIndex--;
        renderBacktestStep(false);
      }
    });
    $('btOptionContractSelect')?.addEventListener('change', (e) => {
      const parts = (e.target.value || '').split('|');
      btSelectedOptionStrike = Number(parts[0]);
      btSelectedOptionType = parts[1] || 'CE';
      updateBacktestOptionHeader();
      drawBacktestOptionCanvas();
    });"""

if "$('btStepBtn')?.addEventListener('click', stepBacktestForward);" in c and "$('btStepBackBtn')" not in c:
    c = c.replace("$('btStepBtn')?.addEventListener('click', stepBacktestForward);", step_back_wire)
    print("4. Wired Step Back button and Option Contract select in initBacktest")

# Hook loadBacktestOptionChain inside loadBacktestData
if "void loadBacktestOptionChain();" not in c:
    c = c.replace("renderBacktestStep(true);", "renderBacktestStep(true);\n    void loadBacktestOptionChain();")
    print("5. Hooked option chain load into loadBacktestData")

# Call wirePriceSensitivitySim('chart') and wirePriceSensitivitySim('reco') in loadChart and loadRecommendations
if "wirePriceSensitivitySim('chart');" not in c:
    c = c.replace("void loadChartBundle();", "void loadChartBundle();\n    if(typeof wirePriceSensitivitySim === 'function') wirePriceSensitivitySim('chart');")
    print("6. Wired price sensitivity in loadChart")

if "wirePriceSensitivitySim('reco');" not in c:
    c = c.replace("async function loadRecommendations(force=false){", "async function loadRecommendations(force=false){\n    if(typeof wirePriceSensitivitySim === 'function') wirePriceSensitivitySim('reco');")
    print("7. Wired price sensitivity in loadRecommendations")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("Saved terminal.html with full JS wiring. Size:", len(c))

