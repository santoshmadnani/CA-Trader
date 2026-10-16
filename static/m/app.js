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
    tab: store.get("tab", "watch"), symbol: store.get("symbol", "NIFTY"), hz: store.get("hz", null), lists: [], listId: store.get("list", null), watch: [],
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

  // Segmented controls get a sliding ink pill that follows aria-selected (works for any .seg, including ones added later).
  function placeInk(seg) { const ink = seg.querySelector(":scope > .seg-ink"), b = seg.querySelector('button[aria-selected="true"]'); if (!ink) return;
    if (!b || !b.offsetWidth) { ink.style.opacity = b ? ink.style.opacity : "0"; return; } ink.style.opacity = "1"; ink.style.width = `${b.offsetWidth}px`; ink.style.transform = `translateX(${b.offsetLeft}px)`; }
  const segRO = "ResizeObserver" in window ? new ResizeObserver((es) => es.forEach((e) => placeInk(e.target))) : null;
  function inkify(root = document) {
    root.querySelectorAll(".seg:not(.has-ink)").forEach((seg) => { seg.classList.add("has-ink"); seg.insertAdjacentHTML("afterbegin", '<span class="seg-ink" aria-hidden="true"></span>');
      new MutationObserver(() => placeInk(seg)).observe(seg, { subtree: true, attributes: true, attributeFilter: ["aria-selected"] }); if (segRO) segRO.observe(seg); placeInk(seg); });
  }
  // Tap ripple on primary buttons.
  document.addEventListener("pointerdown", (e) => { const b = e.target.closest(".btn:not(.tiny)"); if (!b || b.disabled) return; const r = b.getBoundingClientRect(), d = Math.max(r.width, r.height), sp = document.createElement("span");
    sp.className = "ripple"; sp.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`; b.appendChild(sp); setTimeout(() => sp.remove(), 650); }, { passive: true });
  // Swipe-to-confirm slider; Enter/Space also confirms for keyboard users.
  function mountSwipe(el, onDone) {
    const k = el.querySelector(".knob"), f = el.querySelector(".fill"); let x0 = null, x = 0, max = 0;
    const set = (v) => { x = v; k.style.left = `${4 + v}px`; f.style.width = `${58 + v}px`; };
    const reset = () => { el.classList.add("reset"); set(0); setTimeout(() => el.classList.remove("reset"), 360); };
    const done = async () => { haptic(); el.classList.add("busy"); try { await onDone(); } finally { if (el.isConnected) { el.classList.remove("busy"); reset(); } } };
    k.addEventListener("pointerdown", (e) => { if (el.classList.contains("busy")) return; x0 = e.clientX - x; max = el.clientWidth - 58; el.classList.remove("reset"); k.setPointerCapture(e.pointerId); });
    k.addEventListener("pointermove", (e) => { if (x0 !== null) set(Math.max(0, Math.min(max, e.clientX - x0))); });
    const up = () => { if (x0 === null) return; x0 = null; if (x > max * 0.85) { set(max); done(); } else reset(); };
    k.addEventListener("pointerup", up); k.addEventListener("pointercancel", up);
    el.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && !el.classList.contains("busy")) { e.preventDefault(); max = el.clientWidth - 58; el.classList.add("reset"); set(max); setTimeout(done, 300); } });
    return { reset };
  }

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
    $("wList").classList.toggle("settled", !!renderWatch.done); if (S.watch.length) renderWatch.done = true;
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
    if (sheetOpen() && $("tLtp") && $("tSym")) { const t = S.quotes[$("tSym").value.trim().toUpperCase()]; if (t && num(t.ltp) !== null) { $("tLtp").textContent = fmt(t.ltp); $("tLtpWrap").hidden = false; } }
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
    const lot = num(p.lot) || 1, buy = side === "BUY";
    const om = String(p.symbol).match(/^(\S+)\s+(\d+(?:\.\d+)?)\s*(CE|PE)\s*(\d{4}-\d{2}-\d{2})?$/i);
    const title = om ? `${om[2]} ${om[3].toUpperCase()}` : p.symbol, sub = [om ? `${om[1]}${om[4] ? " · expiry " + dmy(om[4]) : ""}` : "", p.plan ? `from the ${String(p.plan).toLowerCase()} plan` : ""].filter(Boolean).join(" · ");
    openSheet(`<div class="sh-head" style="border-bottom:0"><h2 id="sheetTitle" class="${buy ? "up" : "dn"}">${buy ? "Buy" : "Sell"} ${esc(title)}</h2><div class="q small muted">${esc(sub)}<span id="tLtpWrap" hidden>${sub ? " · " : ""}LTP <span class="num" id="tLtp"></span></span></div></div>
      <div class="seg mode-seg" role="tablist" id="tMode"><button type="button" role="tab" aria-selected="true" data-mode="paper">Paper</button><button type="button" role="tab" aria-selected="false" data-mode="live">Live</button></div>
      <form class="form" id="tForm" onsubmit="return false">
        <input type="hidden" id="tSide" value="${side}"><label class="full">Contract<input id="tSym" value="${esc(p.symbol)}" autocomplete="off"></label>
        <div class="field">Lots<div class="stepper"><button type="button" data-step="-1" aria-label="Fewer lots">−</button><input id="tLots" type="number" inputmode="numeric" min="1" step="1" value="1" aria-label="Lots"><button type="button" data-step="1" aria-label="More lots">+</button></div></div>
        <label>Lot size<input id="tLot" type="number" inputmode="numeric" min="1" step="1" value="${lot}"></label>
        <label>Type<select id="tType"><option ${p.entry ? "selected" : ""}>LIMIT</option><option ${p.entry ? "" : "selected"}>MARKET</option></select></label><label>Price<input id="tPx" type="number" inputmode="decimal" step="0.05" value="${p.entry ?? ""}"></label>
        <label>Stop loss<input id="tSl" type="number" inputmode="decimal" step="0.05" value="${p.sl ?? ""}"></label><label>Target<input id="tTg" type="number" inputmode="decimal" step="0.05" value="${p.tgt ?? ""}"></label>
      </form>
      <input type="checkbox" id="tLive" hidden>
      <div class="sum-tiles"><div><span>Value</span><b class="num" id="tVal">—</b></div><div><span>Risk</span><b class="num dn" id="tRisk">—</b></div><div><span>Reward</span><b class="num up" id="tRew">—</b></div></div>
      <div class="sum-line" id="tSum"></div>
      <div class="swipe ${buy ? "" : "sell"}" id="tGo" role="button" tabindex="0" aria-label="Swipe, or press Enter, to place the order"><div class="fill"></div><div class="label" id="tGoLbl"></div><div class="knob"><svg><use href="#m-arrow"/></svg></div></div>`);
    inkify($("sheetBody"));
    const q0 = S.quotes[String(p.symbol).toUpperCase()]; if (q0 && num(q0.ltp) !== null) { $("tLtp").textContent = fmt(q0.ltp); $("tLtpWrap").hidden = false; }
    const upd = () => { const qty = (+$("tLots").value || 0) * (+$("tLot").value || 0), px = +$("tPx").value || 0, sl = +$("tSl").value || 0, tg = +$("tTg").value || 0, live = $("tLive").checked;
      $("tVal").textContent = px ? `₹${fmt(px * qty, 0)}` : "—"; $("tRisk").textContent = px && sl ? `₹${fmt(Math.abs(px - sl) * qty, 0)}` : "—"; $("tRew").textContent = px && tg ? `₹${fmt(Math.abs(tg - px) * qty, 0)}` : "—";
      $("tSum").textContent = `${side} ${qty} × ${$("tSym").value} ${$("tType").value === "LIMIT" && px ? "@ ₹" + fmt(px) : "at market"}${live ? " · goes to your broker" : " · paper trade"}`;
      $("tGoLbl").textContent = `Swipe to place ${live ? "LIVE" : "paper"} ${side.toLowerCase()}`; };
    ["tLots", "tLot", "tPx", "tSl", "tTg", "tType", "tSym"].forEach((id) => $(id).addEventListener("input", upd));
    $("tForm").addEventListener("click", (e) => { const b = e.target.closest("[data-step]"); if (!b) return; haptic(); $("tLots").value = Math.max(1, (+$("tLots").value || 1) + +b.dataset.step); upd(); });
    $("tMode").addEventListener("click", (e) => { const b = e.target.closest("[data-mode]"); if (!b) return; haptic(); $("tMode").querySelectorAll("button").forEach((x) => x.setAttribute("aria-selected", String(x === b))); $("tLive").checked = b.dataset.mode === "live"; upd(); });
    mountSwipe($("tGo"), placeOrder); upd();
  }
  async function placeOrder() {
    const side = $("tSide").value, qty = (+$("tLots").value || 0) * (+$("tLot").value || 0); if (!qty) return toast("Enter a quantity");
    const live = $("tLive").checked;
    if (live && !confirm(`Send a LIVE ${side} order for ${qty} × ${$("tSym").value} to your broker?`)) return;
    const body = { symbol: $("tSym").value.trim(), side, quantity: qty, order_type: $("tType").value, price: $("tType").value === "LIMIT" ? (+$("tPx").value || null) : null,
      stop_loss: +$("tSl").value || null, target: +$("tTg").value || null, paper: !live, live };
    try { const r = await api("/api/orders", { method: "POST", body }); haptic(); toast(`${live ? "Live" : "Paper"} ${side.toLowerCase()} ${r.status || r.execution_state || "placed"} · ${qty} × ${body.symbol}`); closeSheet(false); if (S.tab === "orders") loadOrders(); if (S.tab === "portfolio") loadPortfolio(); }
    catch (err) { toast(`Rejected: ${err.message}`); }
  }

  // ------------------------------------------------------------------ signals
  function renderChips() {
    const syms = [...new Set(["NIFTY", "BANKNIFTY", ...S.watch.filter((s) => !s.includes("|"))])].slice(0, 12);
    $("sigChips").innerHTML = syms.map((s) => `<button type="button" data-chip="${esc(s)}" aria-pressed="${s === S.symbol}">${esc(s)}</button>`).join("");
    $("sigSym").textContent = S.symbol;
  }
  $("sigChips").addEventListener("click", (e) => { const b = e.target.closest("[data-chip]"); if (!b) return; haptic(); S.symbol = b.dataset.chip; store.set("symbol", S.symbol); renderChips(); loadSignals(true); loadQuotes(); });
  $("sigSymBtn").addEventListener("click", () => { setTab("watch"); setTimeout(() => $("wSearch").focus(), 100); });

  // Big price + intraday sparkline. The sparkline is today's Upstox 5m closes plus the live LTP; nothing is drawn without candles.
  const spark = {};
  async function loadSpark(sym) {
    const c = spark[sym]; if (c && Date.now() - c.at < 5 * 60000) return;
    try { const d = await api(`/api/market/candles/${encodeURIComponent(sym)}?timeframe=5m&days=3`, { timeout: 30000 }); const cs = d.candles || [];
      const t = (x) => x.time ?? x.timestamp ?? x.t ?? x[0], cl = (x) => num(x.close ?? x.c ?? x[4]);
      const day = (x) => { const v = t(x); const dt = typeof v === "number" ? new Date(v < 1e12 ? v * 1000 : v) : new Date(v); return dt.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }); };
      const last = cs.length ? day(cs[cs.length - 1]) : null;
      spark[sym] = { at: Date.now(), pts: cs.filter((x) => day(x) === last).map(cl).filter((v) => v !== null) };
      if (sym === S.symbol) renderSigQuote();
    } catch { spark[sym] = { at: Date.now(), pts: [] }; }
  }
  let lastSigLtp = null, lastSigSym = null;
  function renderSigQuote() {
    const q = S.quotes[S.symbol] || {}, v = num(q.ltp), box = $("sigQuote");
    const pts = [...((spark[S.symbol] || {}).pts || []), ...(v !== null ? [v] : [])];
    let svg = "";
    if (pts.length > 2) { const lo = Math.min(...pts), hi = Math.max(...pts), X = (i) => ((i / (pts.length - 1)) * 118).toFixed(1), Y = (p) => (40 - ((p - lo) / (hi - lo || 1)) * 36).toFixed(1);
      const line = pts.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p)}`).join(""), col = pts[pts.length - 1] >= pts[0] ? "var(--up)" : "var(--dn)";
      svg = `<svg class="spark" viewBox="0 0 118 44" preserveAspectRatio="none" aria-hidden="true"><path class="area" d="${line}L118,44L0,44Z" style="fill:${col}"/><path d="${line}" style="stroke:${col}"/></svg>`; }
    if (!box.querySelector(".qc-l")) box.innerHTML = `<div class="qc-l"><span class="ltp" id="sigLtp"></span><span class="chg" id="sigChg"></span></div><div id="sigSpark"></div>`;
    const el = $("sigLtp"); el.textContent = fmt(v); el.className = `ltp ${cls(q.change_pct)}`;
    if (lastSigSym === S.symbol && lastSigLtp !== null && v !== null && v !== lastSigLtp) { el.classList.remove("tick-up", "tick-dn"); requestAnimationFrame(() => el.classList.add(v > lastSigLtp ? "tick-up" : "tick-dn")); }
    lastSigLtp = v; lastSigSym = S.symbol;
    $("sigChg").innerHTML = num(q.change_pct) === null ? "" : `<span class="${cls(q.change_pct)}">${sgn(q.net_change)} (${sgn(q.change_pct)}%)</span>`;
    $("sigSpark").innerHTML = svg;
  }

  async function loadSignals(force) {
    const sym = S.symbol;
    if (force && !S.signals[sym]) { $("sigHz").innerHTML = ""; $("sigPlans").innerHTML = `<div class="plan" style="padding:18px"><span class="skel w40"></span><span class="skel w80"></span><span class="skel w60"></span><span class="skel w80"></span></div>`; }
    renderSigQuote(); if (force) loadSpark(sym);
    try {
      const d = await api(`/api/signals/${encodeURIComponent(sym)}`, { timeout: 60000 }); if (sym !== S.symbol) return;
      S.signals[sym] = { data: d, at: Date.now() }; renderPlans(); $("sigLive").classList.toggle("on", !!d.market_open);
    } catch (e) { if (sym === S.symbol && !S.signals[sym]) $("sigPlans").innerHTML = `<div class="plan"><div class="empty"><b>Signals unavailable</b>${esc(e.message)}</div></div>`; }
    if (force) { loadNextSession(sym); loadSigNews(sym); }
  }

  const FACTOR_NAMES = { trend: "Trend", vwap: "VWAP", momentum: "Momentum", price_action: "Price action", day_change: "Day change", option_flow: "Option flow" };
  const openWhy = new Set(); let drawnKey = null, slideDir = null;
  const isLive = (p) => p && p.available && !p.expired && (p.decision === "BUY" || p.decision === "SELL");
  const optName = (o) => { const s = String(o.symbol || ""); const m = s.match(/(\d+(?:\.\d+)?)\s*(CE|PE)\s*(\d{4}-\d{2}-\d{2})?/i);
    return m ? { name: `${m[1]} ${m[2].toUpperCase()}`, exp: m[3] ? dmy(m[3]) : "" } : { name: s, exp: "" }; };
  const htfPills = (p) => (p.higher_timeframes || []).map((h) => `<span class="pill ${h.bias > 0 ? "up" : h.bias < 0 ? "dn" : ""}">${esc(h.tf)} ${h.bias > 0 ? "▲" : h.bias < 0 ? "▼" : "•"}</span>`).join("");

  function currentPlan() {
    const rec = S.signals[S.symbol]; const plans = (rec && rec.data.plans) || []; if (!plans.length) return { plans, p: null, i: -1 };
    let i = plans.findIndex((x) => x.horizon === S.hz); if (i < 0) { i = Math.max(0, plans.findIndex(isLive)); S.hz = plans[i].horizon; }
    return { plans, p: plans[i], i };
  }
  function renderPlans() {
    const rec = S.signals[S.symbol]; if (!rec) return; const d = rec.data;
    $("sigClosed").innerHTML = d.market_open ? "" : `<div class="closed-note"><span class="pill warn">Market closed</span><span class="small">New plans from 09:15 NSE · 09:00 MCX. Showing the latest read.</span></div>`;
    const { plans, p } = currentPlan();
    $("sigHz").innerHTML = plans.map((x) => `<button type="button" role="tab" data-hz="${esc(x.horizon)}" aria-selected="${x.horizon === S.hz}"><em class="${isLive(x) ? x.decision : ""}"></em><b>${esc(x.label)}</b><span>${esc(x.timeframe)} chart</span></button>`).join("");
    if (!p) { $("sigPlans").innerHTML = `<div class="plan"><div class="empty"><b>No plans</b>The model returned nothing for ${esc(S.symbol)}.</div></div>`; return; }
    const key = `${S.symbol}|${p.horizon}`, first = drawnKey !== key; drawnKey = key;
    const anim = first ? (slideDir ? ` slide-${slideDir}` : " enter") : ""; slideDir = null;
    $("sigPlans").innerHTML = planHtml(p, key, anim, first);
    tickCountdowns(); updateLadders(); animateFactors(false);
  }
  $("sigHz").addEventListener("click", (e) => { const b = e.target.closest("[data-hz]"); if (!b || b.dataset.hz === S.hz) return; haptic();
    const { plans } = currentPlan(); const from = plans.findIndex((x) => x.horizon === S.hz), to = plans.findIndex((x) => x.horizon === b.dataset.hz);
    slideDir = to > from ? "l" : "r"; S.hz = b.dataset.hz; store.set("hz", S.hz); renderPlans(); if (S.chartSym) applyPlanLevels(); });

  const CTX_NAMES = { open: "the opening hour", morning: "late morning", midday: "midday", late: "the afternoon", daily: "daily bars", low: "low", normal: "normal", high: "high" };
  function ctxLine(p) {
    const cx = p.context, st = (p.track_record || {}).context; if (!cx || !st) return "";
    const b = (dim) => (st[dim] || {})[cx[dim]] || {}, t = b("tod"), v = b("vol");
    const part = (name, x) => x.n ? `${name}: ${x.n} past trades, hit ${fmt(x.hit, 0)}%, ${sgn(x.exp_net ?? x.exp, 2)}R after costs` : `${name}: not enough past trades`;
    return `<p class="muted">Context now: ${esc(CTX_NAMES[cx.tod] || cx.tod)}, ${esc(CTX_NAMES[cx.vol] || cx.vol)} volatility. ${esc(part("Same time of day", t))}; ${esc(part("same volatility", v))}.</p>`;
  }
  function planHtml(p, key, anim, draw) {
    const opt = isIdx(S.symbol) || hasOptions(S.symbol);
    const factors = Object.entries(p.factors || {}).map(([k, v]) => { const x = Math.max(-100, Math.min(100, num(v) || 0));
      return `<div class="fx"><span>${esc(FACTOR_NAMES[k] || k)}</span><span class="fx-bar"><i class="${x >= 0 ? "up" : "dn"}" data-v="${x}"></i></span><b class="num ${cls(x)}">${sgn(x, 0)}</b></div>`; }).join("");
    const sc = Math.max(-100, Math.min(100, num(p.score) || 0)), live = isLive(p);
    const ringC = live ? (p.decision === "BUY" ? "var(--up)" : "var(--dn)") : "var(--line-strong)";
    const label = !p.available ? "NO DATA" : p.expired ? "EXPIRED" : p.decision === "BUY" ? (opt ? "BUY · CE" : "BUY") : p.decision === "SELL" ? (opt ? "SELL · PE" : "SELL") : "NO TRADE";
    const head = `<div class="plan-h"><div class="ring" style="--p:${Math.abs(sc)};--c:${ringC}"><div><b class="num">${sgn(sc, 0)}</b><small>score</small></div></div>
      <div class="t"><b>${esc(p.label)}</b><span>${esc(p.timeframe)} chart${p.hold ? ` · hold ${esc(p.hold)}` : ""}</span></div><span class="decision ${live ? p.decision : "NO_TRADE"}">${label}</span></div>`;
    const why = factors || p.instructions || (p.option && p.option.basis) ? `<details class="whybox" data-why="${esc(key)}"${openWhy.has(key) ? " open" : ""}><summary>Why this signal<svg><use href="#m-down"/></svg></summary><div class="why-body">${factors}
      ${p.instructions ? `<p>${esc(p.instructions)}</p>` : ""}${p.option && p.option.basis ? `<p class="muted">Option levels: ${esc(p.option.basis)}</p>` : ""}${ctxLine(p)}${p.gate ? `<p class="muted">Trades need a score beyond ±${esc(p.gate)}.</p>` : ""}</div></details>` : "";
    const tr = p.track_record;
    const stats = tr && tr.signals ? `<div class="stats"><div class="stat"><b class="num">${fmt(tr.t1_hit_rate, 0)}%</b><span>Hit T1 first</span></div>${tr.expectancy_r_net !== undefined && tr.expectancy_r_net !== null ? `<div class="stat"><b class="num ${cls(tr.expectancy_r_net)}">${sgn(tr.expectancy_r_net, 2)}R</b><span>Avg after costs</span></div>` : `<div class="stat"><b class="num ${cls(tr.expectancy_r)}">${sgn(tr.expectancy_r, 2)}R</b><span>Avg per trade</span></div>`}<div class="stat"><b class="num">${esc(tr.filled ?? tr.signals)}</b><span>Past trades</span></div></div><div class="stats-note">Backtest ${esc(dmy(tr.from))} – ${esc(dmy(tr.to))}${tr.cost_r_avg ? ` · costs ≈ ${fmt(tr.cost_r_avg, 2)}R a trade · before costs ${sgn(tr.expectancy_r, 2)}R` : ""}</div>` : "";
    if (!live) {
      const title = !p.available ? "No data yet" : p.expired ? "Entry window closed" : "Sit this one out";
      const text = p.expired && p.valid_until ? `This ${p.decision === "SELL" ? "sell" : "buy"} plan expired at ${hhmm(p.valid_until)}. A new plan appears when the score clears the gate again.` : (p.reason || "");
      return `<article class="plan${anim}">${head}<div class="empty" style="padding:8px 20px 6px"><b>${title}</b>${esc(text)}</div>${p.available ? `<div class="pills">${htfPills(p)}</div>` : ""}${stats}${why}</article>`;
    }
    const buy = p.decision === "BUY", entryRef = buy ? p.entry_low : p.entry_high;
    const levels = [["Target 2", p.target_2, "up"], ["Target 1", p.target_1, "up"], ["Entry zone", entryRef, ""], ["Stop loss", p.stop_loss, "dn"]].sort((a, b) => b[1] - a[1])
      .map(([k, v, c]) => `<div class="lv"><span>${k}</span><b class="num ${c}">${fmt(v)}</b></div>`).join("");
    const o = p.option, on = o ? optName(o) : null;
    return `<article class="plan${anim}" data-plan="${esc(p.horizon)}">${head}
      <div class="ladder-wrap"><div class="ladder${draw ? " draw" : ""}" id="ladder">${ladderInner(p)}</div><div class="levels">${levels}</div></div>
      <div class="tiles"><div class="tile"><span>Reward : risk</span><b class="num">${p.rr_t1 ? `${fmt(p.rr_t1, 2)}<small> : 1</small>` : "—"}</b></div>
        <div class="tile"><span>To entry</span><b class="num" id="sigDist">—</b></div>
        <div class="tile"><span>Time left</span><b class="num countdown" data-short data-until="${esc(p.valid_until)}">${hhmm(p.valid_until)}</b><div class="timebar" id="sigTbar" data-from="${esc(p.as_of || "")}" data-until="${esc(p.valid_until)}"><i></i></div></div></div>
      <div class="steps"><span class="step"><svg><use href="#m-clock"/></svg>Enter by <b>${hhmm(p.valid_until)}</b></span><span class="step"><svg><use href="#m-bolt"/></svg>Book part at <b class="up">T1</b></span>
        <span class="step"><svg><use href="#m-trend"/></svg>Trail to <b class="up">T2</b></span>${p.time_stop_bars ? `<span class="step"><svg><use href="#m-stop"/></svg>Exit after <b>${esc(p.time_stop_bars)}</b> bars</span>` : ""}</div>
      ${o ? `<div class="opt"><div class="opt-h"><span class="opt-name">${esc(on.name)} ${on.exp ? `<small>${esc(on.exp)}</small>` : ""}</span><span class="pill">LTP <b class="num">${fmt(o.ltp)}</b></span><span class="pill">Δ <b class="num">${fmt(o.delta, 2)}</b></span></div>
        <div class="opt-lv"><div><span>Buy</span><b class="num">${fmt(o.entry_low)}</b><small>to ${fmt(o.entry_high)}</small></div><div><span>SL</span><b class="num dn">${fmt(o.stop_loss)}</b></div><div><span>T1</span><b class="num up">${fmt(o.target_1)}</b></div><div><span>T2</span><b class="num up">${fmt(o.target_2)}</b></div></div>
        <button type="button" class="btn cta" data-trade-opt='${esc(JSON.stringify({ symbol: o.symbol, entry: o.entry_high, sl: o.stop_loss, tgt: o.target_1, plan: p.label }))}'>Buy ${esc(on.name)}<svg><use href="#m-arrow"/></svg></button></div>`
        : `<div class="opt"><button type="button" class="btn cta" data-trade-plan='${esc(JSON.stringify({ side: p.decision, symbol: S.symbol, entry: buy ? p.entry_high : p.entry_low, sl: p.stop_loss, tgt: p.target_1, plan: p.label }))}'>${buy ? "Buy" : "Sell"} ${esc(S.symbol)}<svg><use href="#m-arrow"/></svg></button></div>`}
      <div class="pills">${htfPills(p)}</div>${stats}${why}</article>`;
  }
  // Vertical ladder: all levels and the live price on one price scale (top = higher price), for BUY and SELL alike.
  function ladScale(p) { const v = num((S.quotes[S.symbol] || {}).ltp); const vals = [p.stop_loss, p.target_2, p.entry_low, p.entry_high, ...(v !== null ? [v] : [])].map(Number);
    const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo) * 0.1 || 1; return { lo: lo - pad, hi: hi + pad }; }
  function ladderInner(p) {
    const { lo, hi } = ladScale(p), y = (v) => ((hi - v) / (hi - lo)) * 100, buy = p.decision === "BUY";
    const zt = y(Math.max(p.entry_low, p.entry_high)), zb = y(Math.min(p.entry_low, p.entry_high));
    const rk = buy ? [zb, y(p.stop_loss)] : [y(p.stop_loss), zt], rw = buy ? [y(p.target_2), zt] : [zb, y(p.target_2)];
    return `<div class="band risk${buy ? "" : " down"}" style="top:${rk[0]}%;height:${rk[1] - rk[0]}%"></div><div class="band reward${buy ? "" : " down"}" style="top:${rw[0]}%;height:${rw[1] - rw[0]}%"></div>
      <div class="band zone" style="top:${zt}%;height:${Math.max(2.5, zb - zt)}%"></div>
      <div class="lvl SL" style="top:${y(p.stop_loss)}%"><span>SL</span></div><div class="lvl T1" style="top:${y(p.target_1)}%"><span>T1</span></div><div class="lvl T2" style="top:${y(p.target_2)}%"><span>T2</span></div>
      <div class="lad-ltp" id="ladLtp" hidden><b class="num" id="ladLtpV"></b><i></i></div>`;
  }
  function updateLadders() {
    const { p } = currentPlan(); const pin = $("ladLtp"); if (!pin || !isLive(p)) return;
    const v = num((S.quotes[S.symbol] || {}).ltp); if (v === null) { pin.hidden = true; return; }
    const { lo, hi } = ladScale(p); const top = ((hi - v) / (hi - lo)) * 100;
    if (top < 2 || top > 98) { $("ladder").innerHTML = ladderInner(p); return updateLadders(); }   // price left the scale: rescale
    const pn = $("ladLtp"); pn.hidden = false; pn.style.top = `${top}%`; $("ladLtpV").textContent = fmt(v);
    const buy = p.decision === "BUY", inZone = v >= p.entry_low && v <= p.entry_high, dist = buy ? (v > p.entry_high ? v - p.entry_high : p.entry_low - v) : (v < p.entry_low ? p.entry_low - v : v - p.entry_high);
    const de = $("sigDist"); if (de) { de.textContent = inZone ? "In zone" : `${fmt(Math.abs(dist))} pts`; de.className = `num ${inZone ? "up" : ""}`; }
  }
  function animateFactors(fromClosed) {
    const det = $("sigPlans").querySelector("details.whybox"); if (!det) return;
    det.querySelectorAll(".fx-bar i").forEach((i) => { const v = +i.dataset.v, w = det.open ? Math.abs(v) / 2 : 0, l = v < 0 ? 50 - w : 50;
      if (fromClosed) { i.style.width = "0"; i.style.left = "50%"; requestAnimationFrame(() => requestAnimationFrame(() => { i.style.width = w + "%"; i.style.left = l + "%"; })); }
      else { i.style.transition = "none"; i.style.width = w + "%"; i.style.left = l + "%"; requestAnimationFrame(() => (i.style.transition = "")); } });
  }
  $("sigPlans").addEventListener("toggle", (e) => { const d = e.target; if (!d.matches || !d.matches("details[data-why]")) return;
    if (d.open) openWhy.add(d.dataset.why); else openWhy.delete(d.dataset.why); animateFactors(d.open); }, true);
  function tickCountdowns() {
    document.querySelectorAll(".countdown[data-until]").forEach((el) => { const left = (new Date(el.dataset.until) - Date.now()) / 1000;
      const mmss = `${Math.floor(left / 60)}m ${String(Math.floor(left % 60)).padStart(2, "0")}s`;
      el.textContent = left <= 0 ? "Expired" : "short" in el.dataset ? (left < 3600 ? mmss : `${Math.floor(left / 3600)}h ${Math.floor((left % 3600) / 60)}m`) : hhmm(el.dataset.until);
      el.classList.toggle("dn", left < 120); });
    const tb = $("sigTbar"); if (tb) { const end = new Date(tb.dataset.until).getTime(), start = tb.dataset.from ? new Date(tb.dataset.from).getTime() : end - 15 * 60000, left = end - Date.now();
      tb.querySelector("i").style.width = `${Math.max(0, Math.min(100, (left / Math.max(1, end - start)) * 100))}%`; tb.classList.toggle("low", left < 120000); }
    const rec = S.signals[S.symbol]; if (rec && S.tab === "signals") { const s = Math.round((Date.now() - rec.at) / 1000); $("sigAge").textContent = s < 60 ? `updated ${s}s ago` : `updated ${Math.round(s / 60)}m ago`; }
  }
  setInterval(() => { if (!document.hidden && S.tab === "signals") tickCountdowns(); }, 1000);
  $("sigPlans").addEventListener("click", (e) => {
    const b = e.target.closest("[data-trade-opt]"), c = e.target.closest("[data-trade-plan]");
    if (b) { haptic(); setTimeout(() => openTicket("BUY", JSON.parse(b.dataset.tradeOpt)), 120); }
    else if (c) { haptic(); const t = JSON.parse(c.dataset.tradePlan); setTimeout(() => openTicket(t.side, t), 120); }
  });

  async function loadNextSession(sym) {
    const box = $("sigNext"); const cached = S.nextSession[sym];
    if (!cached) box.innerHTML = `<div class="card" style="padding:14px"><span class="skel w60"></span><span class="skel w40"></span></div>`;
    try {
      const d = cached && Date.now() - cached.at < 20 * 60000 ? cached.data : await api(`/api/prediction/next-session/${encodeURIComponent(sym)}`, { timeout: 90000 });
      S.nextSession[sym] = { data: d, at: cached ? cached.at : Date.now() }; if (sym !== S.symbol) return;
      const p = d.prediction || {}, v = (d.validation || {}).direction || {}, g = (d.validation || {}).gap || {};
      if (!p.available) { box.innerHTML = `<div class="card"><div class="card-h"><h3>Next session</h3></div><div class="why">${esc(p.reason || "Not available")}</div></div>`; return; }
      const r = p.expected_range || {};
      box.innerHTML = `<div class="card"><div class="next"><div class="ring" style="--p:${num(p.p_up) || 0}"><div><b class="num">${fmt(p.p_up, 0)}%</b><small>higher</small></div></div>
        <div style="min-width:0"><h3>Next session · ${esc(dmy(p.for_date))}</h3><span class="pill ${p.bias === "UP" ? "up" : p.bias === "DOWN" ? "dn" : ""}">${esc(p.bias)}</span>
        <p style="margin-top:4px">Chance of a higher close · gap-up ${fmt(p.p_gap_up, 0)}%${p.us_session_included ? " · incl. last US session" : ""}</p>
        <div class="rng"><span class="pill num">Low ${fmt(r.low, 0)}</span><span class="pill num">High ${fmt(r.high, 0)}</span><span class="pill">Range hit ${fmt(r.historical_coverage_pct, 0)}%</span></div></div></div>
        <div class="next-track"><div><b class="num">${fmt(v.accuracy_pct, 1)}%</b><span>Direction (vs ${fmt(v.baseline_pct, 0)}%)</span></div><div><b class="num">${fmt(g.accuracy_pct, 1)}%</b><span>Gap (vs ${fmt(g.baseline_pct, 0)}%)</span></div><div><b class="num">${esc(v.test_days || 0)}</b><span>Days tested</span></div></div></div>`;
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
    refreshAlertBadge();
    try { const me = await api("/api/auth/me"); const u = me.user || {}; const name = u.full_name || u.username || "Trader";
      $("uName").textContent = name; $("uMail").textContent = u.email || ""; $("avatar").textContent = name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase(); } catch { /* ignore */ }
    try { const f = await api("/api/funds"); const l = f.local || {};
      $("funds").innerHTML = [["Available (paper)", "₹" + fmt(l.available, 0)], ["Used margin", "₹" + fmt(l.used, 0)], ["Realised P&L", `<span class="${cls(l.realized_pnl)}">₹${fmt(l.realized_pnl, 0)}</span>`], ["Unrealised P&L", `<span class="${cls(l.unrealized_pnl)}">₹${fmt(l.unrealized_pnl, 0)}</span>`]]
        .map(([k, v]) => `<div><span class="k">${k}</span><span class="v">${v}</span></div>`).join(""); } catch { /* ignore */ }
  }
  document.querySelector("#s-account .menu").addEventListener("click", (e) => { const b = e.target.closest("[data-open]"); if (!b) return; haptic();
    ({ alerts: () => openAlerts(), ai: () => openAI(), history: () => { openPage("history"); renderHistory($("histBody"), 7); }, news: () => openNews(S.symbol), chain: () => openChain(hasOptions(S.symbol) ? S.symbol : "NIFTY") }[b.dataset.open] || (() => {}))(); });
  $("themeToggle").addEventListener("click", () => { const dark = document.documentElement.dataset.theme !== "dark"; document.documentElement.dataset.theme = dark ? "dark" : "light"; store.set("theme", dark ? "dark" : "light");
    try { localStorage.setItem("catc_theme", JSON.stringify(dark ? "dark" : "light")); } catch { /* ignore */ } if (S.chart) S.chart.setTheme(); });

  // ------------------------------------------------------------------ signal alerts (push + Telegram)
  const pushSupported = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  const isiOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent);
  const standalone = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  let swReg = null, AL = null;
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).then((r) => { swReg = r; refreshAlertBadge(); }).catch(() => {});
    navigator.serviceWorker.addEventListener("message", (e) => { if (e.data && e.data.type === "open-signals") setTab("signals"); });
  }
  const u8 = (b64) => { const s = atob((b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from(s, (c) => c.charCodeAt(0)); };
  async function thisDeviceSub() { try { const r = swReg || (await navigator.serviceWorker.getRegistration("/")); return r ? await r.pushManager.getSubscription() : null; } catch { return null; } }
  async function refreshAlertBadge() {
    const el = $("alertsState"); if (!el) return;
    const sub = pushSupported() ? await thisDeviceSub() : null;
    const on = !!sub && Notification.permission === "granted";
    el.textContent = on ? "On" : "Off"; el.className = `pill ${on ? "up" : ""}`;
  }
  async function enablePush() {
    if (!pushSupported()) { toast(isiOS() && !standalone() ? "Add CA Trader to your Home Screen first, then open it from there" : "This browser can't show notifications"); return false; }
    if (!AL || !AL.vapid_public_key) { toast("Push isn't available on the server yet"); return false; }
    const perm = await Notification.requestPermission();
    if (perm !== "granted") { toast(perm === "denied" ? "Notifications are blocked. Allow them for catrader.site in your phone settings." : "Notifications not allowed"); return false; }
    const reg = swReg || (await navigator.serviceWorker.register("/sw.js", { scope: "/" })); await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: u8(AL.vapid_public_key) });
    await api("/api/alerts/subscribe", { method: "POST", body: { subscription: sub.toJSON() } });
    return true;
  }
  async function disablePush() { const sub = await thisDeviceSub(); if (sub) { try { await api("/api/alerts/unsubscribe", { method: "POST", body: { endpoint: sub.endpoint } }); } catch { /* ignore */ } await sub.unsubscribe().catch(() => {}); } }
  let alSaveT, alPrevT, alSug = null, alPrev = null, alPrevBusy = false;
  function saveAlerts(patch) { Object.assign(AL.config, patch); renderAlerts(); clearTimeout(alSaveT);
    alSaveT = setTimeout(async () => { try { const r = await api("/api/alerts/config", { method: "POST", body: AL.config }); AL.config = r.config; renderAlerts(); } catch (e) { toast(e.message); } }, 400);
    schedulePreview(); }
  function schedulePreview() { clearTimeout(alPrevT); alPrevT = setTimeout(() => loadPreview(false), 700); }
  async function loadPreview(suggest) {
    if (!AL) return; alPrevBusy = true; if (suggest) alSug = "loading"; renderPreview();
    try { const r = await api("/api/alerts/preview", { method: "POST", body: { config: AL.config, suggest }, timeout: 90000 }); alPrev = r; if (suggest) alSug = r.suggestion || null; }
    catch (e) { alPrev = { available: false, reason: e.message }; if (suggest) alSug = null; }
    alPrevBusy = false; renderPreview();
  }
  async function openAlerts() {
    openPage("alerts"); alSug = null; alPrev = null; $("alertsBody").innerHTML = `<div class="card" style="padding:16px"><span class="skel w60"></span><span class="skel w80"></span></div>`;
    try { AL = await api("/api/alerts/config"); AL.device = pushSupported() ? !!(await thisDeviceSub()) && Notification.permission === "granted" : false; renderAlerts(); loadPreview(false); }
    catch (e) { $("alertsBody").innerHTML = `<div class="empty"><b>Alerts unavailable</b>${esc(e.message)}</div>`; }
  }
  const pctTxt = (v) => (v === null || v === undefined ? "—" : `${fmt(v, 0)}%`), rTxt = (v) => (v === null || v === undefined ? "—" : `${sgn(v, 2)}R`);
  function renderPreview() {
    const box = $("alPreview"); if (!box) return; const p = alPrev;
    if (!p) { box.innerHTML = `<div class="card-h"><h3>Last weeks with these settings</h3></div><div style="padding:0 16px 14px"><span class="skel w80"></span><span class="skel w60"></span></div>`; return; }
    if (!p.available) { box.innerHTML = `<div class="card-h"><h3>Last weeks with these settings</h3></div><div class="why-text">${esc(p.reason || "Not available yet")}</div>`; return; }
    const r = p.result, hz = r.by_horizon || {};
    const sug = alSug === "loading" ? `<div class="why-text"><span class="skel w80"></span>Searching settings on older history…</div>`
      : alSug && alSug.available ? `<div class="al-sug"><b>Suggested for 5–10 a day</b><p>${esc(alSug.note)}</p>
          <div class="al-sug-grid"><span>Score +${esc(alSug.settings.min_score_margin)}</span><span>Hit ≥ ${esc(alSug.settings.min_hit_rate)}%</span><span>Avg ≥ ${fmt(alSug.settings.min_expectancy_r, 2)}R</span><span>HTF ${alSug.settings.require_htf_agree ? "all agree" : "majority"}</span><span>Context ${alSug.settings.context_edge ? "on" : "off"}</span></div>
          <p class="small">Recent untouched period: <b>${fmt(alSug.check.per_day, 1)}/day</b> · hit ${pctTxt(alSug.check.hit)} · ${rTxt(alSug.check.exp_net)} after costs</p>
          <button type="button" class="btn ghost" id="alApply">Apply these settings</button></div>`
      : alSug && !alSug.available ? `<div class="why-text">${esc(alSug.reason)}</div>` : "";
    box.innerHTML = `<div class="card-h"><h3>Last weeks with these settings</h3>${alPrevBusy ? `<span class="pill">updating</span>` : ""}</div>
      <div class="stats" style="padding-top:2px"><div class="stat"><b class="num">${fmt(r.per_day, 1)}</b><span>Alerts / day</span></div><div class="stat"><b class="num">${pctTxt(r.hit)}</b><span>Hit T1 first</span></div><div class="stat"><b class="num ${cls(r.exp_net)}">${rTxt(r.exp_net)}</b><span>Avg after costs</span></div></div>
      <div class="pills">${Object.entries(hz).map(([k, v]) => `<span class="pill ${v.exp_net > 0 ? "up" : v.exp_net < 0 ? "dn" : ""}">${k[0].toUpperCase() + k.slice(1)} · ${v.alerts} · ${rTxt(v.exp_net)}</span>`).join("")}</div>
      <p class="stats-note">Replayed on the most recent 40% of each backtest, using track records from the older part only. Symbols: ${esc((p.symbols || []).join(", "))}${(p.pending || []).length ? ` · still computing ${esc(p.pending.join(", "))}` : ""}</p>
      <div class="al-actions"><button type="button" class="btn primary" id="alSuggest"${alSug === "loading" ? " disabled" : ""}>Suggest settings for 5–10 a day</button></div>${sug}`;
  }
  function renderAlerts() {
    const c = AL.config, on = c.enabled && (AL.device || (c.telegram && AL.telegram_ready));
    const rule = (k, title, sub, val, step, min, max, unit = "") => `<div class="rule"><b>${title}</b><span>${sub}</span><div class="ctl"><button type="button" data-rk="${k}" data-d="${-step}" data-min="${min}" data-max="${max}" aria-label="Lower">−</button><output>${val}${unit}</output><button type="button" data-rk="${k}" data-d="${step}" data-min="${min}" data-max="${max}" aria-label="Higher">+</button></div></div>`;
    const sw = (k, title, sub) => `<div class="rule"><b>${title}</b><span>${sub}</span><div class="ctl"><span class="switch ${c[k] ? "on" : ""}" role="switch" tabindex="0" aria-checked="${!!c[k]}" data-sw="${k}"></span></div></div>`;
    $("alertsBody").innerHTML = `
      <div class="card al-hero"><h3>Notify me on high-conviction signals</h3><span class="switch ${on ? "on" : ""}" role="switch" tabindex="0" aria-checked="${on}" id="alMaster" aria-label="Signal alerts"></span>
        <p>A notification arrives the moment a new plan clears every filter below. You also get a follow-up when it hits a target or the stop.</p>
        <div class="al-status"><span class="pill ${AL.device ? "up" : ""}">This phone: ${AL.device ? "on" : "off"}</span><span class="pill">${esc(AL.devices)} device${AL.devices === 1 ? "" : "s"}</span><span class="pill ${AL.telegram_ready ? "up" : "warn"}">Telegram: ${AL.telegram_ready ? "connected" : "not set up"}</span></div></div>
      ${isiOS() && !standalone() ? `<div class="al-note"><b>On iPhone:</b> tap Share → Add to Home Screen, open CA Trader from the home screen, then switch alerts on here. iOS only allows notifications from home-screen apps.</div>` : ""}
      <div class="card" id="alPreview"></div>
      <div class="al-note"><b>No signal is sure-shot.</b> Judge settings by the result after costs, not the hit rate: a random market already hits a small T1 about 60% of the time.</div>
      <div class="card"><div class="card-h"><h3>What a plan must pass</h3></div>
        ${rule("min_score_margin", "Score strength", "Beyond the no-trade band by at least this much", `+${c.min_score_margin}`, 5, 0, 60)}
        ${rule("min_hit_rate", "Backtest hit rate", "Past trades that reached T1 before the stop", c.min_hit_rate, 5, 30, 95, "%")}
        ${rule("min_expectancy_r", "Average result", c.use_net ? "Average past result per trade, after costs" : "Average past result per trade, before costs", (+c.min_expectancy_r).toFixed(2), 0.05, -0.5, 1, "R")}
        ${sw("use_net", "Count trading costs", "Brokerage, STT, exchange charges, GST and slippage")}
        ${rule("min_signals", "Sample size", "Past trades behind those numbers", c.min_signals, 25, 25, 1000)}
        ${sw("require_htf_agree", "Higher timeframes agree", "Every confirming timeframe points the same way")}
        ${sw("context_edge", "Skip losing contexts", "Block a plan if its time of day or volatility lost money in the backtest")}
        <div class="rule hz-rule"><b>Horizons</b><span>Which plans can alert</span><div class="ctl hz-chips">${["scalp", "intraday", "swing"].map((h) => `<button type="button" data-hzc="${h}" aria-pressed="${(c.horizons || []).includes(h)}">${h[0].toUpperCase() + h.slice(1)}</button>`).join("")}</div></div></div>
      <div class="card"><div class="card-h"><h3>Coverage</h3></div>
        ${rule("scan_watchlist", "Watchlist symbols to scan", "Besides NIFTY and BANKNIFTY, from the top of your watchlist", c.scan_watchlist, 1, 0, 6)}
        ${rule("max_per_day", "Most alerts per day", "Stops new-signal alerts after this many", c.max_per_day, 1, 1, 50)}</div>
      <div class="card"><div class="card-h"><h3>Costs</h3></div>
        ${rule("per_order", "Brokerage per order", "Your broker's flat fee, in ₹", `₹${c.per_order}`, 5, 0, 100)}
        ${rule("slippage_ticks", "Slippage", "Ticks lost per side on entry and exit", c.slippage_ticks, 1, 0, 10)}</div>
      <div class="card"><div class="card-h"><h3>Delivery</h3></div>
        ${sw("push", "Phone notifications", "From the CA Trader app on your subscribed devices")}
        ${sw("telegram", "Telegram", AL.telegram_ready ? "Your configured Telegram chat" : "Add your bot token and chat ID in the desktop settings")}
        ${sw("outcomes", "Result follow-ups", "Target hit, stop hit, time exit or zone missed")}</div>
      <div class="al-actions"><button type="button" class="btn ghost" id="alTest">Send test notification</button></div>
      <p class="hint">Checked every 2 minutes while the market is open.</p>`;
    renderPreview();
  }
  $("alertsBody").addEventListener("click", async (e) => {
    const m = e.target.closest("#alMaster"), r = e.target.closest("[data-rk]"), s = e.target.closest("[data-sw]"), h = e.target.closest("[data-hzc]"), t = e.target.closest("#alTest");
    if (e.target.closest("#alSuggest")) { haptic(); loadPreview(true); return; }
    if (e.target.closest("#alApply") && alSug && alSug.settings) { haptic(); const st = alSug.settings; alSug = null; saveAlerts(st); toast("Suggested settings applied"); return; }
    if (m) { haptic(); const turnOn = m.getAttribute("aria-checked") !== "true";
      if (turnOn) { let got = false; if (AL.config.push) { try { got = await enablePush(); } catch (err) { toast(err.message); } } AL.device = got || AL.device;
        saveAlerts({ enabled: true }); if (got) toast("Alerts on for this phone"); else if (AL.config.telegram && AL.telegram_ready) toast("Alerts on (Telegram)"); }
      else { await disablePush(); AL.device = false; saveAlerts({ enabled: false }); toast("Alerts off"); }
      refreshAlertBadge(); return; }
    if (r) { haptic(); const k = r.dataset.rk, d = +r.dataset.d, v = Math.round((+AL.config[k] + d) * 100) / 100; saveAlerts({ [k]: Math.max(+r.dataset.min, Math.min(+r.dataset.max, v)) }); return; }
    if (s) { haptic(); const k = s.dataset.sw; saveAlerts({ [k]: !AL.config[k] });
      if (k === "push" && !AL.config.push) { await disablePush(); AL.device = false; renderAlerts(); refreshAlertBadge(); }
      else if (k === "push" && AL.config.push && AL.config.enabled) { try { AL.device = await enablePush(); } catch (err) { toast(err.message); } renderAlerts(); refreshAlertBadge(); } return; }
    if (h) { haptic(); const set = new Set(AL.config.horizons || []); set.has(h.dataset.hzc) ? set.delete(h.dataset.hzc) : set.add(h.dataset.hzc); saveAlerts({ horizons: [...set] }); return; }
    if (t) { t.disabled = true; try { if (AL.config.push && !AL.device) AL.device = await enablePush().catch(() => false);
        const res = await api("/api/alerts/test", { method: "POST" }); const p = res.push || {};
        toast(`Test sent · phone ${p.sent || 0}${p.failed ? `, ${p.failed} failed` : ""} · Telegram ${res.telegram || "off"}`); renderAlerts(); refreshAlertBadge(); }
      catch (err) { toast(err.message); } finally { const b = $("alTest"); if (b) b.disabled = false; } }
  });
  $("alertsBody").addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && e.target.matches("[role=switch]")) { e.preventDefault(); e.target.click(); } });

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
    inkify(); renderTicker(); await loadLists(); renderChips(); setTab(S.tab, { silent: true }); loadQuotes();
    api("/api/auth/me").then((me) => { const u = me.user || {}; const n = (u.full_name || u.username || "").split(/\s+/)[0]; if (n) $("tabUser").textContent = n; }).catch(() => {});
  })();
})();
