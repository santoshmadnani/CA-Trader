/* CA Trader mobile app. Every number comes from the backend (Upstox data or values computed from it); nothing is
   invented here. Screens refresh themselves while visible and pause when the app is in the background. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));
  const fmt = (v, d = 2) => (num(v) === null ? "—" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d }));
  const sgn = (v, d = 2) => (num(v) === null ? "—" : (Number(v) > 0 ? "+" : "") + Number(v).toFixed(d));
  const cls = (v) => (num(v) === null ? "" : Number(v) > 0 ? "up" : Number(v) < 0 ? "dn" : "");
  const store = { get(k, d) { try { const v = localStorage.getItem("cam_" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
                  set(k, v) { try { localStorage.setItem("cam_" + k, JSON.stringify(v)); } catch { /* storage unavailable */ } } };
  const hhmm = (iso) => { try { return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" }); } catch { return ""; } };
  const dmy = (iso) => { try { return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", timeZone: "Asia/Kolkata" }); } catch { return ""; } };
  const isIdx = (s) => /^(NIFTY|BANKNIFTY|FINNIFTY|MIDCPNIFTY|SENSEX|BANKEX)$/.test(String(s).split(" ")[0]);
  const hasOptions = (s) => isIdx(s) || /^(CRUDEOIL|NATURALGAS|GOLD|SILVER)/.test(s);
  const root = (s) => String(s || "").split(" ")[0].toUpperCase();

  const S = {
    tab: store.get("tab", "watch"), symbol: store.get("symbol", "NIFTY"), lists: [], listId: store.get("list", null), watch: [],
    quotes: {}, prev: {}, signals: {}, nextSession: {}, chart: null, chartSym: null, chat: store.get("chat", []), pages: [],
  };
  const TICKER = [["NIFTY 50", "NIFTY"], ["BANK NIFTY", "BANKNIFTY"]];
  const TICKER_EXTRA = [["SENSEX", "SENSEX"], ["FIN NIFTY", "FINNIFTY"], ["MIDCAP SELECT", "MIDCPNIFTY"], ["INDIA VIX", "NSE_INDEX|India VIX"]];

  // ------------------------------------------------------------------ network
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
    } catch (e) { if (e.name === "AbortError") throw new Error("The server took too long"); throw e; } finally { clearTimeout(t); }
  }
  function toast(msg) { const el = $("toast"); el.textContent = msg; el.classList.add("show"); clearTimeout(toast._t); toast._t = setTimeout(() => el.classList.remove("show"), 3000); }
  function flash(el, dir) { if (!el || !dir) return; el.classList.remove("flash-up", "flash-dn"); requestAnimationFrame(() => el.classList.add(dir > 0 ? "flash-up" : "flash-dn")); }
  const haptic = () => { try { navigator.vibrate && navigator.vibrate(8); } catch { /* unsupported */ } };

  // Background jobs: each runs on its interval only while its condition holds and the app is visible.
  const jobs = [];
  function job(ms, when, fn) { const j = { ms, when, fn, last: 0 }; jobs.push(j); return j; }
  setInterval(() => { if (document.hidden) return; const now = Date.now(); jobs.forEach((j) => { if (now - j.last >= j.ms && j.when()) { j.last = now; j.fn(); } }); }, 1000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) jobs.forEach((j) => { if (j.when()) { j.last = Date.now(); j.fn(); } }); });

  // ------------------------------------------------------------------ quotes + ticker
  async function loadQuotes() {
    const syms = [...new Set([...S.watch, S.symbol, ...(S.chartSym ? [S.chartSym] : []), ...TICKER.map((x) => x[1]), ...(tickerOpen() ? TICKER_EXTRA.map((x) => x[1]) : [])])];
    try {
      const d = await api(`/api/market/quotes?instruments=${encodeURIComponent(syms.join(","))}`);
      (d.items || []).forEach((q) => { const k = String(q.instrument || q.symbol || "").toUpperCase(); if (!k) return; S.prev[k] = S.quotes[k]; S.quotes[k] = q; });
      renderTicker(); updateWatchPrices(); updateOpenQuotes();
      if (S.chart && S.chartSym) { const q = S.quotes[S.chartSym]; if (q) S.chart.tick(num(q.ltp)); }
    } catch { /* the age indicators show staleness */ }
  }
  const tickerOpen = () => $("tickerMore").getAttribute("aria-expanded") === "true";
  const tk = (label, s) => { const q = S.quotes[s.toUpperCase()] || {}; return `<div class="tk" data-sym="${esc(s)}"><b>${esc(label)}</b><span class="num ${cls(q.change_pct)}">${fmt(q.ltp)}</span><i class="num">${num(q.change_pct) === null ? "" : `${sgn(q.net_change)} (${sgn(q.change_pct)}%)`}</i></div>`; };
  function renderTicker() {
    $("tickerRow").innerHTML = TICKER.map(([l, s]) => tk(l, s)).join("");
    if (tickerOpen()) $("tickerExtra").innerHTML = TICKER_EXTRA.map(([l, s]) => tk(l, s)).join("");
  }
  $("tickerMore").addEventListener("click", () => { const open = !tickerOpen(); $("tickerMore").setAttribute("aria-expanded", String(open)); $("tickerExtra").hidden = !open; if (open) { renderTicker(); loadQuotes(); } });
  $("ticker").addEventListener("click", (e) => { const t = e.target.closest(".tk[data-sym]"); if (t && !t.dataset.sym.includes("|")) openSymbol(t.dataset.sym); });

  // ------------------------------------------------------------------ tabs & navigation
  const TABS = ["watch", "signals", "orders", "portfolio", "account"];
  function setTab(tab, opts = {}) {
    if (!TABS.includes(tab)) tab = "watch";
    const same = S.tab === tab; S.tab = tab; store.set("tab", tab);
    document.querySelectorAll(".screen").forEach((s) => (s.hidden = s.dataset.screen !== tab));
    document.querySelectorAll(".tabbar [data-tab]").forEach((b) => { if (b.dataset.tab === tab) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
    document.querySelector(".tab-ink").style.transform = `translateX(${TABS.indexOf(tab) * 100}%)`;
    if (same && !opts.silent) { const sc = document.querySelector(`#s-${tab} .scroll`); if (sc) sc.scrollTo({ top: 0, behavior: "smooth" }); }
    ({ watch: () => loadQuotes(), signals: () => loadSignals(true), orders: () => loadOrders(), portfolio: () => loadPortfolio(), account: () => loadAccount() }[tab] || (() => {}))();
  }
  document.querySelectorAll(".tabbar [data-tab]").forEach((b) => b.addEventListener("click", () => { haptic(); setTab(b.dataset.tab); }));

  // pushed pages (with browser history so the phone's back gesture closes them)
  function openPage(id) {
    const el = $(`p-${id}`); if (!el || !el.hidden) return; el.hidden = false; el.classList.remove("leaving"); S.pages.push(id);
    history.pushState({ page: id }, "");
  }
  function closePage(fromPop) {
    const id = S.pages.pop(); if (!id) return false; const el = $(`p-${id}`); el.classList.add("leaving");
    setTimeout(() => { el.hidden = true; el.classList.remove("leaving"); if (id === "chart") S.chartSym = null; }, 210);
    if (!fromPop) history.back();
    return true;
  }
  document.querySelectorAll("[data-back]").forEach((b) => b.addEventListener("click", () => closePage(false)));
  window.addEventListener("popstate", () => { if (sheetOpen()) { closeSheet(true); return; } closePage(true); });

  // ------------------------------------------------------------------ bottom sheet (drag down to dismiss)
  const sheetOpen = () => !$("sheet").hidden;
  function openSheet(html) {
    $("sheetBody").innerHTML = html; const sh = $("sheet"), sc = $("scrim");
    sh.classList.remove("leaving"); sc.classList.remove("leaving"); sh.style.transform = ""; sh.hidden = false; sc.hidden = false; sh.scrollTop = 0;
    history.pushState({ sheet: 1 }, "");
  }
  function closeSheet(fromPop) {
    if (!sheetOpen()) return; const sh = $("sheet"), sc = $("scrim"); sh.classList.add("leaving"); sc.classList.add("leaving");
    setTimeout(() => { sh.hidden = true; sc.hidden = true; sh.classList.remove("leaving"); sc.classList.remove("leaving"); sh.style.transform = ""; }, 200);
    if (!fromPop) history.back();
  }
  $("scrim").addEventListener("click", () => closeSheet(false));
  (() => { let y0 = null, dy = 0; const sh = $("sheet");
    sh.addEventListener("touchstart", (e) => { if (sh.scrollTop > 0) return; y0 = e.touches[0].clientY; dy = 0; }, { passive: true });
    sh.addEventListener("touchmove", (e) => { if (y0 === null) return; dy = Math.max(0, e.touches[0].clientY - y0); if (dy > 0) sh.style.transform = `translateY(${dy}px)`; }, { passive: true });
    sh.addEventListener("touchend", () => { if (y0 === null) return; y0 = null; if (dy > 90) closeSheet(false); else { sh.style.transition = "transform .25s"; sh.style.transform = ""; setTimeout(() => (sh.style.transition = ""), 260); } });
  })();

  // ------------------------------------------------------------------ watchlist
  async function loadLists() {
    try { const d = await api("/api/watchlists"); S.lists = d.items || []; } catch { S.lists = []; }
    const g = S.lists.find((x) => x.id === S.listId) || S.lists[0]; S.listId = g ? g.id : null;
    S.watch = g && g.items ? g.items.map((i) => (i.symbol || "").toUpperCase()).filter(Boolean) : [];
    S.meta = Object.fromEntries((g && g.items ? g.items : []).map((i) => [(i.symbol || "").toUpperCase(), i]));
    $("wlTabs").innerHTML = S.lists.map((l) => `<button type="button" role="tab" data-list="${l.id}" aria-selected="${l.id === S.listId}">${esc(l.name || "List " + l.id)}</button>`).join("");
    renderWatch(); renderChips();
  }
  $("wlTabs").addEventListener("click", (e) => { const b = e.target.closest("[data-list]"); if (!b) return; S.listId = +b.dataset.list; store.set("list", S.listId); loadLists().then(loadQuotes); });
  function renderWatch() {
    $("wCount").textContent = `${S.watch.length}/250`;
    $("wList").innerHTML = S.watch.map((s) => { const q = S.quotes[s] || {}, m = (S.meta || {})[s] || {};
      return `<li class="wrow" data-sym="${esc(s)}"><span class="nm">${esc(m.display_name && !isIdx(s) ? s : s)}</span><span class="ltp ${cls(q.change_pct)}" data-ltp="${esc(s)}">${fmt(q.ltp)}</span>` +
        `<span class="ex">${esc(m.instrument_type === "INDEX" ? "INDICES" : (m.exchange || "").toUpperCase())}</span><span class="chg num" data-chg="${esc(s)}">${num(q.change_pct) === null ? "" : `${sgn(q.net_change)} (${sgn(q.change_pct)}%)`}</span></li>`; }).join("")
      || `<li class="empty">Your watchlist is empty. Search above to add instruments.</li>`;
  }
  function updateWatchPrices() {
    S.watch.forEach((s) => { const el = document.querySelector(`[data-ltp="${CSS.escape(s)}"]`); if (!el) return; const q = S.quotes[s] || {}, p = S.prev[s] || {};
      el.textContent = fmt(q.ltp); el.className = `ltp ${cls(q.change_pct)}`;
      const ch = document.querySelector(`[data-chg="${CSS.escape(s)}"]`); if (ch) ch.textContent = num(q.change_pct) === null ? "" : `${sgn(q.net_change)} (${sgn(q.change_pct)}%)`;
      if (num(p.ltp) !== null && num(q.ltp) !== null && q.ltp !== p.ltp) flash(el, q.ltp - p.ltp); });
  }
  $("wList").addEventListener("click", (e) => { const r = e.target.closest(".wrow[data-sym]"); if (r) { haptic(); openSymbol(r.dataset.sym); } });
  let searchT;
  $("wSearch").addEventListener("input", (e) => {
    clearTimeout(searchT); const q = e.target.value.trim(); const box = $("wResults");
    if (q.length < 2) { box.hidden = true; box.innerHTML = ""; return; }
    searchT = setTimeout(async () => { try { const d = await api(`/api/instruments/search?q=${encodeURIComponent(q)}`);
      box.innerHTML = (d.items || []).slice(0, 15).map((it) => `<div class="res" data-open="${esc(it.symbol)}"><div class="nm"><b>${esc(it.symbol)}</b><span>${esc(it.name || "")} · ${esc(it.exchange || "")}</span></div>` +
        `<button type="button" class="add" data-add="${esc(it.symbol)}" data-key="${esc(it.instrument_key || "")}" aria-label="Add ${esc(it.symbol)}"><svg><use href="#m-plus"/></svg></button></div>`).join("") || `<div class="res muted">No matches</div>`;
      box.hidden = false; } catch { /* ignore */ } }, 220);
  });
  $("wResults").addEventListener("click", async (e) => {
    const add = e.target.closest("[data-add]"), open = e.target.closest("[data-open]");
    if (add) { e.stopPropagation(); if (!S.listId) return toast("No watchlist to add to");
      try { await api(`/api/watchlists/${S.listId}/items`, { method: "POST", body: { symbol: add.dataset.add, instrument_key: add.dataset.key || undefined } }); haptic(); toast(`Added ${add.dataset.add}`);
        $("wSearch").value = ""; $("wResults").hidden = true; await loadLists(); loadQuotes(); } catch (err) { toast(err.message); } return; }
    if (open) { $("wResults").hidden = true; $("wSearch").blur(); openSymbol(open.dataset.open); }
  });

  // ------------------------------------------------------------------ symbol sheet
  function openSymbol(sym) {
    S.symbol = sym.toUpperCase(); store.set("symbol", S.symbol); renderChips();
    const inList = S.watch.includes(S.symbol);
    openSheet(`<div class="sh-head"><h2 id="sheetTitle">${esc(S.symbol)}</h2><div class="q" id="shQuote"></div></div>
      <div class="sh-actions">
        <button type="button" data-act="chart"><svg><use href="#m-chart"/></svg>View chart</button>
        <button type="button" data-act="signals"><svg><use href="#m-bolt"/></svg>Signals</button>
        ${hasOptions(S.symbol) ? `<button type="button" data-act="chain"><svg><use href="#m-layers"/></svg>Option chain</button>` : `<button type="button" data-act="news"><svg><use href="#m-news"/></svg>News</button>`}
        <button type="button" data-act="ai"><svg><use href="#m-spark"/></svg>Ask CA AI</button>
      </div>
      <div class="range" id="shRange"></div><div class="kv" id="shKv"></div>
      <div class="sh-btns"><button type="button" class="btn buy" data-act="BUY">Buy</button><button type="button" class="btn sell" data-act="SELL">Sell</button></div>
      ${inList ? `<button type="button" class="sh-link" data-act="remove">Remove from watchlist</button>` : S.listId ? `<button type="button" class="sh-link" data-act="addwl">Add to watchlist</button>` : ""}`);
    updateOpenQuotes(); loadQuotes();
  }
  function updateOpenQuotes() {
    const q = S.quotes[S.symbol] || {};
    if (sheetOpen() && $("shQuote")) {
      $("shQuote").innerHTML = `<span class="num ${cls(q.change_pct)}" style="font-size:17px;font-weight:700">${fmt(q.ltp)}</span> <span class="num">${num(q.change_pct) === null ? "" : `${sgn(q.net_change)} (${sgn(q.change_pct)}%)`}</span>`;
      const lo = num(q.low), hi = num(q.high), lt = num(q.ltp), op = num(q.open);
      if ($("shRange")) $("shRange").innerHTML = lo !== null && hi !== null && hi > lo ? `<div class="eyebrow">Day's range</div><div class="bar"><i style="left:${((Math.min(op ?? lt, lt) - lo) / (hi - lo)) * 100}%;width:${(Math.abs(lt - (op ?? lt)) / (hi - lo)) * 100}%;background:${lt >= (op ?? lt) ? "var(--up)" : "var(--dn)"}"></i><b style="left:${((lt - lo) / (hi - lo)) * 100}%"></b></div><div class="lh"><span>Low <b>${fmt(lo)}</b></span><span>High <b>${fmt(hi)}</b></span></div>` : "";
      if ($("shKv")) $("shKv").innerHTML = [["Open", fmt(q.open)], ["Prev. close", fmt(q.prev_close ?? q.cp)], ["Volume", q.volume ? Number(q.volume).toLocaleString("en-IN") : "—"]].map(([k, v]) => `<div><span class="muted">${k}</span><span>${v}</span></div>`).join("");
    }
    if (S.tab === "signals") { renderSigQuote(); updateLadders(); }
    if (S.chartSym && $("chQuote")) { const c = S.quotes[S.chartSym] || {}; $("chQuote").innerHTML = `<span class="num ${cls(c.change_pct)}">${fmt(c.ltp)}</span> <span class="num">${num(c.change_pct) === null ? "" : `${sgn(c.change_pct)}%`}</span>`; }
  }
  $("sheetBody").addEventListener("click", async (e) => {
    const a = e.target.closest("[data-act]"); if (!a) return; const act = a.dataset.act; haptic();
    if (act === "chart") { closeSheet(false); setTimeout(() => openChart(S.symbol), 220); }
    else if (act === "signals") { closeSheet(false); setTab("signals"); }
    else if (act === "chain") { closeSheet(false); setTimeout(() => openChain(S.symbol), 220); }
    else if (act === "news") { closeSheet(false); setTimeout(() => openNews(S.symbol), 220); }
    else if (act === "ai") { closeSheet(false); setTimeout(() => openAI(`What is the setup in ${S.symbol} right now?`), 220); }
    else if (act === "BUY" || act === "SELL") openTicket(act, { symbol: S.symbol, entry: num((S.quotes[S.symbol] || {}).ltp) });
    else if (act === "remove") { try { await api(`/api/watchlists/${S.listId}/items/${encodeURIComponent(S.symbol)}`, { method: "DELETE" }); toast(`Removed ${S.symbol}`); closeSheet(false); await loadLists(); } catch (err) { toast(err.message); } }
    else if (act === "addwl") { try { await api(`/api/watchlists/${S.listId}/items`, { method: "POST", body: { symbol: S.symbol } }); toast(`Added ${S.symbol}`); closeSheet(false); await loadLists(); loadQuotes(); } catch (err) { toast(err.message); } }
    else if (act === "place") placeOrder();
    else if (act === "exit") exitPosition(a);
    else if (act === "savesl") saveSl(a.dataset.id);
  });

  // ------------------------------------------------------------------ order ticket
  function openTicket(side, p) {
    const lot = num(p.lot) || 1;
    openSheet(`<div class="sh-head" style="border-bottom:0"><h2 id="sheetTitle" class="${side === "BUY" ? "up" : "dn"}">${side === "BUY" ? "Buy" : "Sell"} · ${esc(p.symbol)}</h2><div class="q small muted">Paper trade unless you switch on live below.</div></div>
      <form class="form" id="tForm" onsubmit="return false">
        <input type="hidden" id="tSide" value="${side}"><label class="full">Contract<input id="tSym" value="${esc(p.symbol)}"></label>
        <label>Lots<input id="tLots" type="number" inputmode="numeric" min="1" step="1" value="1"></label><label>Lot size<input id="tLot" type="number" inputmode="numeric" min="1" step="1" value="${lot}"></label>
        <label>Type<select id="tType"><option ${p.entry ? "selected" : ""}>LIMIT</option><option ${p.entry ? "" : "selected"}>MARKET</option></select></label><label>Price<input id="tPx" type="number" inputmode="decimal" step="0.05" value="${p.entry ?? ""}"></label>
        <label>Stop loss<input id="tSl" type="number" inputmode="decimal" step="0.05" value="${p.sl ?? ""}"></label><label>Target<input id="tTg" type="number" inputmode="decimal" step="0.05" value="${p.tgt ?? ""}"></label>
      </form>
      <div class="toggle-row"><span>Send to broker (live)</span><input type="checkbox" id="tLive" aria-label="Live order"></div>
      <div class="summary" id="tSum"></div>
      <div class="sh-btns" style="grid-template-columns:1fr"><button type="button" class="btn ${side === "BUY" ? "buy" : "sell"}" data-act="place" id="tGo">Place paper ${side.toLowerCase()}</button></div>`);
    const upd = () => { const qty = (+$("tLots").value || 0) * (+$("tLot").value || 0), px = +$("tPx").value || 0, sl = +$("tSl").value || 0, tg = +$("tTg").value || 0;
      $("tSum").innerHTML = `${side} <b>${qty}</b> × ${esc($("tSym").value)} ${$("tType").value === "LIMIT" && px ? "@ ₹" + fmt(px) : "at market"}${px ? ` · value ₹${fmt(px * qty, 0)}` : ""}` +
        `${px && sl ? ` · risk <span class="dn">₹${fmt(Math.abs(px - sl) * qty, 0)}</span>` : ""}${px && tg ? ` · reward <span class="up">₹${fmt(Math.abs(tg - px) * qty, 0)}</span>` : ""}`;
      $("tGo").textContent = $("tLive").checked ? `Place LIVE ${side.toLowerCase()}` : `Place paper ${side.toLowerCase()}`; };
    ["tLots", "tLot", "tPx", "tSl", "tTg", "tType", "tLive", "tSym"].forEach((id) => $(id).addEventListener("input", upd)); upd();
  }
  async function placeOrder() {
    const side = $("tSide").value, qty = (+$("tLots").value || 0) * (+$("tLot").value || 0); if (!qty) return toast("Enter a quantity");
    const live = $("tLive").checked;
    if (live && !confirm(`Send a LIVE ${side} order for ${qty} × ${$("tSym").value} to your broker?`)) return;
    const body = { symbol: $("tSym").value.trim(), side, quantity: qty, order_type: $("tType").value, price: $("tType").value === "LIMIT" ? (+$("tPx").value || null) : null,
      stop_loss: +$("tSl").value || null, target: +$("tTg").value || null, paper: !live, live };
    $("tGo").disabled = true;
    try { const r = await api("/api/orders", { method: "POST", body }); haptic(); toast(`Order ${r.status || r.execution_state || "placed"}`); closeSheet(false); if (S.tab === "orders") loadOrders(); if (S.tab === "portfolio") loadPortfolio(); }
    catch (err) { toast(`Rejected: ${err.message}`); } finally { const b = $("tGo"); if (b) b.disabled = false; }
  }

  // ------------------------------------------------------------------ signals
  function renderChips() {
    const syms = [...new Set(["NIFTY", "BANKNIFTY", ...S.watch.filter((s) => !s.includes("|"))])].slice(0, 12);
    $("sigChips").innerHTML = syms.map((s) => `<button type="button" data-chip="${esc(s)}" aria-pressed="${s === S.symbol}">${esc(s)}</button>`).join("");
    $("sigSym").textContent = S.symbol;
  }
  $("sigChips").addEventListener("click", (e) => { const b = e.target.closest("[data-chip]"); if (!b) return; haptic(); S.symbol = b.dataset.chip; store.set("symbol", S.symbol); renderChips(); loadSignals(true); loadQuotes(); });
  $("sigSymBtn").addEventListener("click", () => { setTab("watch"); setTimeout(() => $("wSearch").focus(), 100); });
  function renderSigQuote() { const q = S.quotes[S.symbol] || {}; $("sigQuote").innerHTML = `<span class="ltp num ${cls(q.change_pct)}">${fmt(q.ltp)}</span><span class="num ${cls(q.change_pct)}">${num(q.change_pct) === null ? "" : `${sgn(q.net_change)} (${sgn(q.change_pct)}%)`}</span>`; }

  async function loadSignals(force) {
    const sym = S.symbol;
    if (force && !S.signals[sym]) $("sigPlans").innerHTML = [1, 2, 3].map(() => `<div class="card" style="padding:14px"><span class="skel w40"></span><span class="skel w80"></span><span class="skel w60"></span></div>`).join("");
    renderSigQuote();
    try {
      const d = await api(`/api/signals/${encodeURIComponent(sym)}`, { timeout: 60000 }); if (sym !== S.symbol) return;
      S.signals[sym] = { data: d, at: Date.now() }; renderPlans(); $("sigLive").classList.toggle("on", !!d.market_open);
    } catch (e) { if (sym === S.symbol && !S.signals[sym]) $("sigPlans").innerHTML = `<div class="card empty">${esc(e.message)}</div>`; }
    if (force) { loadNextSession(sym); loadSigNews(sym); }
  }
  const lvl = (k, v, c = "") => `<div><span class="k">${k}</span><span class="v ${c}">${v}</span></div>`;
  const FACTOR_NAMES = { trend: "Trend", vwap: "VWAP", momentum: "Momentum", price_action: "Price action", day_change: "Day change", option_flow: "Option flow" };
  const openWhy = new Set(); let animatedSym = null;
  // Price ladder: SL, entry zone, T1, T2 and the live price placed on one scale (works for BUY and SELL, since it sorts by value).
  function ladder(p) {
    const pts = [num(p.stop_loss), num(p.entry_low), num(p.entry_high), num(p.target_1), num(p.target_2)];
    if (pts.some((x) => x === null)) return "";
    const lo = Math.min(...pts), hi = Math.max(...pts), pad = (hi - lo) * 0.06 || 1, a = lo - pad, b = hi + pad;
    const at = (v) => (((v - a) / (b - a)) * 100).toFixed(2);
    const buy = p.decision === "BUY";
    const mk = (v, k, c) => `<span class="lad-mk ${c}" style="left:${at(v)}%"><i></i><em>${k}</em><b class="num">${fmt(v)}</b></span>`;
    return `<div class="ladder" data-lo="${a}" data-hi="${b}">
      <div class="lad-track"><span class="lad-risk" style="left:${at(Math.min(p.stop_loss, p.entry_low))}%;width:${Math.abs(at(p.entry_low) - at(p.stop_loss)) || 0}%"></span>
        <span class="lad-zone" style="left:${at(p.entry_low)}%;width:${Math.max(1.5, at(p.entry_high) - at(p.entry_low))}%"></span>
        <span class="lad-reward" style="left:${at(buy ? p.entry_high : p.target_2)}%;width:${Math.abs(at(p.target_2) - at(buy ? p.entry_high : p.entry_low))}%"></span>
        <span class="lad-ltp" data-ltp-dot hidden></span></div>
      <div class="lad-marks">${mk(p.stop_loss, "SL", "dn")}${mk(p.target_1, "T1", "up")}${mk(p.target_2, "T2", "up")}</div></div>`;
  }
  function updateLadders() {
    const q = S.quotes[S.symbol] || {}, v = num(q.ltp);
    document.querySelectorAll("#sigPlans .ladder").forEach((l) => { const dot = l.querySelector("[data-ltp-dot]"); if (!dot) return;
      const a = +l.dataset.lo, b = +l.dataset.hi; if (v === null || !(b > a)) { dot.hidden = true; return; }
      dot.hidden = false; dot.style.left = `${Math.max(0, Math.min(100, ((v - a) / (b - a)) * 100))}%`; dot.title = `LTP ${fmt(v)}`; });
  }
  const optName = (o) => { const s = String(o.symbol || ""); const m = s.match(/(\d+(?:\.\d+)?)\s*(CE|PE)\s*(\d{4}-\d{2}-\d{2})?/i);
    return m ? `${m[1]} ${m[2].toUpperCase()}${m[3] ? ` · ${dmy(m[3])}` : ""}` : s; };
  function renderPlans() {
    const rec = S.signals[S.symbol]; if (!rec) return; const d = rec.data;
    const anim = animatedSym !== S.symbol; animatedSym = S.symbol;
    const closedNote = d.market_open ? "" : `<div class="card closed-note"><span class="pill warn">Market closed</span><span class="small muted">New plans from 09:15 NSE · 09:00 MCX</span></div>`;
    const opt = isIdx(S.symbol) || hasOptions(S.symbol);
    $("sigPlans").innerHTML = closedNote + (d.plans || []).map((p, idx) => {
      const enter = anim ? ` enter" style="--i:${idx}` : "";
      if (!p.available) return `<div class="card plan${enter}"><div class="ph"><span class="hz">${esc(p.label)}</span><span class="tf">${esc(p.timeframe)}</span><span class="grow"></span><span class="decision NO_TRADE">NO DATA</span></div><div class="why">${esc(p.reason || "")}</div></div>`;
      const dec = p.expired ? "NO_TRADE" : p.decision, live = !p.expired && (dec === "BUY" || dec === "SELL"), sc = Math.max(-100, Math.min(100, num(p.score) || 0));
      const label = p.expired ? `${p.decision} · EXPIRED` : dec === "BUY" ? (opt ? "BUY · CE" : "BUY") : dec === "SELL" ? (opt ? "SELL · PE" : "SELL") : "NO TRADE";
      const tr = p.track_record, o = p.option, key = `${S.symbol}|${p.horizon}`;
      const factors = Object.entries(p.factors || {}).map(([k, v]) => { const x = Math.max(-100, Math.min(100, num(v) || 0));
        return `<div class="fx"><span>${esc(FACTOR_NAMES[k] || k)}</span><span class="fx-bar"><i class="${x >= 0 ? "up" : "dn"}" style="${x >= 0 ? "left:50%" : `left:${50 + x / 2}%`};width:${Math.abs(x) / 2}%"></i></span><b class="num ${cls(x)}">${sgn(x, 0)}</b></div>`; }).join("");
      const steps = live ? [
        ["m-history", `Enter by <b class="countdown" data-until="${esc(p.valid_until)}">${hhmm(p.valid_until)}</b>`],
        ["m-bolt", `Book part at <b class="up">T1</b>`],
        ["m-trend", `Trail to <b class="up">T2</b>`],
        p.time_stop_bars ? ["m-x", `Exit after <b>${esc(p.time_stop_bars)}</b> bars`] : null,
      ].filter(Boolean) : [];
      return `<div class="card plan${live ? ` live ${dec}` : ""}${enter}" data-plan="${esc(p.horizon)}">
        <div class="ph"><span class="hz">${esc(p.label)}</span><span class="tf">${esc(p.timeframe)} · ${esc(p.hold || "")}</span><span class="grow"></span><span class="decision ${dec}">${label}</span></div>
        <div class="score-bar" title="Score ${sgn(p.score, 0)}"><b style="left:${(100 - p.gate) / 2}%"></b><b style="left:${(100 + p.gate) / 2}%"></b><i style="left:${(sc + 100) / 2}%"></i></div>
        ${live ? `${ladder(p)}
          <div class="lv">${lvl("Entry zone", `${fmt(p.entry_low)}<small>to ${fmt(p.entry_high)}</small>`)}${lvl("Reward : risk", p.rr_t1 ? `${fmt(p.rr_t1, 2)}<small class="inl"> : 1</small>` : "—")}${lvl("Time left", `<span class="countdown" data-short data-until="${esc(p.valid_until)}">${hhmm(p.valid_until)}</span><small>till ${hhmm(p.valid_until)}</small>`)}</div>
          <div class="steps">${steps.map(([ic, t]) => `<span class="step"><svg><use href="#${ic}"/></svg>${t}</span>`).join("")}</div>
          ${o ? `<div class="opt">
            <div class="opt-h"><span class="opt-name">${esc(optName(o))}</span><span class="pill">LTP <b class="num">${fmt(o.ltp)}</b></span><span class="pill">Δ <b class="num">${fmt(o.delta, 2)}</b></span></div>
            <div class="opt-lv"><div><span>Buy</span><b class="num">${fmt(o.entry_low)}<small>– ${fmt(o.entry_high)}</small></b></div><div><span>SL</span><b class="num dn">${fmt(o.stop_loss)}</b></div><div><span>T1</span><b class="num up">${fmt(o.target_1)}</b></div><div><span>T2</span><b class="num up">${fmt(o.target_2)}</b></div></div>
            <button type="button" class="btn trade-opt" data-trade-opt='${esc(JSON.stringify({ symbol: o.symbol, entry: o.entry_high, sl: o.stop_loss, tgt: o.target_1 }))}'>Trade ${esc(optName(o).split(" · ")[0])}<svg><use href="#m-back"/></svg></button></div>` : ""}`
        : `<div class="why">${esc(p.reason || "")}</div>`}
        <div class="meta">${(p.higher_timeframes || []).map((h) => `<span class="pill ${h.bias > 0 ? "up" : h.bias < 0 ? "dn" : ""}">${esc(h.tf)} ${h.bias > 0 ? "▲" : h.bias < 0 ? "▼" : "•"}</span>`).join("")}<span class="pill acc">score ${sgn(p.score, 0)}</span></div>
        ${tr && tr.signals ? `<div class="stats"><div><b class="num">${fmt(tr.t1_hit_rate, 0)}%</b><span>T1 first</span></div><div><b class="num ${cls(tr.expectancy_r)}">${sgn(tr.expectancy_r, 2)}R</b><span>Avg / trade</span></div><div><b class="num">${esc(tr.signals)}</b><span>Backtested</span></div><em>${esc(dmy(tr.from))} – ${esc(dmy(tr.to))}</em></div>` : ""}
        ${factors || p.instructions || (o && o.basis) ? `<details class="whybox" data-why="${esc(key)}"${openWhy.has(key) ? " open" : ""}><summary>Why &amp; full plan<svg><use href="#m-down"/></svg></summary>
          ${factors ? `<div class="fxs">${factors}</div>` : ""}${p.instructions ? `<p>${esc(p.instructions)}</p>` : ""}${o && o.basis ? `<p class="muted">${esc(o.basis)}</p>` : ""}</details>` : ""}
      </div>`; }).join("");
    tickCountdowns(); updateLadders();
  }
  $("sigPlans").addEventListener("toggle", (e) => { const d = e.target.closest && e.target.closest("details[data-why]"); if (!d) return; if (d.open) openWhy.add(d.dataset.why); else openWhy.delete(d.dataset.why); }, true);
  function tickCountdowns() {
    document.querySelectorAll(".countdown[data-until]").forEach((el) => { const left = (new Date(el.dataset.until) - Date.now()) / 1000;
      const mmss = `${Math.floor(left / 60)}m ${String(Math.floor(left % 60)).padStart(2, "0")}s`;
      el.textContent = left <= 0 ? "expired" : "short" in el.dataset ? (left < 3600 ? mmss : `${Math.floor(left / 3600)}h ${Math.floor((left % 3600) / 60)}m`) : hhmm(el.dataset.until);
      el.classList.toggle("dn", left <= 0); });
    const rec = S.signals[S.symbol]; if (rec && S.tab === "signals") { const s = Math.round((Date.now() - rec.at) / 1000); $("sigAge").textContent = s < 60 ? `updated ${s}s ago` : `updated ${Math.round(s / 60)}m ago`; }
  }
  setInterval(() => { if (!document.hidden && S.tab === "signals") tickCountdowns(); }, 1000);
  $("sigPlans").addEventListener("click", (e) => { const b = e.target.closest("[data-trade-opt]"); if (!b) return; const p = JSON.parse(b.dataset.tradeOpt); openTicket("BUY", p); });

  async function loadNextSession(sym) {
    const box = $("sigNext"); const cached = S.nextSession[sym];
    if (!cached) box.innerHTML = `<div class="card" style="padding:14px"><span class="skel w60"></span><span class="skel w40"></span></div>`;
    try {
      const d = cached && Date.now() - cached.at < 20 * 60000 ? cached.data : await api(`/api/prediction/next-session/${encodeURIComponent(sym)}`, { timeout: 90000 });
      S.nextSession[sym] = { data: d, at: cached ? cached.at : Date.now() }; if (sym !== S.symbol) return;
      const p = d.prediction || {}, v = (d.validation || {}).direction || {}, g = (d.validation || {}).gap || {};
      if (!p.available) { box.innerHTML = `<div class="card"><div class="card-h"><h3>Next session</h3></div><div class="why">${esc(p.reason || "Not available")}</div></div>`; return; }
      const r = p.expected_range || {};
      box.innerHTML = `<div class="card next"><div class="card-h"><h3>Next session · ${esc(dmy(p.for_date))}</h3><span class="pill ${p.bias === "UP" ? "up" : p.bias === "DOWN" ? "dn" : ""}">${esc(p.bias)}</span></div>
        <div class="big"><div class="gauge2" style="--p:${num(p.p_up) || 50}">${fmt(p.p_up, 0)}%</div><div><div><b>Chance of a higher close</b></div><div class="small muted">Gap-up chance <b>${fmt(p.p_gap_up, 0)}%</b>${p.us_session_included ? " · includes last US session" : " · US session not closed yet"}</div></div></div>
        <div class="lv" style="margin-top:8px">${lvl("Expected low", fmt(r.low))}${lvl("Expected high", fmt(r.high))}${lvl("Range hit rate", `${fmt(r.historical_coverage_pct, 0)}%`)}</div>
        <div class="track"><span>Tested ${v.test_days || 0} days</span><span>Direction <b>${fmt(v.accuracy_pct, 1)}%</b> <span class="muted">vs ${fmt(v.baseline_pct, 1)}%</span></span><span>Gap <b>${fmt(g.accuracy_pct, 1)}%</b> <span class="muted">vs ${fmt(g.baseline_pct, 1)}%</span></span></div>
        <div class="why">Walk-forward test: each day predicted only from earlier days. Baseline = always guessing the more common outcome.</div></div>`;
    } catch (e) { if (sym === S.symbol) box.innerHTML = `<div class="card"><div class="card-h"><h3>Next session</h3></div><div class="why">${esc(e.message)}</div></div>`; }
  }
  async function loadSigNews(sym) {
    try { const d = await api(`/api/news/unified?symbol=${encodeURIComponent(root(sym))}&limit=40`, { timeout: 30000 }); if (sym !== S.symbol) return;
      const items = (d.events || []).slice(0, 5);
      $("sigNews").innerHTML = `<div class="card"><div class="card-h"><h3>News that can move ${esc(root(sym))}</h3><button type="button" class="pill-btn" data-more-news>All</button></div><ul class="news-mini">${items.map((n) => `<li><span class="dot ${esc(n.sentiment || "")}"></span>${esc(n.headline || n.event)}<div class="small muted">${esc(n.source || "")} · ${esc(hhmm(n.published_at))}</div></li>`).join("") || `<li class="muted">No material news right now.</li>`}</ul></div>`;
    } catch { /* optional */ }
  }
  $("sigNews").addEventListener("click", (e) => { if (e.target.closest("[data-more-news]")) openNews(S.symbol); });

  // ------------------------------------------------------------------ chart page
  const DAYS = { "1m": 3, "3m": 5, "5m": 10, "15m": 20, "30m": 40, "60m": 80, "1D": 400 };
  function openChart(sym) {
    S.chartSym = sym.toUpperCase(); $("chSym").textContent = S.chartSym; openPage("chart");
    if (!S.chart && window.CAChart && window.LightweightCharts) S.chart = window.CAChart.create($("chartCard"), { onTimeframe: () => loadCandles() });
    setTimeout(loadCandles, 60); updateOpenQuotes();
  }
  async function loadCandles() {
    if (!S.chart || !S.chartSym) return; const sym = S.chartSym, tf = S.chart.timeframe;
    try { const d = await api(`/api/market/candles/${encodeURIComponent(sym)}?timeframe=${tf}&days=${DAYS[tf] || 10}`, { timeout: 30000 }); if (sym !== S.chartSym) return;
      S.chart.setData(d.candles || [], sym, tf); applyPlanLevels(); } catch (e) { S.chart.setData([], sym, tf); toast(`Chart: ${e.message}`); }
  }
  function applyPlanLevels() {
    const rec = S.signals[S.chartSym]; if (!rec || !S.chart) { S.chart && S.chart.setLevels([]); return; }
    const want = { "1m": "scalp", "3m": "scalp", "5m": "intraday", "15m": "swing", "30m": "swing" }[S.chart.timeframe] || "intraday";
    const p = (rec.data.plans || []).find((x) => x.horizon === want && (x.decision === "BUY" || x.decision === "SELL"));
    S.chart.setLevels(p ? [{ price: p.entry_high, title: "Zone", color: "--muted" }, { price: p.entry_low, title: "Zone", color: "--muted" }, { price: p.stop_loss, title: "SL", color: "--dn" }, { price: p.target_1, title: "T1", color: "--up" }, { price: p.target_2, title: "T2", color: "--up" }] : []);
  }
  $("chSignals").addEventListener("click", () => { S.symbol = S.chartSym; store.set("symbol", S.symbol); renderChips(); closePage(false); setTab("signals"); });
  document.querySelector("#p-chart .trade-bar").addEventListener("click", (e) => { const b = e.target.closest("[data-trade]"); if (b) openTicket(b.dataset.trade, { symbol: S.chartSym, entry: num((S.quotes[S.chartSym] || {}).ltp) }); });
  document.addEventListener("click", (e) => { if (!e.target.closest(".cc-pop-wrap")) document.querySelectorAll(".cc-pop-wrap .pop").forEach((p) => (p.hidden = true)); });

  // ------------------------------------------------------------------ option chain page
  async function openChain(sym) {
    const r = root(sym); $("ocTitle").textContent = `${r} option chain`; $("ocRows").innerHTML = `<tr><td colspan="5"><span class="skel w60"></span></td></tr>`; $("ocStats").innerHTML = ""; openPage("chain");
    try { const d = await api(`/api/options/${encodeURIComponent(r)}`, { timeout: 30000 }); const st = d.strikes || [], spot = num(d.spot);
      $("ocSub").textContent = `${d.expiry ? "Expiry " + d.expiry : ""} · spot ${fmt(spot)}`;
      if (!st.length || !spot) { $("ocRows").innerHTML = `<tr><td colspan="5" class="muted">No chain from Upstox.</td></tr>`; return; }
      let a = 0, bd = Infinity; st.forEach((s, i) => { const dd = Math.abs(s.strike - spot); if (dd < bd) { bd = dd; a = i; } });
      const view = st.slice(Math.max(0, a - 12), a + 13), coi = st.reduce((x, s) => x + (num((s.call || {}).oi) || 0), 0), poi = st.reduce((x, s) => x + (num((s.put || {}).oi) || 0), 0);
      const short = (v) => { const n = num(v); if (n === null) return "—"; const z = Math.abs(n); return z >= 1e7 ? (n / 1e7).toFixed(1) + "Cr" : z >= 1e5 ? (n / 1e5).toFixed(1) + "L" : z >= 1e3 ? (n / 1e3).toFixed(1) + "K" : n.toFixed(0); };
      $("ocStats").innerHTML = [["PCR (OI)", coi ? (poi / coi).toFixed(2) : "—"], ["Call OI", short(coi)], ["Put OI", short(poi)]].map(([k, v]) => `<div><span class="k">${k}</span><span class="v">${v}</span></div>`).join("");
      $("ocRows").innerHTML = view.map((s) => { const c = s.call || {}, p = s.put || {}, itmC = s.strike < spot, itmP = s.strike > spot;
        const nm = (k) => `${r} ${fmt(s.strike, 0).replace(/,/g, "")} ${k}`;
        return `<tr class="${s === st[a] ? "atm" : ""}"><td class="${itmC ? "itm" : ""}">${short(c.oi)}</td><td class="px ${itmC ? "itm" : ""}" data-pick="${esc(nm("CE"))}" data-px="${num(c.ltp) ?? ""}">${fmt(c.ltp)}</td><td class="mid">${fmt(s.strike, 0)}</td><td class="px ${itmP ? "itm" : ""}" data-pick="${esc(nm("PE"))}" data-px="${num(p.ltp) ?? ""}">${fmt(p.ltp)}</td><td class="${itmP ? "itm" : ""}">${short(p.oi)}</td></tr>`; }).join("");
      const atm = $("ocRows").querySelector("tr.atm"); if (atm) atm.scrollIntoView({ block: "center" });
    } catch (e) { $("ocRows").innerHTML = `<tr><td colspan="5" class="muted">${esc(e.message)}</td></tr>`; }
  }
  $("ocRows").addEventListener("click", (e) => { const td = e.target.closest("td[data-pick]"); if (td) openTicket("BUY", { symbol: td.dataset.pick, entry: num(td.dataset.px) }); });

  // ------------------------------------------------------------------ orders & signal history
  let oseg = "open";
  document.querySelectorAll("[data-oseg]").forEach((b) => b.addEventListener("click", () => { oseg = b.dataset.oseg; document.querySelectorAll("[data-oseg]").forEach((x) => x.setAttribute("aria-selected", String(x === b))); loadOrders(); }));
  async function loadOrders() {
    const box = $("ordersBody");
    if (oseg === "hist") return renderHistory(box, 7);
    try { const d = await api("/api/orders"); const items = d.items || [];
      const open = items.filter((o) => /PENDING|OPEN|TRIGGER/.test(o.status || "")), done = items.filter((o) => !/PENDING|OPEN|TRIGGER/.test(o.status || ""));
      const list = oseg === "open" ? open : done;
      box.innerHTML = list.length ? `<div class="card">${list.slice(0, 100).map((o) => `<div class="ocard"><div><span class="pill ${o.side === "BUY" ? "acc" : "dn"}">${esc(o.side)}</span> <span class="small muted">${fmt(o.filled_quantity ?? o.quantity, 0)}/${fmt(o.quantity, 0)}</span></div><div class="r small muted">${esc(hhmm(o.created_at))} <span class="pill ${/FILL|COMPLETE/.test(o.status) ? "up" : /REJECT|CANCEL/.test(o.status) ? "dn" : "warn"}">${esc(o.status)}</span></div>` +
        `<div class="s">${esc(o.symbol)}</div><div class="r num">${o.price ? "₹" + fmt(o.price) : "MKT"}</div><div class="m">${esc(o.order_type || "")} ${o.paper || o.is_paper ? "· paper" : ""}</div>${oseg === "open" ? `<div class="r"><button type="button" class="btn tiny" data-cancel="${esc(o.id)}">Cancel</button></div>` : "<div></div>"}</div>`).join("")}</div>`
        : `<div class="empty">${oseg === "open" ? "No open orders." : "No executed orders yet."}</div>`;
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  $("ordersBody").addEventListener("click", async (e) => { const b = e.target.closest("[data-cancel]"); if (!b) return; try { await api(`/api/orders/${encodeURIComponent(b.dataset.cancel)}?hard=0`, { method: "DELETE" }); toast("Order cancelled"); loadOrders(); } catch (err) { toast(err.message); } });

  const OUTCOME = { PENDING: ["Waiting for zone", "warn"], OPEN: ["In trade", "acc"], EXPIRED: ["Zone not reached", ""], T1: ["Target 1 hit", "up"], T2: ["Target 2 hit", "up"], SL: ["Stopped out", "dn"], TIME: ["Time exit", "warn"] };
  async function renderHistory(box, days) {
    box.innerHTML = `<div class="card" style="padding:14px"><span class="skel w80"></span><span class="skel w60"></span></div>`;
    try { const d = await api(`/api/signals/history?days=${days}`);
      const st = d.stats || {};
      const stat = (h, l) => { const s = st[h] || {}; return `<div><span class="k">${l}</span><span class="v">${s.target_hit_pct === null || s.target_hit_pct === undefined ? "—" : fmt(s.target_hit_pct, 0) + "%"}</span><span class="small muted">${s.target_hit || 0}/${s.closed || 0} closed · ${s.expired_unfilled || 0} unfilled</span></div>`; };
      box.innerHTML = `<div class="hstats">${stat("scalp", "Scalp")}${stat("intraday", "Intraday")}${stat("swing", "Swing")}</div>` +
        ((d.items || []).length ? `<div class="card">${d.items.map((r) => { const [txt, c] = OUTCOME[r.status] || [r.status, ""];
          return `<div class="hrow"><div><b>${esc(r.symbol)}</b> <span class="pill ${r.side === "BUY" ? "up" : "dn"}">${esc(r.side)}</span> <span class="small muted">${esc(r.horizon)} · ${esc(r.timeframe)}</span></div><div class="small muted">${esc(dmy(r.created_at))} ${esc(hhmm(r.created_at))}</div>` +
            `<div class="small">Zone ${fmt(r.entry_low)}–${fmt(r.entry_high)} · SL ${fmt(r.stop_loss)} · T1 ${fmt(r.target_1)}</div><div><span class="pill ${c}">${esc(txt)}</span>${num(r.r) !== null ? ` <b class="num ${cls(r.r)}">${sgn(r.r, 2)}R</b>` : ""}</div></div>`; }).join("")}</div>`
          : `<div class="empty">No signals issued in this period yet. Plans are recorded automatically while the market is open.</div>`);
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  document.querySelectorAll("#histDays [data-days]").forEach((b) => b.addEventListener("click", () => { document.querySelectorAll("#histDays [data-days]").forEach((x) => x.setAttribute("aria-selected", String(x === b))); renderHistory($("histBody"), +b.dataset.days); }));

  // ------------------------------------------------------------------ portfolio
  let pseg = "positions";
  document.querySelectorAll("[data-pseg]").forEach((b) => b.addEventListener("click", () => { pseg = b.dataset.pseg; document.querySelectorAll("[data-pseg]").forEach((x) => x.setAttribute("aria-selected", String(x === b))); loadPortfolio(); }));
  async function loadPortfolio() {
    const box = $("portBody");
    try {
      if (pseg === "holdings") { const d = await api("/api/holdings"); const it = d.items || [];
        box.innerHTML = it.length ? `<div class="card">${it.map((h) => `<div class="ocard"><div class="s">${esc(h.symbol || h.tradingsymbol)}</div><div class="r num ${cls(h.pnl)}">₹${fmt(h.pnl, 0)}</div><div class="m">Qty ${fmt(h.quantity, 0)} · Avg ${fmt(h.average_price ?? h.avg_price)}</div><div class="r m">LTP ${fmt(h.last_price ?? h.ltp)}</div></div>`).join("")}</div>`
          : `<div class="empty">No holdings from your broker.</div>`; return; }
      const p = await api("/api/positions"); const open = p.open_positions || [], closed = (p.closed_today || []);
      const all = [...open, ...closed]; const tot = all.reduce((a, x) => a + (num(x.pnl) || 0), 0);
      box.innerHTML = `<div class="card pnl-card"><div class="eyebrow">Total P&amp;L</div><div class="v ${cls(tot)}">${tot >= 0 ? "+" : "−"}₹${fmt(Math.abs(tot))}</div></div>` +
        (all.length ? `<div class="card">${all.map((x) => `<div class="ocard" data-pos="${esc(x.id)}"><div class="m">Qty ${fmt(x.status === "CLOSED" ? 0 : x.quantity, 0)} · Avg ${fmt(x.avg_price)}</div><div class="r"><span class="pill ${x.status === "CLOSED" ? "" : "acc"}">${esc(x.trade_type || (x.status === "CLOSED" ? "CLOSED" : "OPEN"))}</span></div>` +
          `<div class="s">${esc(x.symbol)}</div><div class="r num ${cls(x.pnl)}" style="font-weight:700">${sgn(x.pnl)}</div><div class="m">${esc(x.side)} ${x.stop_loss ? `· SL ${fmt(x.stop_loss)}` : ""}</div><div class="r m">LTP ${fmt(x.ltp ?? x.current_price ?? x.exit_price)}</div></div>`).join("")}</div>`
          : `<div class="empty">No positions today.</div>`);
      S.positions = all;
    } catch (e) { box.innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  $("portBody").addEventListener("click", (e) => { const r = e.target.closest("[data-pos]"); if (!r) return; const x = (S.positions || []).find((p) => String(p.id) === r.dataset.pos); if (!x || x.status === "CLOSED") return;
    openSheet(`<div class="sh-head"><h2 id="sheetTitle">${esc(x.symbol)}</h2><div class="q num ${cls(x.pnl)}">${sgn(x.pnl)} · LTP ${fmt(x.ltp ?? x.current_price)}</div></div>
      <div class="kv">${[["Side", esc(x.side)], ["Quantity", fmt(x.quantity, 0)], ["Average", fmt(x.avg_price)], ["Target", fmt(x.target)]].map(([k, v]) => `<div><span class="muted">${k}</span><span>${v}</span></div>`).join("")}</div>
      <form class="form" onsubmit="return false"><label class="full">Stop loss<input id="pSl" type="number" inputmode="decimal" step="0.05" value="${num(x.stop_loss) ?? ""}"></label></form>
      <div class="sh-btns"><button type="button" class="btn ghost" data-act="savesl" data-id="${esc(x.id)}">Save stop loss</button><button type="button" class="btn sell" data-act="exit" data-id="${esc(x.id)}">Exit position</button></div>`); });
  async function exitPosition(b) {
    if (b.dataset.confirm !== "1") { b.dataset.confirm = "1"; b.textContent = "Tap again to exit"; setTimeout(() => { if (b.isConnected) { b.dataset.confirm = ""; b.textContent = "Exit position"; } }, 4000); return; }
    try { const r = await api(`/api/positions/${encodeURIComponent(b.dataset.id)}/square-off`, { method: "POST", body: {} }); haptic(); toast(`Exited at ₹${fmt(r.exit_price)} · P&L ₹${fmt(r.final_pnl, 0)}`); closeSheet(false); loadPortfolio(); } catch (err) { toast(err.message); }
  }
  async function saveSl(id) { try { await api(`/api/positions/${encodeURIComponent(id)}/trail-sl`, { method: "POST", body: { stop_loss: +$("pSl").value } }); toast("Stop loss updated"); closeSheet(false); loadPortfolio(); } catch (err) { toast(err.message); } }

  // ------------------------------------------------------------------ account
  async function loadAccount() {
    try { const me = await api("/api/auth/me"); const u = me.user || {}; const name = u.full_name || u.username || "Trader";
      $("uName").textContent = name; $("uMail").textContent = u.email || ""; $("avatar").textContent = name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase(); } catch { /* ignore */ }
    try { const f = await api("/api/funds"); const l = f.local || {};
      $("funds").innerHTML = [["Available (paper)", "₹" + fmt(l.available, 0)], ["Used margin", "₹" + fmt(l.used, 0)], ["Realised P&L", `<span class="${cls(l.realized_pnl)}">₹${fmt(l.realized_pnl, 0)}</span>`], ["Unrealised P&L", `<span class="${cls(l.unrealized_pnl)}">₹${fmt(l.unrealized_pnl, 0)}</span>`]]
        .map(([k, v]) => `<div><span class="k">${k}</span><span class="v">${v}</span></div>`).join(""); } catch { /* ignore */ }
  }
  document.querySelector("#s-account .menu").addEventListener("click", (e) => { const b = e.target.closest("[data-open]"); if (!b) return; haptic();
    ({ ai: () => openAI(), history: () => { openPage("history"); renderHistory($("histBody"), 7); }, news: () => openNews(S.symbol), chain: () => openChain(hasOptions(S.symbol) ? S.symbol : "NIFTY") }[b.dataset.open] || (() => {}))(); });
  $("themeToggle").addEventListener("click", () => { const dark = document.documentElement.dataset.theme !== "dark"; document.documentElement.dataset.theme = dark ? "dark" : "light"; store.set("theme", dark ? "dark" : "light");
    try { localStorage.setItem("catc_theme", JSON.stringify(dark ? "dark" : "light")); } catch { /* ignore */ } if (S.chart) S.chart.setTheme(); });

  // ------------------------------------------------------------------ news page
  async function openNews(sym) {
    const r = root(sym); $("newsSub").textContent = `${r} and market-moving news`; $("newsList").innerHTML = `<li><span class="skel w80"></span><span class="skel w60"></span></li>`; openPage("news");
    try { const d = await api(`/api/news/unified?symbol=${encodeURIComponent(r)}&limit=80`, { timeout: 30000 });
      $("newsList").innerHTML = (d.events || []).map((n) => `<li><b><span class="dot ${esc(n.sentiment || "")}"></span>${esc(n.headline || n.event)}</b>${n.summary ? `<p>${esc(String(n.summary).slice(0, 260))}</p>` : ""}<time>${esc(n.source || "")} · ${esc(dmy(n.published_at))} ${esc(hhmm(n.published_at))}${n.url ? ` · <a href="${esc(n.url)}" target="_blank" rel="noopener" style="color:var(--accent)">Open</a>` : ""}</time></li>`).join("") || `<li class="muted">No material news right now.</li>`;
    } catch (e) { $("newsList").innerHTML = `<li>${esc(e.message)}</li>`; }
  }

  // ------------------------------------------------------------------ CA AI chat
  function md(text) {   // small, safe Markdown subset for AI replies (escaped first)
    const lines = esc(text).split("\n"); let out = "", list = false, tbl = [];
    const inline = (s) => s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
    const flushTbl = () => { if (!tbl.length) return; const rows = tbl.filter((r) => !/^\s*\|?\s*:?-{2,}/.test(r)); out += "<table>" + rows.map((r, i) => "<tr>" + r.replace(/^\s*\||\|\s*$/g, "").split("|").map((c) => (i ? `<td>${inline(c.trim())}</td>` : `<th>${inline(c.trim())}</th>`)).join("") + "</tr>").join("") + "</table>"; tbl = []; };
    lines.forEach((l) => {
      if (/^\s*\|.*\|\s*$/.test(l)) { tbl.push(l); return; } flushTbl();
      const li = l.match(/^\s*[-*•]\s+(.*)/); if (li) { if (!list) { out += "<ul>"; list = true; } out += `<li>${inline(li[1])}</li>`; return; }
      if (list) { out += "</ul>"; list = false; }
      const h = l.match(/^\s*#{1,4}\s+(.*)/); if (h) { out += `<h4>${inline(h[1])}</h4>`; return; }
      out += l.trim() ? `<div>${inline(l)}</div>` : "<div style='height:6px'></div>";
    });
    flushTbl(); if (list) out += "</ul>"; return out;
  }
  function renderChat() {
    $("aiLog").innerHTML = S.chat.length ? S.chat.map((m) => `<div class="msg ${m.role === "user" ? "me" : "ai"}">${m.role === "user" ? esc(m.text) : md(m.text)}</div>`).join("")
      : `<div class="msg ai">Hi! I'm CA AI. Ask me about any stock or index, a level, a past day, or why a signal says what it says. I answer from live Upstox data.</div>
         <div class="chat-suggest">${["Is NIFTY bullish right now?", "Where is support for BANKNIFTY?", "Compare Reliance and TCS today", "Explain the scalp plan for NIFTY"].map((s) => `<button type="button" data-suggest="${esc(s)}">${esc(s)}</button>`).join("")}</div>`;
    const sc = $("aiScroll"); requestAnimationFrame(() => (sc.scrollTop = sc.scrollHeight));
  }
  function openAI(prefill) { openPage("ai"); renderChat(); if (prefill) { $("aiInput").value = prefill; } setTimeout(() => $("aiInput").focus(), 300); }
  $("aiLog").addEventListener("click", (e) => { const b = e.target.closest("[data-suggest]"); if (b) { $("aiInput").value = b.dataset.suggest; $("aiForm").requestSubmit(); } });
  $("aiClear").addEventListener("click", () => { S.chat = []; store.set("chat", []); renderChat(); });
  $("aiInput").addEventListener("input", (e) => { e.target.style.height = "auto"; e.target.style.height = Math.min(120, e.target.scrollHeight) + "px"; });
  $("aiInput").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && window.matchMedia("(pointer:fine)").matches) { e.preventDefault(); $("aiForm").requestSubmit(); } });
  $("aiForm").addEventListener("submit", async (e) => {
    e.preventDefault(); const q = $("aiInput").value.trim(); if (!q) return;
    const history = S.chat.slice(-8).map((m) => ({ role: m.role === "user" ? "user" : "model", text: m.text }));
    S.chat.push({ role: "user", text: q }); $("aiInput").value = ""; $("aiInput").style.height = "auto"; renderChat();
    $("aiLog").insertAdjacentHTML("beforeend", `<div class="msg ai" id="aiTyping"><span class="typing"><i></i><i></i><i></i></span></div>`); $("aiScroll").scrollTop = 1e9;
    try { const r = await api("/api/ai/ask", { method: "POST", body: { prompt: q, symbol: root(S.symbol), mode: "data", history }, timeout: 70000 });
      S.chat.push({ role: "ai", text: r.reply || "No answer." }); }
    catch (err) { S.chat.push({ role: "ai", text: `Sorry — ${err.message}` }); }
    S.chat = S.chat.slice(-30); store.set("chat", S.chat); renderChat();
  });

  // ------------------------------------------------------------------ refresh schedule (pauses in background)
  job(3000, () => true, loadQuotes);
  job(20000, () => S.tab === "signals", () => loadSignals(false));
  job(120000, () => S.tab === "signals", () => loadSigNews(S.symbol));
  job(5000, () => S.tab === "portfolio" && pseg === "positions", loadPortfolio);
  job(8000, () => S.tab === "orders" && oseg !== "hist", loadOrders);
  job(60000, () => !!S.chartSym && !!S.chart && ["1m", "3m", "5m"].includes(S.chart.timeframe), loadCandles);
  job(60000, () => S.tab === "watch", loadLists);

  // ------------------------------------------------------------------ boot
  window.CAM = { state: S };   // for support/debugging from the browser console
  (async () => {
    renderTicker(); await loadLists(); renderChips(); setTab(S.tab, { silent: true }); loadQuotes();
    api("/api/auth/me").then((me) => { const u = me.user || {}; const n = (u.full_name || u.username || "").split(/\s+/)[0]; if (n) $("tabUser").textContent = n; }).catch(() => {});
  })();
})();
