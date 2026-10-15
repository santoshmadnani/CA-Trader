/* CA Trader chart: TradingView Lightweight Charts (Apache-2.0) + indicators, panes, drawings, legend, fullscreen.
   All series are computed from the candles the backend returns (Upstox); nothing is synthesized. */
(() => {
  "use strict";
  const LWC = window.LightweightCharts;
  const IST_SHIFT = 19800; // Lightweight Charts renders UTC; shift so axis labels read in IST
  const store = { get(k, d) { try { const v = localStorage.getItem("catc_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
                  set(k, v) { try { localStorage.setItem("catc_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } } };
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  // ------------------------------------------------------------ indicator maths
  const sma = (v, n) => v.map((_, i) => (i < n - 1 ? null : v.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0) / n));
  const ema = (v, n) => { const k = 2 / (n + 1); let e = null; return v.map((x, i) => (e = i === 0 ? x : x * k + e * (1 - k))); };
  const rma = (v, n) => { let r = null; return v.map((x, i) => (i < n - 1 ? (r = (r ?? 0) + x / n, null) : i === n - 1 ? (r = (r ?? 0) + x / n) : (r = (r * (n - 1) + x) / n))); };
  function trueRange(c) { return c.map((b, i) => (i === 0 ? b.high - b.low : Math.max(b.high - b.low, Math.abs(b.high - c[i - 1].close), Math.abs(b.low - c[i - 1].close)))); }
  function rsi(c, n) { const ch = c.map((b, i) => (i ? b.close - c[i - 1].close : 0)); const g = rma(ch.map((x) => Math.max(0, x)), n), l = rma(ch.map((x) => Math.max(0, -x)), n);
    return g.map((x, i) => (x === null || l[i] === null ? null : l[i] === 0 ? 100 : 100 - 100 / (1 + x / l[i]))); }
  function macd(c, f, s, sig) { const cl = c.map((b) => b.close); const a = ema(cl, f), b = ema(cl, s); const m = a.map((x, i) => x - b[i]); const sg = ema(m, sig); return { m, sg, h: m.map((x, i) => x - sg[i]) }; }
  function bollinger(c, n, k) { const cl = c.map((b) => b.close); const mid = sma(cl, n);
    return { mid, up: mid.map((m, i) => (m === null ? null : m + k * Math.sqrt(cl.slice(i - n + 1, i + 1).reduce((a, x) => a + (x - m) ** 2, 0) / n))), lo: mid.map((m, i) => (m === null ? null : m - k * Math.sqrt(cl.slice(i - n + 1, i + 1).reduce((a, x) => a + (x - m) ** 2, 0) / n))) }; }
  function vwap(c) { let day = "", pv = 0, vv = 0, tp = 0, n = 0; return c.map((b) => { const d = new Date(b.time * 1000).toISOString().slice(0, 10); // times are already IST-shifted
    if (d !== day) { day = d; pv = 0; vv = 0; tp = 0; n = 0; } const t = (b.high + b.low + b.close) / 3; pv += t * (b.volume || 0); vv += b.volume || 0; tp += t; n++; return vv > 0 ? pv / vv : tp / n; }); }
  function supertrend(c, n, m) { const atr = rma(trueRange(c), n); let up = 0, dn = 0, dir = 1; return c.map((b, i) => { if (atr[i] === null) return null;
    const hl2 = (b.high + b.low) / 2, bu = hl2 + m * atr[i], bl = hl2 - m * atr[i]; const pc = i ? c[i - 1].close : b.close;
    up = i && pc <= up ? Math.min(bu, up || bu) : bu; dn = i && pc >= dn ? Math.max(bl, dn || bl) : bl;
    if (b.close > up) dir = 1; else if (b.close < dn) dir = -1; return { v: dir > 0 ? dn : up, dir }; }); }
  function heikin(c) { const out = []; c.forEach((b, i) => { const close = (b.open + b.high + b.low + b.close) / 4; const open = i ? (out[i - 1].open + out[i - 1].close) / 2 : (b.open + b.close) / 2;
    out.push({ time: b.time, open, close, high: Math.max(b.high, open, close), low: Math.min(b.low, open, close), volume: b.volume }); }); return out; }

  const CATALOG = {
    ema: { name: "EMA", params: { period: 20 }, overlay: true, color: "--c1" },
    sma: { name: "SMA", params: { period: 50 }, overlay: true, color: "--c2" },
    vwap: { name: "VWAP", params: {}, overlay: true, color: "--c3" },
    bb: { name: "Bollinger Bands", params: { period: 20, mult: 2 }, overlay: true, color: "--c4" },
    st: { name: "Supertrend", params: { period: 10, mult: 3 }, overlay: true },
    vol: { name: "Volume", params: {}, overlay: true },
    rsi: { name: "RSI", params: { period: 14 }, overlay: false, color: "--c1" },
    macd: { name: "MACD", params: { fast: 12, slow: 26, signal: 9 }, overlay: false },
    atr: { name: "ATR", params: { period: 14 }, overlay: false, color: "--c2" },
  };

  // ------------------------------------------------------------ chart object
  function create(root, opts = {}) {
    const el = (s) => root.querySelector(s);
    const host = el(".cc-main"), panesHost = el(".cc-panes"), overlay = el(".cc-draw"), legend = el(".cc-legend");
    const state = { raw: [], bars: [], type: store.get("type", "candles"), tf: store.get("tf", "5m"), inds: store.get("inds", [{ id: "ema", params: { period: 9 } }, { id: "ema", params: { period: 21 } }, { id: "vwap", params: {} }, { id: "vol", params: {} }]),
                    tool: "cursor", drawings: [], draft: null, symbol: "", magnet: store.get("magnet", true), levels: [], series: [], panes: [], markers: [] };
    const themeOpts = () => ({
      layout: { background: { type: "solid", color: css("--chart-bg") }, textColor: css("--muted"), fontFamily: css("--f-body"), fontSize: 11 },
      grid: { vertLines: { color: css("--grid") }, horzLines: { color: css("--grid") } },
      rightPriceScale: { borderColor: css("--line") }, timeScale: { borderColor: css("--line"), timeVisible: true, secondsVisible: false, rightOffset: 6 },
      crosshair: { mode: state.magnet ? LWC.CrosshairMode.Magnet : LWC.CrosshairMode.Normal,
                   vertLine: { color: css("--muted"), labelBackgroundColor: css("--accent") }, horzLine: { color: css("--muted"), labelBackgroundColor: css("--accent") } },
    });
    const chart = LWC.createChart(host, { ...themeOpts(), autoSize: true, handleScroll: true, handleScale: true });
    let main = null;

    function buildMain() {
      if (main) chart.removeSeries(main);
      const up = css("--up"), dn = css("--dn");
      if (state.type === "line") main = chart.addLineSeries({ color: css("--accent"), lineWidth: 2 });
      else if (state.type === "area") main = chart.addAreaSeries({ lineColor: css("--accent"), topColor: css("--accent-soft"), bottomColor: "rgba(0,0,0,0)", lineWidth: 2 });
      else if (state.type === "bars") main = chart.addBarSeries({ upColor: up, downColor: dn });
      else main = chart.addCandlestickSeries({ upColor: state.type === "hollow" ? "rgba(0,0,0,0)" : up, downColor: dn, borderUpColor: up, borderDownColor: dn, wickUpColor: up, wickDownColor: dn });
      state.levels.forEach((l) => (l.line = null));
    }
    buildMain();

    function mainData() {
      const bars = state.type === "heikin" ? heikin(state.raw) : state.raw;
      state.bars = bars;
      return state.type === "line" || state.type === "area" ? bars.map((b) => ({ time: b.time, value: b.close })) : bars.map((b) => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close }));
    }

    // ---- indicators
    function clearIndicators() { state.series.forEach((s) => { try { chart.removeSeries(s); } catch { /* removed */ } }); state.series = [];
      state.panes.forEach((p) => p.chart.remove()); state.panes = []; panesHost.innerHTML = ""; }
    const line = (target, color, width = 1.5, extra = {}) => { const s = target.addLineSeries({ color, lineWidth: width, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, ...extra }); return s; };
    const pts = (vals) => vals.map((v, i) => (v === null || v === undefined || isNaN(v) ? { time: state.raw[i].time } : { time: state.raw[i].time, value: v }));
    function addPane(title) {
      const wrap = document.createElement("div"); wrap.className = "cc-pane";
      wrap.innerHTML = `<div class="cc-pane-title">${title}</div><div class="cc-pane-chart"></div>`; panesHost.appendChild(wrap);
      const pc = LWC.createChart(wrap.querySelector(".cc-pane-chart"), { ...themeOpts(), autoSize: true, timeScale: { ...themeOpts().timeScale, visible: false }, rightPriceScale: { borderColor: css("--line"), minimumWidth: 70 } });
      const p = { chart: pc, series: [] }; state.panes.push(p); return p;
    }
    function renderIndicators() {
      clearIndicators(); legendInds.length = 0;
      const c = state.raw; if (!c.length) return;
      const cl = c.map((b) => b.close);
      state.inds.forEach((ind, idx) => {
        const def = CATALOG[ind.id]; if (!def) return; const p = { ...def.params, ...ind.params };
        const col = css(def.color || "--c1");
        if (ind.id === "ema" || ind.id === "sma") { const v = ind.id === "ema" ? ema(cl, p.period) : sma(cl, p.period); const s = line(chart, idx % 2 ? css("--c2") : col); s.setData(pts(v)); state.series.push(s); legendInds.push({ label: `${def.name} ${p.period}`, vals: v, color: idx % 2 ? css("--c2") : col }); }
        if (ind.id === "vwap") { const v = vwap(c); const s = line(chart, col, 1.5, { lineStyle: LWC.LineStyle.Dashed }); s.setData(pts(v)); state.series.push(s); legendInds.push({ label: "VWAP", vals: v, color: col }); }
        if (ind.id === "bb") { const b = bollinger(c, p.period, p.mult); [b.up, b.mid, b.lo].forEach((v, j) => { const s = line(chart, col, j === 1 ? 1 : 1.2, { lineStyle: j === 1 ? LWC.LineStyle.Dotted : LWC.LineStyle.Solid }); s.setData(pts(v)); state.series.push(s); });
          legendInds.push({ label: `BB ${p.period},${p.mult}`, vals: b.mid, color: col }); }
        if (ind.id === "st") { const st = supertrend(c, p.period, p.mult); const s = chart.addLineSeries({ lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
          s.setData(st.map((x, i) => (x ? { time: c[i].time, value: x.v, color: x.dir > 0 ? css("--up") : css("--dn") } : { time: c[i].time }))); state.series.push(s);
          legendInds.push({ label: `Supertrend ${p.period},${p.mult}`, vals: st.map((x) => (x ? x.v : null)), color: css("--muted") }); }
        if (ind.id === "vol") { const s = chart.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false });
          chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
          s.setData(c.map((b) => ({ time: b.time, value: b.volume || 0, color: b.close >= b.open ? css("--up-vol") : css("--dn-vol") }))); state.series.push(s); }
        if (ind.id === "rsi") { const pane = addPane(`RSI ${p.period}`); const v = rsi(c, p.period); const s = line(pane.chart, col, 1.5, { lastValueVisible: true }); s.setData(pts(v));
          s.createPriceLine({ price: 70, color: css("--line-strong"), lineStyle: LWC.LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false });
          s.createPriceLine({ price: 30, color: css("--line-strong"), lineStyle: LWC.LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false }); pane.series.push(s); pane.main = s; }
        if (ind.id === "atr") { const pane = addPane(`ATR ${p.period}`); const v = rma(trueRange(c), p.period); const s = line(pane.chart, col, 1.5, { lastValueVisible: true }); s.setData(pts(v)); pane.series.push(s); pane.main = s; }
        if (ind.id === "macd") { const pane = addPane(`MACD ${p.fast},${p.slow},${p.signal}`); const m = macd(c, p.fast, p.slow, p.signal);
          const h = pane.chart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false }); h.setData(m.h.map((v, i) => ({ time: c[i].time, value: v, color: v >= 0 ? css("--up-vol") : css("--dn-vol") })));
          const a = line(pane.chart, css("--c1")); a.setData(pts(m.m)); const b = line(pane.chart, css("--c4")); b.setData(pts(m.sg)); pane.series.push(h, a, b); pane.main = a; }
      });
      syncPanes(); renderIndicatorChips();
    }
    // keep panes in lock-step with the main chart (scroll, zoom, crosshair)
    let syncing = false;
    function syncPanes() {
      const r = chart.timeScale().getVisibleLogicalRange();
      state.panes.forEach((p) => { if (r) p.chart.timeScale().setVisibleLogicalRange(r);
        p.chart.timeScale().subscribeVisibleLogicalRangeChange((lr) => { if (syncing || !lr) return; syncing = true; chart.timeScale().setVisibleLogicalRange(lr); state.panes.forEach((q) => q !== p && q.chart.timeScale().setVisibleLogicalRange(lr)); syncing = false; });
        p.chart.subscribeCrosshairMove((prm) => { if (syncing) return; syncing = true; if (prm.time) chart.setCrosshairPosition(NaN, prm.time, main); else chart.clearCrosshairPosition(); syncing = false; }); });
    }
    chart.timeScale().subscribeVisibleLogicalRangeChange((lr) => { if (!syncing && lr) { syncing = true; state.panes.forEach((p) => p.chart.timeScale().setVisibleLogicalRange(lr)); syncing = false; } redrawDrawings(); });

    // ---- legend (OHLC + indicator values under the crosshair)
    const legendInds = [];
    const f2 = (v) => (v === null || v === undefined || isNaN(v) ? "—" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    function showLegend(i) {
      const b = state.bars[i]; if (!b) { legend.innerHTML = ""; return; }
      const prev = state.bars[i - 1]; const ch = prev ? ((b.close - prev.close) / prev.close) * 100 : 0;
      const cls = b.close >= b.open ? "up" : "dn";
      legend.innerHTML = `<div class="cc-l1"><b>${state.symbol}</b><span class="muted">${state.tf}</span>` +
        `<span>O <i class="${cls}">${f2(b.open)}</i></span><span>H <i class="${cls}">${f2(b.high)}</i></span><span>L <i class="${cls}">${f2(b.low)}</i></span><span>C <i class="${cls}">${f2(b.close)}</i></span>` +
        `<span class="${ch >= 0 ? "up" : "dn"}">${ch >= 0 ? "+" : ""}${ch.toFixed(2)}%</span>${b.volume ? `<span class="muted">Vol ${Intl.NumberFormat("en-IN", { notation: "compact" }).format(b.volume)}</span>` : ""}</div>` +
        `<div class="cc-l2">${legendInds.map((x) => `<span style="color:${x.color}">${x.label} ${f2(x.vals[i])}</span>`).join("")}</div>`;
    }
    chart.subscribeCrosshairMove((prm) => {
      if (!state.raw.length) return;
      let i = state.bars.length - 1;
      if (prm.time) { const k = state.bars.findIndex((b) => b.time === prm.time); if (k >= 0) i = k; }
      showLegend(i);
      if (!syncing) { syncing = true; state.panes.forEach((p) => { if (prm.time && p.main) p.chart.setCrosshairPosition(NaN, prm.time, p.main); else p.chart.clearCrosshairPosition(); }); syncing = false; }
      if (state.draft && state.tool !== "cursor") { const pt = toPoint(prm.point); if (pt) { state.draft.b = pt; redrawDrawings(); } }
    });

    // ---- data
    function setData(candles, symbol, tf) {
      // compare with what was last *loaded*: the timeframe buttons update state.tf before the new candles arrive
      const fresh = symbol !== state.loadedSym || (tf || state.tf) !== state.loadedTf;
      state.symbol = symbol; state.tf = tf || state.tf; state.loadedSym = symbol; state.loadedTf = state.tf;
      state.raw = (candles || []).map((c) => ({ time: Math.floor(new Date(c.timestamp).getTime() / 1000) + IST_SHIFT, open: +c.open, high: +c.high, low: +c.low, close: +c.close, volume: +(c.volume || 0) }))
        .filter((b) => isFinite(b.open)).sort((a, b) => a.time - b.time).filter((b, i, a) => !i || b.time !== a[i - 1].time);
      main.setData(mainData()); renderIndicators(); applyLevels(); applyMarkers();
      if (fresh) { state.drawings = store.get("draw_" + symbol, []); chart.timeScale().fitContent(); const n = state.raw.length; if (n > 160) chart.timeScale().setVisibleLogicalRange({ from: n - 160, to: n + 6 }); }
      showLegend(state.bars.length - 1); redrawDrawings();
      root.classList.toggle("cc-empty", !state.raw.length);
    }
    function tick(ltp) {   // live price into the forming bar
      const b = state.raw[state.raw.length - 1]; if (!b || !(ltp > 0)) return;
      // Only a bar that is still forming may move: after the close (or before Upstox publishes the session) the last
      // bar is history, and writing today's price into it would draw a fake candle.
      if (Date.now() / 1000 + IST_SHIFT - b.time > barStep() * 2) return;
      b.close = ltp; b.high = Math.max(b.high, ltp); b.low = Math.min(b.low, ltp);
      const d = mainData(); main.update(d[d.length - 1]); showLegend(state.bars.length - 1);
    }
    function setLevels(levels) { state.levels.forEach((l) => l.line && main.removePriceLine(l.line)); state.levels = levels || []; applyLevels(); }
    function applyLevels() { state.levels.forEach((l) => { if (l.line) { try { main.removePriceLine(l.line); } catch { /* gone */ } }
      l.line = l.price ? main.createPriceLine({ price: l.price, color: css(l.color), lineWidth: 1, lineStyle: LWC.LineStyle.Dashed, axisLabelVisible: true, title: l.title }) : null; }); }
    function setMarkers(m) { state.markers = m || []; applyMarkers(); }
    function applyMarkers() { if (!state.raw.length) return; const t0 = state.raw[0].time, t1 = state.raw[state.raw.length - 1].time;
      main.setMarkers(state.markers.map((m) => ({ ...m, time: nearestTime(Math.floor(new Date(m.at).getTime() / 1000) + IST_SHIFT) })).filter((m) => m.time >= t0 && m.time <= t1).sort((a, b) => a.time - b.time)); }
    const nearestTime = (t) => { let best = state.raw[0].time; for (const b of state.raw) { if (b.time <= t) best = b.time; else break; } return best; };

    // ---- drawings (stored per symbol as time/price so they survive reloads)
    const ctx = overlay.getContext("2d");
    // Drawings are stored as (time, price). Times are mapped through a fractional bar index so a point keeps its place
    // between bars, to the right of the last bar, and after switching timeframe (timeToCoordinate only knows exact bars).
    const barStep = () => { const r = state.raw, n = r.length; return n > 1 ? r[n - 1].time - r[n - 2].time : 60; };
    function timeToLogical(t) {
      const r = state.raw; if (!r.length) return null; const n = r.length;
      if (t <= r[0].time) return (t - r[0].time) / barStep();
      if (t >= r[n - 1].time) return n - 1 + (t - r[n - 1].time) / barStep();
      let lo = 0, hi = n - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (r[m].time <= t) lo = m; else hi = m; }
      return lo + (t - r[lo].time) / ((r[hi].time - r[lo].time) || 1);
    }
    function logicalToTime(l) {
      const r = state.raw, n = r.length; if (!n) return null;
      if (l <= 0) return r[0].time + l * barStep();
      if (l >= n - 1) return r[n - 1].time + (l - (n - 1)) * barStep();
      const i = Math.floor(l); return r[i].time + (l - i) * (r[i + 1].time - r[i].time);
    }
    // Lightweight Charts only converts whole bar indices (logicalToCoordinate returns 0 for 12.5, coordinateToLogical
    // rounds), so fractional positions are interpolated between neighbouring bars here.
    function logicalToX(l) {
      const ts = chart.timeScale(), i = Math.floor(l), f = l - i, x0 = ts.logicalToCoordinate(i);
      if (x0 === null) return null; if (!f) return x0; const x1 = ts.logicalToCoordinate(i + 1); return x1 === null ? x0 : x0 + f * (x1 - x0);
    }
    function xToLogical(x) {
      const ts = chart.timeScale(), i = ts.coordinateToLogical(x); if (i === null) return null;
      const x0 = ts.logicalToCoordinate(i), x1 = ts.logicalToCoordinate(i + 1); if (x0 === null || x1 === null || x1 === x0) return i;
      return i + (x - x0) / (x1 - x0);
    }
    function toPoint(p) { if (!p) return null; const l = xToLogical(p.x); const pr = main.coordinateToPrice(p.y);
      if (l === null || pr === null) return null; return { t: logicalToTime(l), p: pr }; }
    const X = (t) => { const l = timeToLogical(t); return l === null ? null : logicalToX(l); }, Y = (p) => main.priceToCoordinate(p);
    // Coalesced and deferred one frame: after setData/zoom the chart applies its new scale on the next frame, and
    // drawing in the same tick would map every point with the previous timeframe's scale.
    let drawQueued = false;
    function redrawDrawings() { if (drawQueued) return; drawQueued = true; requestAnimationFrame(() => requestAnimationFrame(() => { drawQueued = false; drawNow(); })); }
    function drawNow() {
      const r = overlay.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      if (overlay.width !== Math.round(r.width * dpr)) { overlay.width = Math.round(r.width * dpr); overlay.height = Math.round(r.height * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, r.width, r.height);
      const all = state.draft && state.draft.b ? [...state.drawings, state.draft] : state.drawings;
      all.forEach((d) => drawOne(d, r));
    }
    function drawOne(d, r) {
      const col = css("--draw"); ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 1.5; ctx.font = `11px ${css("--f-body")}`; ctx.setLineDash([]);
      const xa = X(d.a.t), ya = Y(d.a.p); if (ya === null) return;
      if (d.type === "hline") { ctx.beginPath(); ctx.moveTo(0, ya); ctx.lineTo(r.width, ya); ctx.stroke(); ctx.fillText(f2(d.a.p), 6, ya - 4); return; }
      if (d.type === "vline") { if (xa === null) return; ctx.beginPath(); ctx.moveTo(xa, 0); ctx.lineTo(xa, r.height); ctx.stroke(); return; }
      if (!d.b) return; const xb = X(d.b.t), yb = Y(d.b.p); if (xa === null || xb === null || yb === null) return;
      if (d.type === "trend" || d.type === "ray") { let x2 = xb, y2 = yb; if (d.type === "ray" && xb !== xa) { x2 = r.width; y2 = ya + (yb - ya) * ((r.width - xa) / (xb - xa)); }
        ctx.beginPath(); ctx.moveTo(xa, ya); ctx.lineTo(x2, y2); ctx.stroke(); [[xa, ya], [xb, yb]].forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 2.5, 0, 7); ctx.fill(); }); }
      if (d.type === "rect") { ctx.globalAlpha = 0.12; ctx.fillRect(Math.min(xa, xb), Math.min(ya, yb), Math.abs(xb - xa), Math.abs(yb - ya)); ctx.globalAlpha = 1; ctx.strokeRect(Math.min(xa, xb), Math.min(ya, yb), Math.abs(xb - xa), Math.abs(yb - ya)); }
      if (d.type === "fib") { const lv = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1]; const x0 = Math.min(xa, xb), x1 = Math.max(xa, xb, x0 + 60);
        lv.forEach((k) => { const p = d.a.p + (d.b.p - d.a.p) * k, y = Y(p); if (y === null) return; ctx.globalAlpha = k === 0 || k === 1 ? 1 : 0.7; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke(); ctx.fillText(`${(k * 100).toFixed(1)}%  ${f2(p)}`, x1 + 4, y + 3); }); ctx.globalAlpha = 1; }
      if (d.type === "measure") { ctx.setLineDash([4, 3]); ctx.strokeRect(Math.min(xa, xb), Math.min(ya, yb), Math.abs(xb - xa), Math.abs(yb - ya)); ctx.setLineDash([]);
        const dp = d.b.p - d.a.p, pct = (dp / d.a.p) * 100, bars = Math.round(Math.abs((d.b.t - d.a.t) / (state.raw[1] ? state.raw[1].time - state.raw[0].time : 60)));
        const txt = `${dp >= 0 ? "+" : ""}${f2(dp)} (${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%) · ${bars} bars`; const tw = ctx.measureText(txt).width + 12;
        ctx.fillStyle = dp >= 0 ? css("--up") : css("--dn"); ctx.fillRect(xb + 6, yb - 10, tw, 20); ctx.fillStyle = "#fff"; ctx.fillText(txt, xb + 12, yb + 4); }
    }
    function nearDrawing(px, py) {
      const near = (x1, y1, x2, y2) => { const L = Math.hypot(x2 - x1, y2 - y1) || 1; const t = Math.max(0, Math.min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (L * L))); return Math.hypot(px - (x1 + t * (x2 - x1)), py - (y1 + t * (y2 - y1))) < 6; };
      return state.drawings.findIndex((d) => { const xa = X(d.a.t), ya = Y(d.a.p); if (d.type === "hline") return Math.abs(py - ya) < 6; if (d.type === "vline") return Math.abs(px - xa) < 6;
        if (!d.b) return false; const xb = X(d.b.t), yb = Y(d.b.p); if ([xa, ya, xb, yb].some((v) => v === null)) return false;
        if (d.type === "rect" || d.type === "fib" || d.type === "measure") return px >= Math.min(xa, xb) - 4 && px <= Math.max(xa, xb) + 60 && py >= Math.min(ya, yb) - 4 && py <= Math.max(ya, yb) + 4;
        return near(xa, ya, xb, yb); });
    }
    function setTool(t) {
      state.tool = t; state.draft = null; overlay.classList.toggle("active", t !== "cursor");
      root.querySelectorAll("[data-tool]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tool === t)));
      redrawDrawings();
    }
    // Pointer events cover mouse, pen and touch: press-drag-release draws in one gesture; tap, then tap again also works.
    const local = (e) => { const r = overlay.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
    let downAt = null;
    function finishDraft(pt) {
      if (!state.draft) return; if (pt) state.draft.b = pt; const done = state.draft; delete done.pending; state.drawings.push(done);
      if (done.type === "measure") setTimeout(() => { const k = state.drawings.indexOf(done); if (k >= 0) { state.drawings.splice(k, 1); redrawDrawings(); } }, 6000); // measure is temporary
      else persist();
      state.draft = null; setTool("cursor");
    }
    overlay.addEventListener("pointerdown", (e) => {
      if (state.tool === "cursor") return; e.preventDefault();
      const p = local(e);
      if (state.tool === "erase") { const k = nearDrawing(p.x, p.y); if (k >= 0) { state.drawings.splice(k, 1); persist(); redrawDrawings(); } return; }
      const pt = toPoint(p); if (!pt) return;
      if (state.tool === "hline" || state.tool === "vline") { state.drawings.push({ type: state.tool, a: pt }); persist(); setTool("cursor"); return; }
      if (state.draft && state.draft.pending) { finishDraft(pt); return; }   // second tap
      try { overlay.setPointerCapture(e.pointerId); } catch { /* not capturable */ }
      downAt = p; state.draft = { type: state.tool, a: pt, b: pt }; redrawDrawings();
    });
    overlay.addEventListener("pointermove", (e) => { if (!state.draft) return; const pt = toPoint(local(e)); if (pt) { state.draft.b = pt; redrawDrawings(); } });
    overlay.addEventListener("pointerup", (e) => {
      if (!state.draft || !downAt) return; const p = local(e); const moved = Math.hypot(p.x - downAt.x, p.y - downAt.y) > 8; downAt = null;
      if (moved) finishDraft(toPoint(p)); else state.draft.pending = true;   // a tap: wait for the second point
    });
    const persist = () => store.set("draw_" + state.symbol, state.drawings.filter((d) => d.type !== "measure"));
    new ResizeObserver(() => redrawDrawings()).observe(host);

    // ---- indicator chips + dialog
    function renderIndicatorChips() {
      const box = el(".cc-chips"); if (!box) return;
      box.innerHTML = state.inds.map((ind, i) => { const def = CATALOG[ind.id] || {}; const p = Object.values({ ...def.params, ...ind.params }).join(",");
        return `<span class="chip">${def.name}${p ? ` (${p})` : ""}<button type="button" data-rm-ind="${i}" aria-label="Remove ${def.name}">×</button></span>`; }).join("");
    }
    root.addEventListener("click", (e) => {
      const rm = e.target.closest("[data-rm-ind]"); if (rm) { state.inds.splice(+rm.dataset.rmInd, 1); store.set("inds", state.inds); renderIndicators(); return; }
      const add = e.target.closest("[data-add-ind]"); if (add) { const id = add.dataset.addInd; const params = {};
        add.closest(".ind-row").querySelectorAll("input[data-p]").forEach((inp) => (params[inp.dataset.p] = +inp.value));
        state.inds.push({ id, params }); store.set("inds", state.inds); renderIndicators(); el(".cc-ind-pop").hidden = true; return; }
      const tool = e.target.closest("[data-tool]"); if (tool) { setTool(state.tool === tool.dataset.tool ? "cursor" : tool.dataset.tool); return; }
      const ty = e.target.closest("[data-ctype]"); if (ty) { state.type = ty.dataset.ctype; store.set("type", state.type); root.querySelectorAll("[data-ctype]").forEach((b) => b.setAttribute("aria-pressed", String(b === ty))); buildMain(); main.setData(mainData()); applyLevels(); applyMarkers(); el(".cc-type-pop").hidden = true; el(".cc-type-btn").innerHTML = ty.innerHTML; return; }
    });
    function buildIndicatorDialog() {
      const pop = el(".cc-ind-pop");
      pop.innerHTML = `<div class="pop-head">Indicators<button type="button" class="x" data-close-pop aria-label="Close">×</button></div>` + Object.entries(CATALOG).map(([id, d]) =>
        `<div class="ind-row"><div><b>${d.name}</b><span class="muted">${d.overlay ? "on price" : "own pane"}</span></div><div class="ind-params">${Object.entries(d.params).map(([k, v]) => `<label>${k}<input type="number" data-p="${k}" value="${v}" step="${k === "mult" ? 0.1 : 1}" min="1"></label>`).join("")}</div><button type="button" class="btn tiny" data-add-ind="${id}">Add</button></div>`).join("");
      pop.addEventListener("click", (e) => { if (e.target.closest("[data-close-pop]")) pop.hidden = true; });
    }
    buildIndicatorDialog();

    // ---- toolbar actions
    el(".cc-ind-btn").addEventListener("click", () => { const p = el(".cc-ind-pop"); p.hidden = !p.hidden; el(".cc-type-pop").hidden = true; });
    el(".cc-type-btn").addEventListener("click", () => { const p = el(".cc-type-pop"); p.hidden = !p.hidden; el(".cc-ind-pop").hidden = true; });
    const startType = root.querySelector(`[data-ctype="${state.type}"]`); if (startType) { startType.setAttribute("aria-pressed", "true"); el(".cc-type-btn").innerHTML = startType.innerHTML; }
    el(".cc-magnet").setAttribute("aria-pressed", String(state.magnet));
    el(".cc-magnet").addEventListener("click", (e) => { state.magnet = !state.magnet; store.set("magnet", state.magnet); e.currentTarget.setAttribute("aria-pressed", String(state.magnet)); chart.applyOptions({ crosshair: { mode: state.magnet ? LWC.CrosshairMode.Magnet : LWC.CrosshairMode.Normal } }); });
    el(".cc-clear").addEventListener("click", () => { state.drawings = []; persist(); redrawDrawings(); });
    el(".cc-fit").addEventListener("click", () => { chart.timeScale().fitContent(); chart.priceScale("right").applyOptions({ autoScale: true }); });
    el(".cc-shot").addEventListener("click", () => { const c = chart.takeScreenshot(); const g = c.getContext("2d"); g.drawImage(overlay, 0, 0, c.width, c.height);
      const a = document.createElement("a"); a.href = c.toDataURL("image/png"); a.download = `${state.symbol}_${state.tf}_${new Date().toISOString().slice(0, 16).replace(/[:T]/g, "")}.png`; a.click(); });
    el(".cc-full").addEventListener("click", () => { if (document.fullscreenElement) document.exitFullscreen(); else root.requestFullscreen?.().catch(() => root.classList.toggle("cc-pseudo-full")); });
    document.addEventListener("fullscreenchange", () => { root.classList.toggle("cc-is-full", document.fullscreenElement === root); setTimeout(redrawDrawings, 60); });
    root.querySelectorAll("[data-tf]").forEach((b) => { b.setAttribute("aria-pressed", String(b.dataset.tf === state.tf)); b.addEventListener("click", () => { state.tf = b.dataset.tf; store.set("tf", state.tf); root.querySelectorAll("[data-tf]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); opts.onTimeframe && opts.onTimeframe(state.tf); }); });
    root.addEventListener("keydown", (e) => { if (e.key === "Escape") setTool("cursor"); if ((e.key === "Delete" || e.key === "Backspace") && state.tool === "erase") setTool("cursor"); });

    function setTheme() { chart.applyOptions(themeOpts()); state.panes.forEach((p) => p.chart.applyOptions({ ...themeOpts(), timeScale: { visible: false } })); buildMain(); main.setData(mainData()); renderIndicators(); applyLevels(); applyMarkers(); redrawDrawings(); }
    const probe = (t) => ({ logical: timeToLogical(t), x: X(t), visible: chart.timeScale().getVisibleLogicalRange(), bars: state.raw.length });
    return { setData, tick, setLevels, setMarkers, setTheme, probe, get timeframe() { return state.tf; }, get symbol() { return state.symbol; } };
  }
  window.CAChart = { create };
})();
