/* CA Trader terminal. Every number on screen comes from the backend (Upstox data or values computed from it) and
   carries its age; nothing is invented client-side. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));
  const fmt = (v, d = 2) => (num(v) === null ? "—" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const sgn = (v, d = 1) => (num(v) === null ? "—" : (Number(v) > 0 ? "+" : "") + Number(v).toFixed(d));
  const cls = (v) => (num(v) === null ? "" : Number(v) > 0 ? "up" : Number(v) < 0 ? "dn" : "");
  const short = (v) => { const n = num(v); if (n === null) return "—"; const a = Math.abs(n); const s = a >= 1e7 ? (a / 1e7).toFixed(2) + "Cr" : a >= 1e5 ? (a / 1e5).toFixed(1) + "L" : a >= 1e3 ? (a / 1e3).toFixed(1) + "K" : a.toFixed(0); return (n < 0 ? "−" : "") + s; };
  const store = { get(k, d) { try { const v = localStorage.getItem("cat_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
                  set(k, v) { try { localStorage.setItem("cat_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } } };
  const S = { symbol: store.get("symbol", "NIFTY"), ws: "trade", watch: [], watchlists: [], wlId: null, quotes: {}, prev: {}, reco: null, chain: null, updated: {}, positions: null, chart: null };
  const INDICES = [["NIFTY 50", "NIFTY"], ["SENSEX", "SENSEX"], ["BANKNIFTY", "BANKNIFTY"]];

  // ---------------- network & helpers ----------------
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
    } catch (e) { if (e.name === "AbortError") throw new Error("Timed out waiting for the server"); throw e; } finally { clearTimeout(t); }
  }
  function toast(msg) { const el = $("toast"); el.textContent = msg; el.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), 3200); }
  function mark(key) { S.updated[key] = Date.now(); renderAges(); }
  function renderAges() {
    const now = Date.now();
    document.querySelectorAll("[data-age]").forEach((el) => { const t = S.updated[el.dataset.age]; if (!t) { el.textContent = "—"; return; }
      const s = Math.round((now - t) / 1000); el.textContent = s < 60 ? `updated ${s}s ago` : `updated ${Math.round(s / 60)}m ago`;
      el.classList.toggle("stale", s > 30 && s <= 120); el.classList.toggle("dead", s > 120); });
    const q = S.updated.quotes, f = $("feedState"); if (!q) return; const age = (now - q) / 1000;
    f.classList.toggle("live", age < 10); f.classList.toggle("stale", age >= 10 && age < 60); f.classList.toggle("down", age >= 60);
    $("feedText").textContent = `Upstox · ${Math.round(age)}s`;
  }
  function every(ms, fn) { fn(); setInterval(() => { if (!document.hidden) fn(); }, ms); }
  function flash(el, dir) { if (!el || !dir) return; el.classList.remove("flash-up", "flash-dn"); void el.offsetWidth; el.classList.add(dir > 0 ? "flash-up" : "flash-dn"); setTimeout(() => el.classList.remove("flash-up", "flash-dn"), 650); }
  const isIdx = (s) => /^(NIFTY|BANKNIFTY|FINNIFTY|MIDCPNIFTY|SENSEX|BANKEX)$/.test(String(s).split(" ")[0]);
  const hasOptions = (s) => isIdx(s) || /^(CRUDEOIL|NATURALGAS|GOLD|SILVER)/.test(s);

  // ---------------- marketwatch ----------------
  async function loadWatchlists() {
    try { const d = await api("/api/watchlists"); S.watchlists = d.items || []; const sel = store.get("wl", null);
      const g = S.watchlists.find((x) => x.id === sel) || S.watchlists[0]; S.wlId = g ? g.id : null;
      S.watch = g && g.items ? g.items.map((i) => (i.symbol || "").toUpperCase()).filter(Boolean) : []; } catch { S.watch = []; }
    if (!S.watch.length) S.watch = [S.symbol];
    if (!S.watch.includes(S.symbol)) S.symbol = S.watch[0];
    $("wlSelect").innerHTML = S.watchlists.map((g) => `<option value="${g.id}" ${g.id === S.wlId ? "selected" : ""}>${esc(g.name || "Watchlist " + g.id)}</option>`).join("");
    renderWatch();
  }
  $("wlSelect").addEventListener("change", async (e) => { store.set("wl", +e.target.value); await loadWatchlists(); loadQuotes(); });
  function renderWatch() {
    $("watchCount").textContent = `${S.watch.length} instrument${S.watch.length === 1 ? "" : "s"}`;
    $("watchList").innerHTML = S.watch.map((s, i) => { const q = S.quotes[s] || {};
      return `<li class="wrow ${s === S.symbol ? "sel" : ""}" data-sym="${esc(s)}" tabindex="0"><span class="sym" title="${esc(s)}">${esc(s)}</span>` +
        `<span class="chg ${cls(q.change_pct)}">${num(q.change_pct) === null ? "" : sgn(q.change_pct, 2) + "%"}</span><span class="ltp ${cls(q.change_pct)}" data-ltp="${esc(s)}">${fmt(q.ltp)}</span>` +
        `<span class="acts"><button type="button" class="act b" data-buy="${esc(s)}" title="Buy">B</button><button type="button" class="act s" data-sell="${esc(s)}" title="Sell">S</button>` +
        `<button type="button" class="act g" data-chart="${esc(s)}" title="Chart"><svg><use href="#i-chart"/></svg></button><button type="button" class="act g" data-remove="${esc(s)}" title="Remove"><svg><use href="#i-x"/></svg></button></span></li>`; }).join("");
  }
  $("watchList").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-buy],[data-sell],[data-chart],[data-remove]"); const row = e.target.closest(".wrow");
    if (b && b.dataset.remove) { e.stopPropagation(); try { await api(`/api/watchlists/${S.wlId}/items/${encodeURIComponent(b.dataset.remove)}`, { method: "DELETE" }); await loadWatchlists(); toast(`Removed ${b.dataset.remove}`); } catch (err) { toast(err.message); } return; }
    if (b && (b.dataset.buy || b.dataset.sell)) { const s = b.dataset.buy || b.dataset.sell; const q = S.quotes[s] || {}; openTicket(b.dataset.buy ? "BUY" : "SELL", { symbol: s, entry: num(q.ltp), lot: 1, sl: null, tgt: null }); return; }
    if (row) { selectSymbol(row.dataset.sym); if (S.ws !== "trade" && S.ws !== "options") location.hash = "#trade"; }
  });
  $("watchList").addEventListener("keydown", (e) => { if (e.key === "Enter") { const r = e.target.closest(".wrow"); if (r) selectSymbol(r.dataset.sym); } });
  let searchT;
  $("symSearch").addEventListener("input", (e) => {
    clearTimeout(searchT); const q = e.target.value.trim(); if (q.length < 2) { $("searchResults").innerHTML = ""; return; }
    searchT = setTimeout(async () => { try { const d = await api(`/api/instruments/search?q=${encodeURIComponent(q)}`);
      $("searchResults").innerHTML = (d.items || []).slice(0, 14).map((it) => `<div class="res"><div class="nm"><b>${esc(it.symbol)}</b><div>${esc(it.name || "")} · ${esc(it.exchange || "")}</div></div>` +
        `<button type="button" class="act g" data-add="${esc(it.symbol)}" data-key="${esc(it.instrument_key || "")}" title="Add to watchlist">+</button><button type="button" class="act g" data-open="${esc(it.symbol)}" title="Open chart"><svg><use href="#i-chart"/></svg></button></div>`).join("") || `<div class="res muted">No matches</div>`; } catch { /* ignore */ } }, 220);
  });
  $("searchResults").addEventListener("click", async (e) => {
    const add = e.target.closest("[data-add]"), open = e.target.closest("[data-open]");
    if (open) { $("searchResults").innerHTML = ""; $("symSearch").value = ""; selectSymbol(open.dataset.open); location.hash = "#trade"; return; }
    if (add && S.wlId) { try { await api(`/api/watchlists/${S.wlId}/items`, { method: "POST", body: { symbol: add.dataset.add, instrument_key: add.dataset.key || undefined } });
      $("searchResults").innerHTML = ""; $("symSearch").value = ""; await loadWatchlists(); loadQuotes(); toast(`Added ${add.dataset.add}`); } catch (err) { toast(err.message); } }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".watch-search")) $("searchResults").innerHTML = ""; if (!e.target.closest(".cc-pop-wrap")) document.querySelectorAll(".cc-pop-wrap .pop").forEach((p) => (p.hidden = true)); });

  async function loadQuotes() {
    const syms = [...new Set([...S.watch, S.symbol, ...INDICES.map((x) => x[1])])];
    try {
      const d = await api(`/api/market/quotes?instruments=${encodeURIComponent(syms.join(","))}`);
      (d.items || []).forEach((q) => { const k = String(q.instrument || q.symbol || "").toUpperCase(); if (!k) return; S.prev[k] = S.quotes[k]; S.quotes[k] = q; });
      mark("quotes");
      S.watch.forEach((s) => { const el = document.querySelector(`[data-ltp="${CSS.escape(s)}"]`); const q = S.quotes[s] || {}, p = S.prev[s] || {};
        if (!el) return; const row = el.closest(".wrow"); el.textContent = fmt(q.ltp); el.className = `ltp ${cls(q.change_pct)}`;
        const ch = row.querySelector(".chg"); ch.textContent = num(q.change_pct) === null ? "" : sgn(q.change_pct, 2) + "%"; ch.className = `chg ${cls(q.change_pct)}`;
        if (num(p.ltp) !== null && num(q.ltp) !== null && q.ltp !== p.ltp) flash(el, q.ltp - p.ltp); });
      renderIndexBar();
      const q = S.quotes[S.symbol]; if (q && S.chart && S.chart.symbol === S.symbol) S.chart.tick(num(q.ltp));
    } catch { /* feed indicator shows staleness */ }
  }
  function renderIndexBar() {
    $("indexBar").innerHTML = INDICES.map(([label, s]) => { const q = S.quotes[s] || {};
      return `<span class="idx-item" data-sym="${s}"><b>${label}</b><span class="num ${cls(q.change_pct)}">${fmt(q.ltp)}</span><span class="small ${cls(q.change_pct)}">${num(q.change_pct) === null ? "" : sgn(q.net_change, 2) + " (" + sgn(q.change_pct, 2) + "%)"}</span></span>`; }).join("");
  }
  $("indexBar").addEventListener("click", (e) => { const i = e.target.closest("[data-sym]"); if (i) { selectSymbol(i.dataset.sym); location.hash = "#trade"; } });
  function selectSymbol(sym) {
    if (!sym) return; S.symbol = sym.toUpperCase(); store.set("symbol", S.symbol);
    document.querySelectorAll(".wrow").forEach((r) => r.classList.toggle("sel", r.dataset.sym === S.symbol));
    S.reco = null; S.chain = null; $("sigSide").innerHTML = `<span class="skeleton w60"></span>`;
    if (S.ws === "trade") { loadReco(); loadCandles(); loadMiniChain(); loadStockMantra(); }
    if (S.ws === "options") loadMiniChain();
    if (S.ws === "research") loadResearch();
  }

  // ---------------- chart ----------------
  function initChart() {
    if (S.chart || !window.CAChart || !window.LightweightCharts) return;
    S.chart = window.CAChart.create($("chartCard"), { onTimeframe: () => loadCandles() });
  }
  const DAYS = { "1m": 3, "3m": 5, "5m": 10, "15m": 20, "30m": 30, "60m": 60, "1D": 365 };
  async function loadCandles() {
    initChart(); if (!S.chart) return;
    const sym = S.symbol, tf = S.chart.timeframe;
    try { const d = await api(`/api/market/candles/${encodeURIComponent(sym)}?timeframe=${tf}&days=${DAYS[tf] || 10}`, { timeout: 30000 });
      if (sym !== S.symbol) return; S.chart.setData(d.candles || [], sym, tf); mark("candles"); applyChartLevels(); }
    catch (e) { S.chart.setData([], sym, tf); toast(`Chart: ${e.message}`); }
  }
  function applyChartLevels() {
    if (!S.chart) return; const r = S.reco || {}; const m = r.signal_model || {}; const u = r.underlying_recommendation || {};
    const dec = m.decision === "BUY" || m.decision === "SELL";
    const src = r.option_type ? u : r;   // option trades: show the underlying levels on the underlying chart
    S.chart.setLevels(dec ? [{ price: num(src.entry), title: "Entry", color: "--muted" }, { price: num(src.stop_loss), title: "SL", color: "--dn" }, { price: num(src.target), title: "Target", color: "--up" }] : []);
  }

  // ---------------- signal ----------------
  async function loadReco() {
    const sym = S.symbol;
    try { const r = await api(`/api/recommendations/${encodeURIComponent(sym)}?timeframe=5m`, { timeout: 30000 });
      if (sym !== S.symbol) return; S.reco = r; mark("reco"); renderSignal(); renderWhy(); applyChartLevels(); loadStockMantra(); }
    catch (e) { $("sigSide").textContent = "Unavailable"; $("sigRationale").textContent = e.message; }
  }
  const modelOf = (r) => (r && r.signal_model) || {};
  function renderSignal() {
    const r = S.reco || {}, m = modelOf(r);
    const dec = m.available && (m.decision === "BUY" || m.decision === "SELL") ? m.decision : null;
    let head = "No trade", c = "";
    if (dec === "BUY") { head = isIdx(S.symbol) ? "Buy call" : "Buy"; c = "up"; } else if (dec === "SELL") { head = isIdx(S.symbol) ? "Buy put" : "Sell"; c = "dn"; } else if (!m.available) head = "No data";
    const side = $("sigSide"); side.textContent = head; side.className = "sig-side " + c;
    const contract = (dec && (dec === "BUY" ? r.call_option : r.put_option)) || r.recommended_option || {};
    $("sigSym").textContent = dec ? (contract.display || contract.symbol || r.display_symbol || S.symbol) : S.symbol;
    const entry = num(contract.entry) ?? num(r.entry), sl = num(contract.stop_loss) ?? num(r.stop_loss), tgt = num(contract.target) ?? num(r.target);
    const ltp = num(contract.cmp) ?? num(contract.ltp) ?? num(r.cmp), lot = num(contract.lot_size) ?? num((r.instrument || {}).lot_size);
    const rr = entry && sl && tgt && entry !== sl ? Math.abs(tgt - entry) / Math.abs(entry - sl) : null;
    $("levels").innerHTML = dec ? [["Entry", fmt(entry)], ["LTP", fmt(ltp)], ["Stop loss", `<span class="dn">${fmt(sl)}</span>`], ["Target", `<span class="up">${fmt(tgt)}</span>`],
      ["Risk : reward", rr ? "1 : " + rr.toFixed(2) : "—"], ["Lot size", fmt(lot, 0)], ["Risk per lot", entry && sl && lot ? "₹" + fmt(Math.abs(entry - sl) * lot, 0) : "—"]].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")
      : `<dt>Why no trade</dt><dd>${m.available ? `${m.agreeing}/${m.factors_used} agree` : "—"}</dd>`;
    const score = num(m.score);
    $("scoreVal").textContent = score === null ? "—" : sgn(score); $("scoreVal").className = "num " + cls(score);
    $("gaugeNeedle").style.left = `${((Math.max(-100, Math.min(100, score || 0)) + 100) / 2)}%`;
    if (m.gate) { $("gateLo").style.left = `${(100 - m.gate) / 2}%`; $("gateHi").style.left = `${(100 + m.gate) / 2}%`; }
    const conf = num((m.confidence || {}).pct);
    $("confVal").textContent = conf === null ? "n/a" : `${Math.round(conf)}%`;
    $("ringFg").style.strokeDashoffset = String(119.4 * (1 - (conf || 0) / 100));
    $("ringFg").style.stroke = conf === null ? "var(--line-strong)" : conf >= 60 ? "var(--up)" : conf >= 50 ? "var(--warn)" : "var(--dn)";
    $("confRing").title = (m.confidence || {}).label || "Confidence not measured";
    $("sigRationale").textContent = dec ? (r.rationale || "") : m.available ? `Score ${sgn(score)} is inside the ±${fmt(m.gate, 0)} gate. A contract and levels appear when it crosses and enough factors agree.` : (m.reason || "");
    S.ticketDefaults = { symbol: contract.symbol || r.symbol || S.symbol, entry, sl, tgt, lot: lot || 1 };
    renderPulse();
  }
  function renderPulse() {
    const q = S.quotes[S.symbol] || {}, ch = S.chain || {}, st = ch.strikes || [];
    const coi = st.reduce((a, s) => a + (num((s.call || {}).oi) || 0), 0), poi = st.reduce((a, s) => a + (num((s.put || {}).oi) || 0), 0);
    $("pulseBox").innerHTML = [["LTP", fmt(q.ltp)], ["Day change", num(q.change_pct) === null ? "—" : `<span class="${cls(q.change_pct)}">${sgn(q.change_pct, 2)}%</span>`],
      ["Day range", q.low ? `${fmt(q.low, 0)}–${fmt(q.high, 0)}` : "—"], ["PCR (OI)", coi ? (poi / coi).toFixed(2) : "—"]].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("");
  }
  function renderWhy() {
    const m = modelOf(S.reco);
    if (!m.available) { $("factorRows").innerHTML = `<tr><td colspan="6" class="muted">${esc(m.reason || "Signal model has no data for this instrument.")}</td></tr>`; return; }
    $("confBasis").textContent = (m.confidence || {}).label ? `Confidence = ${(m.confidence || {}).label}.` : "";
    const cal = m.calibration || {}, v = (cal.validation || {}).test || {};
    $("calibNote").textContent = cal.version ? `Weights ${cal.version}: ${cal.source || ""}.${v.fired ? ` Held-out check: agreed with Stock Mantra on ${v.agree_with_mantra}/${v.fired} calls, right on ${v.model_right}/${v.resolved}.` : ""}` : "";
    $("factorRows").innerHTML = (m.rows || []).map((row) => { const p = num(row.points), w = Math.min(50, Math.abs(p || 0) / 2);
      const bar = p === null ? "" : p >= 0 ? `<span style="left:50%;width:${w}%;background:var(--up)"></span>` : `<span class="neg" style="right:50%;width:${w}%;background:var(--dn)"></span>`;
      return `<tr class="${row.available ? "" : "off"}" title="${esc(row.rule)}"><td><b>${esc(row.name)}</b><span class="src">${esc(row.source)}</span></td><td class="num">${esc(row.input)}</td>` +
        `<td class="r ${cls(p)}">${p === null ? "—" : sgn(p)}</td><td class="r">${fmt(row.weight_pct, 1)}%</td><td><div class="bar">${bar}</div></td><td class="r ${cls(row.contribution)}">${sgn(row.contribution)}</td></tr>`; }).join("");
  }
  async function loadStockMantra() {
    try { const d = await api("/api/telegram/stock-mantra-feed"); const root = S.symbol.split(" ")[0];
      const call = (d.setups || []).find((x) => x.underlying === root); mark("sm"); const box = $("smBox");
      if (!call) { box.className = "sm-card"; box.innerHTML = `<div class="eyebrow">Stock Mantra</div><div class="muted small">${d.live_stream_active ? `No ${esc(root)} call in this session.` : "Listener not connected."}</div>`; return; }
      const ours = modelOf(S.reco).decision, his = call.option_type === "CE" ? "BUY" : "SELL"; const agree = ours === his ? "agree" : ours === "BUY" || ours === "SELL" ? "disagree" : "";
      box.className = `sm-card ${agree}`;
      box.innerHTML = `<div class="eyebrow">Stock Mantra · ${esc(call.time)}</div><div><b>${esc(call.symbol)}</b> near ₹${fmt(call.entry)}</div><div class="small muted">Target ${call.target_1 ? "₹" + fmt(call.target_1) : "open"} · SL ${call.stop_loss ? "₹" + fmt(call.stop_loss) : "not stated"}${num(call.cmp) !== null ? ` · now ₹${fmt(call.cmp)} (${sgn(call.pnl_pct_from_entry)}%)` : ""}</div>` +
        `<div class="small" style="margin-top:4px">${agree === "agree" ? "✓ Our model agrees" : agree === "disagree" ? `Our model says ${esc(ours)}` : "Our model: no trade"}</div>`;
      if (S.chart && call.raw_date) S.chart.setMarkers([{ at: call.raw_date, position: his === "BUY" ? "belowBar" : "aboveBar", color: his === "BUY" ? getComputedStyle(document.documentElement).getPropertyValue("--up") : getComputedStyle(document.documentElement).getPropertyValue("--dn"), shape: his === "BUY" ? "arrowUp" : "arrowDown", text: "SM" }]);
    } catch { /* optional */ }
  }

  // ---------------- dock: chain / positions / orders ----------------
  document.querySelectorAll("[data-dock]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-dock]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    document.querySelectorAll("[data-dock-body]").forEach((x) => (x.hidden = x.dataset.dockBody !== b.dataset.dock));
    store.set("dock", b.dataset.dock); if (b.dataset.dock === "orders") loadOrders(); if (b.dataset.dock === "positions") loadToday();
  }));
  async function loadMiniChain() {
    if (!hasOptions(S.symbol)) { S.chain = null; $("miniChain").innerHTML = `<tr><td colspan="7" class="muted">No options for ${esc(S.symbol)}</td></tr>`; if (S.ws === "options") renderFullChain(); return; }
    try { const d = await api(`/api/options/${encodeURIComponent(S.symbol.split(" ")[0])}`, { timeout: 30000 }); S.chain = d; mark("chain"); renderMiniChain(); renderPulse(); if (S.ws === "options") renderFullChain(); }
    catch (e) { $("miniChain").innerHTML = `<tr><td colspan="7" class="muted">${esc(e.message)}</td></tr>`; }
  }
  const atmIndex = (st, spot) => { let bi = 0, bd = Infinity; st.forEach((s, i) => { const d = Math.abs(Number(s.strike) - spot); if (d < bd) { bd = d; bi = i; } }); return bi; };
  function chainRow(s, isAtm, spot, maxOi, full) {
    const c = s.call || {}, p = s.put || {}, itmC = s.strike < spot, itmP = s.strike > spot;
    const oiBar = (v, put) => `<span class="oi-bar ${put ? "put" : ""}" style="width:${Math.round(((num(v) || 0) / (maxOi || 1)) * 46)}px"></span>`;
    const pick = (n, k) => `data-pick="${esc(n.trading_symbol || n.symbol || `${S.symbol.split(" ")[0]} ${s.strike} ${k}`)}" data-px="${num(n.ltp) ?? ""}" data-lot="${num(n.lot_size) ?? ""}"`;
    const left = full ? [`${oiBar(c.oi)}${short(c.oi)}`, `<span class="${cls(c.change_oi)}">${short(c.change_oi)}</span>`, fmt(c.iv, 1), fmt(c.delta, 2)] : [short(c.oi), `<span class="${cls(c.change_oi)}">${short(c.change_oi)}</span>`];
    const right = full ? [fmt(p.delta, 2), fmt(p.iv, 1), `<span class="${cls(p.change_oi)}">${short(p.change_oi)}</span>`, `${short(p.oi)}${oiBar(p.oi, true)}`] : [`<span class="${cls(p.change_oi)}">${short(p.change_oi)}</span>`, short(p.oi)];
    return `<tr class="${isAtm ? "atm" : ""}">${left.map((x) => `<td class="${itmC ? "itm" : ""}">${x}</td>`).join("")}<td class="px ${itmC ? "itm" : ""}" ${pick(c, "CE")}>${fmt(c.ltp)}</td>` +
      `<td class="mid">${fmt(s.strike, 0)}</td><td class="px ${itmP ? "itm" : ""}" ${pick(p, "PE")}>${fmt(p.ltp)}</td>${right.map((x) => `<td class="${itmP ? "itm" : ""}">${x}</td>`).join("")}</tr>`;
  }
  function renderMiniChain() {
    const d = S.chain || {}, st = d.strikes || [], spot = num(d.spot);
    if (!st.length || !spot) { $("miniChain").innerHTML = `<tr><td colspan="7" class="muted">${esc(d.error || "No chain from Upstox")}</td></tr>`; return; }
    const a = atmIndex(st, spot), rows = st.slice(Math.max(0, a - 5), a + 6), maxOi = Math.max(...rows.map((s) => Math.max(num((s.call || {}).oi) || 0, num((s.put || {}).oi) || 0)));
    $("miniChain").innerHTML = rows.map((s) => chainRow(s, s === st[a], spot, maxOi, false)).join("");
    const coi = st.reduce((x, s) => x + (num((s.call || {}).oi) || 0), 0), poi = st.reduce((x, s) => x + (num((s.put || {}).oi) || 0), 0);
    $("pcrVal").textContent = `PCR ${coi ? (poi / coi).toFixed(2) : "—"} · expiry ${d.expiry || "—"}`;
  }
  function renderFullChain() {
    const d = S.chain || {}, st = d.strikes || [], spot = num(d.spot);
    $("chainTitle").textContent = `${S.symbol.split(" ")[0]} option chain${d.expiry ? " · " + d.expiry : ""}`;
    if (!st.length || !spot) { $("chainRows").innerHTML = `<tr><td colspan="11" class="muted">${esc(d.error || "No option chain from Upstox for this instrument.")}</td></tr>`; $("chainStats").innerHTML = ""; return; }
    const coi = st.reduce((x, s) => x + (num((s.call || {}).oi) || 0), 0), poi = st.reduce((x, s) => x + (num((s.put || {}).oi) || 0), 0);
    const a0 = atmIndex(st, spot), view = st.slice(Math.max(0, a0 - 20), a0 + 21);
    const pain = (k) => st.reduce((x, s) => x + Math.max(0, k - s.strike) * (num((s.call || {}).oi) || 0) + Math.max(0, s.strike - k) * (num((s.put || {}).oi) || 0), 0);
    const mp = st.reduce((best, s) => (pain(s.strike) < pain(best) ? s.strike : best), st[0].strike);
    const maxC = st.reduce((b, s) => ((num((s.call || {}).oi) || 0) > (num((b.call || {}).oi) || 0) ? s : b), st[0]), maxP = st.reduce((b, s) => ((num((s.put || {}).oi) || 0) > (num((b.put || {}).oi) || 0) ? s : b), st[0]);
    $("chainStats").innerHTML = [["Spot", fmt(spot)], ["PCR (OI)", coi ? (poi / coi).toFixed(2) : "—"], ["Max pain", fmt(mp, 0)], ["Call wall", fmt(maxC.strike, 0)], ["Put wall", fmt(maxP.strike, 0)]].map(([k, v]) => `<div><span class="k">${k}</span><span class="v">${v}</span></div>`).join("");
    const maxOi = Math.max(...view.map((s) => Math.max(num((s.call || {}).oi) || 0, num((s.put || {}).oi) || 0)));
    $("chainRows").innerHTML = view.map((s) => chainRow(s, s === st[a0], spot, maxOi, true)).join(""); mark("chainFull");
    const atmRow = $("chainRows").querySelector("tr.atm"); if (atmRow && !renderFullChain._scrolled) { atmRow.scrollIntoView({ block: "center" }); renderFullChain._scrolled = true; }
  }
  ["miniChain", "chainRows"].forEach((id) => $(id).addEventListener("click", (e) => { const td = e.target.closest("td[data-pick]"); if (td) openTicket("BUY", { symbol: td.dataset.pick, entry: num(td.dataset.px), lot: num(td.dataset.lot) || 1, sl: null, tgt: null }); }));

  async function loadToday() {
    try { const p = await api("/api/positions"); S.positions = p; mark("pos"); const open = p.open_positions || [];
      $("posCount").textContent = open.length || "";
      $("dockPos").innerHTML = open.map((x) => `<tr><td><b>${esc(x.symbol)}</b></td><td><span class="pill ${x.side === "BUY" ? "up" : "dn"}">${esc(x.side)}</span></td><td class="r">${fmt(x.quantity, 0)}</td><td class="r">${fmt(x.avg_price)}</td><td class="r">${fmt(x.ltp ?? x.current_price)}</td><td class="r ${cls(x.pnl)}">₹${fmt(x.pnl, 0)}</td><td class="r"><button type="button" class="btn tiny ghost" data-exit="${esc(x.id)}">Exit</button></td></tr>`).join("") || `<tr><td colspan="7" class="muted">No open positions.</td></tr>`;
      if (S.ws === "portfolio") renderPortfolio(p, await api("/api/funds").catch(() => ({})));
    } catch { /* ignore */ }
  }
  async function loadOrders() {
    try { const d = await api("/api/orders"); const items = (d.items || []).slice(0, 60);
      const pill = (s) => `<span class="pill ${/FILL/.test(s) ? "up" : /REJECT|CANCEL/.test(s) ? "dn" : "warn"}">${esc(s)}</span>`;
      $("dockOrders").innerHTML = items.slice(0, 15).map((o) => `<tr><td>${esc(String(o.created_at || "").replace("T", " ").slice(5, 16))}</td><td>${esc(o.symbol)}</td><td>${esc(o.side)}</td><td class="r">${fmt(o.quantity, 0)}</td><td class="r">${fmt(o.price)}</td><td>${pill(o.status)}</td></tr>`).join("") || `<tr><td colspan="6" class="muted">No orders.</td></tr>`;
      $("orderRows").innerHTML = items.map((o) => `<tr><td>${esc(String(o.created_at || "").replace("T", " ").slice(5, 16))}</td><td>${esc(o.symbol)}</td><td>${esc(o.side)}</td><td class="r">${fmt(o.quantity, 0)}</td><td class="r">${fmt(o.price)}</td><td>${esc(o.order_type)}</td><td>${pill(o.status)}</td>` +
        `<td class="r">${/PENDING|OPEN/.test(o.status || "") ? `<button type="button" class="btn tiny ghost" data-cancel="${esc(o.id)}">Cancel</button>` : ""}</td></tr>`).join("") || `<tr><td colspan="8" class="muted">No orders.</td></tr>`;
    } catch (e) { $("orderRows").innerHTML = `<tr><td colspan="8">${esc(e.message)}</td></tr>`; }
  }
  $("orderRows").addEventListener("click", async (e) => { const b = e.target.closest("[data-cancel]"); if (!b) return; try { await api(`/api/orders/${encodeURIComponent(b.dataset.cancel)}?hard=0`, { method: "DELETE" }); toast("Order cancelled"); loadOrders(); } catch (err) { toast(err.message); } });

  // ---------------- order ticket ----------------
  function setTicketSide(side) { $("tSide").value = side; $("tSideToggle").checked = side === "SELL"; $("ticketHead").classList.toggle("sell", side === "SELL");
    $("ticketTitle").textContent = side === "SELL" ? "Sell" : "Buy"; $("tSubmit").className = `btn ${side === "SELL" ? "sell" : "buy"}`; updateTicket(); }
  function openTicket(side, preset) {
    const d = { ...(S.ticketDefaults || { symbol: S.symbol, lot: 1 }), ...(preset || {}) };
    $("tSymbol").value = d.symbol || S.symbol; $("ticketSym").textContent = d.symbol || S.symbol; $("tLot").value = d.lot || 1; $("tLots").value = 1;
    $("tType").value = d.entry ? "LIMIT" : "MARKET"; $("tPrice").value = d.entry ?? ""; $("tSl").value = d.sl ?? ""; $("tTgt").value = d.tgt ?? ""; $("tLive").checked = false;
    setTicketSide(side || "BUY"); $("ticket").showModal(); setTimeout(() => $("tLots").focus(), 50);
  }
  function updateTicket() {
    const qty = (+$("tLots").value || 0) * (+$("tLot").value || 0), px = +$("tPrice").value || 0, sl = +$("tSl").value || 0, tg = +$("tTgt").value || 0, side = $("tSide").value, dir = side === "BUY" ? 1 : -1;
    const risk = px && sl ? Math.abs(px - sl) * qty : null, reward = px && tg ? Math.abs(tg - px) * qty : null;
    $("ticketSym").textContent = $("tSymbol").value;
    $("tSummary").innerHTML = `${side} <b>${qty}</b> × ${esc($("tSymbol").value)} ${$("tType").value === "LIMIT" && px ? "@ ₹" + fmt(px) : "at market"}` +
      `${px ? ` · value ₹${fmt(px * qty, 0)}` : ""}${risk !== null ? ` · risk <span class="dn">₹${fmt(risk, 0)}</span>` : ""}${reward !== null ? ` · reward <span class="up">₹${fmt(reward, 0)}</span>` : ""}` +
      `${sl && px && (sl - px) * dir > 0 ? ` · <span class="warn">stop loss is on the wrong side</span>` : ""} · <b>${$("tLive").checked ? "LIVE order" : "paper trade"}</b>`;
    $("tSubmit").textContent = $("tLive").checked ? `Place live ${side.toLowerCase()}` : `Place paper ${side.toLowerCase()}`;
  }
  ["tLots", "tLot", "tPrice", "tSl", "tTgt", "tType", "tLive", "tSymbol"].forEach((id) => $(id).addEventListener("input", updateTicket));
  $("tSideToggle").addEventListener("change", (e) => setTicketSide(e.target.checked ? "SELL" : "BUY"));
  $("tCancel").addEventListener("click", () => $("ticket").close());
  $("ticketForm").addEventListener("submit", async (e) => {
    e.preventDefault(); const qty = (+$("tLots").value || 0) * (+$("tLot").value || 0);
    const body = { symbol: $("tSymbol").value.trim(), side: $("tSide").value, quantity: qty, order_type: $("tType").value, price: $("tType").value === "LIMIT" ? (+$("tPrice").value || null) : null,
      stop_loss: +$("tSl").value || null, target: +$("tTgt").value || null, paper: !$("tLive").checked, live: $("tLive").checked,
      entry_reco_json: S.reco ? JSON.stringify({ score: modelOf(S.reco).score, decision: modelOf(S.reco).decision, at: new Date().toISOString() }) : null };
    $("tSubmit").disabled = true;
    try { const r = await api("/api/orders", { method: "POST", body }); toast(`Order ${r.status || r.execution_state || "submitted"}`); $("ticket").close(); loadToday(); loadOrders(); }
    catch (err) { toast(`Order rejected: ${err.message}`); } finally { $("tSubmit").disabled = false; }
  });
  $("buyBtn").addEventListener("click", () => openTicket("BUY"));
  $("sellBtn").addEventListener("click", () => openTicket("SELL"));

  // ---------------- market (movers & alerts) ----------------
  let moverCat = "gainers";
  document.querySelectorAll("[data-mov]").forEach((b) => b.addEventListener("click", () => { moverCat = b.dataset.mov; document.querySelectorAll("[data-mov]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); loadMovers(); }));
  async function loadMovers() {
    $("moverRows").innerHTML = `<tr><td colspan="4"><span class="skeleton w60"></span></td></tr>`;
    try { const d = await api(`/api/market/movers?category=${moverCat}&limit=20`);
      $("moverRows").innerHTML = (d.items || []).map((m) => `<tr class="click" data-sym="${esc(m.symbol)}"><td><b>${esc(m.symbol)}</b></td><td class="r">${fmt(m.ltp)}</td><td class="r ${cls(m.change_pct)}">${sgn(m.change_pct, 2)}%</td><td class="r">${short(m.volume)}</td></tr>`).join("") || `<tr><td colspan="4" class="muted">No data from Upstox right now.</td></tr>`;
    } catch (e) { $("moverRows").innerHTML = `<tr><td colspan="4" class="muted">${esc(e.message)}</td></tr>`; }
  }
  $("moverRows").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-sym]"); if (tr) { selectSymbol(tr.dataset.sym); location.hash = "#trade"; } });
  async function loadAlerts() {
    try { const d = await api("/api/notifications"); mark("notif"); const items = d.items || [];
      const unread = items.filter((n) => !n.read && !n.is_read).length; $("alertBadge").hidden = !unread; $("alertBadge").textContent = unread > 99 ? "99+" : unread;
      $("alertList").innerHTML = items.slice(0, 80).map((n) => `<li class="${esc(n.severity || n.level || "")}"><b>${esc(n.title)}</b><br>${esc(n.message || n.body || "")}<time>${esc(String(n.created_at || "").replace("T", " ").slice(0, 16))}</time></li>`).join("") || `<li class="muted">No alerts.</li>`;
    } catch (e) { $("alertList").innerHTML = `<li>${esc(e.message)}</li>`; }
  }

  // ---------------- portfolio ----------------
  function renderPortfolio(p, f) {
    const b = (f && f.buckets) || {}, loc = (f && f.local) || {}, open = p.open_positions || [];
    const openPnl = open.reduce((a, x) => a + (num(x.pnl) || 0), 0);
    $("fundCards").innerHTML = [["Paper balance", "₹" + fmt(loc.balance ?? loc.available_balance, 0)], ["Used margin", "₹" + fmt(loc.used_margin, 0)], ["Trading bucket", "₹" + fmt((b.trading || {}).balance, 0)],
      ["Open P&L", `<span class="${cls(openPnl)}">₹${fmt(openPnl, 0)}</span>`]].map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v.replace("₹—", "—")}</div></div>`).join("");
    $("posRows").innerHTML = open.map((x) => `<tr><td><b>${esc(x.symbol)}</b><div class="muted small">${esc(x.trade_type || "")}</div></td><td><span class="pill ${x.side === "BUY" ? "up" : "dn"}">${esc(x.side)}</span></td><td class="r">${fmt(x.quantity, 0)}</td><td class="r">${fmt(x.avg_price)}</td><td class="r">${fmt(x.ltp ?? x.current_price)}</td><td class="r ${cls(x.pnl)}">₹${fmt(x.pnl, 0)}</td>` +
      `<td class="r"><input type="number" step="0.05" value="${num(x.stop_loss) ?? ""}" data-sl="${esc(x.id)}" aria-label="Stop loss for ${esc(x.symbol)}" style="width:90px" class="num"></td><td class="r">${fmt(x.target)}</td>` +
      `<td class="r"><button type="button" class="btn tiny ghost" data-trail="${esc(x.id)}">Save SL</button> <button type="button" class="btn tiny sell" data-exit="${esc(x.id)}">Exit</button></td></tr>`).join("") || `<tr><td colspan="9" class="muted">No open positions.</td></tr>`;
    const closed = (p.items || []).filter((x) => x.status === "CLOSED").slice(0, 60), tot = closed.reduce((a, x) => a + (num(x.pnl) || 0), 0), wins = closed.filter((x) => (num(x.pnl) || 0) > 0).length;
    $("pnlStats").innerHTML = [["Closed trades", closed.length], ["Winners", wins], ["Net P&L", `<span class="${cls(tot)}">₹${fmt(tot, 0)}</span>`]].map(([k, v]) => `<div><span class="k">${k}</span><span class="v">${v}</span></div>`).join("");
    $("closedRows").innerHTML = closed.map((x) => `<tr><td>${esc(String(x.updated_at || "").replace("T", " ").slice(0, 16))}</td><td>${esc(x.symbol)}</td><td>${esc(x.side)}</td><td class="r">${fmt(x.quantity, 0)}</td><td class="r">${fmt(x.avg_price)}</td><td class="r">${fmt(x.exit_price)}</td><td class="r ${cls(x.pnl)}">₹${fmt(x.pnl, 0)}</td></tr>`).join("") || `<tr><td colspan="7" class="muted">No closed trades.</td></tr>`;
  }
  async function exitOrTrail(e) {
    const ex = e.target.closest("[data-exit]"), tr = e.target.closest("[data-trail]");
    if (ex) { if (ex.dataset.confirm !== "1") { ex.dataset.confirm = "1"; ex.textContent = "Confirm"; setTimeout(() => { ex.dataset.confirm = ""; ex.textContent = "Exit"; }, 4000); return; }
      try { const r = await api(`/api/positions/${encodeURIComponent(ex.dataset.exit)}/square-off`, { method: "POST", body: {} }); toast(`Exited at ₹${fmt(r.exit_price)} · P&L ₹${fmt(r.final_pnl, 0)}`); loadToday(); } catch (err) { toast(err.message); } }
    if (tr) { const inp = document.querySelector(`input[data-sl="${CSS.escape(tr.dataset.trail)}"]`); try { await api(`/api/positions/${encodeURIComponent(tr.dataset.trail)}/trail-sl`, { method: "POST", body: { stop_loss: +inp.value } }); toast("Stop loss updated"); loadToday(); } catch (err) { toast(err.message); } }
  }
  $("posRows").addEventListener("click", exitOrTrail); $("dockPos").addEventListener("click", exitOrTrail);

  // ---------------- research ----------------
  let rtab = store.get("rtab", "context");
  document.querySelectorAll("[data-rt]").forEach((b) => b.addEventListener("click", () => { rtab = b.dataset.rt; store.set("rtab", rtab); loadResearch(); }));
  const panel = (title, body, age) => `<section class="card"><div class="card-head"><h2>${title}</h2>${age ? `<span class="age">${esc(age)}</span>` : ""}</div>${body}</section>`;
  const kvRows = (pairs) => `<div class="kv">${pairs.map(([k, v]) => `<div class="row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("")}</div>`;
  const unavailable = (o) => `<p class="note" style="padding:0 14px 12px">${esc((o && o.reason) || "Not available")}</p>`;
  const tbl = (head, rows) => `<div class="scroll-x" style="padding:0 14px 12px"><table class="list"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
  async function loadResearch() {
    document.querySelectorAll("[data-rt]").forEach((x) => x.setAttribute("aria-selected", String(x.dataset.rt === rtab)));
    const token = (loadResearch.seq = (loadResearch.seq || 0) + 1), body = $("researchBody"), sym = S.symbol.split(" ")[0];
    body.innerHTML = `<section class="card" style="padding:16px"><span class="skeleton w60"></span><br><br><span class="skeleton w40"></span></section>`;
    try {
      if (rtab === "context") {
        const d = await api(`/api/market/other-factors?symbol=${encodeURIComponent(sym)}`, { timeout: 45000 }); if (token !== loadResearch.seq) return;
        const b = d.market_breadth || {}, s = d.sector_rotation || {}, rg = d.regime || {}, v = d.volatility_surface || {}, oi = d.oi_matrix || {}, mi = d.microstructure || {};
        body.innerHTML = `<div class="grid2">` +
          panel("NIFTY 50 breadth", b.available ? kvRows([["Advances / declines", `<span class="up">${b.advances}</span> / <span class="dn">${b.declines}</span>`], ["A/D ratio", fmt(b.ad_ratio)], ["Up-volume share", b.up_volume_pct === null ? "—" : fmt(b.up_volume_pct, 1) + "%"], ["Reading", `<span class="pill ${b.signal === "BULLISH" ? "up" : b.signal === "BEARISH" ? "dn" : ""}">${esc(b.signal)}</span>`]]) : unavailable(b), d.updated_at) +
          panel("Regime (signal model)", rg.available ? kvRows([["Regime", esc(rg.current_regime)], ["Score / gate", `${sgn(rg.score)} / ±${fmt(rg.gate, 0)}`], ["ADX", fmt(rg.adx, 1)]]) : unavailable(rg)) +
          panel("Volatility", kvRows([["India VIX", fmt(v.india_vix)], ["VIX change", num(v.india_vix_change_pct) === null ? "—" : sgn(v.india_vix_change_pct, 2) + "%"], ["ATM IV", fmt(v.atm_iv, 1)], ["Put − call IV skew", fmt(v.skew_put_minus_call, 1)], ["HV 20-day", fmt(v.hv_20, 1)]])) +
          panel(`Open interest${oi.expiry ? " · " + esc(oi.expiry) : ""}`, oi.available ? kvRows([["PCR (OI)", fmt(oi.pcr_oi)], ["PCR (volume)", fmt(oi.pcr_volume)], ["Max pain", fmt(oi.max_pain_strike, 0)]]) + tbl(`<th>Biggest OI changes</th><th class="r">ΔOI</th><th class="r">LTP</th>`, (oi.buildup_highlights || []).map((m) => `<tr><td>${esc(m.strike)}</td><td class="r ${cls(m.oi_change)}">${short(m.oi_change)}</td><td class="r">${fmt(m.ltp)}</td></tr>`).join("")) : unavailable(oi)) +
          panel("Order book", mi.available ? kvRows([["Bid / ask quantity", `${fmt(mi.bid_qty_pct, 1)}% / ${fmt(mi.ask_qty_pct, 1)}%`], ["Imbalance", fmt(mi.imbalance_ratio)], ["Spread", fmt(mi.effective_spread_pct, 3) + "%"]]) : unavailable(mi)) + `</div>` +
          `<div style="height:12px"></div>` + panel("Sector rotation (vs NIFTY, 5 sessions)", s.available ? tbl(`<th>Sector</th><th class="r">1D</th><th class="r">5D</th><th class="r">20D</th><th class="r">RS 5D</th><th>Quadrant</th>`, s.items.map((x) => `<tr><td>${esc(x.sector)}</td><td class="r ${cls(x.ret_1d)}">${sgn(x.ret_1d, 2)}%</td><td class="r ${cls(x.ret_5d)}">${sgn(x.ret_5d, 2)}%</td><td class="r ${cls(x.ret_20d)}">${sgn(x.ret_20d, 2)}%</td><td class="r ${cls(x.rs_vs_nifty)}">${sgn(x.rs_vs_nifty, 2)}</td><td><span class="pill ${x.quadrant === "LEADING" ? "up" : x.quadrant === "LAGGING" ? "dn" : "warn"}">${esc(x.quadrant || "—")}</span></td></tr>`).join("")) : unavailable(s));
      } else if (rtab === "matrix") {
        const d = await api(`/api/market/data-inspector?instrument=${encodeURIComponent(sym)}`, { timeout: 45000 }); if (token !== loadResearch.seq) return;
        body.innerHTML = panel(`Every model input · ${esc(sym)} · now and 5 / 10 / 15 minutes ago`, `<p class="note" style="padding:0 14px">Past values are recomputed from Upstox 5-minute candles as they stood then. ${d.values_missing} unavailable · ${d.candles_used} candles.</p>` +
          tbl(`<th>Input</th><th>Group</th><th class="r">Now</th><th class="r">−5m</th><th class="r">−10m</th><th class="r">−15m</th><th class="r">Δ 5m</th><th>Source</th>`, (d.items || []).map((x) => `<tr><td>${esc(x.name)}</td><td class="muted">${esc(x.category)}</td><td class="r">${fmt(x.val_now)}</td><td class="r">${fmt(x.val_5m)}</td><td class="r">${fmt(x.val_10m)}</td><td class="r">${fmt(x.val_15m)}</td><td class="r ${cls(x.delta_5m)}">${num(x.delta_5m) === null ? "—" : sgn(x.delta_5m, 2)}</td><td class="muted small">${esc(x.primary_source)}</td></tr>`).join("")), d.timestamp);
      } else if (rtab === "mantra") {
        const d = await api(`/api/stockmantra/database`); if (token !== loadResearch.seq) return;
        const s = d.summary || {}, nm = s.new_model || {};
        const card = (t, o) => `<div class="stat"><div class="k">${t}</div><div class="v">${o && o.n !== undefined ? `${o.right ?? o.same}/${o.n} <span class="small muted">${fmt(o.pct ?? o.same_pct, 1)}%</span>` : "—"}</div></div>`;
        body.innerHTML = `<div class="stat-cards">${card("Stock Mantra right (0.3% first, 2h)", s.stock_mantra_right)}${card("Old backtest engine right", s.old_backtest_engine_right)}${card("Old live engine right", s.old_live_engine_right)}` +
          `<div class="stat"><div class="k">New model · held-out week</div><div class="v">${nm.test ? `${nm.test.agree_with_mantra}/${nm.test.fired} <span class="small muted">agree</span> · ${nm.test.model_right}/${nm.test.resolved} <span class="small muted">right</span>` : "—"}</div></div></div>` +
          panel("How this was measured", `<ul class="small" style="margin:10px 14px 4px 30px">${Object.values(d.method || {}).map((m) => `<li>${esc(m)}</li>`).join("")}</ul><p class="note" style="padding:0 14px 12px">${d.calls_parsed} calls from ${d.messages_downloaded} messages (${esc(d.period)}); ${d.calls_analysed} had enough Upstox data.</p>`) +
          panel("Every call", tbl(`<th>Time (IST)</th><th>Call</th><th class="r">Entry</th><th class="r">Reported peak</th><th class="r">Δ</th><th class="r">Implied index move</th><th>Market did</th><th>Old engine</th><th class="r">New score</th>`,
            (d.calls || []).slice().reverse().map((c) => `<tr><td>${esc(String(c.time_ist).replace("T", " ").slice(0, 16))}</td><td><b>${esc(c.contract)}</b></td><td class="r">${fmt(c.entry)}</td><td class="r">${fmt(c.claimed_peak)}</td><td class="r">${fmt(c.delta, 2)}</td><td class="r">${num(c.implied_index_move) === null ? "—" : sgn(c.implied_index_move, 0) + " pts"}</td>` +
              `<td>${c.actual_first_0p3pct ? `<span class="pill ${c.mantra_right ? "up" : c.mantra_right === false ? "dn" : ""}">${esc(c.actual_first_0p3pct)}</span>` : `<span class="muted small">${esc(c.skip || "—")}</span>`}</td><td>${esc(c.old_live_engine || "—")}</td><td class="r ${cls(c.new_model_score)}">${num(c.new_model_score) === null ? "—" : sgn(c.new_model_score)}</td></tr>`).join("")));
      } else if (rtab === "backtest") {
        const y = new Date(Date.now() - 86400000); while ([0, 6].includes(y.getDay())) y.setDate(y.getDate() - 1);
        body.innerHTML = panel("Replay the model on a past day", `<div class="formrow"><label>Symbol<input id="btSym" value="${esc(sym)}"></label><label>Date<input id="btDate" type="date" value="${y.toISOString().slice(0, 10)}"></label><button type="button" class="btn primary" id="btRun">Run replay</button><button type="button" class="btn ghost" id="bt100">Last 100 signals</button></div><p class="note" style="padding:0 14px">The model sees only candles up to each 5-minute step. SL = 1×ATR, target = 1.5×ATR on the underlying; outcome from the candles that followed.</p><div id="btOut" style="padding-bottom:12px"></div>`);
        const run = async (url) => { $("btOut").innerHTML = `<p class="note" style="padding:0 14px">Replaying…</p>`; try { const r = await api(url, { timeout: 150000 }); const it = r.items || r.trades || [], sm = r.summary || {};
          $("btOut").innerHTML = r.error ? `<p class="note" style="padding:0 14px">${esc(r.error)}</p>` : `<div class="stat-strip" style="padding:10px 14px"><div><span class="k">Signals</span><span class="v">${sm.total_trades ?? it.length}</span></div><div><span class="k">Winners</span><span class="v">${sm.wins ?? "—"}</span></div><div><span class="k">Win rate</span><span class="v">${num(sm.win_rate) === null ? "—" : fmt(sm.win_rate, 1) + "%"}</span></div><div><span class="k">Net</span><span class="v ${cls(sm.total_points)}">${sgn(sm.total_points, 1)} pts</span></div></div>` +
            tbl(`<th>Date</th><th>Time</th><th>Signal</th><th class="r">Score</th><th class="r">Entry</th><th class="r">SL</th><th class="r">Target</th><th>Outcome</th><th class="r">Points</th>`, it.map((x) => `<tr><td>${esc(x.date)}</td><td>${esc(x.time)}</td><td><span class="pill ${x.recommendation === "BUY" ? "up" : "dn"}">${esc(x.recommendation)}</span></td><td class="r">${sgn(x.score)}</td><td class="r">${fmt(x.entry)}</td><td class="r">${fmt(x.stop_loss)}</td><td class="r">${fmt(x.target)}</td><td>${esc(x.outcome)} ${esc(x.exit_time || "")}</td><td class="r ${cls(x.final_pnl)}">${sgn(x.final_pnl, 1)}</td></tr>`).join("")); } catch (e) { $("btOut").innerHTML = `<p class="note" style="padding:0 14px">${esc(e.message)}</p>`; } };
        $("btRun").addEventListener("click", () => run(`/api/recommendations/for-date?symbol=${encodeURIComponent($("btSym").value)}&date=${$("btDate").value}&limit=20`));
        $("bt100").addEventListener("click", () => run(`/api/backtest/100-trades?symbol=${encodeURIComponent($("btSym").value)}&count=100`));
      } else if (rtab === "news") {
        const d = await api(`/api/news/unified?symbol=${encodeURIComponent(sym)}`, { timeout: 30000 }); if (token !== loadResearch.seq) return;
        body.innerHTML = panel(`News · ${esc(sym)} and market`, `<ul class="feed-list">${(d.events || []).slice(0, 60).map((n) => `<li class="${n.sentiment === "Positive" ? "success" : n.sentiment === "Negative" ? "error" : ""}"><b>${esc(n.headline || n.event)}</b><br>${esc(n.summary || "")}<time>${esc(n.source || "")} · ${esc(String(n.published_at || "").slice(0, 16))} ${n.url ? `· <a href="${esc(n.url)}" target="_blank" rel="noopener">open</a>` : ""}</time></li>`).join("") || "<li class='muted'>No news.</li>"}</ul>`, d.timestamp);
      } else if (rtab === "fund") {
        const d = await api(`/api/analysis/fundamental/${encodeURIComponent(sym)}`, { timeout: 30000 }); if (token !== loadResearch.seq) return;
        const skip = new Set(["instrument", "provider", "timestamp", "available", "quarterly", "shareholding", "reason"]);
        body.innerHTML = d.available === false ? panel("Fundamentals", unavailable(d)) : panel(`Fundamentals · ${esc(sym)} · ${esc(d.provider || "")}`, kvRows(Object.entries(d).filter(([k, v]) => !skip.has(k) && (typeof v === "number" || typeof v === "string")).map(([k, v]) => [esc(k.replace(/_/g, " ")), typeof v === "number" ? fmt(v) : esc(v)])));
      } else if (rtab === "ask") {
        body.innerHTML = panel("Ask CA AI", `<div style="padding:12px 14px"><label for="askQ" class="sr">Question</label><textarea id="askQ" placeholder="Ask about ${esc(sym)}: levels, why the model says what it says, what happened on a past date…"></textarea><div class="btn-row" style="margin-top:8px"><button type="button" class="btn primary" id="askGo" style="flex:0">Ask</button></div><div id="askOut"></div></div>`);
        $("askGo").addEventListener("click", async () => { const q = $("askQ").value.trim(); if (!q) return; $("askOut").innerHTML = `<p class="note">Thinking…</p>`;
          try { const r = await api("/api/ai/ask", { method: "POST", body: { prompt: q, symbol: sym, mode: "data" }, timeout: 60000 }); $("askOut").innerHTML = `<div class="answer">${esc(r.reply || r.answer || JSON.stringify(r))}</div>`; } catch (e) { $("askOut").innerHTML = `<p class="note">${esc(e.message)}</p>`; } });
      }
    } catch (e) { if (token === loadResearch.seq) body.innerHTML = panel("Not available", `<p class="note" style="padding:0 14px 12px">${esc(e.message)}</p>`); }
  }

  // ---------------- settings ----------------
  async function loadSettings() {
    try { const t = (await api("/api/telegram/settings")).settings || {};
      $("tgEnabled").checked = !!t.enabled; $("tgToken").value = ""; $("tgToken").placeholder = t.bot_token_masked ? `Saved: ${t.bot_token_masked}` : "Paste the bot token from BotFather";
      $("tgChat").value = t.chat_id || ""; $("tgRecos").checked = t.notify_recos !== false; $("tgMin").value = t.min_reco_score ?? 75; $("tgRisk").checked = t.notify_risk !== false; $("tgNews").checked = t.notify_news !== false; } catch (e) { toast(`Telegram settings: ${e.message}`); }
    try { const a = await api("/api/auto-trade"); $("atEnabled").checked = !!a.enabled; $("atCapital").value = a.capital || ""; $("atLoss").value = a.max_loss || ""; $("atProfit").value = a.max_profit || a.desired_profit || "";
      $("atSymbols").value = (a.symbols || []).join(", "); $("atOptions").checked = !!a.options_enabled; } catch (e) { toast(`Auto-trade: ${e.message}`); }
    loadNotes();
  }
  $("tgForm").addEventListener("submit", async (e) => { e.preventDefault();
    const body = { enabled: $("tgEnabled").checked, chat_id: $("tgChat").value.trim(), notify_recos: $("tgRecos").checked, min_reco_score: +$("tgMin").value || 0, notify_risk: $("tgRisk").checked, notify_news: $("tgNews").checked };
    if ($("tgToken").value.trim()) body.bot_token = $("tgToken").value.trim();
    try { await api("/api/telegram/settings", { method: "POST", body }); toast("Telegram settings saved"); loadSettings(); } catch (err) { toast(err.message); } });
  $("tgTest").addEventListener("click", async () => { try { const r = await api("/api/telegram/test", { method: "POST", body: {} }); toast(r.message || "Test sent"); } catch (err) { toast(err.message); } });
  $("atForm").addEventListener("submit", async (e) => { e.preventDefault();
    const body = { enabled: $("atEnabled").checked, capital: +$("atCapital").value || 0, max_loss: +$("atLoss").value || 0, max_profit: +$("atProfit").value || 0,
      symbols: $("atSymbols").value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean), options_enabled: $("atOptions").checked };
    try { await api("/api/auto-trade", { method: "POST", body }); toast("Auto-trade limits saved"); } catch (err) { toast(err.message); } });
  $("nsForm").addEventListener("submit", async (e) => { e.preventDefault(); try { await api("/api/notifications/settings", { method: "POST", body: { auto_prune_days: +$("nsDays").value || 15 } }); toast("Saved"); } catch (err) { toast(err.message); } });
  let notes = [];
  async function loadNotes() {
    try { notes = (await api("/api/notes")).notes || [];
      $("noteList").innerHTML = notes.map((n) => `<li class="click" data-note="${esc(n.id)}"><b>${esc(n.title)}</b> <span class="muted small">${esc(n.folder || "")}</span><br>${esc(String(n.content || "").slice(0, 140))}<time>${esc(String(n.updated_at || "").replace("T", " ").slice(0, 16))}</time></li>`).join("") || `<li class="muted">No notes yet.</li>`;
    } catch (e) { $("noteList").innerHTML = `<li>${esc(e.message)}</li>`; }
  }
  const fillNote = (n) => { $("noteId").value = n ? n.id : ""; $("noteTitle").value = n ? n.title : ""; $("noteFolder").value = n ? (n.folder || "Trade Journal") : "Trade Journal"; $("noteBody").value = n ? n.content : ""; $("noteTags").value = n ? (n.tags || "") : ""; };
  $("noteList").addEventListener("click", (e) => { const li = e.target.closest("[data-note]"); if (li) fillNote(notes.find((n) => n.id === li.dataset.note)); });
  $("noteNew").addEventListener("click", () => fillNote(null));
  $("noteForm").addEventListener("submit", async (e) => { e.preventDefault();
    try { await api("/api/notes", { method: "POST", body: { id: $("noteId").value || undefined, title: $("noteTitle").value.trim() || "Untitled", folder: $("noteFolder").value.trim(), content: $("noteBody").value, tags: $("noteTags").value.trim() } }); toast("Note saved"); fillNote(null); loadNotes(); } catch (err) { toast(err.message); } });
  $("noteDelete").addEventListener("click", async (e) => { const id = $("noteId").value; if (!id) return; const b = e.currentTarget;
    if (b.dataset.confirm !== "1") { b.dataset.confirm = "1"; b.textContent = "Confirm delete"; setTimeout(() => { b.dataset.confirm = ""; b.textContent = "Delete"; }, 4000); return; }
    try { await api(`/api/notes/${encodeURIComponent(id)}`, { method: "DELETE" }); toast("Note deleted"); fillNote(null); loadNotes(); } catch (err) { toast(err.message); } });

  // ---------------- routing, theme, keys ----------------
  const WS = ["trade", "options", "portfolio", "market", "research", "settings"];
  function moveInk() { const a = document.querySelector(`.workspaces a[data-ws="${S.ws}"]`), ink = document.querySelector(".nav-ink"), nav = document.querySelector(".workspaces");
    if (a && ink) { const r = a.getBoundingClientRect(), n = nav.getBoundingClientRect(); ink.style.left = `${r.left - n.left + 8}px`; ink.style.width = `${r.width - 16}px`; } }
  function route() {
    const ws = (location.hash || "#trade").slice(1); S.ws = WS.includes(ws) ? ws : "trade";
    document.querySelectorAll(".ws").forEach((el) => (el.hidden = el.id !== "ws-" + S.ws));
    document.querySelectorAll(".workspaces a").forEach((a) => { if (a.dataset.ws === S.ws) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    moveInk();
    if (S.ws === "trade") { initChart(); loadReco(); loadCandles(); loadMiniChain(); loadToday(); const dk = store.get("dock", "why"); const b = document.querySelector(`[data-dock="${dk}"]`); if (b) b.click(); }
    if (S.ws === "options") { renderFullChain._scrolled = false; if (S.chain) renderFullChain(); loadMiniChain(); }
    if (S.ws === "portfolio") { loadToday(); loadOrders(); }
    if (S.ws === "market") { loadMovers(); loadAlerts(); }
    if (S.ws === "research") loadResearch();
    if (S.ws === "settings") loadSettings();
  }
  window.addEventListener("hashchange", route); window.addEventListener("resize", moveInk);
  $("themeBtn").addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"), nxt = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nxt; store.set("theme", nxt); if (S.chart) setTimeout(() => S.chart.setTheme(), 30);
  });
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, select") || $("ticket").open) return;
    if (e.key === "/") { e.preventDefault(); $("symSearch").focus(); return; }
    if (/^[1-9]$/.test(e.key) && S.watch[+e.key - 1]) selectSymbol(S.watch[+e.key - 1]);
    if (e.key === "b" || e.key === "B") openTicket("BUY");
    if (e.key === "s" || e.key === "S") openTicket("SELL");
    if ((e.key === "f" || e.key === "F") && S.ws === "trade") document.querySelector(".cc-full").click();
  });

  async function boot() {
    try { const me = await api("/api/auth/me"); if (me.user) $("userName").textContent = me.user.full_name || me.user.username || "Account"; } catch { /* redirected if signed out */ }
    await loadWatchlists(); route();
    every(3000, loadQuotes);
    every(20000, () => { if (S.ws === "trade") loadReco(); });
    every(10000, () => { if (S.ws === "trade" || S.ws === "options") loadMiniChain(); });
    every(60000, () => { if (S.ws === "trade") loadCandles(); });
    every(15000, () => { if (S.ws === "trade" || S.ws === "portfolio") loadToday(); if (S.ws === "portfolio") loadOrders(); });
    every(60000, loadAlerts);
    setInterval(renderAges, 1000);
  }
  boot();
})();
