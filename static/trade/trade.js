/* CA Trader trading screen. Every number on screen comes from the backend (Upstox data or values computed from it)
   and carries its age; nothing is invented client-side. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));
  const fmt = (v, d = 2) => (num(v) === null ? "—" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const sgn = (v, d = 1) => (num(v) === null ? "—" : (Number(v) > 0 ? "+" : "") + Number(v).toFixed(d));
  const cls = (v) => (num(v) === null ? "" : Number(v) > 0 ? "up" : Number(v) < 0 ? "dn" : "");
  const store = { get(k, d) { try { const v = localStorage.getItem("cat_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
                  set(k, v) { try { localStorage.setItem("cat_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } } };

  const S = { symbol: store.get("symbol", "NIFTY"), ws: "trade", watch: [], watchlists: [], wlId: null, quotes: {}, reco: null, chain: null,
              updated: {}, timers: [], ws_conn: null, user: null };

  // ---------------- network ----------------
  async function api(path, opts = {}) {
    const init = { credentials: "include", headers: { "Content-Type": "application/json" }, ...opts };
    if (init.body && typeof init.body !== "string") init.body = JSON.stringify(init.body);
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), opts.timeout || 20000); init.signal = ctl.signal;
    try {
      const r = await fetch(path, init);
      if (r.status === 401) { location.href = "/login"; throw new Error("Signed out"); }
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((data.detail && (data.detail.message || data.detail)) || (data.error && (data.error.message || data.error)) || `HTTP ${r.status}`);
      return data;
    } finally { clearTimeout(t); }
  }
  function toast(msg) { const el = $("toast"); el.textContent = msg; el.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), 3500); }
  function mark(key) { S.updated[key] = Date.now(); renderAges(); }
  function renderAges() {
    const now = Date.now();
    document.querySelectorAll("[data-age]").forEach((el) => {
      const t = S.updated[el.dataset.age];
      if (!t) { el.textContent = "—"; return; }
      const s = Math.round((now - t) / 1000);
      el.textContent = s < 60 ? `updated ${s}s ago` : `updated ${Math.round(s / 60)}m ago`;
      el.classList.toggle("stale", s > 30 && s <= 120); el.classList.toggle("dead", s > 120);
    });
    const q = S.updated.quotes; const f = $("feedState");
    if (!q) return;
    const age = (now - q) / 1000;
    f.classList.toggle("live", age < 10); f.classList.toggle("stale", age >= 10 && age < 60); f.classList.toggle("down", age >= 60);
    $("feedText").textContent = `Upstox · quotes ${Math.round(age)}s ago`;
  }
  function every(ms, fn) { fn(); S.timers.push(setInterval(() => { if (!document.hidden) fn(); }, ms)); }

  // ---------------- instruments strip ----------------
  async function loadWatchlists() {
    try {
      const d = await api("/api/watchlists");
      S.watchlists = d.items || [];
      const sel = store.get("wl", null);
      const g = S.watchlists.find((x) => x.id === sel) || S.watchlists[0];
      S.wlId = g ? g.id : null;
      S.watch = (g && g.items ? g.items.map((i) => (i.symbol || "").toUpperCase()).filter(Boolean) : []);
    } catch (e) { S.watch = []; }
    if (!S.watch.length) S.watch = [S.symbol];
    if (!S.watch.includes(S.symbol)) S.symbol = S.watch[0];
    renderTickers();
  }
  function renderTickers() {
    $("tickers").innerHTML = S.watch.map((s, i) => {
      const q = S.quotes[s] || {};
      return `<button type="button" class="tk" data-sym="${esc(s)}" aria-pressed="${s === S.symbol}"><span class="n">${i < 9 ? i + 1 : ""}</span><b>${esc(s)}</b>` +
        `<span class="px">${fmt(q.ltp)}</span><span class="${cls(q.change_pct)}">${num(q.change_pct) === null ? "" : sgn(q.change_pct, 2) + "%"}</span></button>`;
    }).join("");
  }
  $("tickers").addEventListener("click", (e) => { const b = e.target.closest(".tk"); if (b) selectSymbol(b.dataset.sym); });
  async function loadQuotes() {
    const syms = [...new Set([...S.watch, S.symbol])];
    if (!syms.length) return;
    try {
      const d = await api(`/api/market/quotes?instruments=${encodeURIComponent(syms.join(","))}`);
      (d.items || []).forEach((q) => {
        const k = String(q.instrument || q.symbol || "").toUpperCase();
        if (k) S.quotes[k] = q;
      });
      mark("quotes"); renderTickers();
      if (S.ws === "scan") renderWatchRows();
    } catch (e) { /* feed indicator shows staleness */ }
  }
  function selectSymbol(sym) {
    if (!sym) return;
    S.symbol = sym.toUpperCase(); store.set("symbol", S.symbol);
    renderTickers();
    S.reco = null; S.chain = null;
    refreshWorkspace(true);
  }

  // ---------------- TRADE ----------------
  async function loadReco() {
    const sym = S.symbol;
    try {
      const r = await api(`/api/recommendations/${encodeURIComponent(sym)}?timeframe=5m`, { timeout: 30000 });
      if (sym !== S.symbol) return;
      S.reco = r; mark("reco"); renderSignal(); renderWhy(); drawChart();
    } catch (e) { $("sigSide").textContent = "Unavailable"; $("sigRationale").textContent = e.message; }
  }
  function modelOf(r) { return (r && r.signal_model) || {}; }
  function renderSignal() {
    const r = S.reco || {}; const m = modelOf(r);
    const dec = m.available && (m.decision === "BUY" || m.decision === "SELL") ? m.decision : null;
    const opt = r.recommended_option || {};
    const isIdx = /NIFTY|SENSEX|BANKEX/.test(S.symbol);
    let head = "NO TRADE", c = "";
    if (dec === "BUY") { head = isIdx ? "BUY CALL" : "BUY"; c = "up"; }
    else if (dec === "SELL") { head = isIdx ? "BUY PUT" : "SELL"; c = "dn"; }
    else if (!m.available) { head = "NO DATA"; }
    const side = $("sigSide"); side.textContent = head; side.className = "sig-side " + c;
    const contract = (dec && (dec === "BUY" ? r.call_option : r.put_option)) || opt;
    $("sigSym").textContent = dec ? (contract.display || contract.symbol || r.display_symbol || S.symbol) : `${S.symbol} · score inside ±${fmt(m.gate, 0)}`;
    const entry = num(contract.entry) ?? num(r.entry), sl = num(contract.stop_loss) ?? num(r.stop_loss), tgt = num(contract.target) ?? num(r.target);
    const ltp = num(contract.cmp) ?? num(contract.ltp) ?? num(r.cmp);
    const lot = num(contract.lot_size) ?? num((r.instrument || {}).lot_size);
    const rr = entry && sl && tgt && entry !== sl ? Math.abs(tgt - entry) / Math.abs(entry - sl) : null;
    $("levels").innerHTML = dec ? [
      ["Entry", fmt(entry)], ["LTP (Upstox)", fmt(ltp)], ["Stop loss", `<span class="dn">${fmt(sl)}</span>`],
      ["Target", `<span class="up">${fmt(tgt)}</span>`], ["Risk : reward", rr ? "1 : " + rr.toFixed(2) : "—"], ["Lot size (Upstox)", fmt(lot, 0)],
    ].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("") : `<dt>Why no trade</dt><dd>${esc(m.available ? `${m.agreeing}/${m.factors_used} factors agree, score ${sgn(m.score)}` : (m.reason || "No data"))}</dd>`;
    const lad = $("ladder");
    if (dec && entry && sl && tgt) {
      const lo = Math.min(sl, entry, ltp ?? entry), hi = Math.max(tgt, entry, ltp ?? entry), pad = (hi - lo) * 0.08 || 1;
      const y = (v) => `${(1 - (v - (lo - pad)) / (hi - lo + 2 * pad)) * 100}%`;
      lad.innerHTML = `<div style="top:${y(tgt)};border-color:var(--up);color:var(--up)">Target ${fmt(tgt)}</div>` +
        `<div style="top:${y(entry)};border-color:var(--muted);color:var(--muted)">Entry ${fmt(entry)}</div>` +
        (ltp ? `<div style="top:${y(ltp)};border-color:var(--accent);color:var(--accent)">LTP ${fmt(ltp)}</div>` : "") +
        `<div style="top:${y(sl)};border-color:var(--dn);color:var(--dn)">SL ${fmt(sl)}</div>`;
      lad.hidden = false;
    } else lad.hidden = true;
    $("buyBtn").disabled = false; $("sellBtn").disabled = false;
    $("sizeNote").textContent = dec && entry && sl && lot ? `Risk per lot ≈ ₹${fmt(Math.abs(entry - sl) * lot, 0)}` : "";
    $("sigRationale").textContent = dec ? (r.rationale || "") : (m.available ? "The model will show a contract and levels when the score crosses the gate and enough factors agree." : "");
    S.ticketDefaults = { symbol: contract.symbol || r.symbol || S.symbol, entry, sl, tgt, lot: lot || 1, side: "BUY" };
  }
  function renderWhy() {
    const m = modelOf(S.reco);
    if (!m.available) { $("factorRows").innerHTML = `<tr><td colspan="6" class="muted">${esc(m.reason || "Signal model has no data for this instrument.")}</td></tr>`; $("scoreVal").textContent = "—"; return; }
    $("scoreVal").textContent = sgn(m.score); $("scoreVal").className = "big " + cls(m.score);
    $("scoreDecision").textContent = `${m.decision.replace("_", " ")} · gate ±${fmt(m.gate, 0)} · ${m.agreeing}/${m.factors_used} agree (need ${m.min_agree})`;
    $("gaugeNeedle").style.left = `${(Math.max(-100, Math.min(100, m.score)) + 100) / 2}%`;
    $("gateLo").style.left = `${(100 - m.gate) / 2}%`; $("gateHi").style.left = `${(100 + m.gate) / 2}%`;
    const c = m.confidence || {};
    $("confVal").textContent = num(c.pct) === null ? "n/a" : `${fmt(c.pct, 1)}%`;
    $("confBasis").textContent = c.label ? `Confidence = ${c.label}.` : "";
    const cal = m.calibration || {}; const v = (cal.validation || {}).test || {};
    $("calibNote").textContent = cal.version ? `Weights: ${cal.version}. ${cal.source || ""}${v.fired ? ` Held-out check: agreed with Stock Mantra on ${v.agree_with_mantra}/${v.fired} calls; right on ${v.model_right}/${v.resolved}.` : ""}` : "";
    $("factorRows").innerHTML = (m.rows || []).map((row) => {
      const p = num(row.points); const w = Math.min(50, Math.abs(p || 0) / 2);
      const bar = p === null ? "" : p >= 0 ? `<span style="left:50%;width:${w}%;background:var(--up)"></span>` : `<span style="right:50%;width:${w}%;background:var(--dn)"></span>`;
      return `<tr class="${row.available ? "" : "off"}" title="${esc(row.rule)}"><td>${esc(row.name)}<span class="src">${esc(row.source)}</span></td>` +
        `<td class="num">${esc(row.input)}</td><td class="r ${cls(p)}">${p === null ? "—" : sgn(p)}</td><td class="r">${fmt(row.weight_pct, 1)}%</td>` +
        `<td><div class="bar">${bar}</div></td><td class="r ${cls(row.contribution)}">${sgn(row.contribution)}</td></tr>`;
    }).join("");
  }
  async function loadMiniChain() {
    if (!/NIFTY|SENSEX|BANKEX|CRUDE|GOLD|SILVER|NATURALGAS/.test(S.symbol) && !(S.reco && S.reco.option_type)) { $("miniChain").innerHTML = `<tr><td colspan="5" class="muted">No options for ${esc(S.symbol)}</td></tr>`; return; }
    try {
      const root = S.symbol.split(" ")[0];
      const d = await api(`/api/options/${encodeURIComponent(root)}`);
      S.chain = d; mark("chain"); renderMiniChain();
      if (S.ws === "options") renderFullChain();
    } catch (e) { $("miniChain").innerHTML = `<tr><td colspan="5" class="muted">${esc(e.message)}</td></tr>`; }
  }
  function atmIndex(st, spot) { let bi = 0, bd = Infinity; st.forEach((s, i) => { const d = Math.abs(Number(s.strike) - spot); if (d < bd) { bd = d; bi = i; } }); return bi; }
  function renderMiniChain() {
    const d = S.chain || {}; const st = d.strikes || []; const spot = num(d.spot);
    if (!st.length || !spot) { $("miniChain").innerHTML = `<tr><td colspan="5" class="muted">${esc(d.error || "No chain from Upstox")}</td></tr>`; $("pcrVal").textContent = "—"; return; }
    const a = atmIndex(st, spot); const rows = st.slice(Math.max(0, a - 3), a + 4);
    $("miniChain").innerHTML = rows.map((s) => { const c = s.call || {}, p = s.put || {};
      return `<tr class="${Number(s.strike) === Number(st[a].strike) ? "atm" : ""}"><td class="${cls(c.change_oi)}">${short(c.change_oi)}</td><td>${fmt(c.ltp)}</td><td class="mid">${fmt(s.strike, 0)}</td><td>${fmt(p.ltp)}</td><td class="${cls(p.change_oi)}">${short(p.change_oi)}</td></tr>`; }).join("");
    const coi = st.reduce((a2, s) => a2 + (num((s.call || {}).oi) || 0), 0), poi = st.reduce((a2, s) => a2 + (num((s.put || {}).oi) || 0), 0);
    $("pcrVal").textContent = coi ? (poi / coi).toFixed(2) : "—";
  }
  function short(v) { const n = num(v); if (n === null) return "—"; const a = Math.abs(n); const s = a >= 1e7 ? (a / 1e7).toFixed(1) + "Cr" : a >= 1e5 ? (a / 1e5).toFixed(1) + "L" : a >= 1e3 ? (a / 1e3).toFixed(1) + "K" : a.toFixed(0); return (n > 0 ? "+" : n < 0 ? "−" : "") + s; }
  async function loadStockMantra() {
    try {
      const d = await api("/api/telegram/stock-mantra-feed");
      const root = S.symbol.split(" ")[0];
      const call = (d.setups || []).find((x) => x.underlying === root);
      mark("sm");
      const box = $("smBox");
      if (!call) { box.className = "sm-box muted small"; box.textContent = d.live_stream_active ? `No ${root} call from Stock Mantra in this session.` : "Stock Mantra listener is not connected."; return; }
      const m = modelOf(S.reco); const ours = m.decision; const his = call.option_type === "CE" ? "BUY" : "SELL";
      const agree = ours === his ? "agree" : ours === "NO_TRADE" || !ours ? "" : "disagree";
      box.className = `sm-box small ${agree}`;
      box.innerHTML = `<b>${esc(call.symbol)}</b> near ₹${fmt(call.entry)} · ${esc(call.date)} ${esc(call.time)}<br>Target ${call.target_1 ? "₹" + fmt(call.target_1) : "open"}, SL ${call.stop_loss ? "₹" + fmt(call.stop_loss) : "not stated"}` +
        `${num(call.cmp) !== null ? ` · now ₹${fmt(call.cmp)} (${sgn(call.pnl_pct_from_entry)}%)` : ""}<br>${agree === "agree" ? "Our model agrees." : agree === "disagree" ? `Our model says ${esc(ours)}.` : "Our model has no trade right now."}`;
    } catch (e) { /* optional panel */ }
  }
  async function loadToday() {
    try {
      const [p, f] = await Promise.all([api("/api/positions"), api("/api/funds").catch(() => ({}))]);
      const open = p.open_positions || []; const all = p.items || [];
      const openPnl = open.reduce((a, x) => a + (num(x.pnl) || 0), 0);
      const today = new Date().toISOString().slice(0, 10);
      const realised = all.filter((x) => x.status === "CLOSED" && String(x.updated_at || x.closed_at || "").startsWith(today)).reduce((a, x) => a + (num(x.pnl) || 0), 0);
      const bal = (((f.local || {}).balance) ?? ((f.local || {}).available_balance));
      $("todayKv").innerHTML = [["Open positions", open.length], ["Open P&L", `<span class="${cls(openPnl)}">₹${fmt(openPnl, 0)}</span>`], ["Realised today", `<span class="${cls(realised)}">₹${fmt(realised, 0)}</span>`], ["Paper balance", bal !== undefined ? "₹" + fmt(bal, 0) : "—"]]
        .map(([k, v]) => `<div class="row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("");
      S.positions = p; mark("pos");
      if (S.ws === "portfolio") renderPortfolio(p, f);
    } catch (e) { /* ignore */ }
  }

  // chart
  async function loadCandles() {
    const sym = S.symbol;
    try {
      const d = await api(`/api/market/candles/${encodeURIComponent(sym)}?timeframe=5m&days=3`);
      if (sym !== S.symbol) return;
      S.candles = (d.candles || []).slice(-150); mark("candles"); drawChart();
    } catch (e) { S.candles = []; drawChart(e.message); }
  }
  function ema(vals, n) { const k = 2 / (n + 1); let e = vals[0]; return vals.map((v) => (e = v * k + e * (1 - k))); }
  function drawChart(err) {
    const cv = $("chart"); if (!cv || S.ws !== "trade") return;
    const dpr = window.devicePixelRatio || 1; const w = cv.clientWidth, h = 320;
    cv.width = w * dpr; cv.height = h * dpr; const g = cv.getContext("2d"); g.scale(dpr, dpr); g.clearRect(0, 0, w, h);
    const css = getComputedStyle(document.documentElement); const col = (n) => css.getPropertyValue(n).trim();
    const cs = S.candles || [];
    if (!cs.length) { g.fillStyle = col("--muted"); g.font = "13px sans-serif"; g.fillText(err || "No candles from Upstox", 12, 24); return; }
    const pad = { l: 8, r: 64, t: 10, b: 20 };
    const r = S.reco || {}; const lv = [num(r.stop_loss), num(r.target), num(r.entry)].filter((x) => x !== null && (r.option_type ? false : true));
    const highs = cs.map((c) => +c.high), lows = cs.map((c) => +c.low);
    let hi = Math.max(...highs, ...lv), lo = Math.min(...lows, ...lv); const span = hi - lo || 1; hi += span * 0.04; lo -= span * 0.04;
    const X = (i) => pad.l + (i + 0.5) * ((w - pad.l - pad.r) / cs.length), Y = (v) => pad.t + (1 - (v - lo) / (hi - lo)) * (h - pad.t - pad.b);
    g.strokeStyle = col("--line"); g.lineWidth = 1; g.fillStyle = col("--muted"); g.font = "10.5px monospace";
    for (let k = 0; k <= 4; k++) { const v = lo + (hi - lo) * k / 4, y = Y(v); g.beginPath(); g.moveTo(pad.l, y); g.lineTo(w - pad.r, y); g.stroke(); g.fillText(fmt(v, 1), w - pad.r + 6, y + 3); }
    let lastDay = ""; cs.forEach((c, i) => { const dte = String(c.timestamp).slice(0, 10); if (dte !== lastDay) { lastDay = dte; g.fillText(dte.slice(5), X(i), h - 5); } });
    const bw = Math.max(1, ((w - pad.l - pad.r) / cs.length) * 0.6);
    cs.forEach((c, i) => { const up = +c.close >= +c.open; g.strokeStyle = g.fillStyle = up ? col("--up") : col("--dn");
      g.beginPath(); g.moveTo(X(i), Y(+c.high)); g.lineTo(X(i), Y(+c.low)); g.stroke();
      const y1 = Y(Math.max(+c.open, +c.close)), y2 = Y(Math.min(+c.open, +c.close)); g.fillRect(X(i) - bw / 2, y1, bw, Math.max(1, y2 - y1)); });
    const closes = cs.map((c) => +c.close);
    const line = (vals, color) => { g.strokeStyle = color; g.lineWidth = 1.4; g.beginPath(); vals.forEach((v, i) => (i ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)))); g.stroke(); };
    line(ema(closes, 9), col("--accent")); line(ema(closes, 21), col("--muted"));
    let day0 = ""; let acc = 0, n = 0; const vw = cs.map((c) => { const d = String(c.timestamp).slice(0, 10); if (d !== day0) { day0 = d; acc = 0; n = 0; } acc += (+c.high + +c.low + +c.close) / 3; n++; return acc / n; });
    g.setLineDash([4, 3]); line(vw, col("--ink")); g.setLineDash([]);
    if (!r.option_type) [["Target", num(r.target), "--up"], ["Entry", num(r.entry), "--muted"], ["SL", num(r.stop_loss), "--dn"]].forEach(([t, v, c]) => { if (v === null) return; g.strokeStyle = col(c); g.setLineDash([2, 3]); g.beginPath(); g.moveTo(pad.l, Y(v)); g.lineTo(w - pad.r, Y(v)); g.stroke(); g.setLineDash([]); g.fillStyle = col(c); g.fillText(`${t} ${fmt(v, 1)}`, w - pad.r + 6, Y(v) - 4); });
    g.fillStyle = col("--muted"); g.fillText("EMA9 — orange · EMA21 — grey · VWAP (equal-weight) — dashed", pad.l + 4, pad.t + 10);
  }
  window.addEventListener("resize", () => drawChart());

  // ---------------- order ticket ----------------
  function openTicket(side, preset) {
    const d = { ...(S.ticketDefaults || { symbol: S.symbol, lot: 1 }), ...(preset || {}) };
    $("tSymbol").value = d.symbol || S.symbol; $("tSide").value = side || "BUY"; $("tLot").value = d.lot || 1; $("tLots").value = 1;
    $("tType").value = d.entry ? "LIMIT" : "MARKET"; $("tPrice").value = d.entry ?? ""; $("tSl").value = d.sl ?? ""; $("tTgt").value = d.tgt ?? ""; $("tLive").checked = false;
    updateTicket(); $("ticket").showModal();
  }
  function updateTicket() {
    const qty = (+$("tLots").value || 0) * (+$("tLot").value || 0), px = +$("tPrice").value || 0, sl = +$("tSl").value || 0, tg = +$("tTgt").value || 0;
    const side = $("tSide").value; const dir = side === "BUY" ? 1 : -1;
    const risk = px && sl ? Math.abs(px - sl) * qty : null, reward = px && tg ? Math.abs(tg - px) * qty : null;
    $("tSummary").textContent = `${side} ${qty} × ${$("tSymbol").value} ${$("tType").value === "LIMIT" && px ? "@ ₹" + fmt(px) : "at market"}` +
      `${risk !== null ? ` · risk ₹${fmt(risk, 0)}` : ""}${reward !== null ? ` · reward ₹${fmt(reward, 0)}` : ""}${(sl && px && (sl - px) * dir > 0) ? " · check: stop loss is on the wrong side" : ""} · ${$("tLive").checked ? "LIVE order to broker" : "paper trade"}`;
    $("tSubmit").textContent = $("tLive").checked ? "Place live order" : "Place paper order";
  }
  ["tLots", "tLot", "tPrice", "tSl", "tTgt", "tType", "tSide", "tLive", "tSymbol"].forEach((id) => $(id).addEventListener("input", updateTicket));
  $("tCancel").addEventListener("click", () => $("ticket").close());
  $("ticketForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const qty = (+$("tLots").value || 0) * (+$("tLot").value || 0);
    const body = { symbol: $("tSymbol").value.trim(), side: $("tSide").value, quantity: qty, order_type: $("tType").value,
      price: $("tType").value === "LIMIT" ? (+$("tPrice").value || null) : null, stop_loss: +$("tSl").value || null, target: +$("tTgt").value || null,
      paper: !$("tLive").checked, live: $("tLive").checked, entry_reco_json: S.reco ? JSON.stringify({ score: modelOf(S.reco).score, decision: modelOf(S.reco).decision, at: new Date().toISOString() }) : null };
    $("tSubmit").disabled = true;
    try { const r = await api("/api/orders", { method: "POST", body }); toast(`Order placed: ${r.status || r.execution_state || "submitted"}`); $("ticket").close(); loadToday(); }
    catch (err) { toast(`Order rejected: ${err.message}`); }
    finally { $("tSubmit").disabled = false; }
  });
  $("buyBtn").addEventListener("click", () => openTicket("BUY"));
  $("sellBtn").addEventListener("click", () => openTicket("SELL"));

  // ---------------- SCAN ----------------
  function renderWatchSelect() {
    $("wlSelect").innerHTML = S.watchlists.map((g) => `<option value="${g.id}" ${g.id === S.wlId ? "selected" : ""}>${esc(g.name || "Watchlist " + g.id)}</option>`).join("");
  }
  $("wlSelect").addEventListener("change", async (e) => { store.set("wl", +e.target.value); await loadWatchlists(); renderWatchSelect(); renderWatchRows(); loadQuotes(); });
  function renderWatchRows() {
    $("wlRows").innerHTML = S.watch.map((s) => { const q = S.quotes[s] || {};
      return `<tr class="click" data-sym="${esc(s)}"><td><b>${esc(s)}</b></td><td class="r">${fmt(q.ltp)}</td><td class="r ${cls(q.change_pct)}">${num(q.change_pct) === null ? "—" : sgn(q.change_pct, 2) + "%"}</td><td class="r">${short(q.volume).replace("+", "")}</td>` +
        `<td class="r"><button type="button" class="btn tiny" data-remove="${esc(s)}" aria-label="Remove ${esc(s)}">Remove</button></td></tr>`; }).join("") || `<tr><td colspan="5" class="muted">Add an instrument above.</td></tr>`;
  }
  $("wlRows").addEventListener("click", async (e) => {
    const rm = e.target.closest("[data-remove]");
    if (rm) { e.stopPropagation(); try { await api(`/api/watchlists/${S.wlId}/items/${encodeURIComponent(rm.dataset.remove)}`, { method: "DELETE" }); await loadWatchlists(); renderWatchRows(); toast(`Removed ${rm.dataset.remove}`); } catch (err) { toast(err.message); } return; }
    const tr = e.target.closest("tr[data-sym]"); if (tr) { selectSymbol(tr.dataset.sym); location.hash = "#trade"; }
  });
  let searchT;
  $("symSearch").addEventListener("input", (e) => {
    clearTimeout(searchT); const q = e.target.value.trim(); if (q.length < 2) { $("searchResults").innerHTML = ""; return; }
    searchT = setTimeout(async () => { try { const d = await api(`/api/instruments/search?q=${encodeURIComponent(q)}`);
      $("searchResults").innerHTML = (d.items || []).slice(0, 12).map((it) => `<button type="button" data-sym="${esc(it.symbol)}" data-key="${esc(it.instrument_key || "")}">${esc(it.symbol)} <span class="muted small">${esc(it.name || "")} · ${esc(it.exchange || "")}</span></button>`).join(""); } catch { /* ignore */ } }, 250);
  });
  $("searchResults").addEventListener("click", async (e) => {
    const b = e.target.closest("button[data-sym]"); if (!b || !S.wlId) return;
    try { await api(`/api/watchlists/${S.wlId}/items`, { method: "POST", body: { symbol: b.dataset.sym, instrument_key: b.dataset.key || undefined } });
      $("searchResults").innerHTML = ""; $("symSearch").value = ""; await loadWatchlists(); renderWatchRows(); loadQuotes(); toast(`Added ${b.dataset.sym}`); } catch (err) { toast(err.message); }
  });
  let moverCat = "gainers";
  document.querySelectorAll("[data-mov]").forEach((b) => b.addEventListener("click", () => { moverCat = b.dataset.mov; document.querySelectorAll("[data-mov]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); loadMovers(); }));
  async function loadMovers() {
    try { const d = await api(`/api/market/movers?category=${moverCat}&limit=15`);
      $("moverRows").innerHTML = (d.items || []).map((m) => `<tr class="click" data-sym="${esc(m.symbol)}"><td>${esc(m.symbol)}</td><td class="r">${fmt(m.ltp)}</td><td class="r ${cls(m.change_pct)}">${sgn(m.change_pct, 2)}%</td></tr>`).join("") || `<tr><td colspan="3" class="muted">No data</td></tr>`;
    } catch (e) { $("moverRows").innerHTML = `<tr><td colspan="3" class="muted">${esc(e.message)}</td></tr>`; }
  }
  $("moverRows").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-sym]"); if (tr) { selectSymbol(tr.dataset.sym); location.hash = "#trade"; } });
  async function loadAlerts() {
    try { const d = await api("/api/notifications"); mark("notif");
      $("alertList").innerHTML = (d.items || []).slice(0, 60).map((n) => `<li class="${esc(n.severity || n.level || "")}"><b>${esc(n.title)}</b><br>${esc(n.message || n.body || "")}<time>${esc(String(n.created_at || "").replace("T", " ").slice(0, 16))}</time></li>`).join("") || `<li class="muted">No alerts.</li>`;
    } catch (e) { $("alertList").innerHTML = `<li>${esc(e.message)}</li>`; }
  }

  // ---------------- OPTIONS ----------------
  function renderFullChain() {
    const d = S.chain || {}; const st = d.strikes || []; const spot = num(d.spot);
    $("chainTitle").textContent = `Option chain · ${S.symbol.split(" ")[0]} · expiry ${d.expiry || "—"} · spot ${fmt(spot)}`;
    if (!st.length || !spot) { $("chainRows").innerHTML = `<tr><td colspan="11" class="muted">${esc(d.error || "No option chain from Upstox for this instrument.")}</td></tr>`; $("chainStats").innerHTML = ""; return; }
    const coi = st.reduce((x, s) => x + (num((s.call || {}).oi) || 0), 0), poi = st.reduce((x, s) => x + (num((s.put || {}).oi) || 0), 0);
    const a0 = atmIndex(st, spot); const view = st.slice(Math.max(0, a0 - 20), a0 + 21); const a = atmIndex(view, spot);
    const pain = (k) => st.reduce((x, s) => x + Math.max(0, k - s.strike) * (num((s.call || {}).oi) || 0) + Math.max(0, s.strike - k) * (num((s.put || {}).oi) || 0), 0);
    const mp = st.reduce((best, s) => (pain(s.strike) < pain(best) ? s.strike : best), st[0].strike);
    const maxC = st.reduce((b, s) => ((num((s.call || {}).oi) || 0) > (num((b.call || {}).oi) || 0) ? s : b), st[0]);
    const maxP = st.reduce((b, s) => ((num((s.put || {}).oi) || 0) > (num((b.put || {}).oi) || 0) ? s : b), st[0]);
    $("chainStats").innerHTML = [["PCR (OI)", coi ? (poi / coi).toFixed(2) : "—"], ["Max pain", fmt(mp, 0)], ["Highest call OI", fmt(maxC.strike, 0)], ["Highest put OI", fmt(maxP.strike, 0)], ["Source", esc(d.provider || "upstox")]]
      .map(([k, v]) => `<div><span class="k">${k}</span> <span class="v">${v}</span></div>`).join("");
    const cell = (n, k, d2 = 2) => (k === "oi" || k === "change_oi" ? short(n[k]).replace(k === "oi" ? "+" : "", "") : k === "iv" ? fmt(n[k], 1) : k === "delta" ? fmt(n[k], 2) : fmt(n[k], d2));
    $("chainRows").innerHTML = view.map((s, i) => { const c = s.call || {}, p = s.put || {}; const itmC = s.strike < spot, itmP = s.strike > spot;
      return `<tr class="${i === a ? "atm" : ""}">` +
        ["oi", "change_oi", "iv", "delta"].map((k) => `<td class="${itmC ? "itm" : ""} ${k === "change_oi" ? cls(c[k]) : ""}">${cell(c, k)}</td>`).join("") +
        `<td class="px ${itmC ? "itm" : ""}" data-pick="${esc(c.trading_symbol || c.symbol || `${S.symbol} ${s.strike} CE`)}" data-px="${num(c.ltp) ?? ""}" data-lot="${num(c.lot_size) ?? ""}">${fmt(c.ltp)}</td>` +
        `<td class="mid">${fmt(s.strike, 0)}</td>` +
        `<td class="px ${itmP ? "itm" : ""}" data-pick="${esc(p.trading_symbol || p.symbol || `${S.symbol} ${s.strike} PE`)}" data-px="${num(p.ltp) ?? ""}" data-lot="${num(p.lot_size) ?? ""}">${fmt(p.ltp)}</td>` +
        ["delta", "iv", "change_oi", "oi"].map((k) => `<td class="${itmP ? "itm" : ""} ${k === "change_oi" ? cls(p[k]) : ""}">${cell(p, k)}</td>`).join("") + `</tr>`; }).join("");
    mark("chainFull");
  }
  $("chainRows").addEventListener("click", (e) => { const td = e.target.closest("td[data-pick]"); if (td) openTicket("BUY", { symbol: td.dataset.pick, entry: num(td.dataset.px), lot: num(td.dataset.lot) || 1, sl: null, tgt: null }); });

  // ---------------- PORTFOLIO ----------------
  function renderPortfolio(p, f) {
    const b = (f && f.buckets) || {}; const loc = (f && f.local) || {};
    $("fundCards").innerHTML = [["Paper balance", loc.balance ?? loc.available_balance], ["Used margin", loc.used_margin], ["Trading bucket", (b.trading || {}).balance], ["Open positions", (p.open_positions || []).length, 0]]
      .map(([k, v, d]) => `<div><div class="k">${k}</div><div class="v">${d === 0 ? (v ?? "—") : (num(v) === null ? "—" : "₹" + fmt(v, 0))}</div></div>`).join("");
    const open = p.open_positions || [];
    $("posRows").innerHTML = open.map((x) => `<tr><td><b>${esc(x.symbol)}</b><div class="muted small">${esc(x.trade_type || "")}</div></td><td>${esc(x.side)}</td><td class="r">${fmt(x.quantity, 0)}</td><td class="r">${fmt(x.avg_price)}</td><td class="r">${fmt(x.ltp ?? x.current_price)}</td><td class="r ${cls(x.pnl)}">₹${fmt(x.pnl, 0)}</td>` +
      `<td class="r"><input type="number" step="0.05" value="${num(x.stop_loss) ?? ""}" data-sl="${esc(x.id)}" aria-label="Stop loss for ${esc(x.symbol)}" style="width:86px"></td><td class="r">${fmt(x.target)}</td>` +
      `<td class="r"><button type="button" class="btn tiny" data-trail="${esc(x.id)}">Save SL</button> <button type="button" class="btn tiny" data-exit="${esc(x.id)}">Exit</button></td></tr>`).join("") || `<tr><td colspan="9" class="muted">No open positions.</td></tr>`;
    const closed = (p.items || []).filter((x) => x.status === "CLOSED").slice(0, 50);
    const tot = closed.reduce((a, x) => a + (num(x.pnl) || 0), 0), wins = closed.filter((x) => (num(x.pnl) || 0) > 0).length;
    $("pnlStats").innerHTML = [["Closed trades", closed.length], ["Winners", wins], ["Net P&L", `<span class="${cls(tot)}">₹${fmt(tot, 0)}</span>`]].map(([k, v]) => `<div><span class="k">${k}</span> <span class="v">${v}</span></div>`).join("");
    $("closedRows").innerHTML = closed.map((x) => `<tr><td>${esc(String(x.updated_at || "").replace("T", " ").slice(0, 16))}</td><td>${esc(x.symbol)}</td><td>${esc(x.side)}</td><td class="r">${fmt(x.quantity, 0)}</td><td class="r">${fmt(x.avg_price)}</td><td class="r">${fmt(x.exit_price)}</td><td class="r ${cls(x.pnl)}">₹${fmt(x.pnl, 0)}</td></tr>`).join("") || `<tr><td colspan="7" class="muted">No closed trades.</td></tr>`;
  }
  $("posRows").addEventListener("click", async (e) => {
    const ex = e.target.closest("[data-exit]"); const tr = e.target.closest("[data-trail]");
    if (ex) {
      if (ex.dataset.confirm !== "1") { ex.dataset.confirm = "1"; ex.textContent = "Confirm exit"; setTimeout(() => { ex.dataset.confirm = ""; ex.textContent = "Exit"; }, 4000); return; }
      try { const r = await api(`/api/positions/${encodeURIComponent(ex.dataset.exit)}/square-off`, { method: "POST", body: {} }); toast(`Exited at ₹${fmt(r.exit_price)} · P&L ₹${fmt(r.final_pnl, 0)}`); loadToday(); } catch (err) { toast(err.message); }
    }
    if (tr) { const inp = document.querySelector(`input[data-sl="${CSS.escape(tr.dataset.trail)}"]`); try { await api(`/api/positions/${encodeURIComponent(tr.dataset.trail)}/trail-sl`, { method: "POST", body: { stop_loss: +inp.value } }); toast("Stop loss updated"); loadToday(); } catch (err) { toast(err.message); } }
  });
  async function loadOrders() {
    try { const d = await api("/api/orders");
      $("orderRows").innerHTML = (d.items || []).slice(0, 60).map((o) => `<tr><td>${esc(String(o.created_at || "").replace("T", " ").slice(5, 16))}</td><td>${esc(o.symbol)}</td><td>${esc(o.side)}</td><td class="r">${fmt(o.quantity, 0)}</td><td class="r">${fmt(o.price)}</td><td>${esc(o.order_type)}</td>` +
        `<td><span class="pill ${/FILL/.test(o.status) ? "up" : /REJECT|CANCEL/.test(o.status) ? "dn" : "warn"}">${esc(o.status)}</span></td>` +
        `<td class="r">${/PENDING|OPEN/.test(o.status || "") ? `<button type="button" class="btn tiny" data-cancel="${esc(o.id)}">Cancel</button>` : ""}</td></tr>`).join("") || `<tr><td colspan="8" class="muted">No orders.</td></tr>`;
    } catch (e) { $("orderRows").innerHTML = `<tr><td colspan="8">${esc(e.message)}</td></tr>`; }
  }
  $("orderRows").addEventListener("click", async (e) => { const b = e.target.closest("[data-cancel]"); if (!b) return; try { await api(`/api/orders/${encodeURIComponent(b.dataset.cancel)}?hard=0`, { method: "DELETE" }); toast("Order cancelled"); loadOrders(); } catch (err) { toast(err.message); } });

  // ---------------- RESEARCH ----------------
  let rtab = store.get("rtab", "context");
  document.querySelectorAll("[data-rt]").forEach((b) => b.addEventListener("click", () => { rtab = b.dataset.rt; store.set("rtab", rtab); loadResearch(); }));
  const panel = (title, body, age) => `<section class="panel"><div class="panel-head"><span class="label">${title}</span>${age ? `<span class="age">${esc(age)}</span>` : ""}</div>${body}</section>`;
  const kvRows = (pairs) => `<div class="kv">${pairs.map(([k, v]) => `<div class="row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("")}</div>`;
  const unavailable = (o) => `<p class="muted">${esc((o && o.reason) || "Not available")}</p>`;
  async function loadResearch() {
    document.querySelectorAll("[data-rt]").forEach((x) => x.setAttribute("aria-selected", String(x.dataset.rt === rtab)));
    const token = (loadResearch.seq = (loadResearch.seq || 0) + 1);
    const body = $("researchBody"); body.innerHTML = `<p class="muted">Loading…</p>`;
    const sym = S.symbol.split(" ")[0];
    try {
      if (rtab === "context") {
        const d = await api(`/api/market/other-factors?symbol=${encodeURIComponent(sym)}`, { timeout: 40000 }); if (token !== loadResearch.seq) return;
        const b = d.market_breadth || {}, s = d.sector_rotation || {}, rg = d.regime || {}, v = d.volatility_surface || {}, oi = d.oi_matrix || {}, mi = d.microstructure || {};
        body.innerHTML = `<div class="grid2">` +
          panel("NIFTY 50 breadth", b.available ? kvRows([["Advances / declines", `${b.advances} / ${b.declines}`], ["A/D ratio", fmt(b.ad_ratio)], ["Up-volume share", b.up_volume_pct === null ? "—" : fmt(b.up_volume_pct, 1) + "%"], ["Reading", `<span class="pill ${b.signal === "BULLISH" ? "up" : b.signal === "BEARISH" ? "dn" : ""}">${esc(b.signal)}</span>`]]) + `<p class="note">${esc(b.source)}</p>` : unavailable(b), d.updated_at) +
          panel("Regime (signal model)", rg.available ? kvRows([["Regime", esc(rg.current_regime)], ["Score / gate", `${sgn(rg.score)} / ±${fmt(rg.gate, 0)}`], ["ADX", fmt(rg.adx, 1)]]) : unavailable(rg)) +
          panel("Volatility", kvRows([["India VIX", fmt(v.india_vix)], ["VIX change", num(v.india_vix_change_pct) === null ? "—" : sgn(v.india_vix_change_pct, 2) + "%"], ["ATM IV", fmt(v.atm_iv, 1)], ["Put − call IV skew", fmt(v.skew_put_minus_call, 1)], ["HV 20-day", fmt(v.hv_20, 1)]])) +
          panel(`Open interest · ${esc(oi.expiry || "")}`, oi.available ? kvRows([["PCR (OI)", fmt(oi.pcr_oi)], ["PCR (volume)", fmt(oi.pcr_volume)], ["Max pain", fmt(oi.max_pain_strike, 0)]]) + `<table class="list"><thead><tr><th>Biggest OI changes</th><th class="r">ΔOI</th><th class="r">LTP</th></tr></thead><tbody>${(oi.buildup_highlights || []).map((m) => `<tr><td>${esc(m.strike)}</td><td class="r ${cls(m.oi_change)}">${short(m.oi_change)}</td><td class="r">${fmt(m.ltp)}</td></tr>`).join("")}</tbody></table>` : unavailable(oi)) +
          panel("Order book", mi.available ? kvRows([["Bid / ask quantity", `${fmt(mi.bid_qty_pct, 1)}% / ${fmt(mi.ask_qty_pct, 1)}%`], ["Imbalance", fmt(mi.imbalance_ratio)], ["Spread", fmt(mi.effective_spread_pct, 3) + "%"]]) : unavailable(mi)) +
          `</div>` + panel("Sector rotation (vs NIFTY, 5 sessions)", s.available ? `<div class="scroll-x"><table class="list"><thead><tr><th>Sector</th><th class="r">1D</th><th class="r">5D</th><th class="r">20D</th><th class="r">RS 5D</th><th>Quadrant</th></tr></thead><tbody>${s.items.map((x) => `<tr><td>${esc(x.sector)}</td><td class="r ${cls(x.ret_1d)}">${sgn(x.ret_1d, 2)}%</td><td class="r ${cls(x.ret_5d)}">${sgn(x.ret_5d, 2)}%</td><td class="r ${cls(x.ret_20d)}">${sgn(x.ret_20d, 2)}%</td><td class="r ${cls(x.rs_vs_nifty)}">${sgn(x.rs_vs_nifty, 2)}</td><td><span class="pill ${x.quadrant === "LEADING" ? "up" : x.quadrant === "LAGGING" ? "dn" : "warn"}">${esc(x.quadrant || "—")}</span></td></tr>`).join("")}</tbody></table></div><p class="note">${esc(s.source)}</p>` : unavailable(s));
      } else if (rtab === "matrix") {
        const d = await api(`/api/market/data-inspector?instrument=${encodeURIComponent(sym)}`, { timeout: 40000 }); if (token !== loadResearch.seq) return;
        body.innerHTML = panel(`Every model input for ${esc(sym)} · now and 5 / 10 / 15 minutes ago`, `<p class="note">Past values are recomputed from Upstox 5-minute candles as they stood then. ${d.values_missing} values unavailable · ${d.candles_used} candles used.</p><div class="scroll-x"><table class="list"><thead><tr><th>Input</th><th>Group</th><th class="r">Now</th><th class="r">−5m</th><th class="r">−10m</th><th class="r">−15m</th><th class="r">Δ 5m</th><th>Source</th></tr></thead><tbody>` +
          (d.items || []).map((x) => `<tr><td>${esc(x.name)}</td><td class="muted">${esc(x.category)}</td><td class="r">${fmt(x.val_now)}</td><td class="r">${fmt(x.val_5m)}</td><td class="r">${fmt(x.val_10m)}</td><td class="r">${fmt(x.val_15m)}</td><td class="r ${cls(x.delta_5m)}">${num(x.delta_5m) === null ? "—" : sgn(x.delta_5m, 2)}</td><td class="muted small">${esc(x.primary_source)}</td></tr>`).join("") + `</tbody></table></div>`, d.timestamp);
      } else if (rtab === "mantra") {
        const d = await api(`/api/stockmantra/database`); if (token !== loadResearch.seq) return;
        const s = d.summary || {}; const nm = (s.new_model || {});
        const card = (t, o) => `<div><div class="k">${t}</div><div class="v">${o && o.n !== undefined ? `${o.right ?? o.same}/${o.n} · ${fmt(o.pct ?? o.same_pct, 1)}%` : "—"}</div></div>`;
        body.innerHTML = `<div class="kv cards">${card("Stock Mantra right (0.3% first, 2h)", s.stock_mantra_right)}${card("Old backtest engine right", s.old_backtest_engine_right)}${card("Old live engine right", s.old_live_engine_right)}` +
          `<div><div class="k">New model · held-out week</div><div class="v">agreed ${nm.test ? `${nm.test.agree_with_mantra}/${nm.test.fired}` : "—"} · right ${nm.test ? `${nm.test.model_right}/${nm.test.resolved}` : "—"}</div></div></div>` +
          panel("How this was measured", `<ul class="small">${Object.values(d.method || {}).map((m) => `<li>${esc(m)}</li>`).join("")}</ul><p class="note">${d.calls_parsed} calls parsed from ${d.messages_downloaded} messages (${esc(d.period)}); ${d.calls_analysed} had enough Upstox data.</p>`) +
          panel("Every call", `<div class="scroll-x"><table class="list"><thead><tr><th>Time (IST)</th><th>Call</th><th class="r">Entry</th><th class="r">Reported peak</th><th class="r">Δ</th><th class="r">Implied index move</th><th>Market did</th><th>Old engine</th><th class="r">New score</th></tr></thead><tbody>` +
          (d.calls || []).slice().reverse().map((c) => `<tr><td>${esc(String(c.time_ist).replace("T", " ").slice(0, 16))}</td><td><b>${esc(c.contract)}</b></td><td class="r">${fmt(c.entry)}</td><td class="r">${fmt(c.claimed_peak)}</td><td class="r">${fmt(c.delta, 2)}</td><td class="r">${num(c.implied_index_move) === null ? "—" : sgn(c.implied_index_move, 0) + " pts"}</td>` +
            `<td>${c.actual_first_0p3pct ? `<span class="pill ${c.mantra_right ? "up" : c.mantra_right === false ? "dn" : ""}">${esc(c.actual_first_0p3pct)}</span>` : `<span class="muted small">${esc(c.skip || "—")}</span>`}</td>` +
            `<td>${esc(c.old_live_engine || "—")}</td><td class="r ${cls(c.new_model_score)}">${num(c.new_model_score) === null ? "—" : sgn(c.new_model_score)}</td></tr>`).join("") + `</tbody></table></div>`);
      } else if (rtab === "backtest") {
        const y = new Date(Date.now() - 86400000); while ([0, 6].includes(y.getDay())) y.setDate(y.getDate() - 1);
        body.innerHTML = panel("Replay the model on a past day", `<div class="formrow"><label>Symbol<input id="btSym" value="${esc(sym)}"></label><label>Date<input id="btDate" type="date" value="${y.toISOString().slice(0, 10)}"></label><button type="button" class="btn primary" id="btRun" style="flex:0">Run replay</button><button type="button" class="btn" id="bt100" style="flex:0">Last 100 signals</button></div><p class="note">The model sees only candles up to each 5-minute step. SL = 1×ATR, target = 1.5×ATR on the underlying; outcome read from the candles that followed.</p><div id="btOut"></div>`);
        const run = async (url) => { $("btOut").innerHTML = `<p class="muted">Replaying…</p>`; try { const r = await api(url, { timeout: 120000 }); const it = r.items || r.trades || []; const sm = r.summary || {};
          $("btOut").innerHTML = r.error ? `<p class="muted">${esc(r.error)}</p>` : `<div class="kv inline"><div><span class="k">Signals</span> <span class="v">${sm.total_trades ?? it.length}</span></div><div><span class="k">Winners</span> <span class="v">${sm.wins ?? "—"}</span></div><div><span class="k">Win rate</span> <span class="v">${num(sm.win_rate) === null ? "—" : fmt(sm.win_rate, 1) + "%"}</span></div><div><span class="k">Net</span> <span class="v ${cls(sm.total_points)}">${sgn(sm.total_points, 1)} pts</span></div></div>` +
            `<div class="scroll-x"><table class="list"><thead><tr><th>Date</th><th>Time</th><th>Signal</th><th class="r">Score</th><th class="r">Entry</th><th class="r">SL</th><th class="r">Target</th><th>Outcome</th><th class="r">Points</th></tr></thead><tbody>${it.map((x) => `<tr><td>${esc(x.date)}</td><td>${esc(x.time)}</td><td><span class="pill ${x.recommendation === "BUY" ? "up" : "dn"}">${esc(x.recommendation)}</span></td><td class="r">${sgn(x.score)}</td><td class="r">${fmt(x.entry)}</td><td class="r">${fmt(x.stop_loss)}</td><td class="r">${fmt(x.target)}</td><td>${esc(x.outcome)} ${esc(x.exit_time || "")}</td><td class="r ${cls(x.final_pnl)}">${sgn(x.final_pnl, 1)}</td></tr>`).join("")}</tbody></table></div>`; } catch (e) { $("btOut").innerHTML = `<p class="muted">${esc(e.message)}</p>`; } };
        $("btRun").addEventListener("click", () => run(`/api/recommendations/for-date?symbol=${encodeURIComponent($("btSym").value)}&date=${$("btDate").value}&limit=20`));
        $("bt100").addEventListener("click", () => run(`/api/backtest/100-trades?symbol=${encodeURIComponent($("btSym").value)}&count=100`));
      } else if (rtab === "news") {
        const d = await api(`/api/news/unified?symbol=${encodeURIComponent(sym)}`, { timeout: 30000 }); if (token !== loadResearch.seq) return;
        body.innerHTML = panel(`News · ${esc(sym)} and market`, `<ul class="alerts">${(d.events || []).slice(0, 60).map((n) => `<li class="${n.sentiment === "Positive" ? "success" : n.sentiment === "Negative" ? "error" : ""}"><b>${esc(n.headline || n.event)}</b><br>${esc(n.summary || "")}<time>${esc(n.source || "")} · ${esc(String(n.published_at || "").slice(0, 16))} ${n.url ? `· <a href="${esc(n.url)}" target="_blank" rel="noopener">open</a>` : ""}</time></li>`).join("") || "<li class='muted'>No news.</li>"}</ul>`, d.timestamp);
      } else if (rtab === "fund") {
        const d = await api(`/api/analysis/fundamental/${encodeURIComponent(sym)}`, { timeout: 30000 }); if (token !== loadResearch.seq) return;
        const skip = new Set(["instrument", "provider", "timestamp", "available", "quarterly", "shareholding", "reason"]);
        body.innerHTML = d.available === false ? panel("Fundamentals", unavailable(d)) : panel(`Fundamentals · ${esc(sym)} · ${esc(d.provider || "")}`, kvRows(Object.entries(d).filter(([k, v]) => !skip.has(k) && (typeof v === "number" || typeof v === "string")).map(([k, v]) => [esc(k.replace(/_/g, " ")), typeof v === "number" ? fmt(v) : esc(v)])));
      } else if (rtab === "ask") {
        body.innerHTML = panel("Ask CA AI", `<label for="askQ" class="sr">Question</label><textarea id="askQ" placeholder="Ask about ${esc(sym)}: levels, why the model says what it says, what changed in the last hour…"></textarea><div class="btn-row"><button type="button" class="btn primary" id="askGo" style="flex:0">Ask</button></div><div id="askOut"></div>`);
        $("askGo").addEventListener("click", async () => { const q = $("askQ").value.trim(); if (!q) return; $("askOut").innerHTML = `<p class="muted">Thinking…</p>`;
          try { const r = await api("/api/ai/ask", { method: "POST", body: { prompt: q, symbol: sym, mode: "data" }, timeout: 60000 }); $("askOut").innerHTML = `<div class="answer">${esc(r.reply || r.answer || JSON.stringify(r))}</div>`; } catch (e) { $("askOut").innerHTML = `<p class="muted">${esc(e.message)}</p>`; } });
      }
    } catch (e) { body.innerHTML = `<p class="muted">${esc(e.message)}</p>`; }
  }

  // ---------------- routing & lifecycle ----------------
  function refreshWorkspace(symbolChanged) {
    if (S.ws === "trade") { loadReco(); loadCandles(); loadMiniChain(); loadStockMantra(); if (!symbolChanged) loadToday(); }
    if (S.ws === "options") { renderFullChain(); loadMiniChain(); }
    if (S.ws === "research" && symbolChanged) loadResearch();
  }
  function route() {
    const ws = (location.hash || "#trade").slice(1);
    S.ws = ["trade", "scan", "options", "portfolio", "research"].includes(ws) ? ws : "trade";
    document.querySelectorAll(".ws").forEach((el) => (el.hidden = el.id !== "ws-" + S.ws));
    document.querySelectorAll(".workspaces a").forEach((a) => { if (a.dataset.ws === S.ws) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    if (S.ws === "trade") { loadReco(); loadCandles(); loadMiniChain(); loadStockMantra(); loadToday(); setTimeout(drawChart, 30); }
    if (S.ws === "scan") { renderWatchSelect(); renderWatchRows(); loadMovers(); loadAlerts(); }
    if (S.ws === "options") { if (S.chain) renderFullChain(); loadMiniChain(); }
    if (S.ws === "portfolio") { loadToday().then(() => S.positions && api("/api/funds").then((f) => renderPortfolio(S.positions, f)).catch(() => renderPortfolio(S.positions, {}))); loadOrders(); }
    if (S.ws === "research") loadResearch();
  }
  window.addEventListener("hashchange", route);
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, select") || $("ticket").open) return;
    if (/^[1-9]$/.test(e.key) && S.watch[+e.key - 1]) selectSymbol(S.watch[+e.key - 1]);
    if (e.key === "b" || e.key === "B") openTicket("BUY");
    if (e.key === "s" || e.key === "S") openTicket("SELL");
  });
  $("themeBtn").addEventListener("click", () => { const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"); const nxt = cur === "light" ? "dark" : "light"; document.documentElement.dataset.theme = nxt; store.set("theme", nxt); drawChart(); });
  const savedTheme = store.get("theme", null); if (savedTheme) document.documentElement.dataset.theme = savedTheme;

  async function boot() {
    try { const me = await api("/api/auth/me"); S.user = me.user; if (me.user) $("userName").textContent = me.user.full_name || me.user.username || "Menu"; } catch { /* redirected if signed out */ }
    await loadWatchlists();
    route();
    every(3000, loadQuotes);
    every(20000, () => { if (S.ws === "trade") loadReco(); });
    every(10000, () => { if (S.ws === "trade" || S.ws === "options") loadMiniChain(); });
    every(30000, () => { if (S.ws === "trade") { loadCandles(); loadStockMantra(); } });
    every(15000, () => { if (S.ws === "trade" || S.ws === "portfolio") loadToday(); if (S.ws === "portfolio") loadOrders(); });
    every(60000, () => { if (S.ws === "scan") loadAlerts(); });
    setInterval(renderAges, 1000);
  }
  boot();
})();
