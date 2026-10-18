/* CA Fitness Tracker front end. Plain JS, no build step. Talks to /api/fit/* (backend/fitness/router.py). */
(() => {
  "use strict";

  // ------------------------------------------------------------------ helpers
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ic = (n) => `<svg><use href="#i-${n}"/></svg>`;
  const num = (v, d = 0) => (v == null || v === "" || isNaN(v) ? "–" : Number(v).toLocaleString("en-IN", { maximumFractionDigits: d }));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const IST_DAY = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata", year: "numeric", month: "2-digit", day: "2-digit" });
  const IST_HM = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false });
  const today = () => IST_DAY.format(new Date());
  const addDays = (d, n) => { const t = new Date(d + "T12:00:00Z"); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };
  const fmtDay = (d, opts = { weekday: "short", day: "numeric", month: "short" }) => new Date(d + "T12:00:00Z").toLocaleDateString("en-IN", { ...opts, timeZone: "UTC" });
  const dayLabel = (d) => { const t = today(); if (d === t) return "Today"; if (d === addDays(t, -1)) return "Yesterday"; if (d === addDays(t, 1)) return "Tomorrow"; return fmtDay(d); };
  const toMin = (hm) => { const [h, m] = String(hm || "0:0").split(":").map(Number); return h * 60 + (m || 0); };
  const store = { get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  const mins = (m) => { if (m == null) return "–"; m = Math.round(m); return m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m} min`; };
  const clock = (sec) => { sec = Math.max(0, Math.floor(sec)); const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60; return (h ? h + ":" + String(m).padStart(2, "0") : m) + ":" + String(s).padStart(2, "0"); };

  const PUBLIC = (location.pathname.match(/^\/fitnesstracker\/w\/([\w-]+)/) || [])[1] || null;
  const S = { me: null, profile: {}, slots: [], day: today(), dayData: null, tab: "today", activeId: null, nutrients: [], foodDb: null, progDays: 30 };
  const ACTIVITY = [["sedentary", "Sedentary (desk job, little exercise)"], ["light", "Light (1 to 3 workouts a week)"], ["moderate", "Moderate (3 to 5 a week)"], ["active", "Active (6 to 7 a week)"], ["very_active", "Very active (hard training or physical job)"]];
  const GOALS = [["cut", "Lose fat (about 18% deficit)"], ["lean_cut", "Lose slowly (10% deficit)"], ["maintain", "Maintain"], ["lean_bulk", "Lean gain (8% surplus)"], ["bulk", "Gain (15% surplus)"]];
  const MAC = [["protein_g", "Protein", "var(--p)"], ["carb_g", "Carbs", "var(--c)"], ["fat_g", "Fat", "var(--f)"], ["fibre_g", "Fibre", "var(--fb)"]];

  async function api(path, opts = {}) {
    const o = { credentials: "include", headers: {}, ...opts };
    if (o.body !== undefined && typeof o.body !== "string") { o.body = JSON.stringify(o.body); o.headers["Content-Type"] = "application/json"; }
    let r;
    try { r = await fetch("/api/fit" + path, o); } catch (e) { throw new Error("You're offline. Check your connection and try again."); }
    let d = null;
    try { d = await r.json(); } catch (e) {}
    if (r.status === 401 && !PUBLIC) { location.href = "/login?next=/fitnesstracker"; throw new Error("Sign in to continue"); }
    if (!r.ok) {
      const det = d && (d.detail || d.error);
      throw new Error((det && (det.message || (typeof det === "string" ? det : ""))) || `Something went wrong (${r.status})`);
    }
    return d;
  }
  const post = (p, b = {}) => api(p, { method: "POST", body: b });
  const patch = (p, b = {}) => api(p, { method: "PATCH", body: b });
  const put = (p, b = {}) => api(p, { method: "PUT", body: b });
  const del = (p) => api(p, { method: "DELETE" });

  let toastT;
  function toast(msg, ms = 2600) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), ms);
  }
  const fail = (e) => toast(e && e.message ? e.message : String(e));
  const buzz = (p = 12) => { try { navigator.vibrate && navigator.vibrate(p); } catch (e) {} };

  document.addEventListener("pointerdown", (e) => {
    const b = e.target.closest(".btn"); if (!b) return;
    const r = b.getBoundingClientRect(), s = document.createElement("span"), d = Math.max(r.width, r.height);
    s.className = "ripple"; s.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`;
    b.appendChild(s); setTimeout(() => s.remove(), 600);
  });

  // ------------------------------------------------------------------ overlays (sheets & pages) with Android back support
  // One history entry stands for "an overlay is open", so the phone's back button closes the top sheet or page.
  // Closing in code never navigates straight away (a new overlay often opens in the same tick); the entry is dropped
  // a moment later only if nothing is open any more.
  const stack = [];
  let armed = false, ignorePops = 0, disarmT = null;
  const arm = () => { clearTimeout(disarmT); if (!armed) { armed = true; try { history.pushState({ fit: 1 }, ""); } catch (e) {} } };
  const maybeDisarm = () => {
    clearTimeout(disarmT);
    disarmT = setTimeout(() => { if (!stack.length && armed) { armed = false; ignorePops++; try { history.back(); } catch (e) { ignorePops--; } } }, 350);
  };
  window.addEventListener("popstate", () => {
    if (ignorePops > 0) { ignorePops--; return; }
    armed = false;
    const e = stack.pop(); if (e) e.real();
    if (stack.length) arm();
  });
  function overlay(real) {
    const entry = { real };
    stack.push(entry); arm();
    return () => {
      const i = stack.indexOf(entry); if (i < 0) return;
      stack.splice(i, 1); entry.real();
      if (!stack.length) maybeDisarm();
    };
  }
  function sheet(html, { onClose } = {}) {
    const scrim = document.createElement("div"); scrim.className = "scrim";
    const el = document.createElement("div"); el.className = "sheet"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true");
    const z = 30 + stack.length * 10; scrim.style.zIndex = z + 5; el.style.zIndex = z + 6;
    el.innerHTML = `<div class="grip"></div>${html}`;
    document.body.append(scrim, el);
    const close = overlay(() => {
      scrim.classList.add("leaving"); el.classList.add("leaving");
      setTimeout(() => { scrim.remove(); el.remove(); }, 230);
      onClose && onClose();
    });
    scrim.addEventListener("click", close);
    el.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) close(); });
    let y0 = null, dy = 0;
    el.addEventListener("touchstart", (e) => { if (el.scrollTop <= 0 && e.target.closest(".grip, .sh-h")) { y0 = e.touches[0].clientY; dy = 0; el.style.transition = "none"; } }, { passive: true });
    el.addEventListener("touchmove", (e) => { if (y0 == null) return; dy = Math.max(0, e.touches[0].clientY - y0); el.style.transform = `translateY(${dy}px)`; }, { passive: true });
    el.addEventListener("touchend", () => { if (y0 == null) return; y0 = null; el.style.transition = ""; el.style.transform = ""; if (dy > 90) close(); });
    return { el, close };
  }
  function page(head, body, { onClose, cls = "" } = {}) {
    const el = document.createElement("div"); el.className = "page " + cls; el.style.zIndex = 30 + stack.length * 10;
    el.innerHTML = `<div class="page-head"><button type="button" class="icon-btn" data-back aria-label="Back">${ic("left")}</button>${head}</div><div class="scroll">${body}</div>`;
    document.body.append(el);
    const close = overlay(() => { el.classList.add("leaving"); setTimeout(() => el.remove(), 220); onClose && onClose(); });
    el.querySelector("[data-back]").addEventListener("click", close);
    return { el, close, body: el.querySelector(".scroll") };
  }
  function confirmSheet(title, text, okLabel = "Delete", danger = true) {
    return new Promise((res) => {
      let done = false;
      const s = sheet(`<div class="sh-h"><h2>${esc(title)}</h2>${text ? `<p>${esc(text)}</p>` : ""}</div>
        <div class="sh-f"><button type="button" class="btn block ${danger ? "danger" : "primary"}" data-ok>${esc(okLabel)}</button><button type="button" class="btn block" data-close>Cancel</button></div>`,
      { onClose: () => { if (!done) res(false); } });
      s.el.querySelector("[data-ok]").onclick = () => { done = true; res(true); s.close(); };
    });
  }
  function promptSheet(title, fields, okLabel = "Save") {
    return new Promise((res) => {
      let done = false;
      const s = sheet(`<div class="sh-h"><h2>${esc(title)}</h2></div><div class="form">${fields.map((f) => `<label class="field ${f.full === false ? "" : "full"}">${esc(f.label)}
        <input name="${f.name}" type="${f.type || "text"}" value="${esc(f.value ?? "")}" placeholder="${esc(f.placeholder || "")}" ${f.attrs || ""}></label>`).join("")}</div>
        <div class="sh-f"><button type="button" class="btn primary block" data-ok>${esc(okLabel)}</button></div>`, { onClose: () => { if (!done) res(null); } });
      const ok = () => { done = true; const out = {}; $$("input", s.el).forEach((i) => (out[i.name] = i.value.trim())); res(out); s.close(); };
      s.el.querySelector("[data-ok]").onclick = ok;
      s.el.addEventListener("keydown", (e) => { if (e.key === "Enter") ok(); });
      setTimeout(() => { const i = $("input", s.el); i && i.focus(); }, 350);
    });
  }

  // ------------------------------------------------------------------ shared model helpers
  const slotName = (id) => (S.slots.find((s) => s.id === id) || {}).name || "Other";
  function slotNow() {
    const m = toMin(IST_HM.format(new Date()));
    let best = null, bd = 1e9;
    for (const s of S.slots) { if (!s.time_hhmm) continue; const d = Math.abs(toMin(s.time_hhmm) - m); if (d < bd) { bd = d; best = s; } }
    return best ? best.id : (S.slots[0] || {}).id ?? null;
  }
  const slotOptions = (sel) => S.slots.map((s) => `<option value="${s.id}" ${s.id === sel ? "selected" : ""}>${esc(s.name)}${s.time_hhmm ? " · " + s.time_hhmm : ""}</option>`).join("");
  function unitText(qty, unit, label) {
    const q = num(qty, 2);
    if (unit === "g") return `${q} g`;
    if (unit === "ml") return `${q} ml`;
    const l = String(label || unit).replace(/^1 /, "");
    return `${q} × ${l}`;
  }
  const scaleN = (per100, g) => { const o = {}; for (const k in per100 || {}) if (per100[k] != null) o[k] = (per100[k] * g) / 100; return o; };
  const unitG = (units, u) => ((units || []).find((x) => x.u === u) || { g: 1 }).g;
  const pcf = (n) => `<span class="pcf"><i class="p">P</i> ${num(n.protein_g, 1)} · <i class="c">C</i> ${num(n.carb_g, 1)} · <i class="f">F</i> ${num(n.fat_g, 1)}</span>`;
  const srcLabel = { indb: "INDB", "indb-uk": "UK", "indb-us": "US", usda: "USDA", off: "OFF", user: "Mine" };
  const exThumb = (e) => (e.image ? `<img class="thumb" src="${esc(e.image)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'thumb',textContent:'🏋'}))">` : `<span class="thumb">${e.kind === "cardio" ? "🏃" : "🏋"}</span>`);
  const exMeta = (e) => [e.part, e.equipment ? (e.equipment === "body only" ? "Bodyweight" : e.equipment) : null].filter(Boolean).join(" · ");
  function setSummary(sets) {
    const done = (sets || []).filter((s) => s.done !== 0);
    const list = done.length ? done : sets || [];
    if (!list.length) return "No sets";
    if (list.some((s) => s.minutes)) return list.map((s) => `${num(s.minutes, 1)} min${s.distance_km ? " · " + num(s.distance_km, 2) + " km" : ""}`).join(", ");
    const same = list.every((s) => s.reps === list[0].reps && s.weight_kg === list[0].weight_kg);
    if (same) return `${list.length} × ${num(list[0].reps)}${list[0].weight_kg ? " @ " + num(list[0].weight_kg, 1) + " kg" : ""}`;
    return list.map((s) => `${num(s.reps)}${s.weight_kg ? "×" + num(s.weight_kg, 1) : ""}`).join(", ");
  }
  function mdLite(t) {
    const lines = String(t || "").split(/\n+/);
    let out = "", inList = false;
    const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    for (const raw of lines) {
      const l = raw.trim(); if (!l) continue;
      const m = l.match(/^[-*•]\s+(.*)/);
      if (m) { if (!inList) { out += "<ul>"; inList = true; } out += `<li>${inline(m[1])}</li>`; continue; }
      if (inList) { out += "</ul>"; inList = false; }
      out += `<p>${inline(l.replace(/^#+\s*/, ""))}</p>`;
    }
    return out + (inList ? "</ul>" : "");
  }

  async function loadDay(day = S.day) {
    const d = await api("/day/" + day);
    if (day === S.day) { S.dayData = d; S.nutrients = d.nutrients || S.nutrients; }
    return d;
  }
  function setDay(d) {
    if (!d) return;
    if (d.day === S.day) { S.dayData = d; S.nutrients = d.nutrients || S.nutrients; }
    if (S.tab === "today") paintToday(); else if (S.tab === "diet") paintDiet();
  }
  function datebar(id) {
    return `<div class="datebar" id="${id}"><button type="button" data-d="-1" aria-label="Previous day">${ic("left")}</button><b>${esc(dayLabel(S.day))}</b><button type="button" data-d="1" aria-label="Next day">${ic("right")}</button></div>`;
  }
  function bindDatebar(root, rerender) {
    root.querySelectorAll(".datebar [data-d]").forEach((b) => b.addEventListener("click", () => {
      const n = addDays(S.day, Number(b.dataset.d));
      if (n > addDays(today(), 1)) return;
      S.day = n; S.dayData = null; rerender();
    }));
  }

  // ------------------------------------------------------------------ tabs
  const RENDER = {};
  function setTab(t) {
    S.tab = t; store.set("fit_tab", t);
    $$(".screen").forEach((s) => (s.hidden = s.dataset.tab !== t));
    const btns = $$("#tabbar button");
    btns.forEach((b, i) => { if (b.dataset.tab === t) { b.setAttribute("aria-current", "page"); $("#tabInk").style.transform = `translateX(${i * 100}%)`; } else b.removeAttribute("aria-current"); });
    RENDER[t] && RENDER[t]();
  }
  $$("#tabbar button").forEach((b) => b.addEventListener("click", () => { buzz(6); setTab(b.dataset.tab); }));

  // ------------------------------------------------------------------ TODAY
  RENDER.today = () => {
    const el = $("#scr-today");
    const hr = Number(IST_HM.format(new Date()).slice(0, 2));
    const first = ((S.me && S.me.user && S.me.user.name) || "").split(" ")[0];
    const hello = (hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening") + (first ? `, ${first}` : "");
    el.innerHTML = `<header class="head"><h1>${esc(hello)}</h1>${datebar("tdDate")}</header><div class="scroll" id="tdBody"><div class="card card-b"><span class="skel"></span><span class="skel" style="width:60%"></span><span class="skel"></span></div></div>`;
    bindDatebar(el, RENDER.today);
    if (S.dayData && S.dayData.day === S.day) paintToday();
    loadDay().then(paintToday).catch(fail);
  };

  function paintToday() {
    const body = $("#tdBody"); const d = S.dayData;
    if (!body || !d || d.day !== S.day) return;
    const keepText = ($("#aiText") || {}).value || store.get("fit_ai_draft", "");
    const t = d.targets || {}, tot = d.totals || {};
    const eaten = tot.kcal || 0, burnt = d.burnt || 0, goal = t.kcal || 0;
    const left = goal ? goal - eaten + burnt : null;
    const pct = goal ? (eaten / (goal + burnt)) * 100 : 0;
    const wTarget = t.water_ml || 3000, glasses = clamp(Math.round(wTarget / 250), 6, 16), filled = Math.floor((d.water_ml || 0) / 250);
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    body.innerHTML = `
      ${S.activeId ? `<div class="wk-banner" id="tdResume">${ic("timer")}<div class="grow"><b>Workout in progress</b><span>Tap to continue logging sets</span></div>${ic("right")}</div>` : ""}
      <div class="card">
        <div class="energy">
          <div class="ring ${left != null && left < 0 ? "over" : ""}" style="--p:${pct.toFixed(1)}"><div><b>${goal ? num(Math.abs(left)) : num(eaten)}</b><small>${goal ? (left < 0 ? "kcal over" : "kcal left") : "kcal eaten"}</small></div></div>
          <div class="estats">
            <div class="estat"><span>${ic("food").replace("<svg", '<svg style="width:13px;height:13px;vertical-align:-2px"')} Eaten</span><b>${num(eaten)}</b></div>
            <div class="estat"><span>${ic("flame").replace("<svg", '<svg style="width:13px;height:13px;vertical-align:-2px"')} Burnt in workouts</span><b>${num(burnt)}</b></div>
            <div class="estat"><span>Daily target</span><b>${goal ? num(goal) : `<button type="button" class="pill acc" id="tdSetup">Set up targets</button>`}</b></div>
          </div>
        </div>
        <div class="macros">${MAC.map(([k, l, c]) => { const v = tot[k] || 0, g = t[k]; return `<div class="mac"><span>${l}</span><b>${num(v)}${g ? `<small> / ${num(g)} g</small>` : "<small> g</small>"}</b><div class="bar"><i style="background:${c};width:${g ? clamp((v / g) * 100, 0, 100) : 0}%"></i></div></div>`; }).join("")}</div>
      </div>

      <div class="card">
        <div class="card-h"><h3>${ic("sparkle").replace("<svg", '<svg style="width:17px;height:17px;vertical-align:-3px;color:var(--accent)"')} Log my day</h3><span class="pill">Gemini</span></div>
        <div class="ai-box">
          <textarea id="aiText" placeholder="e.g. 2 roti, dal and bhindi for lunch, black coffee at 5, chest day: bench 4x8 at 60, pec deck 3x12, 20 min treadmill. Drank 2 litres water."></textarea>
          <div class="ai-actions">
            <button type="button" class="icon-btn mic" id="aiMic" aria-label="Dictate" ${SR ? "" : "hidden"}>${ic("mic")}</button>
            <button type="button" class="icon-btn" id="aiPhoto" aria-label="Snap your plate">${ic("camera")}</button>
            <button type="button" class="btn primary" id="aiGo">${ic("sparkle")}Log it</button>
          </div>
          <p class="small muted" style="margin:8px 2px 0">You'll review everything before it's saved.${SR ? "" : " Tip: use your keyboard's mic key to dictate."}</p>
        </div>
      </div>

      <div class="card">
        <div class="card-h"><h3>Water</h3><span class="muted small"><b style="color:var(--ink)">${num((d.water_ml || 0) / 1000, 2)}</b> / ${num(wTarget / 1000, 2)} L</span></div>
        <div class="water">
          <div class="glasses" id="tdGlasses" style="--n:${glasses}">${Array.from({ length: glasses }, (_, i) => `<button type="button" class="glass ${i < filled ? "on" : ""}" data-i="${i}" aria-label="${(i + 1) * 250} ml"></button>`).join("")}</div>
          <button type="button" class="icon-btn" data-wa="-250" aria-label="Remove a glass">−</button><button type="button" class="icon-btn" data-wa="250" aria-label="Add a glass" style="color:var(--fb)">${ic("plus")}</button>
        </div>
      </div>

      <div class="card">
        <div class="card-h"><h3>Meals</h3><button type="button" class="pill acc" id="tdDiet">Open diary</button></div>
        <ul class="list">${(d.meals || []).filter((m) => m.items.length || m.id != null).map((m) => `<li class="li" data-slot="${m.id ?? ""}"><div class="t"><b>${esc(m.name)}</b><span>${m.items.length ? esc(m.items.map((x) => x.name).join(", ")) : "Nothing logged"}</span></div><div class="r">${m.items.length ? num(m.totals.kcal) : `<span class="pill">${ic("plus").replace("<svg", '<svg style="width:12px;height:12px"')} Add</span>`}${m.items.length ? "<small>kcal</small>" : ""}</div></li>`).join("")}</ul>
      </div>

      <div class="card">
        <div class="card-h"><h3>Workouts</h3><button type="button" class="pill acc" id="tdStart">${S.activeId ? "Resume" : "Start workout"}</button></div>
        ${(d.workouts || []).length ? `<ul class="list">${d.workouts.map((w) => `<li class="li" data-w="${w.id}"><span class="thumb">🏋</span><div class="t"><b>${esc(w.name || "Workout")}</b><span>${w.ended_at ? "Done" : w.started_at ? "In progress" : "Logged"}</span></div><div class="r">${num(w.kcal)}<small>kcal</small></div></li>`).join("")}</ul>` : `<div class="empty" style="padding:6px 16px 18px">No workout logged ${S.day === today() ? "today" : "this day"}.</div>`}
      </div>

      <div class="card">
        <div class="card-h"><h3>Body weight</h3><button type="button" class="pill acc" id="tdWeight">${d.weight_kg ? "Update" : "Log weight"}</button></div>
        <div class="card-b"><span style="font:800 24px var(--f-display)">${d.weight_kg ? num(d.weight_kg, 1) + " kg" : "–"}</span> <span class="muted small">${d.weight_kg ? "logged " + dayLabel(S.day).toLowerCase() : S.profile.weight_kg ? "last: " + num(S.profile.weight_kg, 1) + " kg" : ""}</span></div>
      </div>`;
    const ta = $("#aiText", body); ta.value = keepText;
    ta.addEventListener("input", debounce(() => store.set("fit_ai_draft", ta.value), 300));
    bindMic($("#aiMic", body), ta);
    $("#aiGo", body).onclick = () => aiParse(ta);
    $("#aiPhoto", body).onclick = () => photoLog(null);
    $("#tdSetup", body) && ($("#tdSetup", body).onclick = () => onboarding(true));
    $("#tdResume", body) && ($("#tdResume", body).onclick = () => openWorkout(S.activeId));
    $("#tdStart", body).onclick = () => (S.activeId ? openWorkout(S.activeId) : startWorkout());
    $("#tdDiet", body).onclick = () => setTab("diet");
    $("#tdWeight", body).onclick = logWeight;
    $$(".li[data-slot]", body).forEach((li) => li.addEventListener("click", () => { const sid = li.dataset.slot ? Number(li.dataset.slot) : null; const m = d.meals.find((x) => x.id === sid); if (m && m.items.length) setTab("diet"); else openFoodSearch({ slotId: sid }); }));
    $$(".li[data-w]", body).forEach((li) => li.addEventListener("click", () => openWorkout(Number(li.dataset.w))));
    $$("#tdGlasses .glass", body).forEach((g) => g.addEventListener("click", () => setWater((Number(g.dataset.i) + 1) * 250 === Math.floor((d.water_ml || 0) / 250) * 250 ? Number(g.dataset.i) * 250 : (Number(g.dataset.i) + 1) * 250)));
    $$("[data-wa]", body).forEach((b) => b.addEventListener("click", () => addWater(Number(b.dataset.wa))));
  }
  async function setWater(ml) { buzz(); try { const r = await post("/water", { day: S.day, set_ml: ml }); S.dayData.water_ml = r.water_ml; paintToday(); } catch (e) { fail(e); } }
  async function addWater(ml) { buzz(); try { const r = await post("/water", { day: S.day, add_ml: ml }); S.dayData.water_ml = r.water_ml; paintToday(); } catch (e) { fail(e); } }
  async function logWeight() {
    const v = await promptSheet("Body weight", [{ name: "w", label: "Weight (kg)", type: "number", value: (S.dayData && S.dayData.weight_kg) || S.profile.weight_kg || "", attrs: 'inputmode="decimal" step="0.1"' }]);
    if (!v || !v.w) return;
    try { const r = await post("/body", { day: S.day, weight_kg: Number(v.w) }); S.profile = r.profile; toast("Weight saved"); setDay(await loadDay()); } catch (e) { fail(e); }
  }

  // voice dictation
  function bindMic(btn, ta) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!btn || !SR) return;
    let rec = null;
    btn.onclick = () => {
      if (rec) { rec.stop(); return; }
      try { rec = new SR(); } catch (e) { toast("Voice input isn't available in this browser"); return; }
      rec.lang = "en-IN"; rec.continuous = true; rec.interimResults = true;
      const base = ta.value.trim() ? ta.value.trim() + " " : "";
      let fin = "";
      rec.onresult = (e) => {
        let interim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) { const r = e.results[i]; if (r.isFinal) fin += r[0].transcript.trim() + " "; else interim += r[0].transcript; }
        ta.value = base + fin + interim; ta.dispatchEvent(new Event("input"));
      };
      rec.onerror = (e) => toast(e.error === "not-allowed" || e.error === "service-not-allowed" ? "Allow microphone access to dictate" : "Voice input stopped");
      rec.onend = () => { rec = null; btn.classList.remove("on"); };
      try { rec.start(); btn.classList.add("on"); buzz(); toast("Listening… tap the mic again to stop", 1800); } catch (e) { rec = null; }
    };
  }

  // ------------------------------------------------------------------ Gemini: parse, photo, review draft
  async function aiParse(ta) {
    const text = ta.value.trim();
    if (text.length < 3) { toast("Describe what you ate or did today"); ta.focus(); return; }
    const btn = $("#aiGo"); btn.disabled = true; btn.innerHTML = `${ic("sparkle")}Reading…`;
    try {
      const r = await post("/ai/parse", { text, day: S.day });
      if (r.slots) S.slots = r.slots;
      reviewDraft(r.draft, () => { ta.value = ""; store.set("fit_ai_draft", ""); });
    } catch (e) { fail(e); }
    finally { btn.disabled = false; btn.innerHTML = `${ic("sparkle")}Log it`; }
  }
  function pickPhoto() {
    return new Promise((res) => {
      const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*"; inp.setAttribute("capture", "environment");
      inp.onchange = () => res(inp.files && inp.files[0] ? inp.files[0] : null); inp.click();
    });
  }
  async function downscale(file, max = 1280) {
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      await new Promise((ok, no) => { img.onload = ok; img.onerror = no; img.src = url; });
      const k = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
      const c = document.createElement("canvas"); c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      return c.toDataURL("image/jpeg", 0.85);
    } finally { URL.revokeObjectURL(url); }
  }
  async function photoLog(slotId) {
    const f = await pickPhoto(); if (!f) return;
    toast("Looking at your plate…", 6000);
    try {
      const image = await downscale(f);
      const r = await post("/ai/photo", { image, day: S.day, slot_id: slotId ?? slotNow() });
      if (r.slots) S.slots = r.slots;
      if (!r.draft.foods.length) { toast("Couldn't spot any food in that photo. Try a clearer, top-down shot."); return; }
      reviewDraft(r.draft);
    } catch (e) { fail(e); }
  }

  function reviewDraft(draft, onSaved) {
    const st = {
      foods: (draft.foods || []).map((f) => {
        const m = f.match;
        return { query: f.query, keep: !!m, food_id: m && m.food_id, name: m && m.name, source: m && m.source, units: (m && m.units) || [], qty: f.qty, unit: f.unit,
          kpg: m && m.grams ? (m.n.kcal || 0) / m.grams : 0, ppg: m && m.grams ? (m.n.protein_g || 0) / m.grams : 0,
          slot: f.slot_id != null ? String(f.slot_id) : f.meal_hint ? "new:" + f.meal_hint : String(slotNow() ?? ""), hint: f.meal_hint, alts: f.alternatives || [] };
      }),
      exs: (draft.exercises || []).map((e) => ({ query: e.query, keep: !!e.match, ex: e.match, sets: e.sets || [], alts: e.alternatives || [] })),
      water: draft.water_ml, weight: draft.weight_kg, keepWater: !!draft.water_ml, keepWeight: !!draft.weight_kg,
    };
    const s = sheet(`<div class="sh-h"><h2>Review before saving</h2><p>${esc(dayLabel(draft.day))}. Untick anything that's wrong, or tap a suggestion to swap the match.</p></div><div class="sh-b" id="drBody"></div>
      <div class="sh-f"><button type="button" class="btn primary block" id="drSave">${ic("check")}Save to my day</button><button type="button" class="btn block" data-close>Cancel</button></div>`);
    const body = $("#drBody", s.el);
    const slotSel = (f, i) => {
      let o = slotOptions(Number(f.slot));
      if (f.hint && !S.slots.some((x) => x.name.toLowerCase() === String(f.hint).toLowerCase())) o += `<option value="new:${esc(f.hint)}" ${f.slot.startsWith("new:") ? "selected" : ""}>New meal: ${esc(f.hint)}</option>`;
      return `<select data-f="${i}" data-k="slot">${o}</select>`;
    };
    const paint = () => {
      let kcal = 0;
      const foods = st.foods.map((f, i) => {
        const g = f.qty * unitG(f.units, f.unit), k = f.kpg * g; if (f.keep) kcal += k;
        return `<div class="dr ${f.keep ? "" : "off"}"><div class="dr-top"><input type="checkbox" data-f="${i}" data-k="keep" ${f.keep ? "checked" : ""} ${f.food_id ? "" : "disabled"} aria-label="Keep">
          <div class="t"><b>${esc(f.name || f.query)}</b><span>${f.food_id ? `${f.source ? `<span class="src">${esc(srcLabel[f.source] || f.source)}</span> ` : ""}${num(g)} g · <strong style="color:var(--ink)">${num(k)} kcal</strong> · ${num(f.ppg * g, 1)} g protein` : `<span class="warn">No match for "${esc(f.query)}"</span>`}</span></div>
          <button type="button" class="icon-btn" data-f="${i}" data-act="pick" aria-label="Choose a different food">${ic("search")}</button></div>
          ${f.food_id ? `<div class="dr-ctl"><input type="number" inputmode="decimal" step="0.5" min="0" value="${f.qty}" data-f="${i}" data-k="qty" aria-label="Quantity">
            <select data-f="${i}" data-k="unit">${f.units.map((u) => `<option value="${esc(u.u)}" ${u.u === f.unit ? "selected" : ""}>${esc(u.label)}${u.u !== "g" && u.u !== "ml" ? ` (${num(u.g)} g)` : ""}</option>`).join("")}</select>${slotSel(f, i)}</div>` : ""}
          ${f.alts.length ? `<div class="alt">${f.alts.map((a, j) => `<button type="button" data-f="${i}" data-alt="${j}">${esc(a.name)}</button>`).join("")}</div>` : ""}</div>`;
      }).join("");
      const exs = st.exs.map((e, i) => `<div class="dr ${e.keep ? "" : "off"}"><div class="dr-top"><input type="checkbox" data-e="${i}" data-k="keep" ${e.keep ? "checked" : ""} ${e.ex ? "" : "disabled"} aria-label="Keep">
          <div class="t"><b>${esc(e.ex ? e.ex.name : e.query)}</b><span>${e.ex ? esc(setSummary(e.sets)) + " · " + esc(e.ex.part || "") : `<span class="warn">No match for "${esc(e.query)}"</span>`}</span></div>
          <button type="button" class="icon-btn" data-e="${i}" data-act="pick" aria-label="Choose a different exercise">${ic("search")}</button></div>
          ${e.alts.length ? `<div class="alt">${e.alts.map((a, j) => `<button type="button" data-e="${i}" data-alt="${j}">${esc(a.name)}</button>`).join("")}</div>` : ""}</div>`).join("");
      body.innerHTML = `${st.foods.length ? `<div class="row" style="justify-content:space-between;margin:4px 0"><b style="font:700 15px var(--f-display)">Food</b><span class="pill acc">${num(kcal)} kcal</span></div>${foods}` : ""}
        ${st.exs.length ? `<div style="margin:14px 0 4px"><b style="font:700 15px var(--f-display)">Workout</b> <span class="small muted">saved as one workout, sets marked done</span></div>${exs}` : ""}
        ${st.water ? `<div class="dr"><div class="dr-top"><input type="checkbox" id="drWater" ${st.keepWater ? "checked" : ""}><div class="t"><b>Water</b><span>+${num(st.water)} ml</span></div></div></div>` : ""}
        ${st.weight ? `<div class="dr"><div class="dr-top"><input type="checkbox" id="drWeight" ${st.keepWeight ? "checked" : ""}><div class="t"><b>Body weight</b><span>${num(st.weight, 1)} kg</span></div></div></div>` : ""}
        ${!st.foods.length && !st.exs.length && !st.water && !st.weight ? `<div class="empty"><b>Nothing to log</b>Try naming foods with amounts, or exercises with sets and reps.</div>` : ""}
        ${draft.notes ? `<p class="small muted">Note: ${esc(draft.notes)}</p>` : ""}`;
    };
    paint();
    body.addEventListener("change", (e) => {
      const t = e.target;
      if (t.id === "drWater") { st.keepWater = t.checked; return; }
      if (t.id === "drWeight") { st.keepWeight = t.checked; return; }
      if (t.dataset.f != null) { const f = st.foods[t.dataset.f]; if (t.dataset.k === "keep") f.keep = t.checked; else if (t.dataset.k === "qty") f.qty = Math.max(0, Number(t.value) || 0); else if (t.dataset.k === "unit") f.unit = t.value; else if (t.dataset.k === "slot") f.slot = t.value; paint(); }
      if (t.dataset.e != null && t.dataset.k === "keep") { st.exs[t.dataset.e].keep = t.checked; paint(); }
    });
    const useFood = (f, food) => {
      Object.assign(f, { food_id: food.id, name: food.name, source: food.source, units: food.units, keep: true, kpg: (food.per100.kcal || 0) / 100, ppg: (food.per100.protein_g || 0) / 100 });
      if (!food.units.some((u) => u.u === f.unit)) { f.unit = food.serving_g ? "serving" : "g"; if (f.unit === "g" && f.qty < 10) f.qty = 100; }
      paint();
    };
    body.addEventListener("click", async (e) => {
      const b = e.target.closest("button"); if (!b) return;
      if (b.dataset.f != null) {
        const f = st.foods[b.dataset.f];
        if (b.dataset.act === "pick") { openFoodSearch({ pick: (food) => useFood(f, food), query: f.query }); return; }
        if (b.dataset.alt != null) { const a = f.alts[b.dataset.alt]; try { const r = await api("/foods/" + encodeURIComponent(a.food_id)); f.alts[b.dataset.alt] = { food_id: f.food_id, name: f.name, source: f.source }; useFood(f, r.food); } catch (er) { fail(er); } }
      }
      if (b.dataset.e != null) {
        const x = st.exs[b.dataset.e];
        if (b.dataset.act === "pick") { pickExercise((ex) => { x.ex = ex; x.keep = true; paint(); }); return; }
        if (b.dataset.alt != null) { const a = x.alts[b.dataset.alt]; if (x.ex) x.alts[b.dataset.alt] = x.ex; x.ex = a; x.keep = true; paint(); }
      }
    });
    $("#drSave", s.el).onclick = async () => {
      const btn = $("#drSave", s.el); btn.disabled = true;
      const out = {
        day: draft.day,
        foods: st.foods.map((f) => ({ food_id: f.food_id, qty: f.qty, unit: f.unit, skip: !f.keep || !f.food_id, slot_id: f.slot.startsWith("new:") ? null : Number(f.slot) || null, new_slot: f.slot.startsWith("new:") ? f.slot.slice(4) : null })),
        exercises: st.exs.map((x) => ({ exercise_id: x.ex && x.ex.id, sets: x.sets, skip: !x.keep || !x.ex })),
        water_ml: st.keepWater ? st.water : null, weight_kg: st.keepWeight ? st.weight : null,
      };
      try {
        const r = await post("/ai/commit", { draft: out });
        const bits = []; if (r.saved.foods) bits.push(`${r.saved.foods} food${r.saved.foods > 1 ? "s" : ""}`); if (r.saved.exercises) bits.push(`${r.saved.exercises} exercise${r.saved.exercises > 1 ? "s" : ""}`);
        toast(bits.length ? `Saved ${bits.join(" and ")}` : "Saved");
        s.close(); onSaved && onSaved();
        const me = await api("/me"); S.slots = me.slots; S.profile = me.profile;
        setDay(r.day);
      } catch (e) { fail(e); btn.disabled = false; }
    };
  }

  // ------------------------------------------------------------------ DIET
  RENDER.diet = () => {
    const el = $("#scr-diet");
    el.innerHTML = `<header class="head"><h1>Diet</h1>${datebar("dtDate")}</header>
      <div class="chips" id="dtActions">
        <button type="button" class="chip" data-a="copy">${"Copy yesterday"}</button><button type="button" class="chip" data-a="meals">Saved meals</button>
        <button type="button" class="chip" data-a="photo">Snap plate</button><button type="button" class="chip" data-a="barcode">Scan barcode</button>
        <button type="button" class="chip" data-a="custom">Custom food</button><button type="button" class="chip" data-a="nutr">All nutrients</button></div>
      <div class="scroll" id="dtBody"><div class="card card-b"><span class="skel"></span><span class="skel"></span></div></div>`;
    bindDatebar(el, RENDER.diet);
    $("#dtActions", el).addEventListener("click", (e) => {
      const a = (e.target.closest("[data-a]") || {}).dataset; if (!a || !a.a) return;
      ({ copy: copyDay, meals: () => savedMeals(null), photo: () => photoLog(null), barcode: () => barcodeSheet(null), custom: () => customFood(null), nutr: nutrientsSheet })[a.a]();
    });
    if (S.dayData && S.dayData.day === S.day) paintDiet();
    loadDay().then(paintDiet).catch(fail);
  };
  function paintDiet() {
    const body = $("#dtBody"); const d = S.dayData;
    if (!body || !d || d.day !== S.day) return;
    const t = d.targets || {}, tot = d.totals || {};
    body.innerHTML = `<div class="card"><div class="mbig">
        <div><b>${num(tot.kcal)}</b><span>kcal${t.kcal ? "<br>of " + num(t.kcal) : ""}</span></div>
        ${MAC.slice(0, 3).map(([k, l, c]) => `<div><b style="color:${c}">${num(tot[k])}</b><span>${l}${t[k] ? "<br>of " + num(t[k]) + " g" : " g"}</span></div>`).join("")}</div></div>
      ${(d.meals || []).map((m) => `<div class="card" data-slot="${m.id ?? ""}">
        <div class="meal-h"><h3>${esc(m.name)}</h3>${m.time_hhmm ? `<span class="tm">${esc(m.time_hhmm)}</span>` : ""}<span class="kc">${m.items.length ? num(m.totals.kcal) + " kcal" : ""}</span>
          ${m.id != null ? `<button type="button" class="icon-btn" data-menu aria-label="Meal options" style="width:34px;height:34px">${ic("more")}</button>` : ""}</div>
        ${m.items.length ? `<ul class="list">${m.items.map((x) => `<li class="li" data-log="${x.id}"><div class="t"><b>${esc(x.name)}</b><span>${esc(unitText(x.qty, x.unit, x.unit_label))} · ${num(x.grams)} g${x.via === "ai" ? " · AI" : ""}</span>${pcf(x.n)}</div><div class="r">${num(x.n.kcal)}<small>kcal</small></div></li>`).join("")}</ul>` : ""}
        ${m.id != null ? `<div class="meal-f"><button type="button" class="btn sm" data-add>${ic("plus")}Add food</button></div>` : ""}
      </div>`).join("")}
      <div style="padding:6px 14px"><button type="button" class="btn block" id="dtSlot">${ic("plus")}Add a meal time (e.g. evening snack)</button></div>
      <p class="small muted" style="padding:4px 18px 0">Nutrition from the Indian Nutrient Databank (INDB), USDA FoodData Central and Open Food Facts. Values are estimates.</p>`;
    $$("[data-slot]", body).forEach((card) => {
      const sid = card.dataset.slot ? Number(card.dataset.slot) : null;
      const add = $("[data-add]", card); add && (add.onclick = () => openFoodSearch({ slotId: sid }));
      const mn = $("[data-menu]", card); mn && (mn.onclick = () => mealMenu(sid));
      $$("[data-log]", card).forEach((li) => li.addEventListener("click", () => editLog(Number(li.dataset.log))));
    });
    $("#dtSlot", body).onclick = addSlot;
  }
  async function addSlot() {
    const v = await promptSheet("New meal time", [{ name: "name", label: "Name", placeholder: "Evening snack" }, { name: "time", label: "Time (optional)", type: "time", value: "17:30" }], "Add");
    if (!v || !v.name) return;
    try { const r = await post("/slots", { name: v.name, time: v.time }); S.slots = r.slots; setDay(await loadDay()); toast(`Added ${v.name}`); } catch (e) { fail(e); }
  }
  function mealMenu(sid) {
    const m = (S.dayData.meals || []).find((x) => x.id === sid) || { items: [] };
    const s = sheet(`<div class="sh-h"><h2>${esc(slotName(sid))}</h2><p>${m.items.length ? num(m.totals.kcal) + " kcal · " + m.items.length + " item" + (m.items.length > 1 ? "s" : "") : "Empty"}</p></div>
      <ul class="list">
        <li class="li" data-a="add"><span class="thumb">${ic("search")}</span><div class="t"><b>Search and add food</b></div></li>
        <li class="li" data-a="photo"><span class="thumb">${ic("camera")}</span><div class="t"><b>Snap this meal</b><span>Gemini identifies the foods, you confirm</span></div></li>
        <li class="li" data-a="copy"><span class="thumb">${ic("copy")}</span><div class="t"><b>Copy from yesterday</b><span>Only this meal</span></div></li>
        <li class="li" data-a="meals"><span class="thumb">${ic("star")}</span><div class="t"><b>Add a saved meal</b></div></li>
        ${m.items.length ? `<li class="li" data-a="save"><span class="thumb">${ic("plus")}</span><div class="t"><b>Save as a meal</b><span>Reuse it in one tap later</span></div></li>` : ""}
        <li class="li" data-a="barcode"><span class="thumb">${ic("barcode")}</span><div class="t"><b>Scan a barcode</b></div></li>
      </ul>`);
    s.el.addEventListener("click", async (e) => {
      const li = e.target.closest("[data-a]"); if (!li) return;
      const a = li.dataset.a; s.close();
      if (a === "add") openFoodSearch({ slotId: sid });
      if (a === "photo") photoLog(sid);
      if (a === "meals") savedMeals(sid);
      if (a === "barcode") barcodeSheet(sid);
      if (a === "copy") { try { const r = await post("/logs/copy", { from: addDays(S.day, -1), to: S.day, slot_id: sid }); toast(r.copied ? `Copied ${r.copied} item${r.copied > 1 ? "s" : ""}` : "Nothing logged there yesterday"); setDay(r); } catch (er) { fail(er); } }
      if (a === "save") {
        const v = await promptSheet("Save meal", [{ name: "name", label: "Meal name", value: `My ${slotName(sid).toLowerCase()}` }]);
        if (!v || !v.name) return;
        try { await post("/meals", { name: v.name, from_slot: sid, day: S.day }); toast("Meal saved"); } catch (er) { fail(er); }
      }
    });
  }
  async function copyDay() {
    if (!(await confirmSheet("Copy yesterday's food?", `Everything logged on ${fmtDay(addDays(S.day, -1))} is added to ${dayLabel(S.day).toLowerCase()}.`, "Copy", false))) return;
    try { const r = await post("/logs/copy", { from: addDays(S.day, -1), to: S.day }); toast(r.copied ? `Copied ${r.copied} items` : "Nothing was logged yesterday"); setDay(r); } catch (e) { fail(e); }
  }
  function nutrientsSheet() {
    const d = S.dayData; if (!d) return;
    const t = d.targets || {};
    sheet(`<div class="sh-h"><h2>Nutrients · ${esc(dayLabel(S.day))}</h2><p>Sum of everything logged. Missing values mean the source didn't report that nutrient.</p></div>
      <div class="sh-b">${nutrientTable(d.totals || {}, t)}</div><div class="sh-f"><button type="button" class="btn block" data-close>Done</button></div>`);
  }
  function nutrientTable(vals, targets = {}) {
    const groups = { main: "Macronutrients", fat: "Fats", min: "Minerals", vit: "Vitamins" };
    let html = "", g = null;
    for (const n of S.nutrients) {
      if (n.group !== g) { g = n.group; html += `<tr class="grp"><td colspan="2">${groups[g] || g}</td></tr>`; }
      const v = vals[n.key];
      html += `<tr><td>${esc(n.label)}</td><td>${v == null ? '<span class="muted">–</span>' : num(v, v < 10 ? 2 : 1) + " " + esc(n.unit)}${targets[n.key] ? `<span class="muted"> / ${num(targets[n.key])}</span>` : ""}</td></tr>`;
    }
    return `<table class="ntab">${html}</table>`;
  }

  // food search page. opts: { slotId, pick(food), query }
  function openFoodSearch(opts = {}) {
    const p = page(`<div class="t"><b>${opts.pick ? "Choose food" : "Add to " + esc(slotName(opts.slotId))}</b><span>${esc(dayLabel(S.day))}</span></div>
      <button type="button" class="icon-btn" data-bc aria-label="Scan barcode">${ic("barcode")}</button>`,
      `<label class="search">${ic("search")}<input type="search" id="fsQ" placeholder="Search roti, paneer, banana, whey…" autocomplete="off" enterkeyhint="search"></label><div id="fsRes"></div>`);
    const q = $("#fsQ", p.el), res = $("#fsRes", p.el);
    let seq = 0;
    const row = (f, favs) => {
      const per = f.serving_g ? { k: ((f.per100.kcal || 0) * f.serving_g) / 100, l: (f.serving_label || "serving") } : { k: f.per100.kcal || 0, l: "100 g" };
      return `<li class="li" data-id="${esc(f.id)}"><span class="thumb">${favs.has(f.id) ? "⭐" : f.kind === "recipe" || f.source === "indb" ? "🍛" : "🥗"}</span>
        <div class="t"><b>${esc(f.name)}</b><span><span class="src">${esc(srcLabel[f.source] || f.source)}</span> ${f.brand ? esc(f.brand) + " · " : ""}per ${esc(per.l)} · P ${num(((f.per100.protein_g || 0) * (f.serving_g || 100)) / 100, 1)} g</span></div>
        <div class="r">${num(per.k)}<small>kcal</small></div></li>`;
    };
    let cache = {};
    const show = (d, query) => {
      const favs = new Set(d.fav_ids || []);
      cache = {}; [...(d.items || []), ...(d.recent || []), ...(d.favourites || [])].forEach((f) => (cache[f.id] = f));
      if (!query) {
        res.innerHTML = `${(d.favourites || []).length ? `<div class="card"><div class="card-h"><h3>Favourites</h3></div><ul class="list">${d.favourites.map((f) => row(f, favs)).join("")}</ul></div>` : ""}
          ${(d.recent || []).length ? `<div class="card"><div class="card-h"><h3>Recent</h3></div><ul class="list">${d.recent.map((f) => row(f, favs)).join("")}</ul></div>` : ""}
          ${!(d.favourites || []).length && !(d.recent || []).length ? `<div class="empty"><b>Search 1,000+ Indian dishes and more</b>Roti, dal makhani, poha, idli, chicken curry, plus USDA ingredients and packaged foods.</div>` : ""}`;
      } else {
        res.innerHTML = (d.items || []).length ? `<div class="card"><ul class="list">${d.items.map((f) => row(f, favs)).join("")}</ul></div>` : `<div class="empty"><b>No match for "${esc(query)}"</b>Try a simpler name, or add it yourself.</div>`;
      }
      res.insertAdjacentHTML("beforeend", `<div style="padding:4px 14px 10px;display:grid;gap:8px"><button type="button" class="btn block" data-custom>${ic("plus")}Create a custom food</button></div>`);
    };
    const run = async () => {
      const my = ++seq, query = q.value.trim();
      if (query.length === 1) return;
      if (query) res.querySelector(".card") || (res.innerHTML = `<div class="card card-b"><span class="skel"></span><span class="skel"></span><span class="skel"></span></div>`);
      try { const d = await api("/foods/search?q=" + encodeURIComponent(query)); if (my === seq) show(d, query); } catch (e) { if (my === seq) fail(e); }
    };
    q.addEventListener("input", debounce(run, 260));
    res.addEventListener("click", (e) => {
      if (e.target.closest("[data-custom]")) { customFood(opts.slotId, (food) => { if (opts.pick) { p.close(); opts.pick(food); } else openFood(food.id, { slotId: opts.slotId, after: p.close }); }, q.value.trim()); return; }
      const li = e.target.closest("[data-id]"); if (!li) return;
      const f = cache[li.dataset.id];
      if (opts.pick) { p.close(); opts.pick(f); return; }
      openFood(li.dataset.id, { slotId: opts.slotId, after: p.close });
    });
    $("[data-bc]", p.el).onclick = () => barcodeSheet(opts.slotId, (food) => { if (opts.pick) { p.close(); opts.pick(food); } else openFood(food.id, { slotId: opts.slotId, after: p.close }); });
    if (opts.query) q.value = opts.query;
    run();
    setTimeout(() => q.focus(), 380);
  }

  // food detail sheet: add a new log, or edit an existing one (opts.log)
  async function openFood(fid, opts = {}) {
    let r;
    try { r = await api("/foods/" + encodeURIComponent(fid)); } catch (e) { fail(e); return; }
    const food = r.food; S.nutrients = r.nutrients || S.nutrients;
    const lg = opts.log;
    let unit = lg ? lg.unit : food.serving_g ? "serving" : "g";
    if (!food.units.some((u) => u.u === unit)) unit = food.units[0].u;
    let qty = lg ? lg.qty : unit === "g" ? 100 : 1;
    let slot = lg ? lg.slot_id : opts.slotId ?? slotNow();
    let fav = false;
    const s = sheet(`<div class="sh-h"><div class="row"><h2 class="grow">${esc(food.name)}</h2><button type="button" class="icon-btn" id="fdFav" aria-label="Favourite">${ic("star")}</button></div>
        <p><span class="src">${esc(srcLabel[food.source] || food.source)}</span> ${food.brand ? esc(food.brand) + " · " : ""}${food.serving_g ? `1 ${esc(food.serving_label || "serving")} = ${num(food.serving_g)} g` : "Values per 100 g"}</p></div>
      <div class="sh-b">
        <div class="row" style="gap:10px;flex-wrap:wrap">
          <div class="stepper"><button type="button" data-q="-1" aria-label="Less">−</button><input id="fdQty" type="number" inputmode="decimal" min="0" step="any" value="${qty}" aria-label="Quantity"><button type="button" data-q="1" aria-label="More">+</button></div>
          <label class="field grow" style="min-width:150px">Unit<select id="fdUnit">${food.units.map((u) => `<option value="${esc(u.u)}" ${u.u === unit ? "selected" : ""}>${esc(u.label)}${u.u !== "g" && u.u !== "ml" ? ` · ${num(u.g)} g` : ""}</option>`).join("")}</select></label>
        </div>
        <label class="field full" style="margin-top:10px">Meal<select id="fdSlot">${slotOptions(slot)}</select></label>
      </div>
      <div class="mbig" id="fdMac"></div>
      <div class="sh-b"><details><summary class="small" style="font-weight:800;cursor:pointer;padding:6px 0">All nutrients</summary><div id="fdTab"></div></details></div>
      <div class="sh-f"><button type="button" class="btn primary block" id="fdOk">${lg ? "Save changes" : `${ic("plus")}Add`}</button>
        ${lg ? `<button type="button" class="btn block danger" id="fdDel">${ic("trash")}Remove</button>` : ""}</div>`);
    const qEl = $("#fdQty", s.el), uEl = $("#fdUnit", s.el);
    const upd = () => {
      const g = qty * unitG(food.units, unit), n = scaleN(food.per100, g);
      $("#fdMac", s.el).innerHTML = `<div><b>${num(n.kcal)}</b><span>kcal · ${num(g)} g</span></div>${MAC.slice(0, 3).map(([k, l, c]) => `<div><b style="color:${c}">${num(n[k], 1)}</b><span>${l} g</span></div>`).join("")}`;
      $("#fdTab", s.el).innerHTML = nutrientTable(n);
    };
    upd();
    qEl.addEventListener("input", () => { qty = Math.max(0, Number(qEl.value) || 0); upd(); });
    uEl.addEventListener("change", () => {
      const was = unit; unit = uEl.value;
      if ((unit === "g" || unit === "ml") && was !== "g" && was !== "ml") qty = Math.round(qty * unitG(food.units, was));
      else if ((was === "g" || was === "ml") && unit !== "g" && unit !== "ml") qty = 1;
      qEl.value = qty; upd();
    });
    $$("[data-q]", s.el).forEach((b) => b.addEventListener("click", () => {
      const step = unit === "g" || unit === "ml" ? (qty >= 100 ? 25 : 10) : 0.5;
      qty = Math.max(0, Math.round((qty + step * Number(b.dataset.q)) * 100) / 100); qEl.value = qty; buzz(5); upd();
    }));
    $("#fdSlot", s.el).addEventListener("change", (e) => (slot = Number(e.target.value)));
    try { const sr = await api("/foods/search?q="); fav = (sr.fav_ids || []).includes(food.id); } catch (e) {}
    const favBtn = $("#fdFav", s.el);
    const paintFav = () => { favBtn.style.color = fav ? "var(--c)" : ""; favBtn.querySelector("svg").setAttribute("fill", fav ? "currentColor" : "none"); };
    paintFav();
    favBtn.onclick = async () => { try { const x = await post("/favs/" + encodeURIComponent(food.id)); fav = x.fav; paintFav(); buzz(); toast(fav ? "Added to favourites" : "Removed from favourites"); } catch (e) { fail(e); } };
    $("#fdOk", s.el).onclick = async () => {
      if (!qty) { toast("Enter an amount"); return; }
      try {
        const d = lg ? await patch("/logs/" + lg.id, { qty, unit, slot_id: slot }) : await post("/logs", { food_id: food.id, qty, unit, slot_id: slot, day: S.day });
        buzz(); toast(lg ? "Updated" : `Added to ${slotName(slot)}`); s.close(); opts.after && opts.after(); setDay(d);
      } catch (e) { fail(e); }
    };
    const dl = $("#fdDel", s.el);
    dl && (dl.onclick = async () => { try { const d = await del("/logs/" + lg.id); toast("Removed"); s.close(); setDay(d); } catch (e) { fail(e); } });
  }
  function editLog(lid) {
    let x = null;
    for (const m of S.dayData.meals) { const it = m.items.find((i) => i.id === lid); if (it) { x = { ...it, slot_id: m.id }; break; } }
    if (!x) return;
    if (!x.food_id) { confirmSheet("Remove this item?", x.name, "Remove").then(async (ok) => { if (ok) { try { setDay(await del("/logs/" + lid)); } catch (e) { fail(e); } } }); return; }
    openFood(x.food_id, { log: x });
  }

  async function savedMeals(slotId) {
    let r;
    try { r = await api("/meals"); } catch (e) { fail(e); return; }
    const s = sheet(`<div class="sh-h"><h2>Saved meals</h2><p>Log a whole meal in one tap. Save one from any meal's ⋯ menu.</p></div>
      <div class="sh-b"><label class="field full" style="margin-bottom:10px">Add to<select id="smSlot">${slotOptions(slotId ?? slotNow())}</select></label></div>
      <div id="smList"></div>`);
    const paint = (items) => {
      $("#smList", s.el).innerHTML = items.length ? `<ul class="list">${items.map((m) => `<li class="li" data-m="${m.id}"><span class="thumb">🍱</span><div class="t"><b>${esc(m.name)}</b><span>${esc(m.items.map((i) => i.name).join(", "))}</span></div>
        <div class="r">${num(m.totals.kcal)}<small>kcal</small></div><button type="button" class="icon-btn" data-delm="${m.id}" aria-label="Delete">${ic("trash")}</button></li>`).join("")}</ul>` : `<div class="empty"><b>No saved meals yet</b>Open a meal's ⋯ menu and choose "Save as a meal".</div>`;
    };
    paint(r.items);
    $("#smList", s.el).addEventListener("click", async (e) => {
      const d = e.target.closest("[data-delm]");
      if (d) { e.stopPropagation(); try { paint((await del("/meals/" + d.dataset.delm)).items); } catch (er) { fail(er); } return; }
      const li = e.target.closest("[data-m]"); if (!li) return;
      const sid = Number($("#smSlot", s.el).value);
      try { const day = await post(`/meals/${li.dataset.m}/log`, { day: S.day, slot_id: sid }); toast(`Added to ${slotName(sid)}`); s.close(); setDay(day); } catch (er) { fail(er); }
    });
  }

  function barcodeSheet(slotId, onFood) {
    const can = "BarcodeDetector" in window && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
    let stream = null, timer = null;
    const stop = () => { clearInterval(timer); if (stream) stream.getTracks().forEach((t) => t.stop()); stream = null; };
    const s = sheet(`<div class="sh-h"><h2>Scan a barcode</h2><p>Looks the product up in Open Food Facts.</p></div>
      <div class="sh-b">${can ? `<video id="bcV" playsinline muted style="width:100%;border-radius:18px;background:#000;aspect-ratio:4/3;object-fit:cover;display:none"></video>
        <button type="button" class="btn primary block" id="bcCam" style="margin-bottom:10px">${ic("camera")}Use camera</button>` : ""}
        <div class="row"><label class="field grow">Barcode number<input id="bcN" inputmode="numeric" pattern="[0-9]*" placeholder="8901234567890"></label><button type="button" class="btn" id="bcGo">Look up</button></div></div>`, { onClose: stop });
    const look = async (code) => {
      code = String(code || "").replace(/\D/g, "");
      if (code.length < 6) { toast("Enter the full barcode number"); return; }
      try { const r = await api("/foods/barcode/" + code); stop(); s.close(); if (onFood) onFood(r.food); else openFood(r.food.id, { slotId }); }
      catch (e) { fail(e); }
    };
    $("#bcGo", s.el).onclick = () => look($("#bcN", s.el).value);
    const cam = $("#bcCam", s.el);
    cam && (cam.onclick = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        const v = $("#bcV", s.el); v.srcObject = stream; v.style.display = "block"; await v.play(); cam.hidden = true;
        const det = new window.BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128"] });
        let busy = false;
        timer = setInterval(async () => {
          if (busy || !stream) return; busy = true;
          try { const c = await det.detect(v); if (c && c[0]) { buzz(30); $("#bcN", s.el).value = c[0].rawValue; look(c[0].rawValue); } } catch (e) {}
          busy = false;
        }, 350);
      } catch (e) { toast("Camera unavailable. Type the number instead."); }
    });
  }

  function customFood(slotId, onFood, name = "") {
    const f = (n, l, ph = "", full = false, type = "number") => `<label class="field ${full ? "full" : ""}">${l}<input name="${n}" type="${type}" ${type === "number" ? 'inputmode="decimal" step="any"' : ""} placeholder="${esc(ph)}"></label>`;
    const s = sheet(`<div class="sh-h"><h2>Custom food</h2><p>Copy the numbers from the pack's nutrition label. Only you can see it.</p></div>
      <div class="form">${f("name", "Name", "Protein bar", true, "text").replace('placeholder="Protein bar"', `placeholder="Protein bar" value="${esc(name)}"`)}${f("brand", "Brand (optional)", "", true, "text")}
        <label class="field full">Values are per<select name="basis"><option value="100">100 g / 100 ml</option><option value="serving">one serving (below)</option></select></label>
        ${f("serving_g", "Serving size (g)", "30")}${f("serving_label", "Serving name", "bar", false, "text")}
        ${f("kcal", "Calories (kcal)", "")}${f("protein_g", "Protein (g)")}${f("carb_g", "Carbs (g)")}${f("fat_g", "Fat (g)")}${f("fibre_g", "Fibre (g)")}${f("sugar_g", "Sugar (g)")}${f("sodium_mg", "Sodium (mg)")}${f("sfa_g", "Saturated fat (g)")}
        ${f("barcode", "Barcode (optional)", "", true, "text")}</div>
      <div class="sh-f"><button type="button" class="btn primary block" id="cfOk">Save food</button></div>`);
    $("#cfOk", s.el).onclick = async () => {
      const v = {}; $$("input, select", s.el).forEach((i) => (v[i.name] = i.value.trim()));
      const basis = v.basis === "serving" ? Number(v.serving_g) || 0 : 100;
      if (!v.name || !v.kcal) { toast("Enter at least a name and calories"); return; }
      if (v.basis === "serving" && !basis) { toast("Enter the serving size in grams"); return; }
      const nutrients = {}; ["kcal", "protein_g", "carb_g", "fat_g", "fibre_g", "sugar_g", "sodium_mg", "sfa_g"].forEach((k) => { if (v[k] !== "") nutrients[k] = Number(v[k]); });
      try {
        const r = await post("/foods", { name: v.name, brand: v.brand, basis_g: basis, nutrients, serving_g: v.serving_g ? Number(v.serving_g) : null, serving_label: v.serving_label || "serving", barcode: v.barcode });
        toast("Food saved"); s.close();
        if (onFood) onFood(r.food); else openFood(r.food.id, { slotId });
      } catch (e) { fail(e); }
    };
  }

  // ------------------------------------------------------------------ WORKOUT
  RENDER.workout = () => {
    const el = $("#scr-workout");
    el.innerHTML = `<header class="head"><h1>Workout</h1><button type="button" class="icon-btn" id="wkPast" aria-label="Log a past workout">${ic("plus")}</button></header><div class="scroll" id="wkBody"><div class="card card-b"><span class="skel"></span><span class="skel"></span></div></div>`;
    $("#wkPast", el).onclick = pastWorkout;
    paintWorkoutTab();
  };
  async function paintWorkoutTab() {
    const body = $("#wkBody"); if (!body) return;
    let ws, rs;
    try { [ws, rs] = await Promise.all([api("/workouts?days=90"), api("/routines")]); } catch (e) { fail(e); return; }
    S.activeId = ws.active_id;
    const byWeek = {};
    ws.items.forEach((w) => { const d = new Date(w.day + "T12:00:00Z"); const mon = addDays(w.day, -((d.getUTCDay() + 6) % 7)); (byWeek[mon] = byWeek[mon] || []).push(w); });
    body.innerHTML = `
      ${S.activeId ? `<div class="wk-banner" id="wkResume">${ic("timer")}<div class="grow"><b>Workout in progress</b><span>Tap to continue</span></div>${ic("right")}</div>` :
      `<div style="padding:8px 14px 0"><button type="button" class="btn primary block" id="wkStart">${ic("plus")}Start an empty workout</button></div>`}
      <div class="card"><div class="card-h"><h3>Routines</h3><button type="button" class="pill acc" id="wkNewR">New routine</button></div>
        ${rs.items.length ? `<ul class="list">${rs.items.map((r) => `<li class="li" data-r="${r.id}"><span class="thumb">📋</span><div class="t"><b>${esc(r.name)}</b><span>${esc(r.items.map((i) => i.name).join(", "))}</span></div><button type="button" class="icon-btn" data-rm="${r.id}" aria-label="Routine options">${ic("more")}</button></li>`).join("")}</ul>`
        : `<div class="empty" style="padding:4px 16px 18px">Save a routine (e.g. Push day) to start it in one tap with last time's weights filled in.</div>`}</div>
      <div class="card"><div class="card-h"><h3>History</h3><span class="muted small">last 90 days</span></div>
        ${ws.items.length ? Object.keys(byWeek).sort().reverse().map((wk) => `<div class="small muted" style="padding:8px 16px 2px;font-weight:800">Week of ${esc(fmtDay(wk, { day: "numeric", month: "short" }))} · ${byWeek[wk].length} workout${byWeek[wk].length > 1 ? "s" : ""}</div>
          <ul class="list">${byWeek[wk].map((w) => `<li class="li" data-w="${w.id}"><span class="thumb">${w.ended_at || !w.started_at ? "🏋" : "⏱"}</span><div class="t"><b>${esc(w.name || "Workout")}</b><span>${esc(dayLabel(w.day))} · ${w.duration_min ? mins(w.duration_min) + " · " : ""}${w.sets} sets${w.volume_kg ? " · " + num(w.volume_kg) + " kg" : ""}</span></div><div class="r">${num(w.kcal)}<small>kcal</small></div></li>`).join("")}</ul>`).join("")
        : `<div class="empty"><b>No workouts yet</b>Start one above, or describe it in "Log my day" on the Today tab.</div>`}</div>
      <p class="small muted" style="padding:0 18px">Calories burnt are estimates from MET values (Compendium of Physical Activities) and your body weight.</p>`;
    const st = $("#wkStart", body); st && (st.onclick = () => startWorkout());
    const rs_ = $("#wkResume", body); rs_ && (rs_.onclick = () => openWorkout(S.activeId));
    $("#wkNewR", body).onclick = () => routineBuilder();
    $$("[data-w]", body).forEach((li) => li.addEventListener("click", () => openWorkout(Number(li.dataset.w))));
    $$("[data-r]", body).forEach((li) => li.addEventListener("click", (e) => {
      if (e.target.closest("[data-rm]")) { routineMenu(rs.items.find((r) => r.id === Number(li.dataset.r))); return; }
      startWorkout({ routine_id: Number(li.dataset.r), name: rs.items.find((r) => r.id === Number(li.dataset.r)).name });
    }));
  }
  function routineMenu(r) {
    const s = sheet(`<div class="sh-h"><h2>${esc(r.name)}</h2><p>${r.items.map((i) => `${esc(i.name)} (${i.sets}×${i.minutes ? num(i.minutes) + " min" : num(i.reps || 10)})`).join(", ")}</p></div>
      <div class="sh-f"><button type="button" class="btn primary block" data-a="start">${ic("dumbbell")}Start this routine</button><button type="button" class="btn block danger" data-a="del">${ic("trash")}Delete routine</button></div>`);
    s.el.addEventListener("click", async (e) => {
      const a = (e.target.closest("[data-a]") || {}).dataset; if (!a || !a.a) return; s.close();
      if (a.a === "start") startWorkout({ routine_id: r.id, name: r.name });
      if (a.a === "del" && (await confirmSheet("Delete this routine?", r.name))) { try { await del("/routines/" + r.id); paintWorkoutTab(); } catch (er) { fail(er); } }
    });
  }
  function routineBuilder() {
    const items = [];
    const s = sheet(`<div class="sh-h"><h2>New routine</h2></div><div class="form"><label class="field full">Name<input id="rbN" placeholder="Push day"></label></div><div id="rbL"></div>
      <div class="sh-f"><button type="button" class="btn block" id="rbAdd">${ic("plus")}Add exercise</button><button type="button" class="btn primary block" id="rbOk">Save routine</button></div>`);
    const paint = () => {
      $("#rbL", s.el).innerHTML = items.length ? `<ul class="list">${items.map((it, i) => `<li class="li">${exThumb(it.ex)}<div class="t"><b>${esc(it.ex.name)}</b><span>${esc(exMeta(it.ex))}</span></div>
        <input type="number" inputmode="numeric" value="${it.sets}" data-i="${i}" data-k="sets" style="width:48px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--surface-2);text-align:center;font-weight:800" aria-label="Sets">
        <span class="muted small">×</span><input type="number" inputmode="numeric" value="${it.ex.kind === "strength" ? it.reps : it.minutes}" data-i="${i}" data-k="${it.ex.kind === "strength" ? "reps" : "minutes"}" style="width:52px;height:34px;border-radius:10px;border:1px solid var(--line);background:var(--surface-2);text-align:center;font-weight:800" aria-label="${it.ex.kind === "strength" ? "Reps" : "Minutes"}">
        <button type="button" class="icon-btn" data-x="${i}" aria-label="Remove" style="width:34px;height:34px">${ic("x")}</button></li>`).join("")}</ul>` : `<div class="empty" style="padding:8px">Add the exercises you usually do.</div>`;
    };
    paint();
    $("#rbL", s.el).addEventListener("change", (e) => { const t = e.target; if (t.dataset.i != null) items[t.dataset.i][t.dataset.k] = Number(t.value) || 0; });
    $("#rbL", s.el).addEventListener("click", (e) => { const x = e.target.closest("[data-x]"); if (x) { items.splice(Number(x.dataset.x), 1); paint(); } });
    $("#rbAdd", s.el).onclick = () => pickExercise((ex) => { items.push({ ex, sets: ex.kind === "strength" ? 3 : 1, reps: 10, minutes: 20 }); paint(); });
    $("#rbOk", s.el).onclick = async () => {
      if (!items.length) { toast("Add at least one exercise"); return; }
      try {
        await post("/routines", { name: $("#rbN", s.el).value.trim() || "My routine", items: items.map((it) => ({ exercise_id: it.ex.id, sets: it.sets, reps: it.ex.kind === "strength" ? it.reps : null, minutes: it.ex.kind !== "strength" ? it.minutes : null })) });
        toast("Routine saved"); s.close(); paintWorkoutTab();
      } catch (e) { fail(e); }
    };
  }
  async function startWorkout(b = {}) {
    try {
      const r = await post("/workouts", { ...b, day: today() });
      S.activeId = r.workout.id; buzz(20);
      openWorkout(r.workout.id, r.workout);
      if (S.tab === "workout") paintWorkoutTab();
    } catch (e) { fail(e); }
  }
  async function pastWorkout() {
    const v = await promptSheet("Log a past workout", [{ name: "day", label: "Date", type: "date", value: S.day, attrs: `max="${today()}"` }, { name: "name", label: "Name", placeholder: "Leg day" }, { name: "dur", label: "Duration (min)", type: "number", value: "60", attrs: 'inputmode="numeric"' }], "Create");
    if (!v) return;
    try {
      const r = await post("/workouts", { day: v.day || S.day, name: v.name, live: false });
      if (Number(v.dur)) await patch("/workouts/" + r.workout.id, { duration_min: Number(v.dur) });
      openWorkout(r.workout.id);
    } catch (e) { fail(e); }
  }

  // rest timer
  const REST = { end: 0, t: null, el: null };
  function restStart(sec = store.get("fit_rest", 90)) {
    if (!sec) return;
    REST.end = Date.now() + sec * 1000;
    if (!REST.el) {
      REST.el = document.createElement("div"); REST.el.className = "rest";
      REST.el.innerHTML = `${ic("timer")}<b id="restT"></b><button type="button" data-r="-15">−15</button><button type="button" data-r="15">+15</button><button type="button" data-r="0">Skip</button>`;
      REST.el.addEventListener("click", (e) => { const b = e.target.closest("[data-r]"); if (!b) return; const n = Number(b.dataset.r); if (!n) restStop(); else REST.end += n * 1000; tickRest(); });
      document.body.appendChild(REST.el);
    }
    clearInterval(REST.t); REST.t = setInterval(tickRest, 250); tickRest();
  }
  function tickRest() {
    if (REST.el) { const zs = $$(".page").map((x) => Number(x.style.zIndex) || 30); REST.el.style.zIndex = zs.length ? Math.max(...zs) + 1 : 25; }
    const left = (REST.end - Date.now()) / 1000;
    if (left <= 0) { buzz([120, 80, 120]); restStop(); toast("Rest over. Next set!"); return; }
    const t = $("#restT"); t && (t.textContent = clock(Math.ceil(left)));
  }
  function restStop() { clearInterval(REST.t); REST.t = null; if (REST.el) { REST.el.remove(); REST.el = null; } }

  // the workout logger page
  async function openWorkout(wid, initial) {
    let W = initial || null;
    const p = page(`<div class="t"><input class="title" id="woName" aria-label="Workout name"><span id="woSub"></span></div><button type="button" class="btn sm primary" id="woFinish">Finish</button>`,
      `<div id="woStats"></div><div id="woEntries"><div class="card card-b"><span class="skel"></span><span class="skel"></span></div></div>
       <div style="padding:6px 14px;display:grid;gap:8px"><button type="button" class="btn block" id="woAdd">${ic("plus")}Add exercise</button></div>
       <div class="card"><div class="card-b" style="padding-top:12px"><textarea id="woNotes" placeholder="Notes (how it felt, energy, pain…)" style="width:100%;min-height:60px;border:0;background:none;outline:0;resize:vertical"></textarea></div></div>
       <div style="padding:6px 14px 20px;display:grid;gap:8px"><button type="button" class="btn block" id="woShare">${ic("share")}Share</button><button type="button" class="btn block danger" id="woDel">${ic("trash")}Delete workout</button></div>`,
      { onClose: () => { clearInterval(clk); if (S.tab === "workout") paintWorkoutTab(); else if (S.tab === "today") loadDay().then(setDay).catch(() => {}); } });
    const live = () => W && W.started_at && !W.ended_at;
    let clk = setInterval(() => { if (live()) { const t = $("#woClock", p.el); t && (t.textContent = clock((Date.now() - new Date(W.started_at).getTime()) / 1000)); } }, 1000);
    const nameEl = $("#woName", p.el);
    nameEl.addEventListener("change", () => patch("/workouts/" + wid, { name: nameEl.value }).then((r) => (W = { ...W, ...r.workout, entries: W.entries })).catch(fail));
    $("#woNotes", p.el).addEventListener("change", (e) => patch("/workouts/" + wid, { notes: e.target.value }).catch(fail));
    const stats = () => {
      const done = W.entries.reduce((a, e) => a + e.sets.filter((s) => s.done).length, 0);
      const vol = W.entries.reduce((a, e) => a + e.sets.filter((s) => s.done).reduce((b, s) => b + (s.weight_kg || 0) * (s.reps || 0), 0), 0);
      $("#woSub", p.el).textContent = `${dayLabel(W.day)}${W.via === "ai" ? " · via AI" : ""}`;
      $("#woStats", p.el).innerHTML = `<div class="stats3" style="padding:12px 14px 2px"><div><b class="timer" id="woClock">${live() ? clock((Date.now() - new Date(W.started_at).getTime()) / 1000) : W.duration_min ? mins(W.duration_min) : "–"}</b><span>${live() ? "Elapsed" : "Duration"}</span></div>
        <div><b>${num(vol)}</b><span>Volume kg</span></div><div><b>${done}</b><span>Sets done</span></div></div>`;
      $("#woFinish", p.el).textContent = live() ? "Finish" : "Done";
    };
    const cols = (e) => (e.kind === "cardio" ? [["minutes", "MIN"], ["distance_km", "KM"]] : e.kind === "time" ? [["minutes", "MIN"]] : [["weight_kg", "KG"], ["reps", "REPS"]]);
    const prevTxt = (e, i) => { const h = e.history && e.history.last && e.history.last[i]; if (!h) return "–"; return e.kind === "strength" ? (h.weight_kg ? `${num(h.weight_kg, 1)}×${num(h.reps)}` : `${num(h.reps)} reps`) : `${num(h.minutes, 1)} min`; };
    const kindLbl = { normal: null, warmup: "W", drop: "D", failure: "F" };
    const entryHtml = (e) => {
      let n = 0;
      const rows = e.sets.map((s, i) => { if (s.kind !== "warmup") n++; return `<tr class="${s.done ? "done" : ""}" data-sid="${s.id}"><td><button type="button" class="idx ${s.kind}" data-kind="${s.kind}" aria-label="Set type">${kindLbl[s.kind] || n}</button></td>
        <td class="prev">${prevTxt(e, i)}</td>${cols(e).map(([k]) => `<td><input type="number" inputmode="decimal" step="any" value="${s[k] ?? ""}" data-k="${k}" placeholder="${k === "reps" ? "0" : "–"}"></td>`).join("")}
        <td><button type="button" class="tick" data-tick aria-label="Mark set done">${ic("check")}</button></td></tr>`; }).join("");
      const h = e.history;
      return `<div class="entry" data-eid="${e.id}"><div class="entry-h">${exThumb(e)}<div class="grow"><b>${esc(e.name)}</b><span>${esc(e.part || "")}${h && h.best ? ` · best ${num(h.best.weight_kg, 1)} kg × ${num(h.best.reps)} (e1RM ${num(h.best.e1rm, 1)})` : h && h.sessions ? ` · ${h.sessions} past sessions` : " · first time"}</span></div>
        <button type="button" class="icon-btn" data-info aria-label="How to">${ic("info")}</button><button type="button" class="icon-btn" data-emenu aria-label="Exercise options">${ic("more")}</button></div>
        <table class="sets"><thead><tr><th>SET</th><th>PREVIOUS</th>${cols(e).map(([, l]) => `<th>${l}</th>`).join("")}<th></th></tr></thead><tbody>${rows}</tbody></table>
        <div class="entry-f"><button type="button" class="btn" data-addset>${ic("plus")}Add set</button></div></div>`;
    };
    const paint = () => {
      if (!W) return;
      if (document.activeElement !== nameEl) nameEl.value = W.name || "";
      const ne = $("#woNotes", p.el); if (document.activeElement !== ne) ne.value = W.notes || "";
      stats();
      $("#woEntries", p.el).innerHTML = W.entries.length ? W.entries.map(entryHtml).join("") : `<div class="empty"><b>Add your first exercise</b>Search 900+ exercises by name, body part or machine.</div>`;
    };
    const findSet = (sid) => { for (const e of W.entries) { const s = e.sets.find((x) => x.id === sid); if (s) return [e, s]; } return [null, null]; };
    const ent = $("#woEntries", p.el);
    ent.addEventListener("change", async (ev) => {
      const inp = ev.target; if (!inp.dataset.k) return;
      const sid = Number(inp.closest("[data-sid]").dataset.sid); const [, s] = findSet(sid); if (!s) return;
      const v = inp.value === "" ? null : Number(inp.value); s[inp.dataset.k] = v;
      try { const r = await patch("/sets/" + sid, { [inp.dataset.k]: v }); const fresh = r.workout; W.kcal = fresh.kcal; W.volume_kg = fresh.volume_kg; stats(); } catch (e) { fail(e); }
    });
    ent.addEventListener("click", async (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      const card = b.closest("[data-eid]"); const eid = card && Number(card.dataset.eid); const entry = W.entries.find((x) => x.id === eid);
      const tr = b.closest("[data-sid]");
      if (b.hasAttribute("data-tick")) {
        const sid = Number(tr.dataset.sid); const [e, s] = findSet(sid);
        const body = { done: !s.done }; $$("input[data-k]", tr).forEach((i) => (body[i.dataset.k] = i.value === "" ? null : Number(i.value)));
        if (body.done && e.kind === "strength" && !body.reps) { toast("Enter reps first"); $("input[data-k=reps]", tr).focus(); return; }
        if (body.done && e.kind !== "strength" && !body.minutes) { toast("Enter minutes first"); $("input[data-k=minutes]", tr).focus(); return; }
        Object.assign(s, body); tr.classList.toggle("done", !!s.done); buzz(s.done ? 15 : 5); stats();
        try {
          const r = await patch("/sets/" + sid, body); W.kcal = r.workout.kcal;
          if (r.pr) { buzz([40, 60, 40]); toast(`🏆 New best on ${e.name}: e1RM ${num(r.pr.e1rm, 1)} kg (was ${num(r.pr.previous, 1)})`, 4000); }
          if (s.done && live()) restStart();
        } catch (er) { fail(er); }
        return;
      }
      if (b.dataset.kind) {
        const order = ["normal", "warmup", "drop", "failure"]; const nk = order[(order.indexOf(b.dataset.kind) + 1) % order.length];
        try { const r = await patch("/sets/" + tr.dataset.sid, { kind: nk }); W = r.workout; paint(); toast({ normal: "Working set", warmup: "Warm-up set (not counted in weekly sets)", drop: "Drop set", failure: "Set to failure" }[nk], 1500); } catch (er) { fail(er); }
        return;
      }
      if (b.hasAttribute("data-addset")) { try { W = (await post(`/entries/${eid}/sets`, {})).workout; paint(); buzz(); } catch (er) { fail(er); } return; }
      if (b.hasAttribute("data-info")) { exerciseInfo(entry.exercise_id); return; }
      if (b.hasAttribute("data-emenu")) {
        const s = sheet(`<div class="sh-h"><h2>${esc(entry.name)}</h2></div><div class="sh-f">
          ${entry.sets.length ? `<button type="button" class="btn block" data-a="last">Remove last set</button>` : ""}
          <button type="button" class="btn block" data-a="info">${ic("info")}How to do it</button><button type="button" class="btn block danger" data-a="rm">${ic("trash")}Remove exercise</button></div>`);
        s.el.addEventListener("click", async (e2) => {
          const a = (e2.target.closest("[data-a]") || {}).dataset; if (!a || !a.a) return; s.close();
          try {
            if (a.a === "last") { W = (await del("/sets/" + entry.sets[entry.sets.length - 1].id)).workout; paint(); }
            if (a.a === "rm") { W = (await del("/entries/" + eid)).workout; paint(); }
            if (a.a === "info") exerciseInfo(entry.exercise_id);
          } catch (er) { fail(er); }
        });
      }
    });
    $("#woAdd", p.el).onclick = () => pickExercise(async (ex) => {
      try { W = (await post(`/workouts/${wid}/entries`, { exercise_id: ex.id })).workout; paint(); buzz(); setTimeout(() => { const c = ent.lastElementChild; c && c.scrollIntoView({ behavior: "smooth", block: "center" }); }, 60); } catch (e) { fail(e); }
    }, { multi: true });
    $("#woFinish", p.el).onclick = async () => {
      if (!live()) { p.close(); return; }
      const pending = W.entries.reduce((a, e) => a + e.sets.filter((s) => !s.done).length, 0);
      const doneN = W.entries.reduce((a, e) => a + e.sets.filter((s) => s.done).length, 0);
      if (!doneN && !(await confirmSheet("Finish without any sets?", "Nothing is marked done, so the workout will be empty.", "Finish anyway"))) return;
      if (pending && doneN && !(await confirmSheet(`Finish workout?`, `${pending} unticked set${pending > 1 ? "s" : ""} will be discarded.`, "Finish", false))) return;
      try {
        const r = await post(`/workouts/${wid}/finish`); W = r.workout; S.activeId = null; restStop(); paint();
        finishSummary(W, r.prs, wid);
      } catch (e) { fail(e); }
    };
    $("#woShare", p.el).onclick = () => shareWorkout(wid);
    $("#woDel", p.el).onclick = async () => {
      if (!(await confirmSheet("Delete this workout?", "All its exercises and sets are removed. This can't be undone."))) return;
      try { await del("/workouts/" + wid); if (S.activeId === wid) S.activeId = null; restStop(); toast("Workout deleted"); p.close(); } catch (e) { fail(e); }
    };
    try { W = (await api("/workouts/" + wid)).workout; paint(); } catch (e) { fail(e); p.close(); }
  }
  function finishSummary(W, prs, wid) {
    buzz([30, 40, 30]);
    const s = sheet(`<div class="sh-h" style="text-align:center"><div style="font-size:44px;line-height:1">🎉</div><h2>Workout complete</h2><p>${esc(W.name || "")}</p></div>
      <div class="stats3"><div><b>${W.duration_min ? mins(W.duration_min) : "–"}</b><span>Duration</span></div><div><b>${num(W.volume_kg)}</b><span>Volume kg</span></div><div><b>${num(W.kcal)}</b><span>kcal (est.)</span></div></div>
      ${prs && prs.length ? `<div class="sh-b"><b style="font:700 15px var(--f-display)">🏆 Personal bests</b><ul class="list">${prs.map((p) => `<li class="li" style="padding:10px 0"><div class="t"><b>${esc(p.exercise)}</b><span>e1RM ${num(p.e1rm, 1)} kg${p.previous ? ` · was ${num(p.previous, 1)}` : " · first record"}</span></div></li>`).join("")}</ul></div>` : ""}
      <div class="sh-f"><button type="button" class="btn block" data-a="share">${ic("share")}Share</button><button type="button" class="btn block" data-a="routine">Save as routine</button><button type="button" class="btn primary block" data-close>Done</button></div>`);
    s.el.addEventListener("click", async (e) => {
      const a = (e.target.closest("[data-a]") || {}).dataset; if (!a || !a.a) return;
      if (a.a === "share") shareWorkout(wid);
      if (a.a === "routine") {
        const v = await promptSheet("Save as routine", [{ name: "name", label: "Routine name", value: W.name || "My routine" }]);
        if (v && v.name) { try { await post("/routines", { name: v.name, from_workout: wid }); toast("Routine saved"); } catch (er) { fail(er); } }
      }
    });
  }
  async function shareWorkout(wid) {
    try {
      const r = await post(`/workouts/${wid}/share`);
      const url = location.origin + r.url;
      if (navigator.share) { try { await navigator.share({ title: "My workout", url }); return; } catch (e) { if (e && e.name === "AbortError") return; } }
      try { await navigator.clipboard.writeText(url); toast("Link copied. Anyone with it can view this workout."); } catch (e) { promptSheet("Share link", [{ name: "u", label: "Copy this link", value: url }], "Done"); }
    } catch (e) { fail(e); }
  }
  async function exerciseInfo(eid) {
    if (!eid) return;
    let r; try { r = await api("/exercises/" + encodeURIComponent(eid)); } catch (e) { fail(e); return; }
    const x = r.exercise, h = r.history;
    const imgs = (x.images || []).slice(0, 2);
    const s = sheet(`${imgs.length ? `<div style="display:grid;grid-template-columns:repeat(${imgs.length},1fr);gap:4px;margin:-6px 0 12px">${imgs.map((u) => `<img class="ex-img" src="${esc(u)}" alt="" loading="lazy">`).join("")}</div>` : ""}
      <div class="sh-h"><h2>${esc(x.name)}</h2><p>${esc(exMeta(x))}${x.level ? " · " + esc(x.level) : ""}${(x.primary || []).length ? " · targets " + esc(x.primary.join(", ")) : ""}${(x.secondary || []).length ? " (also " + esc(x.secondary.join(", ")) + ")" : ""}</p></div>
      ${h && h.sessions ? `<div class="stats3"><div><b>${h.sessions}</b><span>Sessions</span></div><div><b>${h.best ? num(h.best.weight_kg, 1) : "–"}</b><span>Best kg</span></div><div><b>${h.best ? num(h.best.e1rm, 1) : "–"}</b><span>Best e1RM</span></div></div>` : ""}
      ${(x.instructions || []).length ? `<ol class="instr">${x.instructions.map((i) => `<li>${esc(i)}</li>`).join("")}</ol>` : `<p class="small muted" style="padding:0 18px">No instructions for this exercise.</p>`}
      <div class="sh-f"><button type="button" class="btn block" data-close>Close</button></div>`);
    let k = 0; const im = $$(".ex-img", s.el);
    if (im.length === 1 && (x.images || []).length > 1) { const t = setInterval(() => { if (!document.body.contains(s.el)) { clearInterval(t); return; } k = 1 - k; im[0].src = x.images[k]; }, 1200); }
  }

  // exercise picker page
  function pickExercise(cb, { multi = false } = {}) {
    const st = { q: "", part: "", eq: "" };
    let meta = null, seq = 0;
    const p = page(`<div class="t"><b>Add exercise</b><span>${multi ? "Tap to add. Add as many as you like." : "Tap to choose"}</span></div>`,
      `<label class="search">${ic("search")}<input type="search" id="exQ" placeholder="Bench press, lat pulldown, pec deck…" autocomplete="off" enterkeyhint="search"></label>
       <div class="chips" id="exParts"></div><div class="chips" id="exEq"></div><div id="exRes"></div>`);
    const res = $("#exRes", p.el);
    const chips = () => {
      $("#exParts", p.el).innerHTML = [["", "All"], ...meta.parts.map((x) => [x, x])].map(([v, l]) => `<button type="button" class="chip" data-part="${esc(v)}" aria-pressed="${st.part === v}">${esc(l)}</button>`).join("");
      $("#exEq", p.el).innerHTML = [["", "Any equipment"], ...meta.equipment.map((x) => [x.id, x.label])].map(([v, l]) => `<button type="button" class="chip" data-eq="${esc(v)}" aria-pressed="${st.eq === v}">${esc(l)}</button>`).join("");
    };
    let items = [];
    const run = async () => {
      const my = ++seq;
      try {
        const d = await api(`/exercises?q=${encodeURIComponent(st.q)}&part=${encodeURIComponent(st.part)}&equipment=${encodeURIComponent(st.eq)}`);
        if (my !== seq) return;
        if (!meta) { meta = d; chips(); }
        items = d.items;
        res.innerHTML = (items.length ? `<div class="card"><ul class="list">${items.map((e, i) => `<li class="li" data-i="${i}">${exThumb(e)}<div class="t"><b>${esc(e.name)}</b><span>${esc(exMeta(e))}${e.custom ? " · yours" : ""}</span></div><button type="button" class="icon-btn" data-info="${i}" aria-label="How to">${ic("info")}</button></li>`).join("")}</ul></div>`
          : `<div class="empty"><b>Nothing matches</b>Try another name, or create your own.</div>`) + `<div style="padding:4px 14px 10px"><button type="button" class="btn block" data-custom>${ic("plus")}Create a custom exercise</button></div>`;
      } catch (e) { fail(e); }
    };
    $("#exQ", p.el).addEventListener("input", debounce((e) => { st.q = e.target.value.trim(); run(); }, 220));
    p.el.addEventListener("click", (e) => {
      const c = e.target.closest("[data-part],[data-eq]");
      if (c) { if (c.dataset.part != null) st.part = c.dataset.part; else st.eq = c.dataset.eq; chips(); run(); return; }
      const inf = e.target.closest("[data-info]"); if (inf) { exerciseInfo(items[inf.dataset.info].id); return; }
      if (e.target.closest("[data-custom]")) { customExercise((ex) => { if (!multi) p.close(); cb(ex); run(); }, st.q); return; }
      const li = e.target.closest("[data-i]"); if (!li) return;
      const ex = items[li.dataset.i];
      if (multi) { li.style.background = "var(--up-soft)"; setTimeout(() => (li.style.background = ""), 500); toast(`Added ${ex.name}`, 1400); cb(ex); } else { p.close(); cb(ex); }
    });
    run();
  }
  function customExercise(cb, name = "") {
    const s = sheet(`<div class="sh-h"><h2>Custom exercise</h2></div><div class="form">
        <label class="field full">Name<input id="ceN" value="${esc(name)}" placeholder="Hack squat (gym's machine)"></label>
        <label class="field">Body part<select id="ceP">${["Chest", "Back", "Shoulders", "Biceps", "Triceps", "Forearms", "Core", "Quads", "Hamstrings", "Glutes", "Calves", "Neck", "Cardio", "Other"].map((x) => `<option>${x}</option>`).join("")}</select></label>
        <label class="field">Equipment<select id="ceE">${[["machine", "Machine"], ["barbell", "Barbell"], ["dumbbell", "Dumbbell"], ["cable", "Cable"], ["body only", "Bodyweight"], ["kettlebells", "Kettlebell"], ["bands", "Bands"], ["other", "Other"]].map(([v, l]) => `<option value="${v}">${l}</option>`).join("")}</select></label>
        <div class="field full">Logged as<div class="seg" id="ceK" style="margin-top:4px"><button type="button" data-k="strength" aria-pressed="true">Weight × reps</button><button type="button" data-k="cardio" aria-pressed="false">Time + distance</button><button type="button" data-k="time" aria-pressed="false">Time only</button></div></div></div>
      <div class="sh-f"><button type="button" class="btn primary block" id="ceOk">Create</button></div>`);
    let kind = "strength";
    $("#ceK", s.el).addEventListener("click", (e) => { const b = e.target.closest("[data-k]"); if (!b) return; kind = b.dataset.k; $$("#ceK button", s.el).forEach((x) => x.setAttribute("aria-pressed", x === b)); });
    $("#ceP", s.el).addEventListener("change", (e) => { if (e.target.value === "Cardio") $("#ceK [data-k=cardio]", s.el).click(); });
    $("#ceOk", s.el).onclick = async () => {
      const n = $("#ceN", s.el).value.trim(); if (!n) { toast("Name the exercise"); return; }
      try { const r = await post("/exercises", { name: n, part: $("#ceP", s.el).value, equipment: $("#ceE", s.el).value, kind }); s.close(); cb(r.exercise); } catch (e) { fail(e); }
    };
  }

  // ------------------------------------------------------------------ PROGRESS
  RENDER.progress = () => {
    const el = $("#scr-progress");
    el.innerHTML = `<header class="head"><h1>Progress</h1><div class="seg" id="pgRange" style="width:170px">${[7, 30, 90].map((n) => `<button type="button" data-n="${n}" aria-pressed="${S.progDays === n}">${n}d</button>`).join("")}</div></header>
      <div class="scroll" id="pgBody"><div class="card card-b"><span class="skel"></span><span class="skel"></span><span class="skel"></span></div></div>`;
    $("#pgRange", el).addEventListener("click", (e) => { const b = e.target.closest("[data-n]"); if (!b) return; S.progDays = Number(b.dataset.n); RENDER.progress(); });
    paintProgress();
  };
  function barsSvg(series, key, color, target, fmt = (v) => num(v)) {
    const W = 340, H = 150, L = 4, B = 18, T = 14, n = series.length;
    const max = Math.max(target || 0, ...series.map((s) => s[key] || 0)) * 1.12 || 1;
    const bw = (W - L) / n, y = (v) => H - B - ((H - B - T) * v) / max;
    let g = `<line class="ax" x1="0" x2="${W}" y1="${H - B}" y2="${H - B}"/>`;
    series.forEach((s, i) => { const v = s[key] || 0; if (!v) return; g += `<rect x="${(L + i * bw + bw * 0.16).toFixed(1)}" y="${y(v).toFixed(1)}" width="${(bw * 0.68).toFixed(1)}" height="${(H - B - y(v)).toFixed(1)}" rx="${Math.min(4, bw * 0.3).toFixed(1)}" fill="${color}"/>`; });
    if (target) g += `<line x1="0" x2="${W}" y1="${y(target).toFixed(1)}" y2="${y(target).toFixed(1)}" stroke="var(--ink)" stroke-width="1.2" stroke-dasharray="4 4" opacity=".55"/><text x="${W - 2}" y="${(y(target) - 4).toFixed(1)}" text-anchor="end">target ${fmt(target)}</text>`;
    const lab = [0, Math.floor((n - 1) / 2), n - 1];
    lab.forEach((i, j) => { g += `<text x="${(L + i * bw + bw / 2).toFixed(1)}" y="${H - 4}" text-anchor="${j === 0 ? "start" : j === 2 ? "end" : "middle"}">${esc(fmtDay(series[i].day, { day: "numeric", month: "short" }))}</text>`; });
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img">${g}</svg>`;
  }
  function lineSvg(points, color) {
    const W = 340, H = 150, B = 18, T = 16;
    const vs = points.map((p) => p.v), lo = Math.min(...vs), hi = Math.max(...vs), pad = Math.max(0.5, (hi - lo) * 0.15);
    const t0 = new Date(points[0].day).getTime(), t1 = new Date(points[points.length - 1].day).getTime() || t0 + 1;
    const x = (d) => 6 + ((W - 12) * (new Date(d).getTime() - t0)) / Math.max(1, t1 - t0), y = (v) => H - B - ((H - B - T) * (v - lo + pad)) / (hi - lo + 2 * pad);
    const path = points.map((p, i) => `${i ? "L" : "M"}${x(p.day).toFixed(1)},${y(p.v).toFixed(1)}`).join("");
    return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img"><line class="ax" x1="0" x2="${W}" y1="${H - B}" y2="${H - B}"/>
      <path d="${path}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
      ${points.map((p) => `<circle cx="${x(p.day).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="3" fill="${color}"/>`).join("")}
      <text x="2" y="12">${num(hi, 1)} kg</text><text x="2" y="${H - B - 4}">${num(lo, 1)} kg</text>
      <text x="6" y="${H - 4}">${esc(fmtDay(points[0].day, { day: "numeric", month: "short" }))}</text><text x="${W - 6}" y="${H - 4}" text-anchor="end">${esc(fmtDay(points[points.length - 1].day, { day: "numeric", month: "short" }))}</text></svg>`;
  }
  async function paintProgress() {
    const body = $("#pgBody"); if (!body) return;
    let d; try { d = await api("/progress?days=" + S.progDays); } catch (e) { fail(e); return; }
    const t = d.targets || {}, a = d.averages || {};
    const parts = [...new Set(d.weekly_sets.flatMap((w) => Object.keys(w.parts)))].sort();
    const weeks = d.weekly_sets.slice(-6);
    const heatC = (n) => (n ? `color-mix(in srgb, var(--accent) ${clamp(Math.round((n / 20) * 100), 12, 100)}%, var(--surface-2))` : "var(--surface-2)");
    const wpts = (d.weight || []).map((x) => ({ day: x.day, v: x.weight_kg }));
    body.innerHTML = `<div class="card"><div class="mbig" style="padding-top:14px">
        <div><b>${num(a.kcal)}</b><span>avg kcal</span></div><div><b style="color:var(--p)">${num(a.protein_g)}</b><span>avg protein</span></div>
        <div><b>${num(a.workouts)}</b><span>workouts</span></div><div><b>${num(a.days_logged)}</b><span>days logged</span></div></div></div>
      <div class="card"><div class="card-h"><h3>Calories</h3><span class="muted small">days you logged</span></div><div class="card-b">${barsSvg(d.series, "kcal", "var(--accent)", t.kcal)}</div></div>
      <div class="card"><div class="card-h"><h3>Protein</h3><span class="muted small">grams</span></div><div class="card-b">${barsSvg(d.series, "protein_g", "var(--p)", t.protein_g)}</div></div>
      <div class="card"><div class="card-h"><h3>Calories burnt</h3><span class="muted small">workouts, estimated</span></div><div class="card-b">${barsSvg(d.series, "burnt", "var(--up)", null)}</div></div>
      <div class="card"><div class="card-h"><h3>Body weight</h3><button type="button" class="pill acc" id="pgW">Log weight</button></div><div class="card-b">${wpts.length >= 2 ? lineSvg(wpts, "var(--fb)") : `<div class="empty" style="padding:10px">Log your weight on two or more days to see the trend.</div>`}</div></div>
      <div class="card"><div class="card-h"><h3>Weekly sets by muscle</h3><span class="muted small">10 to 20 hard sets is a common target</span></div>
        ${parts.length ? `<div class="heat" style="--n:${weeks.length}"><div class="hr"><span></span>${weeks.map((w) => `<span class="small muted" style="text-align:center">${esc(fmtDay(w.week, { day: "numeric", month: "short" }))}</span>`).join("")}</div>
          ${parts.map((pt) => `<div class="hr"><span class="hl">${esc(pt)}</span>${weeks.map((w) => { const n = w.parts[pt] || 0; return `<span class="hc" style="background:${heatC(n)}${n >= 12 ? ";color:var(--accent-ink)" : ""}">${n || ""}</span>`; }).join("")}</div>`).join("")}</div>`
        : `<div class="empty" style="padding:6px 16px 18px">Finish a few workouts to see which muscles get enough volume.</div>`}</div>
      <div class="card"><div class="card-h"><h3>Personal bests</h3><span class="muted small">estimated 1-rep max</span></div>
        ${d.prs.length ? `<ul class="list">${d.prs.map((p) => `<li class="li" data-ex="${esc(p.exercise_id)}"><div class="t"><b>${esc(p.name)}</b><span>top set ${num(p.top_kg, 1)} kg</span></div><div class="r">${num(p.e1rm, 1)}<small>kg e1RM</small></div></li>`).join("")}</ul>` : `<div class="empty" style="padding:6px 16px 18px">Your best lifts appear here.</div>`}</div>
      <div class="card review"><div class="card-h"><h3>${ic("sparkle").replace("<svg", '<svg style="width:17px;height:17px;vertical-align:-3px;color:var(--accent)"')} Weekly review</h3><button type="button" class="pill acc" id="pgRev">Get review</button></div><div class="card-b" id="pgRevB"><p class="small muted">Gemini reads only your last 7 days of logs and suggests what to adjust.</p></div></div>`;
    $("#pgW", body).onclick = async () => { await logWeight(); paintProgress(); };
    $$("[data-ex]", body).forEach((li) => li.addEventListener("click", () => exerciseInfo(li.dataset.ex)));
    const rb = $("#pgRev", body);
    const review = async (refresh) => {
      rb.disabled = true; $("#pgRevB", body).innerHTML = `<span class="skel"></span><span class="skel" style="width:80%"></span><span class="skel"></span>`;
      try {
        const r = await api("/ai/review" + (refresh ? "?refresh=1" : ""));
        $("#pgRevB", body).innerHTML = r.text ? mdLite(r.text) + `<p class="small muted">Generated ${r.cached ? "earlier today" : "just now"}. AI suggestions, not medical advice.</p>` : `<p class="small muted">${esc(r.reason || "Nothing to review yet.")}</p>`;
        rb.textContent = "Refresh"; rb.onclick = () => review(true);
      } catch (e) { $("#pgRevB", body).innerHTML = `<p class="small muted">${esc(e.message)}</p>`; }
      rb.disabled = false;
    };
    rb.onclick = () => review(false);
  }

  // ------------------------------------------------------------------ ME
  RENDER.me = () => {
    const el = $("#scr-me"); const p = S.profile || {}, t = p.targets || {}, ov = p.overrides || {};
    const u = (S.me && S.me.user) || {};
    const theme = document.documentElement.dataset.theme || "light";
    const rest = store.get("fit_rest", 90);
    const fdb = S.foodDb || {};
    el.innerHTML = `<header class="head"><h1>Me</h1></header><div class="scroll">
      <div class="card"><div class="card-h"><div class="row"><span class="thumb" style="border-radius:50%;background:var(--accent-soft);color:var(--accent);font-weight:800">${esc((u.name || "?").slice(0, 1).toUpperCase())}</span><div><b style="font:700 17px var(--f-display)">${esc(u.name || "")}</b><div class="small muted">${esc(u.email || "")}</div></div></div></div>
        <div class="form" id="meForm">
          <div class="field full">Sex (for the calorie formula)<div class="seg" id="meSex" style="margin-top:4px"><button type="button" data-v="male" aria-pressed="${p.sex !== "female"}">Male</button><button type="button" data-v="female" aria-pressed="${p.sex === "female"}">Female</button></div></div>
          <label class="field">Age<input name="age" type="number" inputmode="numeric" value="${p.age ?? ""}"></label>
          <label class="field">Height (cm)<input name="height_cm" type="number" inputmode="decimal" value="${p.height_cm ?? ""}"></label>
          <label class="field">Weight (kg)<input name="weight_kg" type="number" inputmode="decimal" step="0.1" value="${p.weight_kg ?? ""}"></label>
          <label class="field">Goal<select name="goal">${GOALS.map(([v, l]) => `<option value="${v}" ${(p.goal || "maintain") === v ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>
          <label class="field full">Activity<select name="activity">${ACTIVITY.map(([v, l]) => `<option value="${v}" ${(p.activity || "moderate") === v ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>
        </div><div style="padding:0 16px 16px"><button type="button" class="btn primary block" id="meSave">Save profile</button></div></div>

      <div class="card"><div class="card-h"><h3>Daily targets</h3><span class="muted small">${t.tdee ? `BMR ${num(t.bmr)} · TDEE ${num(t.tdee)}` : "fill in your profile"}</span></div>
        <p class="small muted" style="margin:0;padding:0 16px">Calculated with Mifflin-St Jeor. Type a number to override, or clear it to go back to the calculated value.</p>
        <div class="form" id="meOv">${[["kcal", "Calories (kcal)"], ["protein_g", "Protein (g)"], ["carb_g", "Carbs (g)"], ["fat_g", "Fat (g)"], ["fibre_g", "Fibre (g)"], ["water_ml", "Water (ml)"]].map(([k, l]) => `<label class="field">${l}<input name="${k}" type="number" inputmode="numeric" value="${ov[k] ?? ""}" placeholder="${t[k] != null && !ov[k] ? num(t[k]).replace(/,/g, "") : ""}"></label>`).join("")}</div>
        <div style="padding:0 16px 16px"><button type="button" class="btn block" id="meOvSave">Save targets</button></div></div>

      <div class="card"><div class="card-h"><h3>Meal times</h3><button type="button" class="pill acc" id="meSlotAdd">Add</button></div>
        <ul class="list" id="meSlots">${S.slots.map((s) => `<li class="li" data-s="${s.id}" style="cursor:default"><input value="${esc(s.name)}" data-k="name" aria-label="Meal name" style="flex:1;min-width:0;border:0;background:none;font-weight:700;outline:0">
          <input type="time" value="${esc(s.time_hhmm || "")}" data-k="time" aria-label="Time" style="border:1px solid var(--line);border-radius:10px;background:var(--surface-2);height:34px;padding:0 6px">
          <button type="button" class="icon-btn" data-del aria-label="Delete" style="width:34px;height:34px">${ic("trash")}</button></li>`).join("")}</ul></div>

      <div class="card"><div class="card-h"><h3>Settings</h3></div><div class="card-b" style="display:grid;gap:12px">
        <div><div class="small muted" style="font-weight:700;margin-bottom:4px">Appearance</div><div class="seg" id="meTheme"><button type="button" data-v="light" aria-pressed="${theme !== "dark"}">Light</button><button type="button" data-v="dark" aria-pressed="${theme === "dark"}">Dark</button></div></div>
        <div><div class="small muted" style="font-weight:700;margin-bottom:4px">Rest timer after each set</div><div class="seg" id="meRest">${[0, 60, 90, 120, 180].map((n) => `<button type="button" data-v="${n}" aria-pressed="${rest === n}">${n ? (n >= 120 ? n / 60 + "m" : n + "s") : "Off"}</button>`).join("")}</div></div>
        <div class="small muted">Food database: ${num(fdb.usda_foods || 0)} USDA foods${fdb.state === "running" ? " (importing…)" : ""} plus 1,000+ Indian dishes from INDB.</div></div></div>

      <div class="card"><ul class="list">
        <li class="li" data-go="/terminal"><span class="thumb" style="color:var(--p)">${ic("chart")}</span><div class="t"><b>Switch to CA Trader</b><span>Markets, signals and orders</span></div>${ic("right")}</li>
        <li class="li" data-go="/select"><span class="thumb">${ic("swap")}</span><div class="t"><b>All apps</b></div>${ic("right")}</li>
        <li class="li" data-go="/logout"><span class="thumb" style="color:var(--dn)">${ic("x")}</span><div class="t"><b style="color:var(--dn)">Sign out</b></div></li></ul></div>
      <p class="small muted" style="padding:0 18px 10px">Exercises: free-exercise-db (public domain). Nutrition: INDB, USDA FoodData Central, Open Food Facts. Calorie and nutrient figures are estimates and not medical advice.</p>
    </div>`;
    let sex = p.sex || "male";
    $("#meSex", el).addEventListener("click", (e) => { const b = e.target.closest("[data-v]"); if (!b) return; sex = b.dataset.v; $$("#meSex button", el).forEach((x) => x.setAttribute("aria-pressed", x === b)); });
    $("#meSave", el).onclick = async () => {
      const v = { sex }; $$("#meForm input, #meForm select", el).forEach((i) => (v[i.name] = i.value === "" ? null : i.tagName === "SELECT" ? i.value : Number(i.value)));
      if (!v.age || !v.height_cm || !v.weight_kg) { toast("Fill in age, height and weight to calculate targets"); return; }
      try { const r = await put("/profile", v); S.profile = r.profile; S.dayData = null; toast("Profile saved. Targets updated."); RENDER.me(); } catch (e) { fail(e); }
    };
    $("#meOvSave", el).onclick = async () => {
      const ov2 = {}; $$("#meOv input", el).forEach((i) => { if (i.value !== "") ov2[i.name] = Number(i.value); });
      try { const r = await put("/profile", { overrides: ov2 }); S.profile = r.profile; S.dayData = null; toast("Targets saved"); RENDER.me(); } catch (e) { fail(e); }
    };
    $("#meSlots", el).addEventListener("change", async (e) => {
      const li = e.target.closest("[data-s]"); if (!li || !e.target.dataset.k) return;
      try { const r = await patch("/slots/" + li.dataset.s, { [e.target.dataset.k]: e.target.value }); S.slots = r.slots; S.dayData = null; toast("Saved", 1200); } catch (er) { fail(er); }
    });
    $("#meSlots", el).addEventListener("click", async (e) => {
      const b = e.target.closest("[data-del]"); if (!b) return; const li = b.closest("[data-s]");
      if (!(await confirmSheet("Delete this meal time?", li.querySelector("input").value))) return;
      try { const r = await del("/slots/" + li.dataset.s); S.slots = r.slots; S.dayData = null; RENDER.me(); } catch (er) { fail(er); }
    });
    $("#meSlotAdd", el).onclick = async () => { await addSlot(); RENDER.me(); };
    $("#meTheme", el).addEventListener("click", (e) => { const b = e.target.closest("[data-v]"); if (!b) return; document.documentElement.dataset.theme = b.dataset.v; store.set("cam_theme", b.dataset.v); RENDER.me(); });
    $("#meRest", el).addEventListener("click", (e) => { const b = e.target.closest("[data-v]"); if (!b) return; store.set("fit_rest", Number(b.dataset.v)); RENDER.me(); });
    $$("[data-go]", el).forEach((li) => li.addEventListener("click", () => { try { localStorage.setItem("ca_last_app", li.dataset.go === "/terminal" ? "trading" : "fitness"); } catch (e) {} location.href = li.dataset.go; }));
  };

  // ------------------------------------------------------------------ onboarding
  function onboarding(force) {
    if (!force && store.get("fit_onb_skip", false)) return;
    let sex = "male";
    const s = sheet(`<div class="sh-h"><div style="font-size:40px">💪</div><h2>Welcome to CA Fitness</h2><p>Tell us a little about you to get calorie and protein targets. You can change this any time under Me.</p></div>
      <div class="form" id="obF">
        <div class="field full">Sex (for the calorie formula)<div class="seg" id="obSex" style="margin-top:4px"><button type="button" data-v="male" aria-pressed="true">Male</button><button type="button" data-v="female" aria-pressed="false">Female</button></div></div>
        <label class="field">Age<input name="age" type="number" inputmode="numeric" placeholder="28"></label><label class="field">Height (cm)<input name="height_cm" type="number" inputmode="decimal" placeholder="172"></label>
        <label class="field">Weight (kg)<input name="weight_kg" type="number" inputmode="decimal" step="0.1" placeholder="72"></label>
        <label class="field">Goal<select name="goal">${GOALS.map(([v, l]) => `<option value="${v}" ${v === "maintain" ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label>
        <label class="field full">Activity<select name="activity">${ACTIVITY.map(([v, l]) => `<option value="${v}" ${v === "moderate" ? "selected" : ""}>${esc(l)}</option>`).join("")}</select></label></div>
      <div class="sh-f"><button type="button" class="btn primary block" id="obOk">Get my targets</button><button type="button" class="btn block" id="obSkip">Skip for now</button></div>`);
    $("#obSex", s.el).addEventListener("click", (e) => { const b = e.target.closest("[data-v]"); if (!b) return; sex = b.dataset.v; $$("#obSex button", s.el).forEach((x) => x.setAttribute("aria-pressed", x === b)); });
    $("#obSkip", s.el).onclick = () => { store.set("fit_onb_skip", true); s.close(); };
    $("#obOk", s.el).onclick = async () => {
      const v = { sex }; $$("#obF input, #obF select", s.el).forEach((i) => (v[i.name] = i.value === "" ? null : i.tagName === "SELECT" ? i.value : Number(i.value)));
      if (!v.age || !v.height_cm || !v.weight_kg) { toast("Fill in age, height and weight"); return; }
      try {
        const r = await put("/profile", v); S.profile = r.profile; s.close();
        toast(`Your target: ${num(r.profile.targets.kcal)} kcal and ${num(r.profile.targets.protein_g)} g protein a day`, 4000);
        S.dayData = null; if (S.tab === "today") RENDER.today();
      } catch (e) { fail(e); }
    };
  }

  // ------------------------------------------------------------------ public shared workout
  async function renderPublic() {
    $("#tabbar").hidden = true;
    const el = $("#scr-today");
    el.innerHTML = `<header class="head"><h1>Shared workout</h1></header><div class="scroll public" id="pubB" style="padding-bottom:30px"><div class="card card-b"><span class="skel"></span><span class="skel"></span></div></div>`;
    const b = $("#pubB");
    try {
      const r = await api("/public/workout/" + encodeURIComponent(PUBLIC)); const w = r.workout;
      b.innerHTML = `<div class="card"><div class="card-h"><div><h3 style="font-size:20px">${esc(w.name || "Workout")}</h3><div class="small muted">by ${esc(r.by)} · ${esc(fmtDay(w.day, { weekday: "long", day: "numeric", month: "long" }))}</div></div></div>
        <div class="stats3"><div><b>${w.duration_min ? mins(w.duration_min) : "–"}</b><span>Duration</span></div><div><b>${num(w.volume_kg)}</b><span>Volume kg</span></div><div><b>${num(w.kcal)}</b><span>kcal (est.)</span></div></div></div>
        ${w.entries.map((e) => `<div class="entry"><div class="entry-h">${exThumb(e)}<div class="grow"><b>${esc(e.name)}</b><span>${esc(e.part || "")}</span></div></div>
          <table class="sets"><tbody>${e.sets.map((s, i) => `<tr><td class="prev">${i + 1}</td><td><b>${s.minutes ? num(s.minutes, 1) + " min" + (s.distance_km ? " · " + num(s.distance_km, 2) + " km" : "") : (s.weight_kg ? num(s.weight_kg, 1) + " kg × " : "") + num(s.reps) + " reps"}</b></td></tr>`).join("")}</tbody></table><div style="height:8px"></div></div>`).join("")}
        <div style="padding:10px 14px"><a class="btn primary block" href="/fitnesstracker">Track your own workouts</a></div>`;
    } catch (e) { b.innerHTML = `<div class="empty"><b>Not available</b>${esc(e.message)}</div><div style="padding:10px 14px"><a class="btn primary block" href="/fitnesstracker">Open CA Fitness</a></div>`; }
  }

  // ------------------------------------------------------------------ boot
  async function boot() {
    if (PUBLIC) { renderPublic(); return; }
    try {
      const me = await api("/me");
      S.me = me; S.profile = me.profile; S.slots = me.slots; S.foodDb = me.food_db;
      try { localStorage.setItem("ca_last_app", "fitness"); } catch (e) {}
      api("/workouts?days=2").then((w) => { if (w.active_id && w.active_id !== S.activeId) { S.activeId = w.active_id; if (S.tab === "today") paintToday(); } }).catch(() => {});
    } catch (e) { fail(e); }
    const t = store.get("fit_tab", "today");
    setTab(RENDER[t] ? t : "today");
    if (S.profile && !S.profile.onboarded) setTimeout(() => onboarding(false), 500);
  }
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && !PUBLIC && S.day !== today() && S.tab === "today" && !stack.length) { S.day = today(); RENDER.today(); }
  });
  boot();
})();
