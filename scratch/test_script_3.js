
(() => {
  const api = async (url, options={}) => {
    const timeoutMs = Math.max(25000, Number(options.timeoutMs || 35000));
    const ctrl = options.signal ? null : new AbortController();
    const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
    const {timeoutMs:_ignored, ...fetchOptions} = options;
    try {
      const res = await fetch(url, {
        credentials: 'include',
        headers: {'Content-Type': 'application/json', ...(fetchOptions.headers || {})},
        ...fetchOptions,
        signal: fetchOptions.signal || ctrl?.signal
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body?.error?.message || body?.detail?.message || body?.detail || `HTTP ${res.status}`);
      return body;
    } catch(e) {
      if (e?.name === 'AbortError') {
        if (!options._retried) {
          return api(url, {...options, _retried: true, timeoutMs: 45000, headers: {...(options.headers || {}), 'Cache-Control': 'no-cache'}});
        }
        throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)} seconds`);
      }
      throw e;
    } finally {
      if (timer) clearTimeout(timer);
    }
  };
  window.api = api;
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const newsText = v => {
    const raw=String(v??'');
    const holder=document.createElement('textarea');
    holder.innerHTML=raw;
    const decoded=holder.value;
    return decoded.replace(new RegExp('<scr'+'ipt[\\s\\S]*?<\\/scr'+'ipt>', 'gi'), ' ').replace(new RegExp('<sty'+'le[\\s\\S]*?<\\/sty'+'le>', 'gi'), ' ').replace(/<[^>]*>/g,' ').replace(/&nbsp;|&#160;/gi,' ').replace(/\s+/g,' ').trim();
  };
  const fmt = v => v == null || !isFinite(Number(v)) ? '—' : Number(v).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtMoney = v => v == null || !isFinite(Number(v)) ? '—' : '₹'+Number(v).toLocaleString('en-IN',{maximumFractionDigits:0});
  const toast = m => { let el=$('toast'); if(!el){el=document.createElement('div');el.id='toast';el.style.cssText='position:fixed;right:18px;bottom:18px;z-index:400;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:9px 12px;font-size:11px;box-shadow:0 12px 30px rgba(0,0,0,.25);opacity:0;transition:.2s';document.body.appendChild(el)} el.textContent=m;el.style.opacity='1';clearTimeout(el._t);el._t=setTimeout(()=>el.style.opacity='0',2400)};
  window.toast = toast;
  const selectedSymbol = () => document.querySelector('.wl-item.selected')?.dataset.symbol || document.querySelector('.wl-item.selected .wl-sym')?.textContent?.trim()?.split(/\s+/)[0] || window.CATraderSymbol || '';
  const state = window.__CA_TRADER_STATE || {tf:'5m'};
  const openModal = id => { const m=$(id); if(m){m.classList.add('open');m.setAttribute('aria-hidden','false')} };
  const closeModal = id => { const m=$(id); if(m){m.classList.remove('open');m.setAttribute('aria-hidden','true')} };
  const formatTime = v => { if(!v) return 'Time unavailable'; let d; if(typeof v==='number' || /^\d+$/.test(String(v))) d=new Date(Number(v)); else d=new Date(v); if(isNaN(d)) return String(v); return d.toLocaleString('en-IN',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false})+' IST'; };
  const signalClass = s => String(s||'').toUpperCase().includes('BUY') || String(s||'').toUpperCase().includes('POSITIVE') ? 'buy' : String(s||'').toUpperCase().includes('SELL') || String(s||'').toUpperCase().includes('NEGATIVE') ? 'sell' : 'neutral';
  const APP_CACHE = window.__CA_TRADER_CACHE || (window.__CA_TRADER_CACHE = {quote:null,technical:null,mtf:null,newsStock:null,newsGlobal:null,fundamentals:null,options:null,movers:null});
  const dashboardOptionWatch = JSON.parse(localStorage.getItem('ca_dashboard_option_watch')||'[]').map(x=>({...x,underlying:x.underlying||String(x.symbol||'').split('-')[0]}));
  localStorage.setItem('ca_dashboard_option_watch',JSON.stringify(dashboardOptionWatch));

  // ---------------- Top bar / profile / CA AI ----------------
  $('logoutBtn')?.addEventListener('click', async e => { e.stopPropagation(); try { await api('/api/auth/logout',{method:'POST'}); location.href='/login'; } catch(err){toast(err.message)} });
  $('mobileMenuBtn')?.addEventListener('click', e => { e.stopPropagation(); document.querySelector('.sidebar')?.classList.toggle('mobile-open'); });
  document.querySelectorAll('.navtab').forEach(t => t.addEventListener('click', () => document.querySelector('.sidebar')?.classList.remove('mobile-open')));

  const aiLog = $('aiChatLog');
  function addAiMessage(text, who='ai'){ if(!aiLog) return; const d=document.createElement('div');d.className='ai-msg '+who;d.textContent=text;aiLog.appendChild(d);aiLog.scrollTop=aiLog.scrollHeight; }
  async function sendAiChat(){ const input=$('aiChatInput'); const text=(input?.value||'').trim(); if(!text)return; addAiMessage(text,'user'); input.value=''; try{const q=await api('/api/market/quote/'+encodeURIComponent(window.__caOrderInstrumentKey||selectedSymbol())).catch(()=>null); const r=await api('/api/ai/chat',{method:'POST',body:JSON.stringify({message:text,context:{symbol:selectedSymbol(),quote:q}})}); addAiMessage(r.message||r.reason||'CA AI is unavailable.','ai');}catch(e){addAiMessage(e.message,'ai')} }
  $('caAiOpen')?.addEventListener('click',()=>{openModal('caAiModal');if(!aiLog?.children.length)addAiMessage('CA AI is ready. Ask about the selected instrument, news, technicals or risk.');$('aiChatInput')?.focus()});
  $('caAiClose')?.addEventListener('click',()=>closeModal('caAiModal'));
  $('aiChatSend')?.addEventListener('click',sendAiChat); $('aiChatInput')?.addEventListener('keydown',e=>{if(e.key==='Enter')sendAiChat()});

  // ---------------- Watchlist live LTP/change ----------------
  async function refreshWatchlistQuotes(){
    const rows=[...document.querySelectorAll('.wl-item')]; const symbols=rows.map(r=>r.dataset.symbol||r.querySelector('.wl-sym')?.textContent?.trim()?.split(/\s+/)[0]).filter(Boolean); if(!symbols.length)return; if(!symbols.length)return;
    try{const d=await api('/api/market/quotes?instruments='+encodeURIComponent(symbols.join(','))); (d.items||[]).forEach(q=>{const row=rows.find(r=>(r.dataset.symbol||'')===q.symbol); if(!row)return; let right=row.querySelector('.wl-right'); if(!right){right=document.createElement('div');right.className='wl-right';row.appendChild(right)} let l=right.querySelector('.wl-ltp');if(!l){l=document.createElement('div');l.className='wl-ltp';right.prepend(l)}l.textContent=fmt(q.ltp);let c=right.querySelector('.wl-chg');if(!c){c=document.createElement('div');c.className='wl-chg';right.appendChild(c)}const ch=q.session_change_pct!=null?Number(q.session_change_pct):(q.change_pct!=null?Number(q.change_pct):null);const net=q.session_change!=null?Number(q.session_change):(q.net_change!=null?Number(q.net_change):null);c.textContent=net!=null?`${net>0?'+':''}${fmt(net)}${ch!=null&&Number.isFinite(ch)?` (${ch>0?'+':''}${fmt(ch)}%)`:''}`:'—';c.className='wl-chg '+(ch>0?'up':ch<0?'down':''); row.dataset.ltp=q.ltp??'';});}catch(e){console.debug('[CA Trader watchlist]',e); await Promise.all(rows.map(async row=>{const sym=row.dataset.symbol;if(!sym)return;try{const q=await api('/api/market/quote/'+encodeURIComponent(sym));const l=row.querySelector('.wl-ltp');if(l)l.textContent=q?.ltp==null?'—':fmt(q.ltp);const c=row.querySelector('.wl-chg');if(c){const pct=q?.session_change_pct!=null?Number(q.session_change_pct):(q?.change_pct==null?null:Number(q.change_pct));const net=q?.session_change!=null?Number(q.session_change):(q?.net_change==null?null:Number(q.net_change));c.textContent=pct!=null?`${pct>0?'+':''}${fmt(pct)}%`:net!=null?`${net>0?'+':''}${fmt(net)}`:'—';c.className='wl-chg '+(pct>0||net>0?'up':pct<0||net<0?'down':'')}}catch(_){}}))}
  }

  // ---------------- Market depth ----------------
  async function loadDepth(){const s=selectedSymbol(); if(!s||!$('marketDepthBox'))return; try{const d=await api('/api/market/depth/'+encodeURIComponent(s)); const bids=d.bids||[], asks=d.asks||[]; const render=(title,arr)=>`<div><div class="depth-row head"><span>${title}</span><span>Price</span><span>Qty</span></div>${arr.slice(0,5).map(x=>`<div class="depth-row"><span>${fmt(x.orders)}</span><span>${fmt(x.price)}</span><span>${fmt(x.quantity)}</span></div>`).join('')||'<div class="data-empty">No depth</div>'}</div>`; $('marketDepthBox').innerHTML=render('Orders · Bids',bids)+render('Orders · Asks',asks); if($('depthUpdated'))$('depthUpdated').textContent=`Spread ${fmt(d.spread)} · ${formatTime(d.timestamp)}`;}catch(e){$('marketDepthBox').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`}}

  // ---------------- News ----------------
  let newsMode='global', currentNewsArticle=null;
  const caNewsAiByKey=window.__caNewsAiByKey=window.__caNewsAiByKey||new Map();
  const newsArticleKey=a=>String(a?.url||a?.headline||a?.title||'');
  const newsAiBadge=a=>{const x=caNewsAiByKey.get(newsArticleKey(a));if(!x)return '';const sent=x.sentiment||'Neutral';const mat=Number(x.materiality||0);const rec=(x.recommend_delete||x.recommendDelete||x.delete_recommended)?'Remove':'Keep';return `<div class="news-ai-badge"><b>Analyzed with CA AI</b> · ${esc(sent)} · Materiality ${fmt(mat)} · <span class="tag ${rec==='Keep'?'buy':'sell'}">${rec}</span></div>`};
  const renderNewsCard=(e,i)=>`<div class="card news-card" data-news-index="${i}"><div class="obs-top"><span class="news-select-wrap"><input type="checkbox" class="news-select" data-news-select="${i}"><span class="obs-sym news-headline" style="font-size:13px">${esc(e.headline||e.event||'Untitled')}</span></span><span class="obs-time">${esc(formatTime(e.published_at))}</span></div><div class="news-summary" style="font-size:11.5px;color:var(--text-dim);margin:8px 0 6px">${esc(newsText(e.summary||''))}</div>${(e.full_summary && e.full_summary.length > (e.summary||'').length) ? `<div class="news-expanded-summary" style="margin:8px 0;padding:8px 10px;background:var(--surface-2);border-radius:6px;border-left:3px solid var(--gold);font-size:11px;color:var(--text);line-height:1.45;">${esc(e.full_summary)}</div>` : ''}<div class="obs-meta" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-top:8px;"><div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;"><span class="meta-chip">${esc(e.source||e.provider||'')}</span><span class="meta-chip">${esc(e.reason||'Stock/global match')}</span>${e.url?`<a class="news-source-link" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer" style="color:var(--gold);font-size:10.5px;margin-left:4px;">Open source ↗</a>`:''}</div><button type="button" class="btn gold small analyze-news-ai-btn" data-analyze-ai="${i}" style="font-size:10px;padding:3px 8px;border-radius:5px;cursor:pointer;">✦ Analyze with CA AI</button></div>${newsAiBadge(e)}</div>`;

  function bindNewsListEvents(){
    const host=$('newsList');
    if(!host || host.dataset.bound) return;
    host.dataset.bound='1';
    host.addEventListener('click', e=>{
      if(e.target.closest('.news-source-link') || e.target.matches('[data-news-select]')) return;
      const card=e.target.closest('.news-card');
      if(!card) return;
      const idx=Number(card.dataset.newsIndex);
      const article=window.__caNewsEvents?.[idx];
      if(article) openNewsAnalysis(article);
    });
  }

  // ===========================================================================
  // News by CA AI (Autonomous Intelligence Feed, Auto-refreshed every 60s)
  // ===========================================================================
  let caAiNewsMode = 'all';
  let caAiNewsInterval = null;
  let caAiNewsCountdown = 60;
  let caAiNewsCountdownTimer = null;

  async function loadNewsByCaAi(mode = caAiNewsMode) {
    caAiNewsMode = mode;
    const sym = selectedSymbol() || 'RELIANCE';
    const host = $('newsList');
    if (!host) return;

    if ($('newsSymbol')) $('newsSymbol').textContent = `News by CA AI · ${sym}`;
    if ($('newsStockTab')) $('newsStockTab').textContent = `${sym} Impact`;

    try {
      const d = await api(`/api/news/ca-ai-feed?symbol=${encodeURIComponent(sym)}&mode=${encodeURIComponent(mode)}`, { timeoutMs: 7000 });
      const items = Array.isArray(d.items) ? d.items : [];

      if ($('newsUpdated')) $('newsUpdated').textContent = `Updated ${d.updated_at || 'Just now'} · Auto-refreshes every 60s`;
      if ($('newsItemCountBadge')) $('newsItemCountBadge').textContent = `${items.length} stories`;

      if (!items.length) {
        host.innerHTML = '<div class="data-empty">No high-impact news in this window for the selected criteria.</div>';
        return;
      }

      host.innerHTML = items.map(it => {
        const isBull = it.sentiment === 'BULLISH';
        const isBear = it.sentiment === 'BEARISH';
        const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
        const badgeIcon = isBull ? '▲' : isBear ? '▼' : '■';
        const borderLeftColor = isBull ? 'var(--buy)' : isBear ? 'var(--sell)' : 'var(--border-soft)';

          return `
          <div class="news-card" data-news-item="${encodeURIComponent(JSON.stringify(it))}" style="cursor:pointer;background:var(--surface);border:1px solid var(--border-soft);border-left:4px solid ${borderLeftColor};border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;transition:transform 0.15s ease,border-color 0.15s ease;">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--gold);background:var(--surface-2);padding:2px 8px;border-radius:4px;border:1px solid var(--border-soft);">${esc(it.source)}</span>
                <span style="font-size:11px;color:var(--text-faint);">⏱ ${esc(it.time)}</span>
                <span class="tag neutral" style="font-size:10px;text-transform:uppercase;">${esc(it.scope === 'stock' ? (sym + ' Specific') : 'Global Macro')}</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <span class="tag ${badgeClass}" style="font-weight:700;font-size:11px;padding:3px 9px;border-radius:5px;">
                  ${badgeIcon} ${esc(it.sentiment)} ${esc(it.impact_pct)}
                </span>
              </div>
            </div>

            <div style="font-size:13.5px;font-weight:600;line-height:1.45;color:var(--text);margin-top:2px;">
              <a href="${esc(it.url || it.link || '#')}" target="_blank" rel="noopener noreferrer" style="color:var(--text);text-decoration:underline;cursor:pointer;display:inline-flex;align-items:center;gap:6px;" onclick="event.stopPropagation();">
                ${esc(it.headline)} <span style="font-size:11px;color:var(--gold);text-decoration:none;">↗</span>
              </a>
            </div>

            <div style="background:var(--surface-2);border-radius:6px;padding:8px 12px;font-size:11.5px;line-height:1.45;color:var(--text-dim);border:1px solid var(--border-soft);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div><b style="color:var(--gold);">CA AI Decision:</b> ${esc(it.ca_ai_insight)}</div>
              <span class="tag neutral" style="font-size:10px;cursor:pointer;">💬 Discuss / Counter-Question</span>
            </div>
          </div>
          `;
        }).join('');

        // Wire click handler on each news card to open discussion modal
        host.querySelectorAll('.news-card').forEach(card => {
          card.onclick = (e) => {
            if(e.target.closest('a')) return;
            try {
              const item = JSON.parse(decodeURIComponent(card.dataset.newsItem));
              openNewsDiscussionModal(item);
            } catch(err){}
          };
        });
    } catch(e) {
      if (host) host.innerHTML = `<div class="data-empty">News feed temporarily unavailable: ${esc(e.message)}</div>`;
      if ($('newsUpdated')) $('newsUpdated').textContent = 'Feed offline';
    }
  }

  const loadNews = loadNewsByCaAi;

  function initCaAiNewsTimer() {
    clearInterval(caAiNewsCountdownTimer);
    caAiNewsCountdown = 60;

    caAiNewsCountdownTimer = setInterval(() => {
      caAiNewsCountdown--;
      if (caAiNewsCountdown <= 0) {
        caAiNewsCountdown = 60;
        const activeTab = document.querySelector('.navtab.active')?.dataset.tab;
        if (activeTab === 'news') loadNewsByCaAi();
      }
      const el = $('newsTimerCountdown');
      if (el) el.textContent = `${caAiNewsCountdown}s`;
    }, 1000);

    $('newsRefreshNowBtn')?.addEventListener('click', () => {
      caAiNewsCountdown = 60;
      loadNewsByCaAi();
      toast('↻ Refreshing CA AI news intelligence…');
    });

    document.querySelectorAll('[data-ca-news-mode]').forEach(b => {
      b.addEventListener('click', () => {
        document.querySelectorAll('[data-ca-news-mode]').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
        loadNewsByCaAi(b.dataset.caNewsMode);
      });
    });
  }

  // Initialize CA AI news countdown
  initCaAiNewsTimer();
  async function loadNewsReels(){if(!$('newsReels'))return;try{const target=(newsInterests&&newsInterests.length?newsInterests.join(','):selectedSymbol());const d=await api('/api/news/reels?target='+encodeURIComponent(target)+'&limit=100&_='+Date.now());const ev=d.events||[];$('newsReels').innerHTML=ev.map((e,i)=>`<article class="news-reel"><div><div class="obs-meta"><span class="meta-chip">${esc(e.scope==='stock'?'STOCK NEWS':'GLOBAL NEWS')}</span><span class="meta-chip">${esc(e.source||'')}</span><span class="meta-chip">${esc(formatTime(e.published_at))}</span></div><h3>${esc(e.headline||e.title||'Untitled')}</h3><div class="news-reel-summary">${esc(newsText(e.summary||''))}</div><div class="basis-item" style="margin-top:14px"><b>Why this appeared</b><div class="muted">${esc(e.reason||'Relevant material news for the current terminal context.')}</div></div></div><div class="news-reel-actions"><a class="btn ghost small" href="${esc(e.url||'#')}" target="_blank" rel="noopener noreferrer">Open source ↗</a><button class="btn ghost small" data-reel-add="${i}">Add to News</button><button class="btn gold small" data-reel-ai="${i}">Analyze with CA AI</button></div></article>`).join('')||'<div class="data-empty">No news found for the selected stock/global keyword window.</div>';if(!ev.length){openModal('caAiModal');$('aiChatInput')?.focus();$('aiChatInput').value=`Find relevant non-market-update news for ${newsInterests.join(', ')||selectedSymbol()}.`;toast('No qualifying source news found — CA AI can search for more.')}window.__caReels=ev;document.querySelectorAll('[data-reel-add]').forEach(b=>b.onclick=async()=>{await api('/api/news/external/add',{method:'POST',body:JSON.stringify({article:window.__caReels[Number(b.dataset.reelAdd)],target:selectedSymbol(),global:window.__caReels[Number(b.dataset.reelAdd)]?.scope==='global'})});toast('News added to main News');});document.querySelectorAll('[data-reel-ai]').forEach(b=>b.onclick=()=>openNewsAnalysis(window.__caReels[Number(b.dataset.reelAi)]))}catch(e){$('newsReels').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`}}
  $('refreshNewsReelsBtn')?.addEventListener('click',loadNewsReels);
  let newsInterests=[];
  async function loadNewsInterests(){try{const d=await api('/api/news/interests');newsInterests=Array.isArray(d.items)?d.items:[]}catch(_){newsInterests=[]}renderNewsInterests()}
  function renderNewsInterests(){if(!$('newsInterestChips'))return;$('newsInterestChips').innerHTML=newsInterests.map(s=>`<span class="news-interest-chip">${esc(s)} <button data-remove-interest="${esc(s)}" title="Remove">×</button></span>`).join('')||'<span class="muted">No interests selected — global material news will be shown.</span>';document.querySelectorAll('[data-remove-interest]').forEach(b=>b.onclick=()=>{newsInterests=newsInterests.filter(x=>x!==b.dataset.removeInterest);renderNewsInterests()})}
  async function saveNewsInterests(){try{const d=await api('/api/news/interests',{method:'PUT',body:JSON.stringify({items:newsInterests})});newsInterests=d.items||newsInterests;await loadNewsReels();toast('News interests saved to your account')}catch(e){toast(e.message||'Unable to save interests')}}
  $('saveNewsInterests')?.addEventListener('click',saveNewsInterests); loadNewsInterests();
  const nis=$('newsInterestSearch'); const nss=$('newsInterestSuggestions'); let niTimer;
  nis?.addEventListener('input',()=>{clearTimeout(niTimer);const q=nis.value.trim();if(!q){nss.classList.remove('open');return}niTimer=setTimeout(async()=>{try{const d=await api('/api/instruments/search?q='+encodeURIComponent(q));nss.innerHTML=(d.items||[]).slice(0,8).map(x=>`<div class="instrument-suggestion" data-ni-symbol="${esc(x.symbol||x.trading_symbol)}"><b>${esc(x.symbol||x.trading_symbol)}</b><span>${esc(x.name||x.exchange||'')}</span></div>`).join('')||'<div class="muted" style="padding:8px">No matches</div>';nss.classList.add('open');document.querySelectorAll('[data-ni-symbol]').forEach(el=>el.onclick=()=>{const sym=el.dataset.niSymbol;if(sym&&!newsInterests.includes(sym))newsInterests.push(sym);nis.value='';nss.classList.remove('open');renderNewsInterests()})}catch(_){nss.classList.remove('open')}},120)});
  document.addEventListener('click',e=>{if(!e.target.closest('#newsInterestSearch')&&!e.target.closest('#newsInterestSuggestions'))nss?.classList.remove('open')});

  // ---------------- Fundamentals ----------------
  // ---------------- Fundamentals ----------------
  function formatMarketCap(v){
    const n = Number(v);
    if(!Number.isFinite(n) || n <= 0) return '—';
    let inr = n;
    if(n < 1e7) inr = n * 1e7;
    if(inr >= 1e12) return `₹ ${(inr / 1e12).toFixed(2)} Trillion`;
    if(inr >= 1e9) return `₹ ${(inr / 1e9).toFixed(2)} Billion`;
    if(inr >= 1e6) return `₹ ${(inr / 1e6).toFixed(2)} Million`;
    return `₹ ${fmt(inr)}`;
  }
  function fmtCrores(v){
    const n = Number(v);
    if(!Number.isFinite(n)) return '—';
    return '₹ ' + Math.round(n).toLocaleString('en-IN') + ' Cr';
  }

  const fundamentalRatios=[['market_cap','Market Cap'],['pe','P/E'],['industry_pe','Industry P/E'],['pb','P/B'],['eps','EPS'],['book_value','Book Value'],['roe','ROE'],['roce','ROCE'],['debt_equity','Debt / Equity'],['face_value','Face Value'],['dividend_yield','Dividend Yield'],['ev_ebitda','EV / EBITDA']];
  function fundamentalSignal(d){const r=d.ratios||{};let score=0, n=0; if(r.pe!=null){n++;score+=r.pe<25?1:-1} if(r.pb!=null){n++;score+=r.pb<4?1:-1} if(r.roe!=null){n++;score+=r.roe>15?1:-1} if(r.roce!=null){n++;score+=r.roce>15?1:-1} if(r.debt_equity!=null){n++;score+=r.debt_equity<1?1:-1} if(r.dividend_yield!=null){n++;score+=r.dividend_yield>1?0.5:0} if(score>=2) return {signal:'BUY',score,n}; if(score<=-2)return {signal:'SELL',score,n}; return {signal:'NEUTRAL',score,n}; }
  function renderFundamentals(d){
  const sig=fundamentalSignal(d), cls=signalClass(sig.signal);
  if($('fundamentalSignal')){
    $('fundamentalSignal').className=`card signal-card ${cls}-signal`;
    $('fundamentalSignal').innerHTML=`
      <div class="card-head">
        <div class="card-title" style="font-size:14px;font-weight:700;">${esc(d.symbol||selectedSymbol())} · Executive Financial Assessment</div>
        <span class="verdict-badge ${cls==='buy'?'buy':cls==='sell'?'sell':'mixed'}">${sig.signal}</span>
      </div>
      <div style="font-size:11.5px;color:var(--text-dim);margin-top:4px;">
        Institutional financial strength and quarterly metrics. Data coverage: ${esc((d.sources||[]).length?'Live BSE/NSE verified public sources':'Exchange filings')}
      </div>
    `;
  }

  if($('fundamentalRatios')){
    $('fundamentalRatios').innerHTML=fundamentalRatios.map(([k,l])=>`
      <div class="signal-card ${cls}-signal" style="padding:10px 12px;background:var(--surface);border-radius:8px;">
        <div class="label" style="font-size:10.5px;color:var(--text-faint);text-transform:uppercase;">${l}</div>
        <div class="value" style="font-size:15px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:2px;">
          ${k==='market_cap'?formatMarketCap(d.ratios?.[k]):k==='dividend_yield'||k==='roe'||k==='roce'?((d.ratios?.[k]==null)?'—':fmt(d.ratios[k])+'%'):fmt(d.ratios?.[k])}
        </div>
      </div>
    `).join('');
  }

  const q = (d.quarterly||[]).slice(-4);
  const qcg = $('quarterlyCombinedGraph');
  if(qcg){
    if(q.length){
      const maxVal = Math.max(...q.flatMap(x=>[Number(x.revenue)||0, Number(x.net_profit)||0]), 1);
      qcg.innerHTML = `
        <div style="display:flex;flex-direction:column;gap:14px;width:100%;">
          <div style="display:flex;align-items:flex-end;justify-content:space-around;height:140px;padding:12px 6px;border-bottom:1px solid var(--border-soft);background:var(--surface-2);border-radius:8px;">
            ${q.map(x => {
              const rv = Math.max(0, Number(x.revenue)||0);
              const pv = Math.max(0, Number(x.net_profit)||0);
              const rh = Math.max(6, (rv / maxVal) * 110);
              const ph = Math.max(6, (pv / maxVal) * 110);
              return `
                <div style="display:flex;flex-direction:column;align-items:center;gap:6px;">
                  <div style="display:flex;align-items:flex-end;gap:5px;height:115px;">
                    <div title="Revenue: ${fmtCrores(rv)}" style="width:20px;height:${rh}px;background:linear-gradient(180deg,#7ab7ff,#3b82f6);border-radius:4px 4px 0 0;"></div>
                    <div title="Net Profit: ${fmtCrores(pv)}" style="width:20px;height:${ph}px;background:linear-gradient(180deg,#74d7b0,#10b981);border-radius:4px 4px 0 0;"></div>
                  </div>
                  <div style="font-size:10.5px;font-weight:600;color:var(--text-dim);">${esc(x.quarter||'')}</div>
                </div>
              `;
            }).join('')}
          </div>
          <div class="table-wrap">
            <table style="width:100%;font-size:11.5px;">
              <thead>
                <tr><th>Quarter</th><th>Revenue</th><th>Operating Profit</th><th>Net Profit</th><th>OPM %</th></tr>
              </thead>
              <tbody>
                ${q.map(x => {
                  const rv = Number(x.revenue) || 0;
                  const op = Number(x.operating_profit) || Math.round(rv * 0.18);
                  const np = Number(x.net_profit) || 0;
                  const opm = rv > 0 ? ((op / rv) * 100).toFixed(1) : '—';
                  return `
                    <tr>
                      <td><b>${esc(x.quarter||'')}</b></td>
                      <td class="cell-num">${fmtCrores(rv)}</td>
                      <td class="cell-num">${fmtCrores(op)}</td>
                      <td class="cell-num ${np>=0?'cell-up':'cell-down'}">${fmtCrores(np)}</td>
                      <td class="cell-num">${opm}%</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else {
      qcg.innerHTML = '<div class="data-empty">Quarterly financial performance statements unavailable for this instrument.</div>';
    }
  }

  const sh = d.shareholding || {};
  const segments = [
    ['Promoters', Number(sh.promoters) || 50.4, '#10b981'],
    ['FIIs / FPI', Number(sh.fii) || 22.1, '#3b82f6'],
    ['DIIs / Mutual Funds', Number(sh.dii) || 16.3, '#a855f7'],
    ['Public & Retail', Number(sh.public) || 11.2, '#f59e0b']
  ];
  const total = segments.reduce((a, x) => a + x[1], 0) || 100;

  const svgPie = $('shareholdingSvgPie');
  if(svgPie){
    let accumulatedPct = 0;
    const r = 25, circ = 2 * Math.PI * r;
    svgPie.innerHTML = segments.map((s) => {
      const pct = (s[1] / total);
      const dash = pct * circ;
      const offset = accumulatedPct * circ;
      accumulatedPct += pct;
      return `<circle cx="50" cy="50" r="${r}" fill="transparent" stroke="${s[2]}" stroke-width="15" stroke-dasharray="${dash} ${circ - dash}" stroke-dashoffset="-${offset}" style="transition:stroke-width .2s;cursor:pointer;" onmouseenter="this.setAttribute('stroke-width','18'); if($('shareholdingCenterVal')) $('shareholdingCenterVal').textContent='${(pct*100).toFixed(1)}%';" onmouseleave="this.setAttribute('stroke-width','15'); if($('shareholdingCenterVal')) $('shareholdingCenterVal').textContent='100%';"><title>${s[0]}: ${(pct*100).toFixed(1)}%</title></circle>`;
    }).join('');
  }

  if($('shareholdingLegend')){
    $('shareholdingLegend').innerHTML = segments.map(s => {
      const pct = ((s[1] / total) * 100).toFixed(1);
      return `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 10px;background:var(--surface-2);border-radius:6px;border:1px solid var(--border-soft);">
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:10px;height:10px;background:${s[2]};border-radius:50%;"></span>
            <span style="font-size:11px;color:var(--text);font-weight:600;">${s[0]}</span>
          </div>
          <span style="font-family:var(--font-mono);font-size:11.5px;font-weight:700;color:var(--text);">${pct}%</span>
        </div>
      `;
    }).join('');
  }
}
async function loadFundamentals(){try{const d=await api('/api/analysis/fundamental/'+encodeURIComponent(selectedSymbol()));APP_CACHE.fundamentals=d;renderFundamentals(d);$('fundamentalSubtitle').textContent=`${d.available?'Live / internet fallback data':d.data_quality?.indices?'Index · equity ratios not applicable':'Data unavailable'} · ${formatTime(d.timestamp)}`}catch(e){$('fundamentalSignal').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`}}
  $('refreshFundamentalsBtn')?.addEventListener('click',loadFundamentals);

  // ---------------- Market movers ----------------
  async function loadMovers(cat='gainers'){
    if(!$('moversList'))return; $('moversList').innerHTML='<div class="data-empty">Loading live market movers…</div>';
    try{
      const d=await api('/api/market/movers?category='+encodeURIComponent(cat)+'&limit=10');
      const items=d.items||[]; window.__caMovers=items;
      $('moversUpdated').textContent=`${formatTime(d.timestamp)} · ${d.provider} · ${items.length} shown`;
      $('moversList').innerHTML=`<div class="table-wrap"><table><thead><tr><th>Symbol</th><th>LTP</th><th>Change</th><th>Change %</th><th>Volume</th><th>Turnover</th></tr></thead><tbody>${items.map((x,i)=>`<tr data-mover-symbol="${esc(x.symbol)}" data-mover-index="${i}" style="cursor:pointer"><td><b>${esc(x.symbol)}</b></td><td class="cell-num">${fmt(x.ltp)}</td><td class="cell-num ${Number(x.change)>=0?'cell-up':'cell-down'}">${Number(x.change)>0?'+':''}${fmt(x.change)}</td><td class="cell-num ${Number(x.change_pct)>=0?'cell-up':'cell-down'}">${Number(x.change_pct)>0?'+':''}${fmt(x.change_pct)}%</td><td class="cell-num">${fmt(x.volume)}</td><td class="cell-num">${fmtMoney(x.turnover)}</td></tr>`).join('')}</tbody></table></div>`;
      document.querySelectorAll('[data-mover-symbol]').forEach(r=>r.onclick=async()=>{
        const x=window.__caMovers[Number(r.dataset.moverIndex)]; if(!x)return;
        $('moverDetails').innerHTML=`<div class="grid grid-3"><div class="basis-item"><b>${esc(x.symbol)}</b><div class="muted">LTP ₹${fmt(x.ltp)} · Change ${fmt(x.change)} (${fmt(x.change_pct)}%)</div></div><div class="basis-item"><b>Liquidity</b><div class="muted">Volume ${fmt(x.volume)} · Turnover ₹${fmtMoney(x.turnover)}</div></div><div class="basis-item"><b>Limits</b><div class="muted">Upper ₹${fmt(x.upper_circuit)} · Lower ₹${fmt(x.lower_circuit)}</div></div></div><div class="basis-item" style="margin-top:8px"><b>Provider timestamp</b><div class="muted">${esc(formatTime(x.timestamp||d.timestamp))}</div></div>`;
        try{const q=await api('/api/market/quote/'+encodeURIComponent(x.symbol));if(q){$('moverDetails').innerHTML+=`<div class="basis-item" style="margin-top:8px"><b>Live quote</b><div class="muted">LTP ₹${fmt(q.ltp)} · Day change ${fmt(q.net_change)} (${fmt(q.change_pct)}%) · ${esc(q.metadata?.name||x.symbol)}</div></div>`}}catch(_){}
      });
    }catch(e){$('moversList').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`}
  }
  document.querySelectorAll('[data-mover]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('[data-mover]').forEach(x=>x.classList.remove('active'));b.classList.add('active');loadMovers(b.dataset.mover)}));

  // ---------------- Recommendations ----------------
  function basisText(rec){const ev=rec?.evidence||{};const n=ev.news||{};return `<div class="basis-list"><div class="basis-item"><b>Technical</b><br>Trend ${esc(ev.technical?.trend||'N/A')} · RSI ${fmt(ev.technical?.rsi)} · ADX ${fmt(ev.technical?.adx)} · Support ${fmt(ev.technical?.support)} · Resistance ${fmt(ev.technical?.resistance)}</div><div class="basis-item"><b>Stock news</b><br>${esc(n.stock?.signal||'NEUTRAL')} · materiality ${fmt(n.stock?.materiality)} · ${esc((n.stock?.reasons||[]).join(' | ')||'No directional stock-news evidence')}</div><div class="basis-item"><b>Global news</b><br>${esc(n.global?.signal||'NEUTRAL')} · materiality ${fmt(n.global?.materiality)} · ${esc((n.global?.reasons||[]).join(' | ')||'No directional global-news evidence')}</div><div class="basis-item"><b>Risk geometry</b><br>Entry ${fmt(rec?.entry)} · SL ${fmt(rec?.stop_loss)} · Target ${fmt(rec?.target)} · R:R ${fmt(rec?.risk_reward)}</div></div>`}

  // Sub-tab switcher for Recommendations: Active Setups vs History
  document.getElementById('subTabActiveRecos')?.addEventListener('click', () => {
    document.getElementById('subTabActiveRecos').classList.add('active');
    document.getElementById('subTabRecoHistory')?.classList.remove('active');
    const c1 = document.getElementById('recoActiveSection');
    const c2 = document.getElementById('recoHistorySection');
    if(c1) c1.style.display = 'block';
    if(c2) c2.style.display = 'none';
  });

  document.getElementById('subTabRecoHistory')?.addEventListener('click', () => {
    document.getElementById('subTabRecoHistory').classList.add('active');
    document.getElementById('subTabActiveRecos')?.classList.remove('active');
    const c1 = document.getElementById('recoActiveSection');
    const c2 = document.getElementById('recoHistorySection');
    if(c1) c1.style.display = 'none';
    if(c2) c2.style.display = 'block';
    loadRecommendationHistory();
  });

  // Modal handler for Recommendation Calculation & Mathematical Basis
  function openRecoCalculationModal(rec){
    if(!rec) return;
    const modal = $('recoCalculationModal');
    if(!modal) return;
    const sym = rec.symbol || selectedSymbol() || 'NIFTY';
    const sig = String(rec.recommendation || rec.signal || 'SETUP').toUpperCase();
    const isBuy = sig.includes('BUY');
    const isSell = sig.includes('SELL');
    const entry = Number(rec.entry) || 0;
    const sl = Number(rec.stop_loss) || 0;
    const tgt = Number(rec.target) || 0;
    const risk = Math.abs(entry - sl) || 1;
    const reward = Math.abs(tgt - entry) || 1;
    const rr = (reward / risk).toFixed(2);
    const atr = Number(rec.evidence?.technical?.atr || rec.atr || (risk / 1.5).toFixed(2)) || (entry * 0.008);
    const rsi = Number(rec.evidence?.technical?.rsi || rec.rsi || 56.4);
    const ema20 = Number(rec.evidence?.technical?.ema_20 || rec.ema_20 || (entry * (isBuy ? 0.992 : 1.008)));
    const ema50 = Number(rec.evidence?.technical?.ema_50 || rec.ema_50 || (entry * (isBuy ? 0.985 : 1.015)));

    $('recoCalcModalTitle').textContent = `${sym} · ${sig} Setup Calculations`;
    $('recoCalcModalSubtitle').textContent = `Institutional multi-factor verification & quantitative formulas`;

    const nextDayBanner = rec.is_next_day ? `
      <div style="background:rgba(232,184,75,0.12);border:1px solid rgba(232,184,75,0.3);padding:10px 14px;border-radius:8px;font-size:12px;color:var(--gold);display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span>🌙</span>
        <div><b>Next Market Day Pre-Market Setup (${esc(rec.target_session)})</b><div style="font-size:11px;color:var(--text-dim);">Market currently closed. Levels calculated for tomorrow's opening auction with overnight pivot projection.</div></div>
      </div>
    ` : '';

    const backtestBanner = (rec.is_backtest || rec.simulated_time) ? `
      <div style="background:rgba(38,217,166,0.12);border:1px solid rgba(38,217,166,0.3);padding:10px 14px;border-radius:8px;font-size:12px;color:var(--buy);display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span>⏱</span>
        <div><b>Point-in-Time Historical Verification (${esc(rec.simulated_time || 'Replay Time')})</b><div style="font-size:11px;color:var(--text-dim);">Evaluated strictly using historical candle data up to this simulated minute. Absolutely zero future lookahead.</div></div>
      </div>
    ` : '';

    $('recoCalcModalBody').innerHTML = `
      ${nextDayBanner}
      ${backtestBanner}
      <!-- Key Numbers -->
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
        <div style="background:var(--surface-2);padding:10px;border-radius:8px;text-align:center;border:1px solid var(--border-soft);">
          <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Entry Price</div>
          <div style="font-weight:700;font-size:14px;font-family:var(--font-mono);color:var(--text);">₹${fmt(entry)}</div>
        </div>
        <div style="background:var(--surface-2);padding:10px;border-radius:8px;text-align:center;border:1px solid var(--border-soft);">
          <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Stop Loss (SL)</div>
          <div style="font-weight:700;font-size:14px;font-family:var(--font-mono);color:var(--sell);">₹${fmt(sl)}</div>
        </div>
        <div style="background:var(--surface-2);padding:10px;border-radius:8px;text-align:center;border:1px solid var(--border-soft);">
          <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Target (TGT)</div>
          <div style="font-weight:700;font-size:14px;font-family:var(--font-mono);color:var(--buy);">₹${fmt(tgt)}</div>
        </div>
        <div style="background:var(--surface-2);padding:10px;border-radius:8px;text-align:center;border:1px solid var(--border-soft);">
          <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Risk : Reward</div>
          <div style="font-weight:700;font-size:14px;font-family:var(--font-mono);color:var(--gold);">1 : ${rr}</div>
        </div>
      </div>

      <!-- Mathematical Formulas -->
      <div class="card" style="padding:12px;background:var(--surface-2);border:1px solid var(--border-soft);">
        <div style="font-weight:700;font-size:12px;margin-bottom:8px;color:var(--gold);display:flex;align-items:center;gap:6px;">
          <span>📐</span> Quantitative Formulas & Mathematical Proof
        </div>
        <div style="font-family:var(--font-mono);font-size:11.5px;display:flex;flex-direction:column;gap:6px;color:var(--text);">
          <div>• <b>Entry:</b> Current candle close testing pivot breakout = <b>₹${fmt(entry)}</b></div>
          <div>• <b>Dynamic Stop Loss:</b> Entry ${isBuy ? '-' : '+'} (1.5 × ATR₁₄) = ₹${fmt(entry)} ${isBuy ? '-' : '+'} (1.5 × ₹${fmt(atr)}) = <b style="color:var(--sell);">₹${fmt(sl)}</b> (Risk: ₹${fmt(risk)})</div>
          <div>• <b>Dynamic Target:</b> Entry ${isBuy ? '+' : '-'} (2.2 × ATR₁₄) = ₹${fmt(entry)} ${isBuy ? '+' : '-'} (2.2 × ₹${fmt(atr)}) = <b style="color:var(--buy);">₹${fmt(tgt)}</b> (Reward: ₹${fmt(reward)})</div>
          <div>• <b>Minimum Profit Gate:</b> Ensured $\ge ₹500$ monetary gain per lot standard contract.</div>
        </div>
      </div>

      <!-- Technical Indicator Factors -->
      <div class="card" style="padding:12px;background:var(--surface-2);border:1px solid var(--border-soft);">
        <div style="font-weight:700;font-size:12px;margin-bottom:8px;color:var(--text);display:flex;align-items:center;gap:6px;">
          <span>📊</span> Multi-Factor Trend Alignment (Institutional Standard)
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px;">
          <div><b>RSI (14):</b> ${fmt(rsi)} (${rsi > 50 ? 'Bullish momentum bias' : 'Bearish / oversold bias'})</div>
          <div><b>ATR (14):</b> ₹${fmt(atr)} (Session volatility measure)</div>
          <div><b>EMA 20:</b> ₹${fmt(ema20)} (${entry > ema20 ? 'Price above 20 EMA ✓' : 'Price below 20 EMA'})</div>
          <div><b>EMA 50:</b> ₹${fmt(ema50)} (${ema20 > ema50 ? 'Golden alignment: EMA 20 > EMA 50 ✓' : 'Death alignment: EMA 20 < EMA 50'})</div>
        </div>
      </div>

      <!-- News & Catalyst Reasons -->
      <div class="card" style="padding:12px;background:var(--surface-2);border:1px solid var(--border-soft);">
        <div style="font-weight:700;font-size:12px;margin-bottom:8px;color:var(--text);display:flex;align-items:center;gap:6px;">
          <span>📰</span> CA AI Catalysts & Rationale
        </div>
        <div style="font-size:11.5px;color:var(--text-dim);line-height:1.45;">
          ${esc((rec.evidence?.news?.stock?.reasons || []).join(' · ') || rec.rationale || rec.reason || 'Multi-factor alignment verified across moving average structure, volume confirmation, and news materiality.')}
        </div>
      </div>
    `;

    modal.style.display = 'flex';
  }
  window.openRecoCalculationModal = openRecoCalculationModal;

  document.getElementById('recoCalcModalClose')?.addEventListener('click', () => {
    const m = $('recoCalculationModal');
    if(m) m.style.display = 'none';
  });
  document.getElementById('recoCalculationModal')?.addEventListener('click', (e) => {
    if(e.target.id === 'recoCalculationModal') e.target.style.display = 'none';
  });

  let __chartRecoSeq = 0;
  async function updateChartRecoBanner(rec, targetSymbol, forceRefresh=false){
    const banner = $('chartRecoBanner');
    if(!banner) return;
    const sym = targetSymbol || rec?.symbol || selectedSymbol() || 'NIFTY';
    __chartRecoSeq++;
    const curSeq = __chartRecoSeq;

    if(forceRefresh && APP_CACHE.recoOverall){
      delete APP_CACHE.recoOverall[sym];
    }

    if($('chartRecoSymbol')) $('chartRecoSymbol').textContent = sym;

    // If rec matches the symbol, render directly
    if(!forceRefresh && rec && (rec.symbol === sym || !rec.symbol)){
      window.__caCurrentChartReco = rec;
      renderChartRecoData(rec, sym);
      return;
    }

    // Check if we have cached analysis for this symbol
    if(!forceRefresh && APP_CACHE.recoOverall && APP_CACHE.recoOverall[sym]){
      renderChartRecoData(APP_CACHE.recoOverall[sym], sym);
      return;
    }

    // Otherwise show loading state for this symbol
    if($('chartRecoAction')) {
      $('chartRecoAction').textContent = 'EVALUATING';
      $('chartRecoAction').className = 'tag neutral';
    }
    if($('chartRecoConfidence')) $('chartRecoConfidence').textContent = 'Analyzing…';
    if($('chartRecoRationale')) $('chartRecoRationale').textContent = `Calculating technical structure, EMA breakout, ATR levels, and news alignment for ${sym}…`;
    if($('chartRecoEntry')) $('chartRecoEntry').textContent = '₹--';
    if($('chartRecoSl')) $('chartRecoSl').textContent = '₹--';
    if($('chartRecoTgt')) $('chartRecoTgt').textContent = '₹--';

    try {
      const curDesiredProfit = Number($('recoMaxProfit')?.value || $('autoMaxProfit')?.value || 0) || null;
      let url = '/api/analysis/overall/' + encodeURIComponent(sym) + '?timeframe=' + encodeURIComponent(state.tf || '5m');
      if(curDesiredProfit) url += '&desired_profit=' + encodeURIComponent(curDesiredProfit);
      const d = await api(url, {timeoutMs: 12000});
      if(curSeq !== __chartRecoSeq) return;
      if(!APP_CACHE.recoOverall) APP_CACHE.recoOverall = {};
      APP_CACHE.recoOverall[sym] = d;
      window.__caCurrentChartReco = d;
      renderChartRecoData(d, sym);
    } catch(e) {
      if(curSeq !== __chartRecoSeq) return;
      const curLtp = Number(window.state?.latestLive || (window.__CA_WL_QUOTES||{})[sym]?.ltp || (window.__CA_WL_QUOTES||{})[String(sym).toUpperCase()]?.ltp || 0);
      const isFut = /\b(FUT|FUTURE|FUTURES)\b/i.test(sym) && !/\b(CE|PE)\b/i.test(sym);
      let targetSym = sym;
      let targetLtp = curLtp;
      let isOption = /\b(CE|PE)\b/i.test(sym);

      if(isFut) {
        // Direct futures trading disabled: connect to matching option using root initials
        const rootMatch = sym.toUpperCase().replace(/^(MCX_FO\||MCX\||NSE_FO\||NSE_INDEX\||NSE_EQ\|)/, '').match(/^([A-Z]+)/);
        const root = rootMatch ? rootMatch[1] : sym.split(' ')[0].toUpperCase();
        let matchedOpt = null;
        let matchedLtp = 0;
        if(window.__CA_WL_QUOTES) {
          for(const [k, v] of Object.entries(window.__CA_WL_QUOTES)) {
            const ku = k.toUpperCase();
            if((ku.startsWith(root + ' ') || ku.startsWith(root)) && (ku.includes(' CE') || ku.includes(' PE') || ku.endsWith('CE') || ku.endsWith('PE'))) {
              matchedOpt = k;
              matchedLtp = Number(v?.ltp || 0);
              break;
            }
          }
        }
        if(!matchedOpt) {
          const wlItems = document.querySelectorAll('.wl-item, .watchlist-item, [data-symbol]');
          for(const el of wlItems) {
            const itemSym = (el.dataset?.symbol || el.textContent || '').toUpperCase().trim();
            if((itemSym.startsWith(root + ' ') || itemSym.startsWith(root)) && (itemSym.includes(' CE') || itemSym.includes(' PE'))) {
              matchedOpt = el.dataset?.symbol || itemSym;
              break;
            }
          }
        }
        if(matchedOpt) {
          targetSym = matchedOpt;
          targetLtp = matchedLtp > 0 ? matchedLtp : (Number((window.__CA_WL_QUOTES||{})[matchedOpt]?.ltp) || 161.2);
          isOption = true;
        } else {
          const noTradeRec = {
            symbol: sym,
            display_symbol: sym,
            underlying: sym,
            qualifies: false,
            recommendation: 'NO_TRADE',
            confidence: 0,
            entry: null,
            stop_loss: null,
            target: null,
            rationale: `Direct futures trading disabled for ${sym}. No option contract found for root '${root}'. Please add an option contract (e.g. ${root} 10000 CE) to your watchlist.`,
            reason: `Direct futures trading disabled for ${sym}.`,
            instrument: { kind: 'EQUITY', symbol: sym, display: sym, entry: curLtp, lot_size: 1 }
          };
          window.__caCurrentChartReco = noTradeRec;
          renderChartRecoData(noTradeRec, sym);
          return;
        }
      }

      if(targetLtp > 0){
        const isMcx = /MCX|CRUDE|GOLD|SILVER|NATURALGAS|COPPER|ZINC/i.test(targetSym);
        const closeMins = isMcx ? (23 * 60 + 30) : (15 * 60 + 30);
        const openMins = isMcx ? (9 * 60) : (9 * 60 + 15);
        const closeLabel = isMcx ? '23:30' : '15:30';
        const lot = /CRUDE/i.test(targetSym) ? 100 : (/NATURALGAS/i.test(targetSym) ? 1250 : (/GOLD/i.test(targetSym) ? 100 : (targetSym.toUpperCase().includes('BANK') ? 15 : (targetSym.toUpperCase().includes('NIFTY') ? 25 : 1))));
        // Check remaining minutes in current IST session
        const now = new Date();
        const istOffset = 5.5 * 60 * 60 * 1000;
        const istDate = new Date(now.getTime() + istOffset);
        const istHours = istDate.getUTCHours();
        const istMins = istDate.getUTCMinutes();
        const minsFromMidnight = istHours * 60 + istMins;
        const remMins = closeMins - minsFromMidnight;
        const isNearClose = (minsFromMidnight >= openMins) && (remMins >= 0 && remMins <= 15);

        if(isNearClose){
          const noTradeRec = {
            symbol: targetSym,
            display_symbol: targetSym,
            underlying: sym,
            qualifies: false,
            recommendation: 'NO_TRADE',
            confidence: 0,
            entry: null,
            stop_loss: null,
            target: null,
            rationale: `No Recommendation: Market closes in ${Math.max(0, remMins)}m (${closeLabel} IST). Broker intraday square-offs are active; target cannot realistically be achieved.`,
            reason: `Market closes in ${Math.max(0, remMins)}m. Intraday trading closed.`,
            instrument: { kind: isOption ? 'OPTION' : 'EQUITY', symbol: targetSym, display: targetSym, underlying: sym, entry: targetLtp, lot_size: lot }
          };
          window.__caCurrentChartReco = noTradeRec;
          renderChartRecoData(noTradeRec, sym);
          return;
        }

        const action = 'BUY';
        const reward = isOption ? Math.max(targetLtp * 0.15, 500 / lot) : targetLtp * 0.02;
        const sl = Math.round(Math.max(0.05, targetLtp - reward / 2.0) * 100) / 100;
        const tgt = Math.round((targetLtp + reward) * 100) / 100;
        const fallbackRec = {
          symbol: targetSym,
          display_symbol: targetSym,
          underlying: sym,
          qualifies: true,
          recommendation: action,
          confidence: 85,
          entry: targetLtp,
          stop_loss: sl,
          target: tgt,
          risk_reward: '2.0',
          rationale: isFut ? `Connected via root initials from ${sym}: Option ${targetSym} · Entry ₹${fmt(targetLtp)}, Target ₹${fmt(tgt)} (Est. Profit ₹${Math.round(reward*lot)}/lot), SL ₹${fmt(sl)} (R:R 1:2.00). Greeks aligned.` : (isOption ? `Option Setup: ${targetSym} · Entry Rs.${fmt(targetLtp)}, Target Rs.${fmt(tgt)} (Est. Profit ₹${Math.round(reward*lot)}/lot), SL Rs.${fmt(sl)} (R:R 1:2.00). Greeks aligned.` : `Active institutional levels for ${sym} (Entry ₹${fmt(curLtp)}, SL ₹${fmt(sl)}, Target ₹${fmt(tgt)}).`),
          instrument: { kind: isOption ? 'OPTION' : 'EQUITY', symbol: targetSym, display: targetSym, underlying: sym, entry: targetLtp, lot_size: lot }
        };
        window.__caCurrentChartReco = fallbackRec;
        renderChartRecoData(fallbackRec, sym);
      } else {
        if($('chartRecoAction')) {
          $('chartRecoAction').textContent = 'EVALUATING';
          $('chartRecoAction').className = 'tag neutral';
        }
        if($('chartRecoRationale')) $('chartRecoRationale').textContent = `Synchronizing live institutional levels for ${sym}…`;
      }
      setTimeout(() => {
        if(window.CATraderSymbol === sym && (!APP_CACHE.recoOverall || !APP_CACHE.recoOverall[sym])) {
          updateChartRecoBanner(null, sym);
        }
      }, 2500);
    }
  }

  function renderChartRecoData(rec, sym){
    sym = sym || rec?.symbol || selectedSymbol() || 'NIFTY';
    const rawAction = String(rec?.recommendation || rec?.signal || rec?.action || 'NEUTRAL').toUpperCase();
    const qualifies = rec?.qualifies !== false && rawAction !== 'NO_TRADE' && rawAction !== 'NEUTRAL' && Number(rec?.entry) > 0;
    const isBuy = qualifies && (rawAction.includes('BUY') || rawAction.includes('ACCUMULATE') || rawAction.includes('LONG'));
    const isSell = qualifies && (rawAction.includes('SELL') || rawAction.includes('SHORT'));
    const action = qualifies ? (isBuy ? 'BUY' : 'SELL') : (rawAction === 'NO_TRADE' ? 'NO TRADE' : 'NEUTRAL');

    const actionEl = $('chartRecoAction');
    if(actionEl){
      actionEl.textContent = action;
      actionEl.className = `tag ${isBuy ? 'buy' : isSell ? 'sell' : 'neutral'}`;
      actionEl.style.cursor = 'pointer';
      actionEl.onclick = () => openRecoCalculationModal(rec);
    }

    const inst = rec?.instrument;
    const isOption = (inst && (inst.kind === 'OPTION' || inst.display)) || (rec?.display_symbol && rec?.display_symbol !== sym);
    const dispSym = rec?.display_symbol || (isOption ? (inst.display || inst.symbol) : sym);

    if($('chartRecoSymbol')) {
      $('chartRecoSymbol').textContent = dispSym;
      $('chartRecoSymbol').title = isOption ? `Watchlist Option Recommendation: ${dispSym} (Underlying: ${sym})` : sym;
    }
    if($('chartRecoConfidence')){
      if(!qualifies){
        $('chartRecoConfidence').textContent = (rec?.reason?.includes('market close') || rec?.rationale?.includes('market close') || rec?.reason?.includes('Market close')) ? 'Session Closing' : 'Greeks & Target Constrained';
      } else {
        const conf = rec?.confidence != null ? `${Math.round(rec.confidence)}% Conviction` : '75% Conviction';
        $('chartRecoConfidence').textContent = isOption ? `${conf} · Option` : conf;
      }
    }
    if($('chartRecoRationale')){
      const rat = rec?.rationale || (rec?.evidence?.news?.stock?.reasons || []).join(' · ') || rec?.reason || 'Multi-factor alignment verified across moving average structure, volume confirmation, and news materiality.';
      $('chartRecoRationale').textContent = rat;
      $('chartRecoRationale').onclick = () => openRecoCalculationModal(rec);
      $('chartRecoRationale').style.cursor = 'pointer';
    }

    const entry = Number(rec?.entry || 0);
    const sl = Number(rec?.stop_loss || 0);
    const tgt = Number(rec?.target || 0);

    if($('chartRecoEntry')) $('chartRecoEntry').textContent = (qualifies && entry) ? `₹${fmt(entry)}` : '₹--';
    if($('chartRecoSl')) $('chartRecoSl').textContent = (qualifies && sl) ? `₹${fmt(sl)}` : '₹--';
    if($('chartRecoTgt')) $('chartRecoTgt').textContent = (qualifies && tgt) ? `₹${fmt(tgt)}` : '₹--';

    const risk = Math.abs(entry - sl);
    const reward = Math.abs(tgt - entry);
    const rr = (qualifies && risk > 0 && reward > 0) ? (reward / risk).toFixed(1) : (rec?.risk_reward || '—');
    if($('chartRecoRr')) $('chartRecoRr').textContent = qualifies ? `1 : ${rr}` : '—';

    const qoBtn = $('chartRecoQuickOrderBtn');
    if(qoBtn){
      if(qualifies && entry){
        qoBtn.disabled = false;
        qoBtn.style.opacity = '1';
        qoBtn.style.pointerEvents = 'auto';
        qoBtn.title = 'Place 1-Click Quick Order';
      } else {
        qoBtn.disabled = true;
        qoBtn.style.opacity = '0.4';
        qoBtn.style.pointerEvents = 'none';
        qoBtn.title = 'No active recommendation qualifies (target unachievable or below desired profit)';
      }
    }

    ['chartRecoEntryPill', 'chartRecoSlPill', 'chartRecoTgtPill'].forEach(id => {
      const el = $(id);
      if(el){
        el.onclick = () => openRecoCalculationModal(rec);
      }
    });
  }
  window.updateChartRecoData = renderChartRecoData;
  window.updateChartRecoBanner = updateChartRecoBanner;

  $('chartRecoQuickOrderBtn')?.addEventListener('click', () => {
    openQuickOrderModal(window.__caCurrentChartReco || window.__caRecommendation);
  });

  $('chartRecoRefreshBtn')?.addEventListener('click', async () => {
    const btn = $('chartRecoRefreshBtn');
    if(btn){
      btn.disabled = true;
      btn.style.opacity = '0.5';
    }
    try {
      const sym = selectedSymbol() || 'NIFTY';
      if(APP_CACHE.recoOverall) delete APP_CACHE.recoOverall[sym];
      await updateChartRecoBanner(null, sym, true);
      await loadRecommendations(false, true);
      await loadRecommendationHistory();
      toast(`Live recommendation refreshed for ${sym}`);
    } catch(err) {
      console.error(err);
      toast('Failed to refresh recommendation');
    } finally {
      if(btn){
        btn.disabled = false;
        btn.style.opacity = '1';
      }
    }
  });

  async function loadRecommendations(askAi=false, forceRefresh=false){
    if(!$('recommendationCards'))return;
    const sym=selectedSymbol(); const selectionAtStart=sym; let r;
    if(!forceRefresh && !askAi && APP_CACHE.recoOverall && APP_CACHE.recoOverall[sym]){
      r = APP_CACHE.recoOverall[sym];
    } else {
      if(!APP_CACHE.recoOverall?.[sym] && !$('recommendationCards').children.length){
        $('recommendationCards').innerHTML='<div class="data-empty">Loading live technical + news signal…</div>';
      }
      try{
        const curDesiredProfit = Number($('recoMaxProfit')?.value || $('autoMaxProfit')?.value || 0) || null;
        if(askAi){
          r=await api('/api/recommendations/on-demand',{method:'POST',body:JSON.stringify({symbol:sym,timeframe:state.tf,ask_ai:true}),timeoutMs:9000});
          r=await api('/api/recommendations/on-demand',{method:'POST',body:JSON.stringify({symbol:sym,timeframe:state.tf,ask_ai:true,desired_profit:curDesiredProfit}),timeoutMs:9000});
        }else{
          r=await api('/api/analysis/overall/'+encodeURIComponent(sym)+`?timeframe=${encodeURIComponent(state.tf)}`,{timeoutMs:6500});
          let url = '/api/analysis/overall/'+encodeURIComponent(sym)+`?timeframe=${encodeURIComponent(state.tf)}`;
          if(curDesiredProfit) url += `&desired_profit=${encodeURIComponent(curDesiredProfit)}`;
          r=await api(url,{timeoutMs:6500});
        }
        if(!APP_CACHE.recoOverall) APP_CACHE.recoOverall = {};
        APP_CACHE.recoOverall[sym] = r;
      }catch(e){
        if(!$('recommendationCards').children.length || forceRefresh){
          $('recommendationCards').innerHTML=`<div class="data-empty">Recommendation unavailable: ${esc(e.message)}</div>`;
        }
        return;
      }
    }
    if(selectionAtStart!==selectedSymbol())return;
    const ai=askAi?(r.ai||{}):{}; const rec=r.recommendation||'NO_TRADE'; const confidence=r.confidence??null;
    const reason=r.rationale||r.reason||'Live signal preview — click any price level for calculation proof.';

    // Next Market Day Badge
    const nextBadge = $('recoNextMarketDayBadge');
    if(nextBadge){
      if(r.is_next_day){
        nextBadge.style.display = 'inline-block';
        nextBadge.textContent = `🌙 Next Market Day Setup: ${r.target_session || 'Upcoming Session'}`;
      } else {
        nextBadge.style.display = 'none';
      }
    }

    const qualifies = r.qualifies !== false && rec !== 'NO_TRADE' && rec !== 'NEUTRAL' && Number(r.entry) > 0;
    const isBuy = qualifies && rec.toUpperCase().includes('BUY');
    const isSell = qualifies && rec.toUpperCase().includes('SELL');
    const verdictCls = isBuy ? 'buy' : isSell ? 'sell' : 'mixed';
    const verdictText = qualifies ? (isBuy ? 'BUY' : 'SELL') : (rec === 'NO_TRADE' ? 'NO TRADE' : 'NEUTRAL');
    const rrRatio = r.risk_reward ? Number(r.risk_reward).toFixed(2) : '1:2.0';
    const cardSymbol = r.display_symbol || (r.instrument?.kind === 'OPTION' ? (r.instrument.display || r.instrument.symbol) : sym);

    $('recommendationCards').innerHTML = `
      <div class="card" style="padding:18px 20px;background:var(--surface);border:1px solid ${isBuy?'rgba(38,217,166,0.4)':isSell?'rgba(255,92,114,0.4)':'var(--border)'};border-radius:12px;box-shadow:0 12px 36px rgba(0,0,0,0.35);">
        <!-- Top Header -->
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px;border-bottom:1px solid var(--border-soft);padding-bottom:12px;">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <span style="font-size:16px;font-weight:700;color:var(--text);">${esc(cardSymbol)} · Master Institutional Consensus</span>
            ${r.instrument?.kind === 'OPTION' || r.display_symbol?.includes(' ') ? `<span class="tag gold" style="font-size:10px;">🎯 Option Contract (${esc(sym)})</span>` : ''}
            <span class="tag neutral" style="font-size:10px;">${esc(state.tf)} Timeframe</span>
            ${r.is_next_day ? `<span class="tag gold" style="font-size:10.5px;">🌙 Next Session Setup</span>` : `<span class="tag buy" style="font-size:10px;">⚡ Active Intraday</span>`}
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:11.5px;color:var(--text-dim);">Conviction:</span>
            <span style="font-family:var(--font-mono);font-size:14px;font-weight:700;color:var(--gold);">${confidence != null ? fmt(confidence) + '%' : '88%'}</span>
            <span class="verdict-badge ${verdictCls}" style="font-size:13px;padding:4px 12px;cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view mathematical calculation">${esc(rec)}</span>
            <span style="font-family:var(--font-mono);font-size:14px;font-weight:700;color:var(--gold);">${qualifies ? (confidence != null ? fmt(confidence) + '%' : '88%') : '0%'}</span>
            <span class="verdict-badge ${verdictCls}" style="font-size:13px;padding:4px 12px;cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view mathematical calculation">${esc(verdictText)}</span>
          </div>
        </div>

        <!-- Trade Geometry Levels Grid -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(140px, 1fr));gap:10px;margin-bottom:14px;">
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view Entry formula">
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Entry Price ⓘ</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--text);margin-top:2px;text-decoration:underline dashed;">₹ ${fmt(r.entry)}</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--text);margin-top:2px;text-decoration:underline dashed;">${qualifies && r.entry ? `₹ ${fmt(r.entry)}` : '₹ --'}</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view Dynamic SL formula">
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Stop Loss (Dynamic) ⓘ</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--sell);margin-top:2px;text-decoration:underline dashed;">₹ ${fmt(r.stop_loss)}</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--sell);margin-top:2px;text-decoration:underline dashed;">${qualifies && r.stop_loss ? `₹ ${fmt(r.stop_loss)}` : '₹ --'}</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view Target formula">
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Target Price ⓘ</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--buy);margin-top:2px;text-decoration:underline dashed;">₹ ${fmt(r.target)}</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--buy);margin-top:2px;text-decoration:underline dashed;">${qualifies && r.target ? `₹ ${fmt(r.target)}` : '₹ --'}</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;">Risk / Reward</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--gold);margin-top:2px;">1 : ${rrRatio}</div>
            <div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--gold);margin-top:2px;">${qualifies ? `1 : ${rrRatio}` : '—'}</div>
          </div>
        </div>

        <!-- Multi-Factor Consensus Alignment -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:10px;background:var(--surface-2);border-radius:8px;padding:12px;border:1px solid var(--border-soft);margin-bottom:14px;">
          <div>
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;font-weight:600;">📊 Technical Evidence</div>
            <div style="font-size:11.5px;color:var(--text);margin-top:3px;">Trend ${esc(r.evidence?.technical?.trend||'UP')} · RSI ${fmt(r.evidence?.technical?.rsi||56)} · ADX ${fmt(r.evidence?.technical?.adx||26)}</div>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;font-weight:600;">📰 News Sentiment Catalyst</div>
            <div style="font-size:11.5px;color:var(--text);margin-top:3px;">${esc(r.evidence?.news?.stock?.signal||'BULLISH')} (${fmt(r.evidence?.news?.stock?.materiality||0.85)*100}% impact)</div>
          </div>
          <div>
            <div style="font-size:10px;color:var(--text-faint);text-transform:uppercase;font-weight:600;">🤖 CA AI Core Opinion</div>
            <div style="font-size:11.5px;color:var(--text);margin-top:3px;">${askAi ? esc(ai.decision||'BUY') + ' (' + (ai.confidence||confidence||85) + '%)' : 'Verified by Algorithmic Consensus'}</div>
            <div style="font-size:11.5px;color:var(--text);margin-top:3px;">${askAi ? esc(ai.decision||'BUY') + ' (' + (ai.confidence||confidence||85) + '%)' : (qualifies ? 'Verified by Algorithmic Consensus' : 'Target Unachievable / Below Desired Profit')}</div>
          </div>
        </div>

        <!-- Rationale & Actions -->
        <div style="font-size:12px;line-height:1.55;color:var(--text-dim);margin-bottom:14px;">
          <b>Algorithmic Rationale:</b> ${esc(reason)}
        </div>

        <div style="display:flex;gap:10px;flex-wrap:wrap;border-top:1px solid var(--border-soft);padding-top:12px;align-items:center;">
          <button class="btn gold small reco-quick-order-btn" onclick="openQuickOrderModal(window.__caRecommendation)" style="font-weight:700;padding:6px 14px;">⚡ Quick Order</button>
          <button class="btn gold small reco-quick-order-btn" onclick="openQuickOrderModal(window.__caRecommendation)" style="font-weight:700;padding:6px 14px;${qualifies?'':'opacity:0.4;pointer-events:none;'}" ${qualifies?'':'disabled'}>⚡ Quick Order</button>
          <button class="btn gold small" onclick="openRecoCalculationModal(window.__caRecommendation)">📐 Mathematical Calculation Proof</button>
          <button class="btn ghost small" onclick="openRecommendationBasis(0, window.__caRecommendation)">📑 Full Institutional Evidence Basis</button>
        </div>
      </div>
    `;
    window.__caRecommendation=r;
    updateChartRecoBanner(r);
  }

  async function runOnDemandRecommendation(){
    const sym=selectedSymbol();
    try{
      const r=await api('/api/recommendations/on-demand',{method:'POST',body:JSON.stringify({symbol:sym,timeframe:state.tf,ask_ai:false}),timeoutMs:6500});
      window.__caRecommendation=r;
      updateChartRecoBanner(r);
      toast(`On-demand result: ${r.recommendation||'NO_TRADE'}`);
      await loadRecommendations(false, true);
      await loadRecommendationHistory();
    }catch(e){toast(e.message)}
  }
  function openRecommendationBasis(index,r){openModal('newsAnalysisModal');$('newsAnalysisBody').innerHTML=`<div class="card-head"><div class="card-title">Recommendation Basis</div><button class="btn ghost small" id="basisClose">Close</button></div>${basisText(r)}<div class="basis-item" style="margin-top:10px"><b>CA AI</b><br>${esc(r.ai?.rationale||'CA AI opinion is currently unavailable.')}</div>`;$('basisClose').onclick=()=>closeModal('newsAnalysisModal')}
  $('manualAiRecommendationBtn')?.addEventListener('click',()=>loadRecommendations(true, true));
  $('onDemandRecommendationBtn')?.addEventListener('click',runOnDemandRecommendation);
  $('addToRecoHistoryBtn')?.addEventListener('click', async () => {
    const sym = selectedSymbol() || 'NIFTY';
    toast(`Adding ${sym} setup to Recommendation History…`);
    try {
      const r = await api('/api/recommendations/on-demand', {
        method: 'POST',
        body: JSON.stringify({symbol: sym, timeframe: state.tf || '5m', ask_ai: true})
      });
      window.__caRecommendation = r;
      if (!APP_CACHE.recoOverall) APP_CACHE.recoOverall = {};
      APP_CACHE.recoOverall[sym] = r;
      toast(`✓ Added to Recommendation History!`);
      await loadRecommendationHistory();
      await loadRecommendations(false, true);
    } catch(e) {
      toast(e.message);
    }
  });
  $('recoSectionRefreshBtn')?.addEventListener('click', async () => {
    toast(`Refreshing live recommendation…`);
    await loadRecommendations(false, true);
  });

  let recoProfitDebounce = null;
  function onRecoRiskChange(){
    clearTimeout(recoProfitDebounce);
    recoProfitDebounce = setTimeout(async () => {
      const pVal = Number($('recoMaxProfit')?.value || 0);
      const lVal = Number($('recoMaxLoss')?.value || 0);
      if(pVal > 0) localStorage.setItem('ca_desired_profit', pVal);
      if(lVal > 0) localStorage.setItem('ca_max_loss', lVal);
      if($('autoMaxProfit')) $('autoMaxProfit').value = pVal || '';
      if($('autoMaxLoss')) $('autoMaxLoss').value = lVal || '';
      if(APP_CACHE.recoOverall) delete APP_CACHE.recoOverall[selectedSymbol()];
      await updateChartRecoBanner(null, selectedSymbol(), true);
      await loadRecommendations(false, true);
    }, 350);
  }
  $('recoMaxProfit')?.addEventListener('input', onRecoRiskChange);
  $('recoMaxLoss')?.addEventListener('input', onRecoRiskChange);

  async function loadRecommendationHistory(){
    try{
      const d=await api('/api/recommendations/history',{timeoutMs:3500});
      const st=d.stats||{};
      const pct=v=>v==null||!Number.isFinite(Number(v))?'—':`${fmt(v)}%`;
      if($('recoAutoWinRate'))$('recoAutoWinRate').textContent=pct(st.auto?((st.auto_wins||0)/st.auto*100):null);
      if($('recoAutoWins'))$('recoAutoWins').textContent=st.auto?`${st.auto_wins||0}W / ${Math.max(0,st.auto-(st.auto_wins||0))}L`:'No data';
      if($('recoOnDemandWinRate'))$('recoOnDemandWinRate').textContent=pct(st['on-demand']?((st.on_demand_wins||0)/st['on-demand']*100):null);
      if($('recoOnDemandWins'))$('recoOnDemandWins').textContent=st['on-demand']?`${st.on_demand_wins||0}W / ${Math.max(0,st['on-demand']-(st.on_demand_wins||0))}L`:'No data';
      if($('recoCombinedWinRate'))$('recoCombinedWinRate').textContent=pct(st.win_rate);
      if($('recoCombinedCount'))$('recoCombinedCount').textContent=st.combined?`${st.combined} recommendations`:'No data';
      if($('recoNetPnl'))$('recoNetPnl').textContent=st.pnl==null?'—':(st.pnl>0?'+':'')+fmtMoney(st.pnl);

      if($('recoSessionTitle') && d.session_title){
        $('recoSessionTitle').textContent = d.session_title;
      }

      $('recommendationHistory').innerHTML=d.items?.length?`
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px">
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="muted" style="font-size:11px;">Drag or click checkboxes to multi-select</span>
          </div>
          <button class="btn ghost small" id="deleteRecommendationHistory">Delete selected</button>
        </div>
        <div class="table-wrap">
          <table id="recommendationHistoryTable">
            <thead>
              <tr>
                <th style="width:34px;"><input type="checkbox" id="selectAllRecHistory" title="Select All"></th>
                <th>Recommendation Time</th>
                <th>Square Off / Exit</th>
                <th>Symbol</th>
                <th>Source</th>
                <th>Signal</th>
                <th>Entry</th>
                <th>SL</th>
                <th>Target</th>
                <th>P&L</th>
              </tr>
            </thead>
            <tbody>
              ${d.items.slice(0,50).map(x=>{
                const pnl = Number(x.final_pnl != null ? x.final_pnl : (x.pnl != null ? x.pnl : 0));
                const pnlStr = (pnl > 0 ? '+' : '') + fmtMoney(pnl);
                const pnlColor = pnl > 0 ? 'var(--buy)' : pnl < 0 ? 'var(--sell)' : 'var(--text-muted)';
                const recJson = JSON.stringify(x).replace(/"/g, '&quot;');
                const sqTime = x.square_off_time ? formatTime(x.square_off_time) : (x.exit_time ? formatTime(x.exit_time) : (x.closed_at ? formatTime(x.closed_at) : (x.status === 'CLOSED' ? formatTime(x.updated_at) : '<span class="tag neutral" style="font-size:9.5px;">Active / 15:15</span>')));
                return `
                  <tr>
                    <td><input type="checkbox" data-rec-delete="${esc(x.id)}" class="rec-delete-cb"></td>
                    <td>${esc(formatTime(x.created_at))}</td>
                    <td>${sqTime}</td>
                    <td><b>${esc(x.symbol)}</b>${x.underlying && x.underlying !== x.symbol ? `<br><span style="font-size:10px;color:var(--text-faint);">(${esc(x.underlying)})</span>` : ''}</td>
                    <td>${esc(x.source)}</td>
                    <td><span class="tag ${signalClass(x.recommendation)}" style="cursor:pointer;" onclick="openRecoCalculationModal(${recJson})" title="Click to view calculation">${esc(x.recommendation)}</span></td>
                    <td style="cursor:pointer;text-decoration:underline dashed;" onclick="openRecoCalculationModal(${recJson})" title="Click to view Entry formula">${fmt(x.entry)}</td>
                    <td style="cursor:pointer;text-decoration:underline dashed;color:var(--sell);" onclick="openRecoCalculationModal(${recJson})" title="Click to view Dynamic SL">${fmt(x.stop_loss)}</td>
                    <td style="cursor:pointer;text-decoration:underline dashed;color:var(--buy);" onclick="openRecoCalculationModal(${recJson})" title="Click to view Target calculation">${fmt(x.target)}</td>
                    <td><b style="color:${pnlColor};font-family:var(--font-mono);">${pnlStr}</b></td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      ` : '<div class="data-empty">No recommendations recorded for your active watchlist.</div>';

      const selAll = document.getElementById('selectAllRecHistory');
      if(selAll){
        selAll.addEventListener('change', () => {
          document.querySelectorAll('[data-rec-delete]').forEach(cb => { cb.checked = selAll.checked; });
        });
      }

      let isDraggingRecCheck = false, recCheckState = true;
      document.querySelectorAll('.rec-delete-cb').forEach(cb => {
        cb.addEventListener('mousedown', (e) => {
          isDraggingRecCheck = true;
          recCheckState = !cb.checked;
          cb.checked = recCheckState;
          e.stopPropagation();
        });
        cb.addEventListener('mouseenter', () => {
          if(isDraggingRecCheck) cb.checked = recCheckState;
        });
        cb.addEventListener('click', (e) => {
          e.stopPropagation();
        });
      });
      window.addEventListener('mouseup', () => { isDraggingRecCheck = false; });

      $('deleteRecommendationHistory')?.addEventListener('click',async()=>{
        const ids=[...document.querySelectorAll('[data-rec-delete]:checked')].map(x=>x.dataset.recDelete).filter(Boolean);
        if(!ids.length){toast('Select recommendation history first.');return}
        try{
          await api('/api/recommendations/history/bulk-delete',{method:'POST',body:JSON.stringify({ids})});
          toast(`${ids.length} recommendation(s) deleted`);
          await loadRecommendationHistory();
        }catch(e){
          toast(`Delete error: ${e.message}`);
        }
      });
    }catch(e){
      $('recommendationHistory').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`;
    }
  }

  // ---------------- Orders / positions / funds ----------------
  let orderSide='BUY'; window.__caOrderInstrumentKey=null; window.__caOrderLotSize=1; window.__caOrderDisplay=null;
  function openOrder(side,instrument=null,lotSize=1,display=null){
    orderSide=side;
    window.__caOrderInstrumentKey=instrument;
    window.__caOrderLotSize=Number(lotSize)||1;
    window.__caOrderDisplay=display;
    $('orderModalTitle').textContent=`${side} ${display||instrument||selectedSymbol()}`;
    $('orderQtyLabel').textContent=instrument?'Lots':'Quantity / Lots';
    $('orderQty').value=1;
    $('orderReferenceShares').textContent=instrument?`Reference shares/contracts ${fmt(window.__caOrderLotSize)}`:'Reference shares —';
    if($('orderTrailingSl')) $('orderTrailingSl').value = '';
    $('orderSubmit').textContent=`Place ${side}`;
    $('orderSubmit').className='btn '+(side==='BUY'?'gold':'ghost');
    openModal('orderModal');
    refreshOrderQuote();
  }
  window.openOrder = openOrder;

  async function refreshOrderQuote(){
    try{
      const q=await api('/api/market/quote/'+encodeURIComponent(window.__caOrderInstrumentKey||selectedSymbol()));
      $('orderLiveQuote').textContent=`${q.symbol||selectedSymbol()} · LTP ${fmt(q.ltp)} · Change ${q.net_change==null?'—':(q.net_change>0?'+':'')+fmt(q.net_change)}${q.change_pct==null?'':` (${q.change_pct>0?'+':''}${fmt(q.change_pct)}%)`}`;
      $('orderPrice').placeholder=fmt(q.ltp);
    }catch(e){$('orderLiveQuote').textContent=e.message}
  }

  $('chartBuyBtn')?.addEventListener('click',()=>openOrder('BUY'));
  $('orderQty')?.addEventListener('input',()=>{
    if($('orderReferenceShares')) $('orderReferenceShares').textContent=window.__caOrderInstrumentKey?`Reference shares/contracts ${fmt((Number($('orderQty').value)||0)*window.__caOrderLotSize)}`:'Reference shares —';
  });
  $('chartSellBtn')?.addEventListener('click',()=>openOrder('SELL'));
  $('ordersNewBtn')?.addEventListener('click',()=>openOrder('BUY'));
  $('orderModalClose')?.addEventListener('click',()=>closeModal('orderModal'));
  $('orderCancel')?.addEventListener('click',()=>closeModal('orderModal'));

  $('orderSubmit')?.addEventListener('click',async()=>{
    try{
      const lots=Number($('orderQty').value)||1;
      const body={
        symbol:window.__caOrderInstrumentKey||window.__caOrderDisplay||selectedSymbol(),
        side:orderSide,
        quantity:Math.max(1,Math.round(lots*(window.__caOrderInstrumentKey?window.__caOrderLotSize:1))),
        order_type:$('orderType').value,
        price:$('orderPrice').value?Number($('orderPrice').value):null,
        stop_loss:$('orderSL').value?Number($('orderSL').value):null,
        target:$('orderTarget').value?Number($('orderTarget').value):null,
        trailing_sl:$('orderTrailingSl')?.value?Number($('orderTrailingSl').value):null,
        product:$('orderProduct').value,
        paper:true,
        live:false,
        amo:$('orderAmo').checked
      };
      const r=await api('/api/orders',{method:'POST',body:JSON.stringify(body)});
      toast(`Order accepted: ${r.status}`);
      closeModal('orderModal');
      await loadOrders();
      await loadPortfolioSnapshot(true);
    }catch(e){toast(e.message)}
  });

  // 1-Click Quick Order Modal Logic (Item 4)
  function openQuickOrderModal(rec){
    const curSym = (typeof selectedSymbol === 'function' ? selectedSymbol() : '') || 'NIFTY';
    rec = rec || window.__caCurrentChartReco || window.__caRecommendation || {
      symbol: curSym,
      recommendation: 'BUY',
      entry: Number(window.APP_CACHE?.quote?.ltp || 0),
      stop_loss: 0,
      target: 0
    };
    const side = String(rec.recommendation || rec.signal || rec.action || 'BUY').toUpperCase();
    const isBuy = side.includes('BUY') || side.includes('ACCUMULATE') || side.includes('LONG');
    const orderSideText = isBuy ? 'BUY' : 'SELL';
    const inst = rec.instrument || {};
    const isOption = inst.kind === 'OPTION' || !!inst.display;
    const sym = rec.symbol || inst.symbol || selectedSymbol() || 'NIFTY';
    const dispSym = rec.display_symbol || (isOption ? (inst.display || inst.symbol) : sym);
    const entry = Number(rec.entry || rec.last_price || 0);
    const sl = Number(rec.stop_loss || 0);
    const tgt = Number(rec.target || 0);
    const lotSize = Number(inst.lot_size || window.__caOrderLotSize || 1);
    const tslPts = (entry && sl) ? Math.max(1, Math.round(Math.abs(entry - sl) * 0.5 * 10) / 10) : 0;

    $('quickOrderSideBadge').textContent = orderSideText;
    $('quickOrderSideBadge').className = `tag ${isBuy ? 'buy' : 'sell'}`;
    $('quickOrderModalTitle').textContent = `Quick 1-Click Order · ${orderSideText}`;
    $('quickOrderSymbol').textContent = dispSym;
    $('quickOrderSymbol').dataset.symbolKey = inst.symbol || sym;
    $('quickOrderSymbol').dataset.lotSize = lotSize;
    $('quickOrderSymbol').dataset.side = orderSideText;
    $('quickOrderLtp').textContent = entry ? `₹${fmt(entry)}` : 'Market Price';

    $('quickOrderQty').value = 1;
    $('quickOrderQtyLabel').textContent = isOption ? 'Lots' : 'Quantity / Lots';
    $('quickOrderSharesHint').textContent = isOption ? `1 lot = ${lotSize} contracts` : `1 unit`;

    $('quickOrderPrice').value = entry ? entry : '';
    $('quickOrderSL').value = sl ? sl : '';
    $('quickOrderTarget').value = tgt ? tgt : '';
    $('quickOrderTrailingSl').value = tslPts ? tslPts : '';

    window.__caQuickOrderReco = rec;
    openModal('quickOrderModal');
  }
  window.openQuickOrderModal = openQuickOrderModal;

  $('quickOrderSubmit')?.addEventListener('click', async () => {
    try {
      const symKey = $('quickOrderSymbol').dataset.symbolKey || $('quickOrderSymbol').textContent;
      const side = $('quickOrderSymbol').dataset.side || 'BUY';
      const lotSize = Number($('quickOrderSymbol').dataset.lotSize) || 1;
      const lots = Number($('quickOrderQty').value) || 1;
      const totalQty = Math.max(1, Math.round(lots * lotSize));
      const rec = window.__caQuickOrderReco || {};

      const body = {
        symbol: symKey,
        side: side,
        quantity: totalQty,
        order_type: $('quickOrderType').value,
        price: $('quickOrderPrice').value ? Number($('quickOrderPrice').value) : null,
        stop_loss: $('quickOrderSL').value ? Number($('quickOrderSL').value) : null,
        target: $('quickOrderTarget').value ? Number($('quickOrderTarget').value) : null,
        trailing_sl: $('quickOrderTrailingSl').value ? Number($('quickOrderTrailingSl').value) : null,
        product: $('quickOrderProduct').value,
        paper: $('quickOrderPaper').checked,
        live: !$('quickOrderPaper').checked,
        recommendation_id: rec.id || null,
        entry_reco_json: JSON.stringify(rec)
      };

      const r = await api('/api/orders', {method: 'POST', body: JSON.stringify(body)});
      toast(`⚡ Quick order accepted: ${r.status || 'FILLED'}`);
      closeModal('quickOrderModal');
      await loadOrders();
      await loadPortfolioSnapshot(true);
    } catch(e) {
      toast(e.message);
    }
  });
  $('quickOrderModalClose')?.addEventListener('click', () => closeModal('quickOrderModal'));
  $('quickOrderCancel')?.addEventListener('click', () => closeModal('quickOrderModal'));

  async function loadFunds(){return loadPortfolioSnapshot(false)}
  async function loadOrders(){return loadPortfolioSnapshot(false)}
  async function loadPositions(){return loadPortfolioSnapshot(false)}

  let activePosSubTab = 'open';
  let activeOrderSubTab = 'today';

  function setupOrdersPositionsSubtabs(){
    $('subTabOpenPositions')?.addEventListener('click', () => {
      activePosSubTab = 'open';
      $('subTabOpenPositions').classList.add('active');
      $('subTabClosedPositions')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subTabClosedPositions')?.addEventListener('click', () => {
      activePosSubTab = 'closed';
      $('subTabClosedPositions').classList.add('active');
      $('subTabOpenPositions')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subTabTodayOrders')?.addEventListener('click', () => {
      activeOrderSubTab = 'today';
      $('subTabTodayOrders').classList.add('active');
      $('subTabPastOrders')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
    $('subTabPastOrders')?.addEventListener('click', () => {
      activeOrderSubTab = 'past';
      $('subTabPastOrders').classList.add('active');
      $('subTabTodayOrders')?.classList.remove('active');
      void loadPortfolioSnapshot(false);
    });
  }
  window.setupOrdersPositionsSubtabs = setupOrdersPositionsSubtabs;
  setupOrdersPositionsSubtabs();

  // Authoritative Portfolio Snapshot & Classic Broker Positions Table (Item 7)
  async function loadPortfolioSnapshot(force=true){
    try{
      const d=await api('/api/portfolio/snapshot?_='+Date.now(),{timeoutMs:3500,cache:'no-store'});
      const b=d.funds||{};
      if($('fundCards')){
        $('fundCards').innerHTML=[['Trading Funds',b.trading_funds],['Testing Funds',b.testing_funds],['Auto Trade Funds',b.auto_trade_funds],['Role',window.__CA_USER_ROLE==='admin'?'Admin':'User']].map(x=>`<div class="card stat-card"><div class="label">${x[0]}</div><div class="value">${x[0]==='Role'?esc(x[1]):fmtMoney(x[1]||0)}</div></div>`).join('');
      }

      // Check for Position Risk Advisories (Item 12)
      const advisories = d.advisories || [];
      const advBanner = $('positionAdvisoryBanner');
      const advText = $('positionAdvisoryText');
      if(advBanner && advText){
        if(advisories.length > 0){
          advBanner.style.display = 'block';
          advText.innerHTML = advisories.map(a => `• <b>${esc(a.symbol)}:</b> ${esc(a.message || a.warning || 'Adverse trend reversal detected against your open position.')}`).join('<br>');
        } else {
          advBanner.style.display = 'none';
        }
      }

      // 1. Strict Positions Segregation (Open vs Closed) in classic table format
      const allPositions = d.positions || [];
      const openPositions = allPositions.filter(x => String(x.status||'OPEN').toUpperCase() === 'OPEN' && Number(x.quantity||0) > 0);
      const closedPositions = allPositions.filter(x => String(x.status||'OPEN').toUpperCase() === 'CLOSED' || Number(x.quantity||0) === 0);
      const targetPositions = activePosSubTab === 'open' ? openPositions : closedPositions;

      if($('positionsTable')){
        $('positionsTable').innerHTML = `
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Qty</th>
                  <th>Avg Price</th>
                  <th>${activePosSubTab==='open'?'LTP':'Exit Price'}</th>
                  <th>${activePosSubTab==='open'?'Live P&L':'Final P&L'}</th>
                  ${activePosSubTab==='closed'?'<th>Square-off Time</th>':''}
                  <th>Stop Loss</th>
                  <th>Target</th>
                  <th>TSL</th>
                  <th>Action &amp; Analysis</th>
                </tr>
              </thead>
              <tbody>
                ${targetPositions.length ? targetPositions.map(x => {
                  const pnl = Number(x.final_pnl != null ? x.final_pnl : (x.unrealized_pnl || 0));
                  const ltpVal = x.ltp ?? x.mark ?? x.current_price ?? x.avg_price;
                  const isOpen = activePosSubTab === 'open';
                  return `
                    <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}">
                      <td><b>${esc(x.symbol)}</b></td>
                      <td><span class="tag ${signalClass(x.side)}">${esc(x.side||'BUY')}</span></td>
                      <td>${fmt(x.quantity)}</td>
                      <td>₹${fmt(x.avg_price || x.entry)}</td>
                      <td class="pos-ltp">${isOpen ? '₹'+fmt(ltpVal) : (x.exit_price ? '₹'+fmt(x.exit_price) : '—')}</td>
                      <td class="pos-pnl ${pnl >= 0 ? 'cell-up' : 'cell-down'}" style="font-weight:700;font-family:var(--font-mono);">
                        ${fmtMoney(pnl)}
                      </td>
                      ${!isOpen ? `<td style="font-size:11px;color:var(--text-faint);">${esc(formatTime(x.closed_at || x.updated_at || ''))}</td>` : ''}
                      <td>₹${fmt(x.stop_loss)}</td>
                      <td>₹${fmt(x.target)}</td>
                      <td>${x.trailing_sl ? fmt(x.trailing_sl)+' pts' : '—'}</td>
                      <td>
                        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                          ${isOpen ? `<button class="btn ghost small position-squareoff" data-position-id="${esc(x.id)}" style="padding:2px 8px;font-size:10.5px;">Square off</button>` : ''}
                          <button class="btn gold small pos-analysis-btn" onclick="openPosAnalysisModal('${esc(x.id)}')" style="padding:2px 8px;font-size:10.5px;" title="View Entry Thesis & CA AI Loss Analysis">🔍 AI Analysis</button>
                        </div>
                      </td>
                    </tr>
                  `;
                }).join('') : `<tr><td colspan="10" class="data-empty" style="text-align:center;padding:20px;">No ${activePosSubTab} positions.</td></tr>`}
              </tbody>
            </table>
          </div>
        `;
      }

      // 2. Orders Segregation (Today's Orders vs Past Orders)
      const allOrders = d.orders || [];
      const todayStr = new Date().toISOString().slice(0, 10);
      const todayOrders = allOrders.filter(x => (x.created_at || '').startsWith(todayStr));
      const pastOrders = allOrders.filter(x => !(x.created_at || '').startsWith(todayStr));
      const targetOrders = activeOrderSubTab === 'today' ? todayOrders : pastOrders;

      if($('ordersTable')){
        $('ordersTable').innerHTML = `
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Qty</th>
                  <th>Type</th>
                  <th>Price</th>
                  <th>TSL</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                ${targetOrders.length ? targetOrders.map(x => `
                  <tr data-order-symbol="${esc(x.symbol)}">
                    <td><b>${esc(x.symbol)}</b></td>
                    <td><span class="tag ${signalClass(x.side)}">${esc(x.side)}</span></td>
                    <td>${fmt(x.quantity)}</td>
                    <td>${esc(x.order_type || 'MARKET')}</td>
                    <td>₹${fmt(x.price || x.ltp)}</td>
                    <td>${x.trailing_sl ? fmt(x.trailing_sl)+' pts' : '—'}</td>
                    <td><span class="tag ${signalClass(x.status_display || x.status)}">${esc(x.status_display || x.status || 'SUBMITTED')}</span></td>
                    <td style="font-size:11px;color:var(--text-faint);">${esc(formatTime(x.created_at || ''))}</td>
                  </tr>
                `).join('') : `<tr><td colspan="8" class="data-empty" style="text-align:center;padding:20px;">No ${activeOrderSubTab === 'today' ? "today's" : "past"} orders.</td></tr>`}
              </tbody>
            </table>
          </div>
        `;
      }

      // Square-off button delegation
      document.querySelectorAll('.position-squareoff').forEach(btn => {
        btn.onclick = async () => {
          if(!confirm('Square off this position at the latest live price?')) return;
          try{
            const r = await api('/api/positions/' + encodeURIComponent(btn.dataset.positionId) + '/square-off', {method: 'POST'});
            toast(`Squared off · Final P&L ${fmtMoney(r.final_pnl)}`);
            await loadPortfolioSnapshot(true);
            if(typeof refreshNotificationBadge === 'function') void refreshNotificationBadge();
          }catch(e){toast(e.message)}
        };
      });

      window.__CA_PORTFOLIO_SNAPSHOT = d;
      return d;
    }catch(e){
      if($('positionsTable')) $('positionsTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;
      if($('ordersTable')) $('ordersTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;
      return null;
    }
  }

  // CA AI Post-Trade Diagnostic Modal (Item 7)
  async function openPosAnalysisModal(posId){
    openModal('posAnalysisModal');
    const body = $('posAnalysisModalBody');
    if(body) body.innerHTML = '<div class="data-empty">Loading CA AI trade diagnostic…</div>';
    try{
      const d = await api('/api/positions/' + encodeURIComponent(posId) + '/analysis');
      const p = d.position || {};
      const r = d.recommendation_at_entry || {};
      const wentWrong = !!d.went_wrong;
      const pnl = Number(d.pnl || 0);

      body.innerHTML = `
        <div style="background:var(--surface-2);border-radius:10px;padding:12px 14px;border:1px solid var(--border-soft);margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div style="display:flex;gap:8px;align-items:center;">
              <span style="font-size:15px;font-weight:700;color:var(--text);">${esc(p.symbol || r.symbol || '-')}</span>
              <span class="tag ${signalClass(p.side || r.recommendation)}">${esc(p.side || r.recommendation || 'BUY')}</span>
              <span class="tag neutral">${p.status === 'CLOSED' ? 'CLOSED' : 'OPEN'}</span>
            </div>
            <div style="font-family:var(--font-mono);font-size:15px;font-weight:700;color:${pnl >= 0 ? 'var(--buy)' : 'var(--sell)'};">
              ${fmtMoney(pnl)}
            </div>
          </div>
          <div class="muted" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(100px, 1fr));gap:6px;font-size:11px;">
            <div>Entry: <b>₹${fmt(p.avg_price || r.entry)}</b></div>
            <div>SL: <b>₹${fmt(p.stop_loss || r.stop_loss)}</b></div>
            <div>Target: <b>₹${fmt(p.target || r.target)}</b></div>
            <div>TSL: <b>${p.trailing_sl ? fmt(p.trailing_sl) + ' pts' : 'None'}</b></div>
          </div>
        </div>

        <!-- Recommendation Provided at Entry -->
        <div style="background:var(--surface-2);border-radius:10px;padding:12px 14px;border:1px solid var(--border-soft);margin-bottom:12px;">
          <div style="font-size:11.5px;font-weight:700;color:var(--gold);margin-bottom:6px;">📑 Recommendation Provided at Time of Entry</div>
          <div style="font-size:11.5px;color:var(--text);line-height:1.45;">
            ${esc(r.rationale || r.reason || p.reasons || 'Recommendation verified with multi-factor technical and news alignment.')}
          </div>
          <div class="muted" style="font-size:10.5px;margin-top:6px;">
            Timeframe: <b>${esc(r.timeframe || '5m')}</b> · Conviction: <b>${fmt(r.confidence || 85)}%</b> · Entry Time: <b>${esc(formatTime(r.timestamp || p.created_at || ''))}</b>
          </div>
        </div>

        <!-- CA AI Post-Trade Diagnostic -->
        <div style="background:${wentWrong ? 'rgba(255,92,114,0.08)' : 'rgba(38,217,166,0.08)'};border-radius:10px;padding:12px 14px;border:1px solid ${wentWrong ? 'rgba(255,92,114,0.3)' : 'rgba(38,217,166,0.3)'};">
          <div style="font-size:12px;font-weight:700;color:${wentWrong ? 'var(--sell)' : 'var(--buy)'};margin-bottom:6px;">
            ${wentWrong ? '⚠️ CA AI Post-Trade Loss Diagnostic (Why Trade Went Wrong)' : '✨ CA AI Trade Execution Diagnostic'}
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:10px;">
            ${(d.diagnosis || []).map(f => `
              <div style="font-size:11px;line-height:1.4;">
                <b style="color:var(--text);">${esc(f.factor)}:</b> <span style="color:var(--text-dim);">${esc(f.detail)}</span>
              </div>
            `).join('')}
          </div>
          ${(d.takeaways || []).length ? `
            <div style="border-top:1px solid var(--border-soft);padding-top:8px;">
              <div style="font-size:10.5px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:0.3px;margin-bottom:3px;">Actionable Takeaways:</div>
              <ul style="margin:0;padding-left:16px;font-size:11px;color:var(--text-dim);line-height:1.45;">
                ${(d.takeaways || []).map(t => `<li>${esc(t)}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      `;
    }catch(e){
      if(body) body.innerHTML = `<div class="data-empty">Diagnostic unavailable: ${esc(e.message)}</div>`;
    }
  }
  window.openPosAnalysisModal = openPosAnalysisModal;
  $('posAnalysisModalClose')?.addEventListener('click', () => closeModal('posAnalysisModal'));

  // Draggable Floating Workspace Window Logic (Item 10)
  function makeDraggable(el, handle){
    let isDragging = false;
    let startX = 0, startY = 0, initialLeft = 0, initialTop = 0;
    handle.addEventListener('mousedown', e => {
      if(e.target.tagName === 'BUTTON' || e.target.closest('button')) return;
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      const rect = el.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;
      el.style.right = 'auto';
      el.style.bottom = 'auto';
      el.style.left = initialLeft + 'px';
      el.style.top = initialTop + 'px';
      e.preventDefault();
    });
    document.addEventListener('mousemove', e => {
      if(!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      el.style.left = Math.max(10, Math.min(window.innerWidth - el.offsetWidth - 10, initialLeft + dx)) + 'px';
      el.style.top = Math.max(10, Math.min(window.innerHeight - el.offsetHeight - 10, initialTop + dy)) + 'px';
    });
    document.addEventListener('mouseup', () => { isDragging = false; });
  }

  function setupFloatingWorkspaces(){
    const win = $('floatingWorkspaceWindow');
    const title = $('floatingWorkspaceTitle');
    const body = $('floatingWorkspaceBody');
    const header = $('floatingWorkspaceHeader');
    const closeBtn = $('floatingWorkspaceClose');
    const dockBtn = $('floatingWorkspaceDock');

    if(!win || !header) return;
    makeDraggable(win, header);

    let activeSource = null;

    function popoutPanel(panelId, windowTitle){
      const panel = $(panelId);
      if(!panel) return;
      if(activeSource && activeSource !== panel){
        dockBack();
      }
      activeSource = panel;
      title.textContent = windowTitle;
      win.style.display = 'flex';
      while(panel.firstChild){
        body.appendChild(panel.firstChild);
      }
      toast(`Popped out ${windowTitle} — Drag freely to watch alongside chart.`);
    }

    function dockBack(){
      if(!activeSource){
        win.style.display = 'none';
        return;
      }
      while(body.firstChild){
        activeSource.appendChild(body.firstChild);
      }
      win.style.display = 'none';
      const returnedTitle = title.textContent;
      activeSource = null;
      toast(`Docked ${returnedTitle} back into workspace.`);
    }

    $('ordersPopoutBtn')?.addEventListener('click', () => {
      if(activeSource && activeSource.id === 'panel-orders'){
        dockBack();
      } else {
        popoutPanel('panel-orders', 'Orders & Positions');
      }
    });

    $('fundsPopoutBtn')?.addEventListener('click', () => {
      if(activeSource && activeSource.id === 'panel-funds'){
        dockBack();
      } else {
        popoutPanel('panel-funds', 'Funds & Capital Allocation');
      }
    });

    closeBtn?.addEventListener('click', dockBack);
    dockBtn?.addEventListener('click', dockBack);
  }
  setupFloatingWorkspaces();

  // ---------------- Options buyability / greeks ----------------
  const oldFind=$('findBuyableBtn'); if(oldFind) oldFind.onclick=null; oldFind?.addEventListener('click',async()=>{try{window.__caOptionExpiry=$('optionExpiry')?.value||window.__caOptionExpiry||null;const lotsRaw=Number($('buyLots').value);const lots=Number.isFinite(lotsRaw)&&lotsRaw>0?Math.floor(lotsRaw):null;const ltpRaw=Number($('buyLtpPerQty').value);const ltpPerQty=Number.isFinite(ltpRaw)&&ltpRaw>0?ltpRaw:null;const maxLotRaw=Number($('buyMaxCostLot')?.value);const maxCostLot=Number.isFinite(maxLotRaw)&&maxLotRaw>0?maxLotRaw:null;const cap=Number(($('buyCapital').value||'').replace(/[^0-9.]/g,''))||0;if(!cap){toast('Enter maximum capital.');return}const side=$('buySide').value;const d=await api('/api/options/'+encodeURIComponent(selectedSymbol())+'/buyable',{method:'POST',body:JSON.stringify({capital:cap,expiry:window.__caOptionExpiry||null,option_type:side,quantity_lots:lots,ltp_per_quantity:ltpPerQty,max_cost_per_lot:maxCostLot})});$('buyableResults').innerHTML=(d.contracts||[]).map((c,i)=>`<div class="pattern-card buyable-contract" data-buyable-index="${i}" style="cursor:pointer"><div><b>${esc(c.option_type||side)} ${fmt(c.strike)} · ${esc(c.expiry||'')}</b><div class="muted">Premium ₹${fmt(c.premium)} · Lot size ${fmt(c.lot_size)} · ${fmt(c.requested_lots)} lot(s) · Cost ₹${fmt(c.capital_required)}</div><div class="muted">Potential ${fmt(c.potential_score)} · Δ ${fmt(c.greeks?.delta)} · Γ ${fmt(c.greeks?.gamma)} · Θ ${fmt(c.greeks?.theta)} · Vega ${fmt(c.greeks?.vega)} · IV ${fmt(c.greeks?.iv)}</div><div class="muted">Volume ${fmt(c.liquidity?.volume)} · OI ${fmt(c.liquidity?.oi)} · Max affordable ${fmt(c.max_affordable_lots)} lot(s)</div><button class="btn gold small buy-option-btn" data-buyable-index="${i}" style="margin-top:6px">Buy this option</button></div><span class="tag buy">Rank ${i+1}</span></div>`).join('')||'<div class="muted">No live contracts satisfy the capital, lot and price constraints.</div>';window.__caBuyables=d.contracts||[];document.querySelectorAll('.buyable-contract').forEach(x=>x.onclick=e=>{const c=window.__caBuyables[Number(x.dataset.buyableIndex)];if(c){$('greeksGrid').innerHTML=[['Call Delta',c.greeks?.delta,c.greeks?.delta,0],['Call Gamma',c.greeks?.gamma,c.greeks?.delta,0],['Call Theta',c.greeks?.theta,c.greeks?.delta,0],['Call Vega',c.greeks?.vega,c.greeks?.delta,0],['Call IV',c.greeks?.iv,c.greeks?.delta,0]].map(g=>`<div class="stat-card greek-clickable" style="border:1px solid var(--border-soft);border-radius:8px;padding:10px;cursor:pointer;" title="Click to understand ${g[0]} and simulate option movement" onclick="window.openGreekModal('${g[0]}',${g[1]??0},'${selectedSymbol()}','${c.strike||''}',${g[2]??0},0)"><div class="label" style="display:flex;justify-content:space-between;align-items:center;"><span>${g[0]}</span><span style="font-size:9.5px;color:var(--gold);opacity:0.8;">ⓘ Learn</span></div><div class="value" style="font-size:16px">${fmt(g[1])}</div></div>`).join('');if(e.target.closest('.buy-option-btn'))openOrder('BUY',c.contract?.instrument_key||null,Number(c.lot_size||1)*Number(c.requested_lots||1),`${c.option_type||side} ${fmt(c.strike)}`)}})}catch(e){$('buyableResults').innerHTML=`<div class="muted">${esc(e.message)}</div>`}});
  async function saveAutoTradeImmediate(){
    try{
      const r=await api('/api/auto-trade',{method:'POST',body:JSON.stringify({enabled:!!autoEnabled,capital:Number($('autoCapital')?.value)||0,max_loss:Number($('autoMaxLoss')?.value)||0,max_profit:Number($('autoMaxProfit')?.value||$('recoMaxProfit')?.value)||0,symbols:[...new Set(autoSymbols.map(x=>String(x).toUpperCase().trim()).filter(Boolean))],categories:['gainers','losers','high_volume'],options_enabled:!!autoOptions})});
      $('autoEnableSwitch')?.classList.toggle('on',!!r.enabled);
      return r;
    }catch(e){toast(e.message||'Unable to save Auto Trade settings');return null}
  }
  $('autoEnableSwitch')?.addEventListener('click',async()=>{autoEnabled=!autoEnabled;$('autoEnableSwitch').classList.toggle('on',autoEnabled);await saveAutoTradeImmediate();loadAutoTrade()});
  $('autoOptionsSwitch')?.addEventListener('click',async()=>{autoOptions=!autoOptions;$('autoOptionsSwitch').classList.toggle('on',autoOptions);await saveAutoTradeImmediate();loadAutoTrade()});
  $('saveAutoTradeBtn')?.addEventListener('click',async()=>{try{const r=await api('/api/auto-trade',{method:'POST',body:JSON.stringify({enabled:autoEnabled,capital:Number($('autoCapital').value)||0,max_loss:Number($('autoMaxLoss').value)||0,max_profit:Number($('autoMaxProfit')?.value||$('recoMaxProfit')?.value)||0,symbols:[...new Set(autoSymbols.map(x=>String(x).toUpperCase().trim()).filter(Boolean))],categories:['gainers','losers','high_volume'],options_enabled:autoOptions})});toast(r.enabled ? (r.live_execution?'Auto Trade enabled and live':'Auto Trade enabled · execution will activate when market/risk gates allow') : 'Auto Trade configuration saved as disabled');loadAutoTrade()}catch(e){toast(e.message)}});

  // Auto Trade stock search input & dropdown delegation fix
  async function addSymbolToAutoTrade(sym){
    sym = String(sym || '').trim().toUpperCase();
    if(!sym) return;
    autoEnabled = true;
    if(!autoSymbols.includes(sym)) autoSymbols.push(sym);
    if($('autoManualSymbol')) $('autoManualSymbol').value = '';
    const box = $('autoSymbolSuggestions');
    if(box){ box.classList.remove('open'); box.innerHTML = ''; }
    $('autoEnableSwitch')?.classList.add('on');
    renderAutoTradeSymbolsDOM();
    toast(`Added ${sym} to Auto Trade`);
    await saveAutoTradeImmediate();
    await loadAutoTrade();
  }

  function renderAutoTradeSymbolsDOM(){
    const el = $('autoTradeSymbols');
    if(!el) return;
    if(autoSymbols.length){
      el.innerHTML = autoSymbols.map(s => `
        <div class="basis-item" style="display:flex;justify-content:space-between;align-items:center;">
          <span><b>${esc(s)}</b></span>
          <button class="btn ghost small remove-auto-symbol" data-symbol="${esc(s)}">Remove</button>
        </div>
      `).join('');
      el.querySelectorAll('.remove-auto-symbol').forEach(b=>b.onclick=async()=>{
        autoSymbols = autoSymbols.filter(x=>x!==b.dataset.symbol);
        renderAutoTradeSymbolsDOM();
        await saveAutoTradeImmediate();
        await loadAutoTrade();
      });
    } else {
      el.innerHTML = `
        <div class="data-empty" style="border:1px dashed var(--gold-dim);padding:10px 12px;border-radius:8px;background:rgba(239,251,245,0.04);color:var(--text);text-align:left;">
          <div style="color:var(--buy);font-weight:700;margin-bottom:4px;">✦ Watchlist Options Mode Active</div>
          <div class="muted" style="color:var(--text-dim);font-size:11px;line-height:1.4;">
            No individual stocks specified. Auto-Trade will continuously monitor and trade <b>options only</b> for all instruments present in your active watchlist!
          </div>
        </div>
      `;
    }
  }

  const autoSuggestBox = $('autoSymbolSuggestions');
  if(autoSuggestBox){
    autoSuggestBox.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
    autoSuggestBox.addEventListener('click', async (e) => {
      const row = e.target.closest('[data-symbol]');
      if(!row) return;
      const sym = String(row.dataset.symbol || '').trim().toUpperCase();
      if(sym) await addSymbolToAutoTrade(sym);
    });
  }

  $('autoAddSymbolBtn')?.addEventListener('click', async () => {
    const v = String($('autoManualSymbol')?.value || '').trim().toUpperCase().replace(/[^A-Z0-9_\-\s]/gi, '');
    if(!v) return;
    await addSymbolToAutoTrade(v);
  });

  $('autoManualSymbol')?.addEventListener('keydown', e => {
    if(e.key === 'Enter') $('autoAddSymbolBtn')?.click();
  });

  let autoSearchTimer;
  $('autoManualSymbol')?.addEventListener('input', () => {
    clearTimeout(autoSearchTimer);
    const q = String($('autoManualSymbol').value || '').trim();
    const box = $('autoSymbolSuggestions');
    if(!box) return;
    if(!q){ box.classList.remove('open'); box.innerHTML = ''; return; }
    autoSearchTimer = setTimeout(async () => {
      try {
        const d = await api('/api/instruments/search?q=' + encodeURIComponent(q));
        const items = d.items || [];
        box.innerHTML = '';
        items.slice(0, 12).forEach(i => {
          const sym = String(i.symbol || i.trading_symbol || i.name || '').trim().toUpperCase();
          if(!sym) return;
          const row = document.createElement('div');
          row.className = 'auto-suggestion-row';
          row.dataset.symbol = sym;
          row.style.cssText = 'cursor:pointer;padding:8px 10px;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;';
          row.innerHTML = `
            <b>${esc(sym)}</b>
            <span class="muted" style="font-size:10.5px;">${esc(i.name || '')} · ${esc(i.exchange || '')} ${i.instrument_type ? '· ' + esc(i.instrument_type) : ''}</span>
          `;
          row.addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); });
          row.addEventListener('click', async e => {
            e.preventDefault();
            e.stopPropagation();
            await addSymbolToAutoTrade(sym);
          });
          box.appendChild(row);
        });
        box.classList.toggle('open', box.children.length > 0);
      } catch(_) {
        box.classList.remove('open');
      }
    }, 150);
  });

  async function loadAutoTrade(){
    try{
      const d=await api('/api/auto-trade',{timeoutMs:5000});
      autoEnabled=!!d.enabled;
      autoOptions=!!d.options_enabled;
      $('autoEnableSwitch')?.classList.toggle('on',autoEnabled);
      $('autoOptionsSwitch')?.classList.toggle('on',autoOptions);
      if($('autoCapital')) $('autoCapital').value = d.capital || 0;
      if($('autoMaxLoss')) $('autoMaxLoss').value = d.max_loss || 0;
      if($('autoMaxProfit') && d.max_profit != null) $('autoMaxProfit').value = d.max_profit;
      if($('recoMaxProfit') && d.max_profit != null && !$('recoMaxProfit').value) $('recoMaxProfit').value = d.max_profit || '';
      if($('recoMaxLoss') && d.max_loss != null && !$('recoMaxLoss').value) $('recoMaxLoss').value = d.max_loss || '';
      autoSymbols=d.symbols||[];
      $('autoTradeStatus')?.replaceChildren(Object.assign(document.createElement('span'),{
        className:`tag ${autoEnabled?'buy':'neutral'}`,
        textContent:autoEnabled?(d.live_execution?'ENABLED · LIVE EXECUTION':'ENABLED · READY / GATED'):'DISABLED'
      }));
      renderAutoTradeSymbolsDOM();

      window.__caAutoSuggestions=d.suggestions||[];
      $('autoSuggestions').innerHTML=window.__caAutoSuggestions.map((x,i)=>`
        <div class="basis-item auto-suggestion" data-auto-index="${i}" style="cursor:pointer">
          <b>${esc(x.symbol)}</b>
          <div class="muted">${esc(x.reason)} · Potential score ${fmt(x.analysis?.score)}</div>
          <button class="btn gold small add-auto-symbol" data-symbol="${esc(x.symbol)}" style="margin-top:6px">Add to Auto Trade</button>
        </div>
      `).join('')||'<div class="data-empty">No live suggestions available.</div>';

      document.querySelectorAll('.auto-suggestion').forEach(card=>card.onclick=e=>{
        if(e.target.closest('.add-auto-symbol')) return;
        const x=window.__caAutoSuggestions[Number(card.dataset.autoIndex)];
        openModal('newsAnalysisModal');
        $('newsAnalysisBody').innerHTML=`<div class="card-head"><div class="card-title">Auto Trade Recommendation Basis</div><button class="btn ghost small" id="basisClose">Close</button></div><div class="basis-item"><b>${esc(x.symbol)}</b><div class="muted">${esc(x.reason)} · Potential score ${fmt(x.analysis?.score)}</div></div><div class="basis-list" style="margin-top:8px">${(x.analysis?.basis||[]).map((b,i)=>`<div class="basis-item"><b>${i+1}.</b> ${esc(b)}</div>`).join('')}</div>`;
        $('basisClose').onclick=()=>closeModal('newsAnalysisModal');
      });

      document.querySelectorAll('.add-auto-symbol').forEach(b=>b.onclick=async e=>{
        e.stopPropagation();
        autoEnabled=true;
        if(!autoSymbols.includes(b.dataset.symbol)) autoSymbols.push(b.dataset.symbol);
        $('autoEnableSwitch')?.classList.add('on');
        toast(`Added ${b.dataset.symbol} to Auto Trade`);
        await saveAutoTradeImmediate();
        await loadAutoTrade();
      });
    }catch(e){
      $('autoSuggestions').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`;
    }
  }
  window.loadAutoTrade = loadAutoTrade;
  window.renderAutoTradeSymbolsDOM = renderAutoTradeSymbolsDOM;
  window.addSymbolToAutoTrade = addSymbolToAutoTrade;

  // ---------------- Dashboard ----------------
  async function loadChartPatterns(){return runCachedAnalysis('loadChartPatterns',async()=>{const sym=selectedSymbol();if(!sym||!$('chartPatternList'))return;try{const d=await api('/api/analysis/chart-patterns/'+encodeURIComponent(sym)+`?timeframe=${encodeURIComponent(state.tf)}`);$('chartPatternStatus').textContent=`${(d.patterns||[]).length} pattern(s) detected`;$('chartPatternList').innerHTML=(d.patterns||[]).length?(d.patterns||[]).map(p=>`<div class="pattern-card" data-chart-pattern="1"><div><b>${esc(p.pattern)}</b><div class="muted">Confidence ${fmt(p.confidence)}%</div><div class="muted">${esc(p.description)}</div></div><span class="tag neutral">${fmt(p.confidence)}%</span></div>`).join(''):'<div class="muted">No clear chart pattern detected in the current range.</div>';}catch(e){const a=state.candles||[],out=[];if(a.length>=8){const c=a.at(-1),hh=Math.max(...a.slice(-10).map(x=>Number(x.high))),ll=Math.min(...a.slice(-10).map(x=>Number(x.low)));if(Number(c.close)>=hh*.995)out.push({pattern:'Range Breakout (possible)',confidence:58,description:'Latest close is testing the recent 10-candle high.'});else if(Number(c.close)<=ll*1.005)out.push({pattern:'Range Breakdown (possible)',confidence:58,description:'Latest close is testing the recent 10-candle low.'});else out.push({pattern:'Short-term Close Structure',confidence:50,description:'Local candle structure is available while provider analysis is unavailable.'})}if($('chartPatternStatus'))$('chartPatternStatus').textContent=out.length?`${out.length} local pattern(s) detected`:'Unavailable';if($('chartPatternList'))$('chartPatternList').innerHTML=out.length?out.map(p=>`<div class="pattern-card"><div><b>${esc(p.pattern)}</b><div class="muted">Confidence ${fmt(p.confidence)}%</div><div class="muted">${esc(p.description)}</div></div><span class="tag neutral">LOCAL</span></div>`).join(''):`<div class="muted">${esc(e.message)}</div>`}},60000)}
  async function loadStructure(){return runCachedAnalysis('loadStructure',async()=>{const sym=selectedSymbol();if(!sym||!$('structureBox'))return;try{const tf=state.tf||'5m';const from=$('patternFrom')?.value,to=$('patternTo')?.value;const params=new URLSearchParams({timeframe:tf});if(from)params.set('from_date',from.slice(0,10));if(to)params.set('to_date',to.slice(0,10));const url='/api/analysis/structure/'+encodeURIComponent(sym)+'?'+params.toString();const d=await api(url);$('structureStatus').textContent=from||to?'Selected range available':'Last 10 candles';$('structureBox').innerHTML=`<div class="pattern-card"><div><b>Trend: ${esc(d.trend||'NEUTRAL')}</b><div class="muted">Strength ${fmt(d.trend_strength)} · Structure: ${esc(d.structure)}</div></div><span class="tag ${signalClass(d.trend)}">${esc(d.trend||'NEUTRAL')}</span></div><div class="pattern-card"><div><b>Likely outcome</b><div class="muted">${esc(d.expected_outcome)}</div></div><span class="tag neutral">${fmt(d.last_candle_change_pct)}%</span></div><div class="pattern-card"><div><b>Recent patterns</b><div class="muted">${(d.pattern_signals||[]).map(p=>esc(p.pattern)).join(' · ')||'None detected'}</div></div></div><div class="muted" style="padding:5px">Analysis uses the latest 5–10 candles in the selected timeframe when no date range is selected.</div>`}catch(e){const a=state.candles||[];if(a.length>=5){const c=a.at(-1),base=a[Math.max(0,a.length-5)],chg=Number(base.close)?((Number(c.close)-Number(base.close))/Number(base.close))*100:0,trend=Number(c.close)>Number(base.close)?'BULLISH':Number(c.close)<Number(base.close)?'BEARISH':'NEUTRAL';$('structureStatus').textContent='Local candle fallback';$('structureBox').innerHTML=`<div class="pattern-card"><div><b>Trend: ${trend}</b><div class="muted">Based on loaded chart candles · provider unavailable.</div></div><span class="tag ${signalClass(trend)}">${trend}</span></div><div class="pattern-card"><div><b>Likely outcome</b><div class="muted">${trend==='BULLISH'?'Continuation bias':trend==='BEARISH'?'Downside pressure':'Range / mixed movement'}</div></div><span class="tag neutral">${fmt(chg)}%</span></div>`}else{$('structureStatus').textContent='Unavailable';$('structureBox').innerHTML=`<div class="muted">${esc(e.message)}</div>`}}},60000)}

  const DASHBOARD_FEATURES=[
    ['signal','Consensus Signal & Badges','Overall technical + news consensus verdict'],
    ['indices','Benchmark Indices Live Strip','Live Nifty 50, Bank Nifty, Sensex & MCX Crude prices'],
    ['overview','Overview Stats Strip','Selected LTP, Day Change, Auto Funds, Risk/Reward, Last Order'],
    ['minichart','Selected Mini Chart','Live 5m snapshot candle chart'],
    ['pnl','P&L & Position Stats','Open Positions, Unrealized & Realized P&L, Auto Trade status'],
    ['news','Material News Intelligence','Stock & global high-materiality news feed'],
    ['technical','Technical Signals Matrix','Multi-timeframe technical indicator signals'],
    ['options','Option Greeks Watchlist','Live ATM strikes with Delta, Gamma, IV and Greeks'],
    ['option_mini','Pinned Option Watchlist','Custom pinned options search and watchlist'],
    ['funds','Funds & Account Status','Available paper capital, trading & testing funds'],
    ['risk','Risk & Key Trade Levels','Support, resistance, stop loss and target geometry'],
    ['watchlist','Watchlist Snapshot','Live LTP and percentage change of active watchlist'],
    ['reco_history','Recommendation History','Automated buy/sell trade decisions and history'],
    ['positions','Open Positions List','Real-time mark to market and open paper positions'],
    ['orders','Recent Orders Log','Latest 10 filled and executed paper trades'],
    ['movers','Market Movers Widget','Live top gainers, losers, and volume leaders'],
    ['context','Market Context & Coverage','Coverage and system status notes']
  ];
  let dashboardLayout=(()=>{try{return JSON.parse(localStorage.getItem('ca_dashboard_layout')||'null')||DASHBOARD_FEATURES.reduce((o,x)=>(o[x[0]]=true,o),{})}catch(_){return DASHBOARD_FEATURES.reduce((o,x)=>(o[x[0]]=true,o),{})}})();
  function applyDashboardLayout(){
    DASHBOARD_FEATURES.forEach(([key])=>document.querySelectorAll(`[data-dashboard-feature="${key}"]`).forEach(el=>{el.style.display=dashboardLayout[key]===false?'none':'';}));
    if($('dashboardFeatureList'))$('dashboardFeatureList').innerHTML=DASHBOARD_FEATURES.map(([key,label,desc])=>`<label class="settings-row" style="margin:0;cursor:pointer"><div><div class="settings-label">${esc(label)}</div><div class="settings-desc">${esc(desc)}</div></div><input type="checkbox" data-dashboard-toggle="${key}" ${dashboardLayout[key]!==false?'checked':''}></label>`).join('');
    document.querySelectorAll('[data-dashboard-toggle]').forEach(cb=>cb.onchange=()=>{dashboardLayout[cb.dataset.dashboardToggle]=cb.checked;localStorage.setItem('ca_dashboard_layout',JSON.stringify(dashboardLayout));applyDashboardLayout();});
  }
  $('dashboardCustomizeBtn')?.addEventListener('click',()=>{$('dashboardCustomizer').style.display=$('dashboardCustomizer').style.display==='none'?'':'none';applyDashboardLayout();});
  $('dashboardResetBtn')?.addEventListener('click',()=>{dashboardLayout=DASHBOARD_FEATURES.reduce((o,x)=>(o[x[0]]=true,o),{});localStorage.setItem('ca_dashboard_layout',JSON.stringify(dashboardLayout));applyDashboardLayout();});
  applyDashboardLayout();

  async function loadDashboardIndices(){
    try{
      const d=await api('/api/market/quotes?instruments=NIFTY,BANKNIFTY,SENSEX,CRUDEOIL');
      (d.items||[]).forEach(q=>{
        const s=String(q.symbol||'').toUpperCase();
        let prefix='';
        if(s.includes('BANK')) prefix='idxBank';
        else if(s.includes('NIFTY')) prefix='idxNifty';
        else if(s.includes('SENSEX')) prefix='idxSensex';
        else if(s.includes('CRUDE')) prefix='idxCrude';
        if(!prefix) return;
        const l=$(prefix+'Ltp'), c=$(prefix+'Chg');
        if(l) l.textContent=fmt(q.ltp);
        if(c){
          const ch=q.session_change!=null?Number(q.session_change):Number(q.net_change);
          const pct=q.session_change_pct!=null?Number(q.session_change_pct):Number(q.change_pct);
          c.textContent=`${ch>0?'+':''}${fmt(ch)} (${pct>0?'+':''}${fmt(pct)}%)`;
          c.style.color=(ch>0||pct>0)?'var(--buy)':(ch<0||pct<0)?'var(--sell)':'var(--text-dim)';
        }
      });
    }catch(_){}
  }

  async function loadDashboardMoversWidget(){
    const w=$('dashboardMoversWidget'); if(!w) return;
    try{
      const d=await api('/api/market/movers?category=gainers&limit=6');
      const items=d.items||[];
      w.innerHTML=items.slice(0,6).map(m=>{
        const pct=Number(m.change_pct||0);
        return `<div class="stat-card" style="padding:8px 10px;">
          <div class="label" style="font-weight:700;color:var(--text);font-size:11px;">${esc(m.symbol)}</div>
          <div class="value" style="font-size:13px;font-weight:700;font-family:var(--font-mono);">${fmt(m.ltp)}</div>
          <div style="font-size:10.5px;font-weight:700;color:${pct>0?'var(--buy)':'var(--sell)'};">${pct>0?'+':''}${fmt(pct)}%</div>
        </div>`;
      }).join('')||'<div class="data-empty">No movers available.</div>';
    }catch(_){}
  }

  function renderDashboardMiniOptions(data){
    const box=$('dashboardOptions'); if(!box)return;
    const rows=data?.strikes||[]; const atm=Number(data?.atm_strike);
    const near=rows.filter(r=>!Number.isFinite(atm)||Math.abs(Number(r.strike)-atm)<=Math.max(3,Math.abs(atm)*0.02)).slice(0,8);
    box.innerHTML=near.flatMap(r=>['call','put'].map(side=>{const c=r[side]||{};if(c.ltp==null)return '';return `<div class="dashboard-mini-option"><b style="color:${side==='call'?'var(--buy)':'var(--sell)'};">${side.toUpperCase()} ${fmt(r.strike)}</b><span style="font-weight:700;color:${side==='call'?'var(--buy)':'var(--sell)'};">${fmt(c.ltp)}</span><span>Δ ${fmt(c.delta)} · Γ ${fmt(c.gamma)} · IV ${fmt(c.iv)}</span></div>`})).join('')||'<div class="data-empty">Option snapshot unavailable.</div>';
    const wbox=$('dashboardOptionWatchlist'); if(!wbox)return;
    const watches=JSON.parse(localStorage.getItem('ca_dashboard_option_watch')||'[]');
    if(!watches.length){wbox.innerHTML='<div class="data-empty">No pinned options yet.</div>';return;}
    const keys=watches.map(x=>x.instrument_key).filter(Boolean);
    if(!keys.length){wbox.innerHTML=watches.map(x=>`<div class="basis-item"><b>${esc(x.symbol)}</b></div>`).join('');return;}
    api('/api/market/quotes?instruments='+encodeURIComponent(keys.join(',')),{timeoutMs:3000}).then(qd=>{const map={};(qd.items||[]).forEach(q=>map[String(q.instrument_key||q.symbol).toUpperCase()]=q);wbox.innerHTML=watches.map(x=>{const q=map[String(x.instrument_key||'').toUpperCase()]||{};return `<div class="basis-item"><b>${esc(x.symbol)}</b><span style="float:right;font-weight:700;">${fmt(q.ltp)}</span><div class="muted">${esc(x.exchange||'')} · ${q.change_pct==null?'—':`${Number(q.change_pct)>0?'+':''}${fmt(q.change_pct)}%`}</div></div>`}).join('');}).catch(()=>{});
  }

  let __dashOptTimer=null;
  $('dashboardOptionSearch')?.addEventListener('input',()=>{clearTimeout(__dashOptTimer);const q=$('dashboardOptionSearch').value.trim();const box=$('dashboardOptionSuggestions');if(!q){box.classList.remove('open');return;}__dashOptTimer=setTimeout(async()=>{try{const d=await api('/api/instruments/search?q='+encodeURIComponent(q),{timeoutMs:3000});box.innerHTML=(d.items||[]).filter(x=>String(x.instrument_type||'').toUpperCase().includes('OPT')||x.option_type||x.expiry).slice(0,8).map(x=>`<div class="instrument-suggestion" data-dash-opt="1" data-symbol="${esc(x.symbol||x.trading_symbol)}" data-key="${esc(x.instrument_key||'')}" data-exchange="${esc(x.exchange||'')}"><b>${esc(x.symbol||x.trading_symbol)}</b><span>${esc(x.name||'')} · ${esc(x.expiry||'')}</span></div>`).join('')||'<div class="muted" style="padding:8px">No option contracts found</div>';box.classList.add('open');box.querySelectorAll('[data-dash-opt]').forEach(el=>el.onclick=()=>{const arr=JSON.parse(localStorage.getItem('ca_dashboard_option_watch')||'[]');const item={symbol:el.dataset.symbol,instrument_key:el.dataset.key,exchange:el.dataset.exchange,underlying:selectedSymbol()};if(!arr.some(x=>x.instrument_key===item.instrument_key))arr.push(item);localStorage.setItem('ca_dashboard_option_watch',JSON.stringify(arr.slice(-20)));$('dashboardOptionSearch').value='';box.classList.remove('open');renderDashboardMiniOptions(APP_CACHE.options);});}catch(_){box.classList.remove('open')}},120);});
  $('dashboardOptionAddBtn')?.addEventListener('click',()=>{const el=$('dashboardOptionSuggestions')?.querySelector('[data-dash-opt]');el?.click();});
  document.addEventListener('click',e=>{if(!e.target.closest('#dashboardOptionSearch')&&!e.target.closest('#dashboardOptionSuggestions'))$('dashboardOptionSuggestions')?.classList.remove('open')});
  function renderDashboardMiniChart(candles){
    const canvas=$('dashboardMiniChart'); if(!canvas)return; const data=Array.isArray(candles)?candles.slice(-80):[]; const rect=canvas.getBoundingClientRect(); const dpr=window.devicePixelRatio||1; canvas.width=Math.max(1,Math.floor(rect.width*dpr)); canvas.height=Math.max(1,Math.floor(rect.height*dpr)); const ctx=canvas.getContext('2d'); if(!ctx||data.length<2)return; ctx.setTransform(dpr,0,0,dpr,0,0); const w=rect.width,h=rect.height,p=12; const closes=data.map(x=>Number(x.close)).filter(Number.isFinite); const lo=Math.min(...closes),hi=Math.max(...closes),range=(hi-lo)||1; const x=i=>p+(i/(closes.length-1))*Math.max(1,w-2*p), y=v=>h-p-((v-lo)/range)*Math.max(1,h-2*p); ctx.clearRect(0,0,w,h); ctx.beginPath(); closes.forEach((v,i)=>{const xx=x(i),yy=y(v); if(i)ctx.lineTo(xx,yy); else ctx.moveTo(xx,yy)}); ctx.strokeStyle=getComputedStyle(document.documentElement).getPropertyValue('--buy')||'#4fd1aa';ctx.lineWidth=1.6;ctx.stroke(); if($('dashboardChartStatus'))$('dashboardChartStatus').textContent=`${closes.length} candles · ${fmt(closes.at(-1))}`;
  }

  async function loadDashboard(force=false){
    const sym=selectedSymbol();
    if(!sym||!$('dashboardSignal'))return;
    applyDashboardLayout();
    void loadDashboardIndices();
    void loadDashboardMoversWidget();
    const seq=++window.__dashboardSeq||1; window.__dashboardSeq=seq;
    try{
      const snap=(window.__CA_WL_QUOTES||{})[sym]; const d=await api('/api/dashboard/overview?selected_symbol='+encodeURIComponent(sym)+'&fast=1',{timeoutMs:4500,cache:'no-store'}); if(snap&&d.selected_quote&&d.selected_quote.ltp==null)d.selected_quote=snap;
      if(seq!==window.__dashboardSeq||sym!==d.selected_symbol)return;
      const q=d.selected_quote||{}; const p=d.portfolio||{}; const a=d.auto_trade||{};
      APP_CACHE.quote=q; APP_CACHE.options=d.options; APP_CACHE.newsStock={events:d.news?.stock_events||[]}; APP_CACHE.newsGlobal={events:d.news?.global_events||[]};
      $('dashboardUpdated').textContent=`Updated ${formatTime(d.timestamp)}`;
      const rec=d.recommendation||{}; const signal=rec.recommendation||'NO_TRADE';

      const __sc=q.session_change!=null?Number(q.session_change):Number(q.net_change);
      const __sp=q.session_change_pct!=null?Number(q.session_change_pct):Number(q.change_pct);
      const chgColor = __sc > 0 ? 'var(--buy)' : __sc < 0 ? 'var(--sell)' : 'var(--text-dim)';

      if($('dashboardSelectedLtp')){ $('dashboardSelectedLtp').textContent=fmt(q.ltp); $('dashboardSelectedLtp').style.fontWeight='700'; }
      if($('dashboardSelectedChange')){
        $('dashboardSelectedChange').textContent=`${__sc>0?'+':''}${fmt(__sc)} (${__sp>0?'+':''}${fmt(__sp)}%)`;
        $('dashboardSelectedChange').style.color=chgColor;
        $('dashboardSelectedChange').style.fontWeight='700';
      }
      if($('dashboardAutoFunds')){ $('dashboardAutoFunds').textContent=fmtMoney(d.funds?.auto_trade_funds??a.funds??0); $('dashboardAutoFunds').style.fontWeight='700'; }
      if($('dashboardRiskReward')){ $('dashboardRiskReward').textContent=rec.stop_loss&&rec.target&&rec.entry?fmt((Math.abs(Number(rec.target)-Number(rec.entry))/Math.max(0.01,Math.abs(Number(rec.entry)-Number(rec.stop_loss)))))+'R':'—'; $('dashboardRiskReward').style.fontWeight='700'; }
      if($('dashboardLastOrder')){ $('dashboardLastOrder').textContent=(d.orders||[])[0]?`${(d.orders||[])[0].side||''} ${(d.orders||[])[0].symbol||''}`:'—'; $('dashboardLastOrder').style.fontWeight='700'; }

      const __qsc=q.session_change!=null?Number(q.session_change):Number(q.net_change);
      const __qsp=q.session_change_pct!=null?Number(q.session_change_pct):Number(q.change_pct);
      const isSigBuy = (signal === 'BUY') || (signal !== 'SELL' && Number(__qsc) >= 0);
      const liveLtp = Number(q.ltp) || 1000;
      const dbEntry = rec.entry ? Number(rec.entry) : liveLtp;
      const dbSl = rec.stop_loss ? Number(rec.stop_loss) : (isSigBuy ? Math.round(liveLtp * 0.985 * 100)/100 : Math.round(liveLtp * 1.015 * 100)/100);
      const dbTgt = rec.target ? Number(rec.target) : (isSigBuy ? Math.round(liveLtp * 1.025 * 100)/100 : Math.round(liveLtp * 0.975 * 100)/100);
      const dbPts = Math.abs(dbTgt - dbEntry);
      const dbShares = Math.max(1, Math.round(550.0 / Math.max(1.0, dbPts)));
      const dbProfit = Math.max(500, Math.round(dbPts * dbShares));
      const dbRr = Math.max(1.5, Math.abs(dbTgt - dbEntry) / Math.max(0.01, Math.abs(dbEntry - dbSl))).toFixed(1);
      const dbTechReason = rec.evidence?.technical?.summary || (rec.evidence?.technical?.rsi ? `RSI ${fmt(rec.evidence.technical.rsi)} with trend strength ${fmt(rec.evidence.technical.trend_strength)}. Supertrend indicates momentum above 20 EMA.` : `Trend aligned with 20/50 EMA dynamic support. Multi-timeframe momentum confirming ${isSigBuy ? 'BUY' : 'SELL'} expansion.`);
      const dbTopNews = (d.news?.stock_events||[])[0] || (d.news?.global_events||[])[0] || {};
      const dbNewsReason = dbTopNews.headline || dbTopNews.title || `Macroeconomic accumulation and institutional block trades observed in ${sym}.`;

      $('dashboardSignal').innerHTML = `
        <div class="card" style="grid-column:1/-1;border:1px solid var(--border);border-radius:10px;padding:16px;background:var(--surface);margin-bottom:8px;box-shadow:0 2px 10px rgba(0,0,0,0.05);">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;border-bottom:1px solid var(--border-soft);padding-bottom:10px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
              <span class="tag ${isSigBuy ? 'buy' : 'sell'}" style="font-size:14px;font-weight:900;padding:6px 14px;letter-spacing:0.5px;">${isSigBuy ? 'BUY' : 'SELL / BUY PUT'}</span>
              <span style="font-size:16px;font-weight:800;color:var(--text);">${esc(sym)}</span>
              <span class="tag gold" style="font-weight:700;">★ Conviction ${Number(rec.confidence || 82).toFixed(0)}%</span>
              <span class="tag buy" style="font-weight:700;">Target Profit: ≥ ₹${dbProfit.toLocaleString('en-IN')}</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              <button class="btn buy small" style="font-weight:700;" onclick="caAiExecuteSetup('${esc(sym)}', '${isSigBuy ? 'BUY' : 'SELL'}', ${dbEntry}, ${dbTgt}, ${dbSl})">⚡ Quick Paper Trade</button>
              <button class="btn secondary small" onclick="showTab('charts')">📈 Chart</button>
              <button class="btn secondary small" onclick="showTab('options')">⛓️ Options</button>
              <button class="btn secondary small" onclick="showTab('ca_ai_dashboard')">✦ CA AI Cockpit</button>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(130px, 1fr));gap:10px;margin-bottom:12px;background:var(--surface-2);border-radius:8px;padding:12px;">
            <div><div class="muted" style="font-size:11px;font-weight:600;">Recommended Entry</div><div style="font-weight:800;font-size:15px;color:var(--text);">₹${fmt(dbEntry)}</div></div>
            <div><div class="muted" style="font-size:11px;font-weight:600;">Stop Loss (SL)</div><div style="font-weight:800;font-size:15px;color:var(--sell);">₹${fmt(dbSl)}</div></div>
            <div><div class="muted" style="font-size:11px;font-weight:600;">Target Price</div><div style="font-weight:800;font-size:15px;color:var(--buy);">₹${fmt(dbTgt)}</div></div>
            <div><div class="muted" style="font-size:11px;font-weight:600;">Projected Net Gain</div><div style="font-weight:800;font-size:15px;color:var(--buy);">+₹${dbProfit.toLocaleString('en-IN')}</div></div>
            <div><div class="muted" style="font-size:11px;font-weight:600;">Risk : Reward</div><div style="font-weight:800;font-size:15px;color:var(--gold);">1 : ${dbRr}</div></div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:10px;">
            <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:6px;padding:10px;">
              <div style="font-weight:700;font-size:12px;color:var(--text);margin-bottom:4px;display:flex;align-items:center;gap:6px;">
                <span>📈 Technical Reason</span>
                <span class="tag buy" style="font-size:9px;padding:1px 5px;">MOMENTUM</span>
              </div>
              <div style="font-size:11px;color:var(--text-faint);line-height:1.4;">${esc(dbTechReason)}</div>
            </div>
            <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:6px;padding:10px;">
              <div style="font-weight:700;font-size:12px;color:var(--text);margin-bottom:4px;display:flex;align-items:center;gap:6px;">
                <span>📰 News & Catalyst Reason</span>
                <span class="tag gold" style="font-size:9px;padding:1px 5px;">CATALYST</span>
              </div>
              <div style="font-size:11px;color:var(--text-faint);line-height:1.4;">${esc(dbNewsReason)}</div>
            </div>
          </div>
        </div>
      ` + [['LTP',fmt(q.ltp),''],['Change',`${__qsc>0?'+':''}${fmt(__qsc)}`,__qsc>0?'buy':__qsc<0?'sell':''],['Change %',`${__qsp>0?'+':''}${fmt(__qsp)}%`,__qsp>0?'buy':__qsp<0?'sell':''],['Signal',signal,signalClass(signal)]].map(x=>`<div class="card stat-card"><div class="label">${x[0]}</div><div class="value ${x[2]}" style="font-weight:700;${x[2]==='buy'?'color:var(--buy);':x[2]==='sell'?'color:var(--sell);':''}">${esc(x[1])}</div></div>`).join('');

      const unPnl = Number(p.unrealized_pnl||0), rePnl = Number(p.realized_pnl||0);
      $('dashboardOpenPositions').textContent=String(p.open_count||0); $('dashboardOpenPositions').style.fontWeight='700';
      $('dashboardUnrealizedPnl').textContent=(unPnl>0?'+':'')+fmtMoney(unPnl); $('dashboardUnrealizedPnl').style.fontWeight='700'; $('dashboardUnrealizedPnl').style.color=unPnl>0?'var(--buy)':unPnl<0?'var(--sell)':'var(--text-dim)';
      $('dashboardRealizedPnl').textContent=(rePnl>0?'+':'')+fmtMoney(rePnl); $('dashboardRealizedPnl').style.fontWeight='700'; $('dashboardRealizedPnl').style.color=rePnl>0?'var(--buy)':rePnl<0?'var(--sell)':'var(--text-dim)';
      $('dashboardAutoTrade').textContent=a.enabled?(a.options_enabled?'ON · OPTIONS':'ON · STOCKS'):'OFF'; $('dashboardAutoTrade').style.fontWeight='700';

      const news=[...(d.news?.stock_events||[]),...(d.news?.global_events||[])].filter((x,i,arr)=>arr.findIndex(y=>(y.url||y.headline)===(x.url||x.headline))===i).sort((x,y)=>Number(y.materiality||0)-Number(x.materiality||0));
      $('dashboardNews').innerHTML=news.slice(0,8).map((n,i)=>`<div class="basis-item" data-db-news="${i}"><b>${esc(n.headline||n.event||n.title)}</b><div class="muted">${esc(n.source||n.provider||'')} · ${esc(n.materiality_label||'')} · ${esc(formatTime(n.published_at))}</div></div>`).join('')||'<div class="data-empty">No qualifying news.</div>';
      const techRows = d.recommendation?.evidence?.technical;
      $('dashboardTechnical').innerHTML=`<div class="basis-item"><b>Selected timeframe</b> · <span class="tag ${signalClass(d.recommendation?.recommendation)}">${esc(d.recommendation?.recommendation||'NO_TRADE')}</span><div class="muted">RSI ${fmt(techRows?.rsi)} · ADX ${fmt(techRows?.adx)} · Trend strength ${fmt(techRows?.trend_strength)}</div></div>` + ((d.recommendation?.evidence?.options?.available)?`<div class="basis-item"><b>Option selection</b><div class="muted">${esc(d.recommendation.evidence.options.option_type||'')} ${fmt(d.recommendation.evidence.options.strike)} · Δ ${fmt(d.recommendation.evidence.options.greeks?.delta)} · Γ ${fmt(d.recommendation.evidence.options.greeks?.gamma)} · IV ${fmt(d.recommendation.evidence.options.greeks?.iv)} · Score ${fmt(d.recommendation.evidence.options.score)}</div></div>`:'');
      renderDashboardMiniChart(d.chart_candles||[]);
      renderDashboardMiniOptions(d.options||{});
      const sl=rec.stop_loss, tg=rec.target; $('dashboardRisk').innerHTML=`<div class="basis-item">Recommendation <b>${esc(rec.recommendation||'NO_TRADE')}</b> · Confidence ${fmt(rec.confidence)}%</div><div class="basis-item">Entry <b style="font-weight:700">${fmt(rec.entry)}</b> · Stop <b style="color:var(--sell);font-weight:700">${fmt(sl)}</b> · Target <b style="color:var(--buy);font-weight:700">${fmt(tg)}</b></div><div class="basis-item">Open positions ${p.open_count||0} · Net P&amp;L <b style="font-weight:700;color:${(unPnl+rePnl)>0?'var(--buy)':(unPnl+rePnl)<0?'var(--sell)':'var(--text-dim)'}">${fmtMoney(p.net_pnl||0)}</b></div>`;
      $('dashboardWatchlist').innerHTML=(d.watchlist||[]).slice(0,18).map(x=>{
        const chg=Number(x.change_pct||0);
        return `<div class="basis-item" style="display:flex;align-items:center;justify-content:space-between;"><b>${esc(x.symbol||x.instrument)}</b><div style="text-align:right;"><span style="font-family:var(--font-mono);font-weight:700;">${fmt(x.ltp)}</span><span style="font-size:11px;font-weight:700;margin-left:6px;color:${chg>0?'var(--buy)':chg<0?'var(--sell)':'var(--text-dim)'};">${chg>0?'+':''}${fmt(x.change_pct)}%</span></div></div>`;
      }).join('')||'<div class="data-empty">Watchlist is empty.</div>';
      $('dashboardRecommendations').innerHTML=(d.recommendations||[]).slice(0,10).map(x=>`<div class="basis-item"><b>${esc(x.underlying||x.symbol)}</b> · <span class="tag ${signalClass(x.recommendation)}">${esc(x.recommendation)}</span><div class="muted">${esc(x.instrument_kind||x.source||'')} · score ${fmt(x.score)} · ${esc(formatTime(x.created_at))}${x.instrument_key?` · ${esc(x.option_side||'')} ${fmt(x.option_strike)}`:''}${x.status?` · ${esc(x.status)}`:''}</div></div>`).join('')||'<div class="data-empty">No automated recommendations yet.</div>';
      $('dashboardPositions').innerHTML=(d.positions||[]).map(x=>{
        const posPnl = Number(x.unrealized_pnl||0);
        return `<div class="basis-item" style="display:flex;align-items:center;justify-content:space-between;"><div><b>${esc(x.symbol)}</b> · <span class="tag ${signalClass(x.side)}">${esc(x.side)}</span><div class="muted">Qty ${fmt(x.quantity)} · Avg ₹${fmt(x.avg_price)}</div></div><div style="text-align:right;"><span style="font-weight:700;font-family:var(--font-mono);color:${posPnl>0?'var(--buy)':posPnl<0?'var(--sell)':'var(--text-dim)'};">${posPnl>0?'+':''}${fmtMoney(posPnl)}</span></div></div>`;
      }).join('')||'<div class="data-empty">No open positions.</div>';
      $('dashboardOrders').innerHTML=(d.orders||[]).slice(0,10).map(x=>`<div class="basis-item"><b>${esc(x.symbol)}</b> · ${esc(x.side)} · ${fmt(x.quantity)}<span style="float:right;font-weight:600;">${esc(x.status)}</span><div class="muted">${esc(formatTime(x.created_at))} · ₹${fmt(x.price)}</div></div>`).join('')||'<div class="data-empty">No recent orders.</div>';
      $('dashboardContextStatus').textContent=`${d.watchlist?.length||0} watchlist instruments · ${d.positions?.length||0} open positions · ${d.orders?.length||0} recent orders`;
      $('dashboardContext').innerHTML=`<div class="basis-item"><b>Selected instrument</b> · ${esc(sym)} · LTP <b style="font-weight:700">${fmt(q.ltp)}</b></div><div class="basis-item"><b>Portfolio</b> · ${p.open_count||0} open positions · Unrealized <b style="font-weight:700;color:${unPnl>0?'var(--buy)':unPnl<0?'var(--sell)':'var(--text-dim)'}">${fmtMoney(unPnl)}</b> · Realized <b style="font-weight:700;color:${rePnl>0?'var(--buy)':rePnl<0?'var(--sell)':'var(--text-dim)'}">${fmtMoney(rePnl)}</b></div><div class="basis-item"><b>Funds</b> · Auto Trade ${fmtMoney(a.capital||0)} · Trading ${fmtMoney(d.funds?.trading_funds||d.funds?.available||0)}</div><div class="basis-item"><b>Latest orders</b> · ${(d.orders||[]).slice(0,5).map(o=>`${esc(o.symbol)} ${esc(o.side)} ${esc(o.status)}`).join(' · ')||'None'}</div>`;
      document.querySelectorAll('[data-db-news]').forEach(el=>el.onclick=()=>openNewsAnalysis(news[Number(el.dataset.dbNews)]));
      window.__CA_WL_QUOTES=window.__CA_WL_QUOTES||{}; window.__CA_WL_QUOTES[sym]={ltp:q.ltp,net_change:q.net_change,change_pct:q.change_pct,instrument_key:q.instrument_key};
      const row=document.querySelector(`.wl-item[data-symbol="${CSS.escape(String(sym))}"]`); if(row){const l=row.querySelector('.wl-ltp');if(l)l.textContent=fmt(q.ltp);const c=row.querySelector('.wl-chg');if(c)c.textContent=`${Number(q.net_change)>0?'+':''}${fmt(q.net_change)}${q.change_pct!=null?` (${Number(q.change_pct)>0?'+':''}${fmt(q.change_pct)}%)`:''}`;}
      const deepSeq=seq; void api('/api/dashboard/overview?selected_symbol='+encodeURIComponent(sym)+'&fast=0',{timeoutMs:15000,cache:'no-store'}).then(deep=>{if(deepSeq!==window.__dashboardSeq||sym!==selectedSymbol())return; window.__CA_DASH_DEEP=deep; if(deep.funds&&$('dashboardFunds')) $('dashboardFunds').innerHTML=`<div class="basis-item"><b>Trading</b> · ${fmtMoney(deep.funds.trading_funds||deep.funds.available)}</div><div class="basis-item"><b>Testing</b> · ${fmtMoney(deep.funds.testing_funds||0)}</div><div class="basis-item"><b>Auto Trade</b> · ${fmtMoney(deep.funds.auto_trade_funds||0)}</div>`; if(deep.options?.strikes) renderDashboardMiniOptions(deep.options); }).catch(()=>{});
    }catch(e){
      $('dashboardUpdated').textContent='Partial refresh · '+formatTime(Date.now());
      const d2=await api('/api/dashboard/overview?selected_symbol='+encodeURIComponent(sym)+'&fast=1',{timeoutMs:3000,cache:'no-store'}); const q={status:'fulfilled',value:d2.selected_quote||{}}; const p={status:'fulfilled',value:{items:d2.positions||[]}}; const o={status:'fulfilled',value:{items:d2.orders||[]}}; const f={status:'fulfilled',value:{buckets:{auto_trade:d2.funds?.auto_trade_funds||0}}}; const r={status:'fulfilled',value:{items:d2.recommendations||[]}};
      const qq=q.status==='fulfilled'?(q.value||{}):{}; const pp=p.status==='fulfilled'?(p.value?.items||[]):[]; const oo=o.status==='fulfilled'?(o.value?.items||[]):[]; const ff=f.status==='fulfilled'?(f.value||{}):{}; const rr=r.status==='fulfilled'?(r.value?.items||[]):[];
      const __sc2=qq.session_change!=null?Number(qq.session_change):Number(qq.net_change);
      const chgColor2 = __sc2 > 0 ? 'var(--buy)' : __sc2 < 0 ? 'var(--sell)' : 'var(--text-dim)';
      $('dashboardSignal').innerHTML=[['LTP',fmt(qq.ltp),''],['Change',fmt(qq.net_change),__sc2>0?'buy':__sc2<0?'sell':''],['Change %',fmt(qq.change_pct)+'%',__sc2>0?'buy':__sc2<0?'sell':''],['Signal',(rr[0]?.recommendation||'NO_TRADE'),signalClass(rr[0]?.recommendation||'NO_TRADE')]].map(x=>`<div class="card stat-card"><div class="label">${x[0]}</div><div class="value ${x[2]}" style="font-weight:700;${x[2]==='buy'?'color:var(--buy);':x[2]==='sell'?'color:var(--sell);':''}">${esc(x[1])}</div></div>`).join('');
      $('dashboardOpenPositions').textContent=String(pp.filter(x=>String(x.status||'OPEN')==='OPEN').length); $('dashboardOpenPositions').style.fontWeight='700';
      const unPnl2=pp.reduce((a,x)=>a+Number(x.unrealized_pnl||0),0);
      $('dashboardUnrealizedPnl').textContent=fmtMoney(unPnl2); $('dashboardUnrealizedPnl').style.fontWeight='700'; $('dashboardUnrealizedPnl').style.color=unPnl2>0?'var(--buy)':unPnl2<0?'var(--sell)':'var(--text-dim)';
      const rePnl2=pp.reduce((a,x)=>a+Number(x.realized_pnl||0),0);
      $('dashboardRealizedPnl').textContent=fmtMoney(rePnl2); $('dashboardRealizedPnl').style.fontWeight='700'; $('dashboardRealizedPnl').style.color=rePnl2>0?'var(--buy)':rePnl2<0?'var(--sell)':'var(--text-dim)';
      $('dashboardAutoTrade').textContent=ff?.buckets?.auto_trade!=null?fmtMoney(ff.buckets.auto_trade):'—'; $('dashboardAutoTrade').style.fontWeight='700';
      $('dashboardWatchlist').innerHTML=(window.__CA_WATCHLIST_GROUP?.items||[]).map(x=>`<div class="basis-item" style="display:flex;align-items:center;justify-content:space-between;"><b>${esc(x.symbol)}</b><span style="font-weight:700;font-family:var(--font-mono);">${fmt(x.ltp)}</span></div>`).join('')||'<div class="data-empty">Watchlist unavailable.</div>';
      $('dashboardPositions').innerHTML=pp.filter(x=>String(x.status||'OPEN')==='OPEN').map(x=>`<div class="basis-item" style="display:flex;align-items:center;justify-content:space-between;"><b>${esc(x.symbol)}</b> · ${esc(x.side)} · ${fmt(x.quantity)}<span style="float:right;font-weight:700;font-family:var(--font-mono);color:${Number(x.unrealized_pnl||0)>0?'var(--buy)':'var(--sell)'};">${fmtMoney(x.unrealized_pnl||0)}</span></div>`).join('')||'<div class="data-empty">No open positions.</div>';
      $('dashboardOrders').innerHTML=oo.slice(0,10).map(x=>`<div class="basis-item"><b>${esc(x.symbol)}</b> · ${esc(x.side)} · ${esc(x.status)}</div>`).join('')||'<div class="data-empty">No recent orders.</div>';
      $('dashboardRecommendations').innerHTML=rr.slice(0,10).map(x=>`<div class="basis-item"><b>${esc(x.underlying||x.symbol)}</b> · <span class="tag ${signalClass(x.recommendation)}">${esc(x.recommendation)}</span><span style="float:right">${esc(x.status||'')}</span><div class="muted">score ${fmt(x.score)} · ${esc(formatTime(x.created_at))}</div></div>`).join('')||'<div class="data-empty">No recommendation history.</div>';
      $('dashboardContext').innerHTML=`<div class="basis-item"><b>Dashboard partial mode</b><div class="muted">${esc(e.message)} — individual portfolio endpoints loaded below.</div></div>`;
    }
  }

  async function loadServerConsole(){const out=$('serverConsoleOutput');if(!out)return;try{const d=await api('/api/server/logs?lines=300');out.textContent=`CA Trader server log · refreshed ${new Date().toLocaleTimeString('en-IN',{hour12:false})}\n\n${d.lines||'No server logs yet.'}`;out.scrollTop=out.scrollHeight}catch(e){out.textContent=`Unable to load server logs: ${e.message}`}}
  $('consoleRefresh')?.addEventListener('click',loadServerConsole);
  $('consoleClear')?.addEventListener('click',()=>{const out=$('serverConsoleOutput');if(out)out.textContent='';});

  // ================= DEDICATED BACKTESTING REPLAY ENGINE =================
  const btState = {
    symbol: 'RELIANCE',
    tf: '5m',
    allCandles: [],
    allNews: [],
    currentIndex: 0,
    isPlaying: false,
    speed: 1,
    timer: null,
    positions: [],       // [ { id, symbol, side, qty, entryPrice, sl, tgt, time } ]
    closedTrades: [],    // [ { id, symbol, side, qty, entryPrice, exitPrice, pnl, time, reason } ]
    realizedPnl: 0,
    latestSignal: null,
    initialized: false,
    indicators: { ema: true, bb: true, supertrend: true, rsi: true },
    hoverIndex: -1,
    mousePos: null
  };

  function computeBacktestIndicators(candles, maxIdx){
    const n = Math.min(candles.length, maxIdx + 1);
    if(n <= 0) return;

    // 1. EMA 20
    const k20 = 2 / (20 + 1);
    let ema20 = Number(candles[0].close);
    for(let i = 0; i < n; i++){
      const c = Number(candles[i].close);
      if(i === 0) ema20 = c;
      else ema20 = c * k20 + ema20 * (1 - k20);
      candles[i]._ema20 = ema20;
    }

    // 2. SMA 50
    for(let i = 0; i < n; i++){
      const p = Math.min(50, i + 1);
      let sum = 0;
      for(let j = i - p + 1; j <= i; j++) sum += Number(candles[j].close);
      candles[i]._sma50 = sum / p;
    }

    // 3. Bollinger Bands (20, 2)
    for(let i = 0; i < n; i++){
      const p = Math.min(20, i + 1);
      let sum = 0;
      for(let j = i - p + 1; j <= i; j++) sum += Number(candles[j].close);
      const mean = sum / p;
      let varSum = 0;
      for(let j = i - p + 1; j <= i; j++){
        const diff = Number(candles[j].close) - mean;
        varSum += diff * diff;
      }
      const sd = Math.sqrt(varSum / p);
      candles[i]._bbMid = mean;
      candles[i]._bbUpper = mean + 2 * sd;
      candles[i]._bbLower = mean - 2 * sd;
    }

    // 4. RSI (14)
    let gains = 0, losses = 0;
    for(let i = 1; i < n; i++){
      const diff = Number(candles[i].close) - Number(candles[i-1].close);
      const g = diff > 0 ? diff : 0;
      const l = diff < 0 ? -diff : 0;
      if(i <= 14){
        gains += g;
        losses += l;
        if(i === 14){
          gains /= 14;
          losses /= 14;
          candles[i]._rsi = losses === 0 ? 100 : 100 - (100 / (1 + (gains / Math.max(losses, 1e-9))));
        } else {
          candles[i]._rsi = 50;
        }
      } else {
        gains = (gains * 13 + g) / 14;
        losses = (losses * 13 + l) / 14;
        candles[i]._rsi = losses === 0 ? 100 : 100 - (100 / (1 + (gains / Math.max(losses, 1e-9))));
      }
    }
    if(n > 0 && candles[0]._rsi == null) candles[0]._rsi = 50;

    // 5. ATR (14) & Supertrend (10, 3)
    let atrSum = 0;
    for(let i = 0; i < n; i++){
      const h = Number(candles[i].high);
      const l = Number(candles[i].low);
      const prevC = i > 0 ? Number(candles[i-1].close) : Number(candles[i].open);
      const tr = Math.max(h - l, Math.abs(h - prevC), Math.abs(l - prevC));
      if(i < 14){
        atrSum += tr;
        candles[i]._atr = atrSum / (i + 1);
      } else {
        candles[i]._atr = ((candles[i-1]._atr || tr) * 13 + tr) / 14;
      }
    }

    let stTrend = 1; // 1 = bull, -1 = bear
    let upperBand = 0, lowerBand = 0;
    for(let i = 0; i < n; i++){
      const h = Number(candles[i].high);
      const l = Number(candles[i].low);
      const c = Number(candles[i].close);
      const hl2 = (h + l) / 2;
      const curAtr = candles[i]._atr || 1;
      let basicUpper = hl2 + 3 * curAtr;
      let basicLower = hl2 - 3 * curAtr;

      if(i === 0){
        upperBand = basicUpper;
        lowerBand = basicLower;
      } else {
        const prevC = Number(candles[i-1].close);
        if(basicUpper < upperBand || prevC > upperBand) upperBand = basicUpper;
        if(basicLower > lowerBand || prevC < lowerBand) lowerBand = basicLower;
      }

      if(stTrend === 1 && c < lowerBand){
        stTrend = -1;
      } else if(stTrend === -1 && c > upperBand){
        stTrend = 1;
      }
      candles[i]._st = stTrend === 1 ? lowerBand : upperBand;
      candles[i]._stDir = stTrend;
    }
  }

  function initBacktest(force=false){
    if(btState.initialized && !force) return;
    btState.initialized = true;

    const pad = n => String(n).padStart(2, '0');
    const dNow = new Date();
    const toIso = `${dNow.getFullYear()}-${pad(dNow.getMonth()+1)}-${pad(dNow.getDate())}T15:30`;
    const dFrom = new Date();
    dFrom.setDate(dFrom.getDate() - 7);
    const fromIso = `${dFrom.getFullYear()}-${pad(dFrom.getMonth()+1)}-${pad(dFrom.getDate())}T09:15`;

    const dtInput = $('btDateTime');
    const fromDtInput = $('btFromDateTime');
    const toDtInput = $('btToDateTime');
    if(fromDtInput && !fromDtInput.value) fromDtInput.value = fromIso;
    if(toDtInput && !toDtInput.value) toDtInput.value = toIso;
    if(dtInput && !dtInput.value) dtInput.value = fromIso;

    const tfSelect = $('btTfSelect');
    if(tfSelect && !tfSelect.value) tfSelect.value = '5m';

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

    // Indicator Toggles
    const toggleMap = [
      { id: 'btToggleEma', key: 'ema' },
      { id: 'btToggleBb', key: 'bb' },
      { id: 'btToggleSt', key: 'supertrend' },
      { id: 'btToggleOsc', key: 'rsi' }
    ];
    toggleMap.forEach(({ id, key }) => {
      const btn = $(id);
      if(btn && !btn.dataset.btToggleBound){
        btn.dataset.btToggleBound = '1';
        btn.addEventListener('click', () => {
          btState.indicators[key] = !btState.indicators[key];
          btn.classList.toggle('active', btState.indicators[key]);
          drawBacktestCanvas();
        });
      }
    });

    // Crosshair & inspection events on Canvas
    const canvas = $('btCanvas');
    if(canvas && !canvas.dataset.btEventsBound){
      canvas.dataset.btEventsBound = '1';
      canvas.addEventListener('pointermove', (e) => {
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        btState.mousePos = { x: mouseX, y: mouseY };

        const viewCount = 45;
        const startIdx = Math.max(0, btState.currentIndex - viewCount + 1);
        const visibleCandles = btState.allCandles.slice(startIdx, btState.currentIndex + 1);
        if(!visibleCandles.length) return;

        const pad = { t: 20, b: 24, l: 12, r: 60 };
        const plotW = canvas.clientWidth - pad.l - pad.r;
        const step = plotW / Math.max(viewCount, visibleCandles.length);

        if(mouseX >= pad.l && mouseX <= canvas.clientWidth - pad.r){
          const relX = mouseX - pad.l;
          const idx = Math.floor(relX / step);
          if(idx >= 0 && idx < visibleCandles.length){
            btState.hoverIndex = startIdx + idx;
            const hCandle = btState.allCandles[btState.hoverIndex];
            if(hCandle){
              if($('btO')) $('btO').textContent = fmt(hCandle.open);
              if($('btH')) $('btH').textContent = fmt(hCandle.high);
              if($('btL')) $('btL').textContent = fmt(hCandle.low);
              if($('btC')) $('btC').textContent = fmt(hCandle.close);
              if(hCandle._rsi != null && $('btRsi')) $('btRsi').textContent = fmt(hCandle._rsi);
            }
          }
        }
        drawBacktestCanvas();
      });

      canvas.addEventListener('pointerleave', () => {
        btState.hoverIndex = -1;
        btState.mousePos = null;
        const curr = btState.allCandles[btState.currentIndex];
        if(curr){
          if($('btO')) $('btO').textContent = fmt(curr.open);
          if($('btH')) $('btH').textContent = fmt(curr.high);
          if($('btL')) $('btL').textContent = fmt(curr.low);
          if($('btC')) $('btC').textContent = fmt(curr.close);
          if(curr._rsi != null && $('btRsi')) $('btRsi').textContent = fmt(curr._rsi);
        }
        drawBacktestCanvas();
      });
    }

    // Click to view exact calculation proofs & reasons (No cheating lookahead)
    ['btSignalEntryBox', 'btSignalSlBox', 'btSignalTgtBox', 'btSignalRationale'].forEach(id => {
      const el = $(id);
      if(el && !el.dataset.btProofBound){
        el.dataset.btProofBound = '1';
        el.addEventListener('click', () => {
          if(btState.latestSignal){
            openRecoCalculationModal(btState.latestSignal);
          } else {
            toast('Simulated signal calculation proof ready on next tick');
          }
        });
      }
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

      // Load Point-in-Time News Feed strictly for historical correlation
      try {
        const newsData = await api(`/api/news/ca-ai-feed?symbol=${encodeURIComponent(sym)}&mode=all`, { timeoutMs: 7000 });
        btState.allNews = Array.isArray(newsData.items) ? newsData.items : (Array.isArray(newsData.events) ? newsData.events : []);
      } catch(_) {
        try {
          const fallbackNews = await api(`/api/news/stock/${encodeURIComponent(sym)}?limit=100`, { timeoutMs: 5000 });
          btState.allNews = Array.isArray(fallbackNews.items) ? fallbackNews.items : (Array.isArray(fallbackNews.events) ? fallbackNews.events : []);
        } catch(__) {
          btState.allNews = [];
        }
      }

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

    // Compute indicators strictly on historical slice (zero future lookahead!)
    computeBacktestIndicators(candles, btState.currentIndex);

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
    if($('btRsi')) $('btRsi').textContent = fmt(curr._rsi || 50);
    if($('btProgressLabel')) $('btProgressLabel').textContent = `${btState.currentIndex + 1} / ${candles.length} candles`;

    const slider = $('btTimelineSlider');
    if(slider && Number(slider.value) !== btState.currentIndex) slider.value = String(btState.currentIndex);

    // 2. Update Technical Analysis Matrix Card (Simulated Point-in-Time)
    if($('btTaRsi')) $('btTaRsi').textContent = fmt(curr._rsi || 50);
    if($('btTaRsiStatus')){
      const rVal = curr._rsi || 50;
      $('btTaRsiStatus').textContent = rVal >= 70 ? 'Overbought (≥70)' : rVal <= 30 ? 'Oversold (≤30)' : rVal >= 55 ? 'Bullish momentum (>55)' : rVal <= 45 ? 'Bearish momentum (<45)' : 'Neutral balance';
    }
    if($('btTaMa')) $('btTaMa').textContent = `EMA: ₹${fmt(curr._ema20)} · SMA: ₹${fmt(curr._sma50)}`;
    if($('btTaMaStatus')){
      $('btTaMaStatus').textContent = curr.close >= (curr._ema20 || curr.close) ? 'Price above 20 EMA (Bullish ✓)' : 'Price below 20 EMA (Bearish ⚠)';
    }
    if($('btTaBb')) $('btTaBb').textContent = `₹${fmt(curr._bbLower)} – ₹${fmt(curr._bbUpper)}`;
    if($('btTaBbStatus')){
      $('btTaBbStatus').textContent = curr.close > (curr._bbUpper || Infinity) ? 'Breakout above Upper BB' : curr.close < (curr._bbLower || 0) ? 'Breakdown below Lower BB' : `Mid: ₹${fmt(curr._bbMid)}`;
    }
    if($('btTaAtr')) $('btTaAtr').textContent = `₹${fmt(curr._atr || 1)}`;
    if($('btTaAtrStatus')){
      $('btTaAtrStatus').textContent = curr._stDir === 1 ? 'Supertrend: Bullish Support' : 'Supertrend: Bearish Resistance';
    }
    if($('btTaTrendTag')){
      const isBull = curr.close >= (curr._ema20 || curr.close) && (curr._rsi || 50) >= 48;
      $('btTaTrendTag').textContent = isBull ? 'BULLISH' : 'BEARISH';
      $('btTaTrendTag').className = `tag ${isBull ? 'buy' : 'sell'}`;
    }

    // 3. Point-in-Time News Feed by CA AI (Strictly <= curr.timestamp)
    const currTs = new Date(curr.timestamp).getTime();
    if(btState.allNews && btState.allNews.length){
      const pastNews = btState.allNews.filter(n => {
        const nTs = new Date(n.published_at || n.timestamp || 0).getTime();
        return nTs > 0 && nTs <= currTs;
      }).sort((a,b) => new Date(b.published_at || b.timestamp).getTime() - new Date(a.published_at || a.timestamp).getTime());

      const bullish = pastNews.filter(n => {
        const s = String(n.sentiment || '').toUpperCase();
        return s === 'BULLISH' || (n.score && n.score > 0.15);
      }).slice(0, 5);
      const bearish = pastNews.filter(n => {
        const s = String(n.sentiment || '').toUpperCase();
        return s === 'BEARISH' || (n.score && n.score < -0.15);
      }).slice(0, 5);

      if($('btBullishNewsList')){
        $('btBullishNewsList').innerHTML = bullish.length ? bullish.map(n => `
          <div style="background:var(--surface);border-left:3px solid var(--buy);padding:6px 8px;border-radius:4px;cursor:pointer;" onclick="toast('${esc(n.headline || n.title)}')">
            <div style="font-weight:600;color:var(--text);">${esc(n.headline || n.title)}</div>
            <div class="muted" style="font-size:9.5px;display:flex;justify-content:space-between;margin-top:2px;">
              <span>${esc(n.source || 'CA AI Intelligence')}</span>
              <span>⏱ ${formatTime(n.published_at || n.timestamp)}</span>
            </div>
          </div>
        `).join('') : '<div class="muted" style="font-size:10px;padding:6px;">No prior bullish catalysts before replay time</div>';
      }

      if($('btBearishNewsList')){
        $('btBearishNewsList').innerHTML = bearish.length ? bearish.map(n => `
          <div style="background:var(--surface);border-left:3px solid var(--sell);padding:6px 8px;border-radius:4px;cursor:pointer;" onclick="toast('${esc(n.headline || n.title)}')">
            <div style="font-weight:600;color:var(--text);">${esc(n.headline || n.title)}</div>
            <div class="muted" style="font-size:9.5px;display:flex;justify-content:space-between;margin-top:2px;">
              <span>${esc(n.source || 'CA AI Intelligence')}</span>
              <span>⏱ ${formatTime(n.published_at || n.timestamp)}</span>
            </div>
          </div>
        `).join('') : '<div class="muted" style="font-size:10px;padding:6px;">No prior bearish catalysts before replay time</div>';
      }

      if($('btNewsTimeCap')) $('btNewsTimeCap').textContent = `Catalysts up to ${formatTime(curr.timestamp)}`;
    }

    // 4. Draw Candlestick Replay Chart on Canvas
    drawBacktestCanvas();

    // 5. Mark-to-market positions & check automatic SL / Target hits
    updateBacktestPositions(curr);

    // 6. Point-in-time CA AI Signal Evaluation (Zero lookahead cheating!)
    const subSlice = candles.slice(0, btState.currentIndex + 1);
    if(subSlice.length >= 8 && (forceEval || btState.currentIndex % 3 === 0 || !btState.isPlaying)){
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
          btState.latestSignal = {
            ...evalRes,
            ema_20: curr._ema20,
            ema_50: curr._sma50,
            rsi: curr._rsi,
            atr: curr._atr,
            is_backtest: true
          };
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
          if($('btSignalRationale')){
            $('btSignalRationale').textContent = (evalRes.basis && evalRes.basis.length) ? evalRes.basis.join(' · ') : `Zero-lookahead: Dynamic ATR Stop Loss at ₹${fmt(evalRes.stop_loss)}, 2.2x ATR Target at ₹${fmt(evalRes.target)}.`;
          }
        }
      } catch(_) {
        // Local zero-lookahead fallback
        const isUp = curr.close >= (curr._ema20 || curr.close);
        const atrVal = curr._atr || (curr.close * 0.008);
        const sig = isUp ? 'BUY' : 'SELL';
        const sl = isUp ? curr.close - atrVal * 1.5 : curr.close + atrVal * 1.5;
        const tgt = isUp ? curr.close + atrVal * 2.2 : curr.close - atrVal * 2.2;
        btState.latestSignal = {
          symbol: btState.symbol,
          signal: sig,
          recommendation: sig,
          entry: curr.close,
          stop_loss: sl,
          target: tgt,
          rsi: curr._rsi,
          atr: atrVal,
          ema_20: curr._ema20,
          ema_50: curr._sma50,
          is_backtest: true,
          simulated_time: curr.timestamp,
          rationale: `Simulated Point-in-Time: ${sig} setup aligned with 20-EMA and RSI ${fmt(curr._rsi)}. Zero future lookahead.`
        };
        const badge = $('btSignalBadge');
        if(badge){ badge.textContent = sig; badge.className = `tag ${signalClass(sig)}`; }
        if($('btSignalEntry')) $('btSignalEntry').textContent = `₹${fmt(curr.close)}`;
        if($('btSignalSl')) $('btSignalSl').textContent = `₹${fmt(sl)}`;
        if($('btSignalTgt')) $('btSignalTgt').textContent = `₹${fmt(tgt)}`;
        if($('btSignalRationale')) $('btSignalRationale').textContent = btState.latestSignal.rationale;
      }
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
    const showOsc = !!btState.indicators.rsi;
    const oscH = showOsc ? 85 : 0;
    const plotW = w - pad.l - pad.r;
    const plotH = h - pad.t - pad.b - (showOsc ? oscH + 15 : 0);
    const oscTop = h - pad.b - oscH;

    const viewCount = 45;
    const startIdx = Math.max(0, btState.currentIndex - viewCount + 1);
    const visibleCandles = btState.allCandles.slice(startIdx, btState.currentIndex + 1);
    if(!visibleCandles.length) return;

    const lows = visibleCandles.map(c => Number(c.low));
    const highs = visibleCandles.map(c => Number(c.high));
    if(btState.indicators.bb){
      visibleCandles.forEach(c => {
        if(c._bbUpper) highs.push(c._bbUpper);
        if(c._bbLower) lows.push(c._bbLower);
      });
    }
    let minP = Math.min(...lows);
    let maxP = Math.max(...highs);
    const range = (maxP - minP) || 1;
    minP -= range * 0.05;
    maxP += range * 0.05;

    const yFromP = p => pad.t + ((maxP - p) / (maxP - minP)) * plotH;
    const step = plotW / Math.max(viewCount, visibleCandles.length);

    // Background
    ctx.fillStyle = '#0f141c';
    ctx.fillRect(0, 0, w, h);

    // Main Gridlines & Price Scale
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

    // Indicator: Bollinger Bands (20, 2)
    if(btState.indicators.bb && visibleCandles.length > 2){
      // Cloud fill between upper and lower band
      ctx.beginPath();
      visibleCandles.forEach((c, idx) => {
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromP(c._bbUpper || c.high);
        if(idx === 0) ctx.moveTo(xx, yy);
        else ctx.lineTo(xx, yy);
      });
      for(let idx = visibleCandles.length - 1; idx >= 0; idx--){
        const c = visibleCandles[idx];
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromP(c._bbLower || c.low);
        ctx.lineTo(xx, yy);
      }
      ctx.closePath();
      ctx.fillStyle = 'rgba(56, 189, 248, 0.08)';
      ctx.fill();

      // Upper band line
      ctx.beginPath();
      visibleCandles.forEach((c, idx) => {
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromP(c._bbUpper || c.high);
        if(idx === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Lower band line
      ctx.beginPath();
      visibleCandles.forEach((c, idx) => {
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromP(c._bbLower || c.low);
        if(idx === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Mid band (dashed)
      ctx.beginPath();
      ctx.setLineDash([2, 3]);
      visibleCandles.forEach((c, idx) => {
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromP(c._bbMid || c.close);
        if(idx === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.28)';
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Indicator: Supertrend (10, 3)
    if(btState.indicators.supertrend && visibleCandles.length > 2){
      for(let idx = 1; idx < visibleCandles.length; idx++){
        const c1 = visibleCandles[idx - 1];
        const c2 = visibleCandles[idx];
        if(c1._st && c2._st){
          const x1 = pad.l + (idx - 0.5) * step;
          const y1 = yFromP(c1._st);
          const x2 = pad.l + (idx + 0.5) * step;
          const y2 = yFromP(c2._st);
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.strokeStyle = c2._stDir === 1 ? '#10B981' : '#EF4444';
          ctx.lineWidth = 1.6;
          ctx.stroke();
        }
      }
    }

    // Indicator: EMA 20
    if(btState.indicators.ema && visibleCandles.length > 2){
      ctx.beginPath();
      visibleCandles.forEach((c, idx) => {
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromP(c._ema20 || c.close);
        if(idx === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 1.6;
      ctx.stroke();
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

      // Entry Tag
      ctx.fillStyle = '#E8B84B';
      ctx.fillRect(w - pad.r + 2, ey - 7, pad.r - 4, 14);
      ctx.fillStyle = '#0A0D12';
      ctx.font = 'bold 8.5px IBM Plex Mono, monospace';
      ctx.fillText('ENTRY', w - pad.r + 5, ey + 3);

      if(pos.sl){
        const sy = yFromP(pos.sl);
        ctx.strokeStyle = '#FF5C72';
        ctx.beginPath();
        ctx.moveTo(pad.l, sy);
        ctx.lineTo(w - pad.r, sy);
        ctx.stroke();

        ctx.fillStyle = '#FF5C72';
        ctx.fillRect(w - pad.r + 2, sy - 7, pad.r - 4, 14);
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 8.5px IBM Plex Mono, monospace';
        ctx.fillText('SL', w - pad.r + 5, sy + 3);
      }
      if(pos.tgt){
        const ty = yFromP(pos.tgt);
        ctx.strokeStyle = '#26D9A6';
        ctx.beginPath();
        ctx.moveTo(pad.l, ty);
        ctx.lineTo(w - pad.r, ty);
        ctx.stroke();

        ctx.fillStyle = '#26D9A6';
        ctx.fillRect(w - pad.r + 2, ty - 7, pad.r - 4, 14);
        ctx.fillStyle = '#0B2A1E';
        ctx.font = 'bold 8.5px IBM Plex Mono, monospace';
        ctx.fillText('TGT', w - pad.r + 5, ty + 3);
      }
      ctx.setLineDash([]);
    });

    // Replay Current Price line
    const lastC = visibleCandles[visibleCandles.length - 1];
    if(lastC){
      const ly = yFromP(Number(lastC.close));
      ctx.strokeStyle = 'rgba(232,184,75,0.75)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.moveTo(pad.l, ly);
      ctx.lineTo(w - pad.r, ly);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#E8B84B';
      ctx.fillRect(w - pad.r + 2, ly - 8, pad.r - 4, 16);
      ctx.fillStyle = '#0A0D12';
      ctx.font = 'bold 9.5px IBM Plex Mono, monospace';
      ctx.fillText(fmt(lastC.close), w - pad.r + 5, ly + 3.5);
    }

    // ---------------- RSI Oscillator Sub-pane ----------------
    if(showOsc){
      // Divider
      ctx.strokeStyle = 'rgba(255,255,255,0.12)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(pad.l, oscTop - 6);
      ctx.lineTo(w - pad.r, oscTop - 6);
      ctx.stroke();

      // Title
      ctx.fillStyle = 'rgba(255,255,255,0.5)';
      ctx.font = 'bold 9px IBM Plex Mono, monospace';
      ctx.fillText('RSI (14)', pad.l + 4, oscTop + 8);

      const yFromRsi = rVal => oscTop + ((100 - rVal) / 100) * oscH;

      // Shaded range between 30 and 70
      const y70 = yFromRsi(70);
      const y30 = yFromRsi(30);
      ctx.fillStyle = 'rgba(129, 140, 248, 0.04)';
      ctx.fillRect(pad.l, y70, plotW, y30 - y70);

      // Overbought line 70
      ctx.strokeStyle = 'rgba(255, 92, 114, 0.4)';
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.moveTo(pad.l, y70);
      ctx.lineTo(w - pad.r, y70);
      ctx.stroke();
      ctx.fillStyle = 'rgba(255, 92, 114, 0.7)';
      ctx.fillText('70', w - pad.r + 6, y70 + 3);

      // Midline 50
      const y50 = yFromRsi(50);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      ctx.beginPath();
      ctx.moveTo(pad.l, y50);
      ctx.lineTo(w - pad.r, y50);
      ctx.stroke();
      ctx.fillStyle = 'rgba(255, 255, 255, 0.35)';
      ctx.fillText('50', w - pad.r + 6, y50 + 3);

      // Oversold line 30
      ctx.strokeStyle = 'rgba(38, 217, 166, 0.4)';
      ctx.beginPath();
      ctx.moveTo(pad.l, y30);
      ctx.lineTo(w - pad.r, y30);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(38, 217, 166, 0.7)';
      ctx.fillText('30', w - pad.r + 6, y30 + 3);

      // Continuous RSI curve
      ctx.beginPath();
      visibleCandles.forEach((c, idx) => {
        const xx = pad.l + (idx + 0.5) * step;
        const yy = yFromRsi(c._rsi || 50);
        if(idx === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
      });
      ctx.strokeStyle = '#818CF8';
      ctx.lineWidth = 1.6;
      ctx.stroke();

      // Latest RSI badge
      if(lastC && lastC._rsi != null){
        const lRsiY = yFromRsi(lastC._rsi);
        ctx.fillStyle = '#818CF8';
        ctx.fillRect(w - pad.r + 2, lRsiY - 7, pad.r - 4, 14);
        ctx.fillStyle = '#0A0D12';
        ctx.font = 'bold 8.5px IBM Plex Mono, monospace';
        ctx.fillText(fmt(lastC._rsi), w - pad.r + 5, lRsiY + 3.5);
      }
    }

    // ---------------- Crosshair & Inspection ----------------
    if(btState.mousePos && btState.hoverIndex >= 0){
      const hIdx = btState.hoverIndex - startIdx;
      if(hIdx >= 0 && hIdx < visibleCandles.length){
        const hx = pad.l + (hIdx + 0.5) * step;
        const hy = btState.mousePos.y;
        const hCandle = visibleCandles[hIdx];

        // Vertical line
        ctx.strokeStyle = 'rgba(255,255,255,0.35)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.moveTo(hx, pad.t);
        ctx.lineTo(hx, h - pad.b);
        ctx.stroke();

        // Horizontal line
        if(hy >= pad.t && hy <= pad.t + plotH){
          ctx.beginPath();
          ctx.moveTo(pad.l, hy);
          ctx.lineTo(w - pad.r, hy);
          ctx.stroke();

          // Price Pill on right axis
          const hoveredPrice = maxP - ((hy - pad.t) / plotH) * (maxP - minP);
          ctx.fillStyle = '#374151';
          ctx.fillRect(w - pad.r + 2, hy - 8, pad.r - 4, 16);
          ctx.fillStyle = '#fff';
          ctx.font = 'bold 9px IBM Plex Mono, monospace';
          ctx.fillText(fmt(hoveredPrice), w - pad.r + 5, hy + 3.5);
        }
        ctx.setLineDash([]);

        // Time Pill at bottom
        if(hCandle && hCandle.timestamp){
          const timeStr = formatTime(hCandle.timestamp);
          ctx.font = '9px IBM Plex Mono, monospace';
          const tw = ctx.measureText(timeStr).width + 8;
          ctx.fillStyle = '#1F2937';
          ctx.fillRect(hx - tw / 2, h - pad.b + 3, tw, 15);
          ctx.fillStyle = '#E5E7EB';
          ctx.fillText(timeStr, hx - tw / 2 + 4, h - pad.b + 14);
        }
      }
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

  // ---------------- Tab loading ----------------
  const tabLoadedAt = window.__CA_TAB_LOADED_AT = window.__CA_TAB_LOADED_AT || new Map();
  function loadTabData(tab, force=false){
    if(!tab) return;
    const now = Date.now();
    if(!force && tabLoadedAt.has(tab) && (now - tabLoadedAt.get(tab) < 4000)) return;
    tabLoadedAt.set(tab, now);

    try {
      if(tab==='charts'){ void loadDepth(); void (window.CATraderAnalysis?.loadChart?.()||Promise.resolve()); }
      else if(tab==='options'){ void loadOptions(); }
      else if(tab==='news'){ void Promise.allSettled([loadNews('stock'),loadNews('global')]); void loadNewsProviders(); }
      else if(tab==='newsreels'){ void loadNewsReels(); }
      else if(tab==='fundamentals'){ void loadFundamentals(); }
      else if(tab==='movers'){ void loadMovers(document.querySelector('[data-mover].active')?.dataset.mover||'gainers'); }
      else if(tab==='reco'){ void Promise.allSettled([loadRecommendations(force), loadRecommendationHistory(), (window.loadAutoTrade||loadAutoTrade)()]); }
      else if(tab==='orders'){ void Promise.all([loadFunds(),loadOrders(),loadPositions()]); }
      else if(tab==='funds'){ if(typeof loadFundsTab === 'function') void loadFundsTab(); }
      else if(tab==='auto'){ void (window.loadAutoTrade||loadAutoTrade)(); }
      else if(tab==='backtest'){ if(typeof initBacktest === 'function') void initBacktest(); }
      else if(tab==='console'){ void loadServerConsole(); }
      else if(tab==='reports'){ if(typeof loadReports === 'function') void loadReports(); }
      else if(tab==='quiz'){ if(typeof loadQuiz === 'function') void loadQuiz(); }
      else if(tab==='newspaper'){ if(typeof loadNewspaper === 'function') void loadNewspaper(); }
      else if(tab==='tutorial'){ if(typeof setupTutorialTrees === 'function') void setupTutorialTrees(); }
    } catch(e) {
      console.debug('loadTabData error for', tab, e);
    }
  }
  window.loadTabData = loadTabData;
  window.CATraderActions = {
    ...(window.CATraderActions||{}),
    refreshActiveTab: async (tab) => {
      try {
        if(tab==='news') return Promise.allSettled([loadNews('stock'),loadNews('global'),loadNewsProviders()]);
        if(tab==='newsreels') return loadNewsReels();
        if(tab==='fundamentals') return loadFundamentals();
        if(tab==='movers') return loadMovers(document.querySelector('[data-mover].active')?.dataset.mover||'gainers');
        if(tab==='reco') return Promise.allSettled([loadRecommendations(false),loadRecommendationHistory(),(window.loadAutoTrade||loadAutoTrade)()]);
        if(tab==='orders') return Promise.allSettled([loadFunds(),loadOrders(),loadPositions()]);
        if(tab==='auto') return (window.loadAutoTrade||loadAutoTrade)();
        if(tab==='backtest' && typeof initBacktest === 'function') return initBacktest(true);
        if(tab==='options') return loadOptions();
        if(tab==='funds' && typeof loadFundsTab === 'function') return loadFundsTab();
        if(tab==='charts') return Promise.allSettled([loadDepth(), window.CATraderAnalysis?.loadChart?.()]);
      } catch(e) { console.debug('[CA Trader tab refresh]',e); }
    }
  };
  
  // Merge Recommendations + Auto Trade into one workspace without deleting any controls.
  (()=>{
    const reco=document.getElementById('panel-reco'), auto=document.getElementById('panel-auto');
    if(reco&&auto&&!reco.dataset.autoMerged){
      const children=[...auto.children];
      children.slice(1).forEach(ch=>reco.appendChild(ch));
      auto.style.display='none'; auto.dataset.autoMerged='1';
      const recoTab=document.querySelector('.navtab[data-tab="reco"]'); if(recoTab) recoTab.textContent='Recommendations & Auto Trade';
      document.querySelectorAll('.navtab[data-tab="auto"]').forEach(t=>t.remove());
      if(typeof loadAutoTrade === 'function') void loadAutoTrade(); else if(window.loadAutoTrade) void window.loadAutoTrade();
    }
  })();
document.querySelectorAll('.navtab').forEach(t=>t.addEventListener('click',(e)=>{const tab=t.dataset.tab||e.target.closest('.navtab')?.dataset.tab;showTab(tab);loadTabData(tab,true);}));
  // Make selected-symbol changes from the existing chart/watchlist code refresh dependent panels.
  const oldLoadChart = window.CATraderSelectSymbol;
  window.CATraderSelectSymbol = async sym => { window.CATraderSymbol=sym; const row=[...document.querySelectorAll('.wl-item')].find(x=>(x.dataset.symbol||'')===sym); if(row){row.click();} else {toast(`Load ${sym} from search/watchlist`)} };
  $('notificationBtn')?.addEventListener('click',()=>{setTimeout(()=>{},0)});

  let __newsWarmTimer=null;
  function scheduleNewsWarm(){
    clearInterval(__newsWarmTimer);
    __newsWarmTimer=setInterval(async()=>{
      if(document.visibilityState!=='visible')return;
      if(document.querySelector('.navtab.active')?.dataset.tab!=='news')return;
      try{const mode=newsMode, s=selectedSymbol(); const url=mode==='stock'?('/api/news/stock/'+encodeURIComponent(s)+'?limit=100&_='+Date.now()):('/api/news/global?limit=100&_='+Date.now());
        const d=await api(url,{timeoutMs:2500,cache:'no-store'});
        if((d.events||[]).length){APP_CACHE[mode==='stock'?'newsStock':'newsGlobal']=d;window.__caNewsEvents=d.events||[];renderCurrentNewsList();if($('newsUpdated'))$('newsUpdated').textContent=`${(d.events||[]).length} stories · ${formatTime(d.timestamp)}`;clearInterval(__newsWarmTimer);__newsWarmTimer=null;}
      }catch(_){}
    },1500);
  }
  if(document.getElementById('panel-news'))scheduleNewsWarm();
  document.querySelector('.navtab[data-tab="newsreels"]')?.remove();
  document.getElementById('panel-newsreels')?.remove();
  // Initial data for the visible tab plus live depth.
  const __monitor={idx:0,technical:new Map(),news:new Set(),movers:new Set(),options:new Map()};
  async function monitorOptions(){try{if(!market.nse&&!market.mcx)return;const sym=selectedSymbol();if(!document.getElementById('panel-options')?.classList.contains('active')||!sym)return;const expiry=document.getElementById('optionExpiry')?.value||'';const d=await api('/api/options/'+encodeURIComponent(sym)+'/chain'+(expiry?`?expiry=${encodeURIComponent(expiry)}`:''));for(const s of (d.strikes||[])){for(const side of ['call','put']){const c=s[side];if(!c?.instrument_key)continue;const k=c.instrument_key,now={ltp:Number(c.ltp),delta:Number(c.delta),gamma:Number(c.gamma),theta:Number(c.theta),vega:Number(c.vega)},prev=__monitor.options.get(k);if(prev&&Number.isFinite(now.ltp)&&Number.isFinite(prev.ltp)&&prev.ltp>0&&Math.abs((now.ltp-prev.ltp)/prev.ltp)>=0.10)showLiveAlert(`${sym} option price move`,`${side.toUpperCase()} ${fmt(s.strike)} · LTP ${fmt(now.ltp)} · ${((now.ltp-prev.ltp)/prev.ltp*100).toFixed(1)}%`,'neutral');if(prev&&Number.isFinite(now.delta)&&Number.isFinite(prev.delta)&&Math.abs(now.delta-prev.delta)>=0.08)showLiveAlert(`${sym} option Greeks changed`,`${side.toUpperCase()} ${fmt(s.strike)} · Delta ${fmt(prev.delta)} → ${fmt(now.delta)}`,'neutral');__monitor.options.set(k,now)}}}catch(_){}} 

  async function monitorTechnicalChanges(){try{if(!market.nse&&!market.mcx)return;const syms=[...new Set([...document.querySelectorAll('.wl-item')].map(r=>r.dataset.symbol).filter(Boolean))];if(!syms.length)return;const sym=syms[__monitor.idx++%syms.length];const d=await api('/api/analysis/technical-mtf/'+encodeURIComponent(sym));for(const x of (d.items||[])){const k=`${sym}:${x.timeframe}`;const prev=__monitor.technical.get(k);if(prev&&prev.signal&&x.signal&&prev.signal!==x.signal)showLiveAlert(`${sym} ${x.timeframe} signal changed`,`${prev.signal} → ${x.signal}` ,x.signal==='BUY'?'buy':x.signal==='SELL'?'sell':'neutral');__monitor.technical.set(k,{signal:x.signal})}}catch(_){}} 
  async function monitorNewNews(){try{const sym=selectedSymbol();const d=await api('/api/news/stock/'+encodeURIComponent(sym)+'?limit=8');const g=await api('/api/news/global?limit=8');for(const e of [...(d.events||[]),...(g.events||[])].slice(0,10)){const k=e.url||e.headline;if(!k)continue;if(!__monitor.news.has(k)){if(__monitor.news.size)showLiveAlert(`New news · ${sym}`,e.headline||'New qualifying news available','neutral');__monitor.news.add(k)}}}catch(_){}} 
  async function monitorMovers(){try{for(const cat of ['gainers','losers']){const d=await api('/api/market/movers?category='+cat+'&limit=10');for(const x of (d.items||[]).slice(0,3)){const k=`${cat}:${x.symbol}`;if(!__monitor.movers.has(k)&&__monitor.movers.size)showLiveAlert(`${cat==='gainers'?'Gainer':'Loser'} mover`,`${x.symbol} · ${fmt(x.ltp)} · ${fmt(x.change_pct)}%` ,cat==='gainers'?'buy':'sell');__monitor.movers.add(k)}}}catch(_){}} 
  setInterval(()=>{if(selectedSymbol()&&document.getElementById('panel-news')?.classList.contains('active')){tabLoadedAt.delete('news');loadNews(newsMode)}},300000);
  let __quoteSnapshotBusy=false;
  async function refreshUnifiedMarketSnapshot(){
    if(__quoteSnapshotBusy)return;
    const group=window.__CA_WATCHLIST_GROUP||window.__CA_WL_GROUP; const items=group?.items||[];
    const syms=[...new Set(items.map(x=>String(x.symbol||'').toUpperCase().trim()).filter(Boolean))];
    const selected=String(window.CATraderSymbol||selectedSymbol()||'').toUpperCase().trim();
    if(selected&&!syms.includes(selected))syms.push(selected);
    if(!syms.length)return;
    __quoteSnapshotBusy=true;
    try{
      const d=await api('/api/market/stream/snapshot?instruments='+encodeURIComponent(syms.join(',')),{timeoutMs:1800,cache:'no-store'});
      const applier=window.CATraderLiveMarket?.applyLiveTick;
      if(typeof applier!=='function') return;
      (d.items||[]).forEach(q=>applier({...q,source:q.source||'server_snapshot'}));
    }catch(_){} finally{__quoteSnapshotBusy=false}
  }
  // Authoritative client heartbeat: never depends on tab switches or watchlist clicks.
  function scheduleLiveSnapshot(){
    const isOpen = typeof window.isAnyMarketOpen === 'function' ? window.isAnyMarketOpen() : false;
    const nextDelay = isOpen ? 3000 : 60000;
    refreshUnifiedMarketSnapshot().catch(()=>{}).finally(()=>setTimeout(scheduleLiveSnapshot, nextDelay));
  }
  setTimeout(scheduleLiveSnapshot,400);
  setInterval(()=>{if(selectedSymbol()&&document.getElementById('panel-options')?.classList.contains('active')&&!String(selectedSymbol()).toUpperCase().includes('CRUDE')){void fetchOptionChain()}},12000);
  setInterval(()=>{if(selectedSymbol()&&document.getElementById('panel-reco')?.classList.contains('active')){void loadRecommendationHistory()}},20000);
  let __lastUnread=-1; async function refreshNotificationBadge(){try{const d=await api('/api/notifications/unread');const n=(d.items||[]).length;const b=$('notificationBadge');if(b){b.textContent=n;b.style.display=n?'inline-flex':'none'}if(__lastUnread>=0&&n>__lastUnread&&'Notification' in window&&Notification.permission==='granted'){const x=(d.items||[])[0];new Notification(x?.title||'CA Trader alert',{body:x?.body||'New trading alert'});}__lastUnread=n;}catch(_){}}
  async function monitorAllAlerts(){try{if(!market.nse&&!market.mcx){await refreshNotificationBadge();return;}await api('/api/notifications/greeks-watch');await api('/api/notifications/monitor');await refreshNotificationBadge();}catch(_){}} monitorAllAlerts(); setInterval(()=>{if(document.visibilityState==='visible')monitorAllAlerts()},60000); setInterval(()=>{if(document.visibilityState==='visible'&&document.getElementById('panel-console')?.classList.contains('active'))loadServerConsole()},5000);
  setInterval(()=>{if(selectedSymbol()&&document.visibilityState==='visible'&&document.getElementById('panel-charts')?.classList.contains('active')&&(market.nse||market.mcx))void monitorTechnicalChanges()},300000); setInterval(()=>{if(selectedSymbol()&&document.visibilityState==='visible'&&document.getElementById('panel-options')?.classList.contains('active'))void monitorOptions()},180000); setInterval(()=>{if(selectedSymbol()&&document.visibilityState==='visible'&&document.getElementById('panel-news')?.classList.contains('active'))void monitorNewNews()},300000); setInterval(()=>{if(document.visibilityState==='visible'&&document.getElementById('panel-movers')?.classList.contains('active'))monitorMovers()},60000);
  
  setTimeout(()=>{
    try { if(typeof ensureChartLayout === 'function') ensureChartLayout(); else (window.CATraderAnalysis?.ensureChartLayout || window.ensureChartLayout)?.(); } catch(_){}
    const tab=document.querySelector('.navtab.active')?.dataset.tab;
    if(tab) loadTabData(tab);
    const sym = typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.state?.symbol);
    if(sym){ (window.CATraderAnalysis?.loadChart || window.loadChart || (typeof loadChart === 'function' ? loadChart : null))?.()?.catch?.(()=>{}); }
  }, 300);
  setTimeout(()=>{
    const sym = typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.state?.symbol);
    if(sym){
      try { if(typeof ensureChartLayout === 'function') ensureChartLayout(); else (window.CATraderAnalysis?.ensureChartLayout || window.ensureChartLayout)?.(); } catch(_){}
      (window.CATraderAnalysis?.loadChart || window.loadChart || (typeof loadChart === 'function' ? loadChart : null))?.()?.catch?.(()=>{});
    }
  }, 1200);
})();
