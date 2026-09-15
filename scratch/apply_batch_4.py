import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert Backtesting Engine right before "// ---------------- Tab loading ----------------"
target_tab_load = "  // ---------------- Tab loading ----------------"
idx_target = content.find(target_tab_load)

bt_engine_code = """  // ================= DEDICATED BACKTESTING REPLAY ENGINE =================
  const btState = {
    symbol: 'RELIANCE',
    tf: '5m',
    allCandles: [],
    currentIndex: 0,
    isPlaying: false,
    speed: 1,
    timer: null,
    positions: [],       // [ { id, symbol, side, qty, entryPrice, sl, tgt, time } ]
    closedTrades: [],    // [ { id, symbol, side, qty, entryPrice, exitPrice, pnl, time, reason } ]
    realizedPnl: 0,
    latestSignal: null,
    initialized: false
  };

  function initBacktest(force=false){
    if(btState.initialized && !force) return;
    btState.initialized = true;

    // Set default datetime to 5 market days ago 09:15
    const dtInput = $('btDateTime');
    if(dtInput && !dtInput.value){
      const d = new Date();
      d.setDate(d.getDate() - 5);
      d.setHours(9, 15, 0, 0);
      const pad = n => String(n).padStart(2, '0');
      const iso = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T09:15`;
      dtInput.value = iso;
    }

    // Controls
    $('btLoadDataBtn')?.addEventListener('click', () => loadBacktestData());
    $('btPlayPauseBtn')?.addEventListener('click', toggleBacktestPlay);
    $('btStepBtn')?.addEventListener('click', stepBacktestForward);
    $('btResetBtn')?.addEventListener('click', resetBacktestReplay);

    // Speed buttons
    document.querySelectorAll('[data-bt-speed]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('[data-bt-speed]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        btState.speed = Number(btn.dataset.btSpeed) || 1;
        if(btState.isPlaying){
          pauseBacktest();
          playBacktest();
        }
      });
    });

    // Timeline Slider
    $('btTimelineSlider')?.addEventListener('input', (e) => {
      const idx = Number(e.target.value);
      if(Number.isFinite(idx) && idx >= 0 && idx < btState.allCandles.length){
        btState.currentIndex = idx;
        renderBacktestStep(false);
      }
    });

    // Selectors
    $('btSymbolSelect')?.addEventListener('change', (e) => {
      btState.symbol = e.target.value;
      loadBacktestData();
    });

    $('btTfSelect')?.addEventListener('change', (e) => {
      btState.tf = e.target.value;
      loadBacktestData();
    });

    // Order Execution
    $('btBuyBtn')?.addEventListener('click', () => placeBacktestOrder('BUY'));
    $('btSellBtn')?.addEventListener('click', () => placeBacktestOrder('SELL'));

    // Initial load
    loadBacktestData();
  }
  window.initBacktest = initBacktest;

  async function loadBacktestData(){
    pauseBacktest();
    const sym = $('btSymbolSelect')?.value || btState.symbol || 'RELIANCE';
    const tf = $('btTfSelect')?.value || btState.tf || '5m';
    const startTime = $('btDateTime')?.value || '';
    btState.symbol = sym;
    btState.tf = tf;

    const placeholder = $('btChartPlaceholder');
    if(placeholder){
      placeholder.style.display = 'flex';
      placeholder.textContent = `Loading historical ${sym} ${tf} replay candles…`;
    }

    try {
      let url = `/api/backtest/candles/${encodeURIComponent(sym)}?timeframe=${encodeURIComponent(tf)}`;
      if(startTime) url += `&start_time=${encodeURIComponent(startTime)}`;
      const d = await api(url, { timeoutMs: 12000 });
      const candles = Array.isArray(d.candles) ? d.candles : [];
      if(!candles.length) throw new Error('No historical candle data found for selected timeframe');

      btState.allCandles = candles;
      btState.currentIndex = Math.min(25, candles.length - 1);

      const slider = $('btTimelineSlider');
      if(slider){
        slider.min = '0';
        slider.max = String(candles.length - 1);
        slider.value = String(btState.currentIndex);
      }

      if(placeholder) placeholder.style.display = 'none';
      toast(`Loaded ${candles.length} candles for replay`);
      renderBacktestStep(true);
    } catch(e) {
      if(placeholder){
        placeholder.style.display = 'flex';
        placeholder.textContent = `Replay data error: ${e.message}`;
      }
      toast(e.message);
    }
  }

  function toggleBacktestPlay(){
    if(btState.isPlaying) pauseBacktest();
    else playBacktest();
  }

  function playBacktest(){
    if(!btState.allCandles.length){ toast('Load replay data first'); return; }
    if(btState.currentIndex >= btState.allCandles.length - 1){
      btState.currentIndex = 0;
    }
    btState.isPlaying = true;
    const btn = $('btPlayPauseBtn');
    if(btn){
      btn.textContent = '⏸ Pause';
      btn.style.background = 'var(--sell)';
      btn.style.color = '#fff';
    }
    const intervalMs = Math.max(75, Math.round(1000 / btState.speed));
    clearInterval(btState.timer);
    btState.timer = setInterval(() => {
      if(btState.currentIndex < btState.allCandles.length - 1){
        btState.currentIndex++;
        renderBacktestStep(false);
      } else {
        pauseBacktest();
        toast('Historical replay completed');
      }
    }, intervalMs);
  }

  function pauseBacktest(){
    btState.isPlaying = false;
    clearInterval(btState.timer);
    btState.timer = null;
    const btn = $('btPlayPauseBtn');
    if(btn){
      btn.textContent = '▶ Play';
      btn.style.background = 'var(--buy)';
      btn.style.color = '#0B2A1E';
    }
  }

  function stepBacktestForward(){
    pauseBacktest();
    if(!btState.allCandles.length) return;
    if(btState.currentIndex < btState.allCandles.length - 1){
      btState.currentIndex++;
      renderBacktestStep(true);
    } else {
      toast('At end of replay stream');
    }
  }

  function resetBacktestReplay(){
    pauseBacktest();
    btState.currentIndex = Math.min(25, btState.allCandles.length - 1);
    btState.positions = [];
    btState.closedTrades = [];
    btState.realizedPnl = 0;
    renderBacktestStep(true);
    toast('Replay reset to beginning');
  }

  let __btEvalSeq = 0;
  async function renderBacktestStep(forceEval = false){
    const candles = btState.allCandles;
    if(!candles.length || btState.currentIndex >= candles.length) return;

    const curr = candles[btState.currentIndex];
    const first = candles[0];

    // 1. Update Header stats
    if($('btSymbolTitle')) $('btSymbolTitle').textContent = `${btState.symbol} (${btState.tf}) · Replay`;
    if($('btLtp')) $('btLtp').textContent = `₹${fmt(curr.close)}`;
    if($('btChange')){
      const net = curr.close - first.open;
      const pct = (net / (first.open || 1)) * 100;
      $('btChange').textContent = `${net >= 0 ? '+' : ''}${fmt(net)} (${pct >= 0 ? '+' : ''}${fmt(pct)}%)`;
      $('btChange').style.color = net >= 0 ? 'var(--buy)' : 'var(--sell)';
    }
    if($('btSimulatedClock')) $('btSimulatedClock').textContent = formatTime(curr.timestamp);
    if($('btO')) $('btO').textContent = fmt(curr.open);
    if($('btH')) $('btH').textContent = fmt(curr.high);
    if($('btL')) $('btL').textContent = fmt(curr.low);
    if($('btC')) $('btC').textContent = fmt(curr.close);
    if($('btProgressLabel')) $('btProgressLabel').textContent = `${btState.currentIndex + 1} / ${candles.length} candles`;

    const slider = $('btTimelineSlider');
    if(slider && Number(slider.value) !== btState.currentIndex) slider.value = String(btState.currentIndex);

    // 2. Draw Candlestick Replay Chart on Canvas
    drawBacktestCanvas();

    // 3. Mark-to-market positions & check automatic SL / Target hits
    updateBacktestPositions(curr);

    // 4. Point-in-time CA AI Signal Evaluation (Zero lookahead cheating!)
    const subSlice = candles.slice(0, btState.currentIndex + 1);
    if(subSlice.length >= 10 && (forceEval || btState.currentIndex % 4 === 0 || !btState.isPlaying)){
      const seq = ++__btEvalSeq;
      try {
        const evalRes = await api('/api/backtest/evaluate', {
          method: 'POST',
          body: JSON.stringify({
            instrument: btState.symbol,
            timeframe: btState.tf,
            candles: subSlice.slice(-80)
          }),
          timeoutMs: 4000
        });
        if(seq === __btEvalSeq && evalRes){
          btState.latestSignal = evalRes;
          const sig = evalRes.recommendation || 'NO_TRADE';
          const badge = $('btSignalBadge');
          if(badge){
            badge.textContent = sig;
            badge.className = `tag ${signalClass(sig)}`;
          }
          if($('btSignalEntry')) $('btSignalEntry').textContent = `₹${fmt(evalRes.entry)}`;
          if($('btSignalSl')) $('btSignalSl').textContent = `₹${fmt(evalRes.stop_loss)}`;
          if($('btSignalTgt')) $('btSignalTgt').textContent = `₹${fmt(evalRes.target)}`;
          if($('btTrendTag')){
            $('btTrendTag').textContent = evalRes.trend || 'NEUTRAL';
            $('btTrendTag').className = `tag ${signalClass(evalRes.trend)}`;
          }
          if($('btRsi')) $('btRsi').textContent = fmt(evalRes.rsi);
          if($('btSignalRationale')){
            $('btSignalRationale').textContent = (evalRes.basis && evalRes.basis.length) ? evalRes.basis.join(' · ') : `Zero-lookahead: Dynamic ATR Stop Loss at ₹${fmt(evalRes.stop_loss)}, 2.2x ATR Target at ₹${fmt(evalRes.target)}.`;
          }
        }
      } catch(_) {}
    }
  }

  function drawBacktestCanvas(){
    const canvas = $('btCanvas');
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

    const pad = { t: 20, b: 24, l: 12, r: 60 };
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b;

    const viewCount = 45;
    const startIdx = Math.max(0, btState.currentIndex - viewCount + 1);
    const visibleCandles = btState.allCandles.slice(startIdx, btState.currentIndex + 1);
    if(!visibleCandles.length) return;

    const lows = visibleCandles.map(c => Number(c.low));
    const highs = visibleCandles.map(c => Number(c.high));
    let minP = Math.min(...lows);
    let maxP = Math.max(...highs);
    const range = (maxP - minP) || 1;
    minP -= range * 0.05;
    maxP += range * 0.05;

    const yFromP = p => pad.t + ((maxP - p) / (maxP - minP)) * plotH;
    const step = plotW / Math.max(viewCount, visibleCandles.length);

    // Background & Gridlines
    ctx.fillStyle = '#0f141c';
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.font = '9px IBM Plex Mono, monospace';
    ctx.fillStyle = 'rgba(255,255,255,0.4)';

    for(let i = 0; i <= 5; i++){
      const yy = pad.t + (i * plotH) / 5;
      ctx.beginPath();
      ctx.moveTo(pad.l, yy);
      ctx.lineTo(w - pad.r, yy);
      ctx.stroke();

      const val = maxP - ((maxP - minP) * i) / 5;
      ctx.fillText(fmt(val), w - pad.r + 6, yy + 3);
    }

    // Draw Candlesticks
    visibleCandles.forEach((c, idx) => {
      const xx = pad.l + (idx + 0.5) * step;
      const isUp = Number(c.close) >= Number(c.open);
      const color = isUp ? '#26D9A6' : '#FF5C72';

      // Wicks
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(xx, yFromP(Number(c.high)));
      ctx.lineTo(xx, yFromP(Number(c.low)));
      ctx.stroke();

      // Bodies
      const oY = yFromP(Number(c.open));
      const cY = yFromP(Number(c.close));
      const topY = Math.min(oY, cY);
      const bH = Math.max(2, Math.abs(cY - oY));
      const bw = Math.max(3, step * 0.65);

      ctx.fillStyle = color;
      ctx.fillRect(xx - bw / 2, topY, bw, bH);
    });

    // Draw active position lines
    btState.positions.forEach(pos => {
      const ey = yFromP(pos.entryPrice);
      ctx.strokeStyle = '#E8B84B';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(pad.l, ey);
      ctx.lineTo(w - pad.r, ey);
      ctx.stroke();

      if(pos.sl){
        const sy = yFromP(pos.sl);
        ctx.strokeStyle = '#FF5C72';
        ctx.beginPath();
        ctx.moveTo(pad.l, sy);
        ctx.lineTo(w - pad.r, sy);
        ctx.stroke();
      }
      if(pos.tgt){
        const ty = yFromP(pos.tgt);
        ctx.strokeStyle = '#26D9A6';
        ctx.beginPath();
        ctx.moveTo(pad.l, ty);
        ctx.lineTo(w - pad.r, ty);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    });

    // Latest price dotted line
    const lastC = visibleCandles[visibleCandles.length - 1];
    if(lastC){
      const ly = yFromP(Number(lastC.close));
      ctx.strokeStyle = 'rgba(232,184,75,0.7)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.moveTo(pad.l, ly);
      ctx.lineTo(w - pad.r, ly);
      ctx.stroke();
      ctx.setLineDash([]);

      // Price tag
      ctx.fillStyle = '#E8B84B';
      ctx.fillRect(w - pad.r + 2, ly - 8, pad.r - 4, 16);
      ctx.fillStyle = '#0A0D12';
      ctx.font = 'bold 9.5px IBM Plex Mono, monospace';
      ctx.fillText(fmt(lastC.close), w - pad.r + 5, ly + 3.5);
    }
  }

  function updateBacktestPositions(curr){
    const ltp = Number(curr.close);
    const low = Number(curr.low);
    const high = Number(curr.high);
    let unrealized = 0;
    const surviving = [];

    btState.positions.forEach(pos => {
      let closed = false;
      let exitPrice = ltp;
      let reason = 'Square off';

      if(pos.side === 'BUY'){
        if(pos.sl && low <= pos.sl){
          closed = true;
          exitPrice = pos.sl;
          reason = 'Stop Loss Hit';
        } else if(pos.tgt && high >= pos.tgt){
          closed = true;
          exitPrice = pos.tgt;
          reason = 'Target Hit';
        }
      } else {
        if(pos.sl && high >= pos.sl){
          closed = true;
          exitPrice = pos.sl;
          reason = 'Stop Loss Hit';
        } else if(pos.tgt && low <= pos.tgt){
          closed = true;
          exitPrice = pos.tgt;
          reason = 'Target Hit';
        }
      }

      if(closed){
        const pnl = pos.side === 'BUY' ? (exitPrice - pos.entryPrice) * pos.qty : (pos.entryPrice - exitPrice) * pos.qty;
        btState.realizedPnl += pnl;
        btState.closedTrades.push({
          ...pos,
          exitPrice,
          pnl,
          reason,
          exitTime: curr.timestamp
        });
        toast(`[Backtest] Position closed: ${pos.symbol} ${pos.side} @ ₹${fmt(exitPrice)} (${reason}, P&L: ₹${fmt(pnl)})`);
      } else {
        const pnl = pos.side === 'BUY' ? (ltp - pos.entryPrice) * pos.qty : (pos.entryPrice - ltp) * pos.qty;
        pos.currentPnl = pnl;
        unrealized += pnl;
        surviving.push(pos);
      }
    });

    btState.positions = surviving;

    // Render tables and stats
    renderBacktestPositionsTable(ltp);
    renderBacktestPerformance(unrealized);
  }

  function renderBacktestPositionsTable(ltp){
    const tbody = $('btPositionsTableBody');
    if(!tbody) return;

    if(!btState.positions.length){
      tbody.innerHTML = '<tr><td colspan="7" class="data-empty" style="padding:16px;text-align:center;">No open simulation positions. Place a trade above.</td></tr>';
      return;
    }

    tbody.innerHTML = btState.positions.map(p => {
      const pnl = Number(p.currentPnl || 0);
      const pnlStr = (pnl >= 0 ? '+' : '') + fmtMoney(pnl);
      const color = pnl >= 0 ? 'var(--buy)' : 'var(--sell)';
      return `
        <tr>
          <td><b>${esc(p.symbol)}</b></td>
          <td><span class="tag ${signalClass(p.side)}">${esc(p.side)}</span></td>
          <td>${p.qty}</td>
          <td>₹${fmt(p.entryPrice)}</td>
          <td>₹${fmt(ltp)}</td>
          <td><b style="color:${color};font-family:var(--font-mono);">${pnlStr}</b></td>
          <td>
            <button class="btn ghost small" onclick="squareOffBacktestPosition(${p.id})" style="padding:2px 8px;font-size:10px;">Square Off</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  function renderBacktestPerformance(unrealized){
    const totalTrades = btState.closedTrades.length;
    const wins = btState.closedTrades.filter(t => t.pnl > 0).length;
    const winRate = totalTrades ? ((wins / totalTrades) * 100).toFixed(1) : '0.0';
    const net = btState.realizedPnl + unrealized;

    if($('btActivePosCount')) $('btActivePosCount').textContent = String(btState.positions.length);
    if($('btUnrealizedPnl')){
      $('btUnrealizedPnl').textContent = `Unrealized: ${unrealized >= 0 ? '+' : ''}${fmtMoney(unrealized)}`;
      $('btUnrealizedPnl').style.color = unrealized >= 0 ? 'var(--buy)' : 'var(--sell)';
    }
    if($('btRealizedPnl')){
      $('btRealizedPnl').textContent = `Realized: ${btState.realizedPnl >= 0 ? '+' : ''}${fmtMoney(btState.realizedPnl)}`;
      $('btRealizedPnl').style.color = btState.realizedPnl >= 0 ? 'var(--buy)' : 'var(--sell)';
    }
    if($('btStatTrades')) $('btStatTrades').textContent = String(totalTrades);
    if($('btStatWinRate')) $('btStatWinRate').textContent = `${winRate}%`;
    if($('btStatNetProfit')){
      $('btStatNetProfit').textContent = `${net >= 0 ? '+' : ''}${fmtMoney(net)}`;
      $('btStatNetProfit').style.color = net >= 0 ? 'var(--buy)' : 'var(--sell)';
    }
  }

  function placeBacktestOrder(side){
    if(!btState.allCandles.length || btState.currentIndex >= btState.allCandles.length){
      toast('No replay data loaded');
      return;
    }
    const curr = btState.allCandles[btState.currentIndex];
    const qty = Number($('btOrderQty')?.value) || 10;
    const customSl = Number($('btCustomSl')?.value) || (btState.latestSignal?.stop_loss ? Number(btState.latestSignal.stop_loss) : null);
    const customTgt = Number($('btCustomTgt')?.value) || (btState.latestSignal?.target ? Number(btState.latestSignal.target) : null);

    const pos = {
      id: Date.now() + Math.floor(Math.random() * 1000),
      symbol: btState.symbol,
      side,
      qty,
      entryPrice: Number(curr.close),
      sl: customSl,
      tgt: customTgt,
      entryTime: curr.timestamp,
      currentPnl: 0
    };

    btState.positions.push(pos);
    toast(`[Simulated] Placed ${side} order for ${qty} ${btState.symbol} @ ₹${fmt(curr.close)}`);
    renderBacktestPositionsTable(Number(curr.close));
    renderBacktestPerformance(0);
    drawBacktestCanvas();
  }
  window.placeBacktestOrder = placeBacktestOrder;

  function squareOffBacktestPosition(id){
    const idx = btState.positions.findIndex(p => p.id === id);
    if(idx === -1) return;
    const curr = btState.allCandles[btState.currentIndex];
    const ltp = Number(curr ? curr.close : 0);
    const pos = btState.positions[idx];
    const pnl = pos.side === 'BUY' ? (ltp - pos.entryPrice) * pos.qty : (pos.entryPrice - ltp) * pos.qty;

    btState.realizedPnl += pnl;
    btState.closedTrades.push({
      ...pos,
      exitPrice: ltp,
      pnl,
      reason: 'Manual Square off',
      exitTime: curr?.timestamp || ''
    });

    btState.positions.splice(idx, 1);
    toast(`Squared off ${pos.symbol} (${pnl >= 0 ? '+' : ''}${fmtMoney(pnl)})`);
    renderBacktestPositionsTable(ltp);
    renderBacktestPerformance(0);
    drawBacktestCanvas();
  }
  window.squareOffBacktestPosition = squareOffBacktestPosition;

"""

if idx_target != -1:
    content = content[:idx_target] + bt_engine_code + content[idx_target:]
    print("✓ Inserted Backtesting Engine implementation")
else:
    print("⚠ Could not find target_tab_load")

# 2. Update loadTabData to include backtest
old_ltd = "      else if(tab==='auto'){ void loadAutoTrade(); }"
new_ltd = """      else if(tab==='auto'){ void loadAutoTrade(); }
      else if(tab==='backtest'){ if(typeof initBacktest === 'function') void initBacktest(); }"""

if old_ltd in content:
    content = content.replace(old_ltd, new_ltd, 1)
    print("✓ Added backtest to loadTabData")
else:
    print("⚠ Could not find old_ltd")

# 3. Update refreshActiveTab to include backtest
old_rat = "        if(tab==='auto') return loadAutoTrade();"
new_rat = """        if(tab==='auto') return loadAutoTrade();
        if(tab==='backtest' && typeof initBacktest === 'function') return initBacktest(true);"""

if old_rat in content:
    content = content.replace(old_rat, new_rat, 1)
    print("✓ Added backtest to refreshActiveTab")
else:
    print("⚠ Could not find old_rat")

# 4. Update onSymbolChanged to include backtest
old_osc = "    else if(tab==='auto') void loadAutoTrade();"
new_osc = """    else if(tab==='auto') void loadAutoTrade();
    else if(tab==='backtest') void (typeof initBacktest === 'function' && initBacktest());"""

if old_osc in content:
    content = content.replace(old_osc, new_osc, 1)
    print("✓ Added backtest to onSymbolChanged")
else:
    print("⚠ Could not find old_osc")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Batch 4 completed successfully.")

