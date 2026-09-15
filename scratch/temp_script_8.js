
(() => {
  const $ = window.$ || (id => document.getElementById(id));
  const esc = window.esc || (v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
  const api = window.api || (async (u, o={}) => { const r = await fetch(u, {credentials:'include', headers:{'Content-Type':'application/json'}, ...o}); return r.json(); });
  const toast = window.toast || ((m) => console.log(m));
  const selectedSymbol = window.selectedSymbol || (() => window.state?.symbol || 'RELIANCE');
  const fmtMoney = window.fmtMoney || (v => '₹' + Number(v||0).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2}));
  const formatTime = window.formatTime || (v => { try { const d = new Date(v); return isNaN(d) ? String(v||'') : d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}); } catch(_) { return String(v||''); } });
  const isOscillator = (name) => ['RSI','MACD','STOCH','CCI','WILLR','ADX'].includes(String(name||'').toUpperCase());
  const draw = () => (window.draw || window.CATraderAnalysis?.draw)?.();

  // Interactive CA AI News Discussion Logic (Item 17)
  let currentDiscussNews = null;

  function openNewsDiscussionModal(item){
    currentDiscussNews = item;
    const modal = $('newsDiscussionModal');
    if(!modal) return;

    const isBull = item.sentiment === 'BULLISH';
    const isBear = item.sentiment === 'BEARISH';
    const badgeClass = isBull ? 'buy' : isBear ? 'sell' : 'neutral';
    const badgeText = `${isBull ? '▲ 100% Buy Signal' : isBear ? '▼ 100% Sell Signal' : '● ' + item.sentiment} (${item.impact_pct || 'High'})`;

    if($('newsModalProbBadge')){
      $('newsModalProbBadge').className = `tag ${badgeClass}`;
      $('newsModalProbBadge').textContent = badgeText;
    }
    if($('newsModalMeta')) $('newsModalMeta').textContent = `${item.source} · ${item.time} · ${item.scope || 'Global'}`;
    if($('newsModalHeadline')) $('newsModalHeadline').textContent = item.headline;
    if($('newsModalSummary')) $('newsModalSummary').innerHTML = `<b>CA AI Assessment:</b> ${esc(item.ca_ai_insight || item.summary || '')}`;

    const chatLog = $('newsChatLog');
    if(chatLog){
      chatLog.innerHTML = `
        <div style="background:var(--surface);border-left:3px solid var(--gold);padding:8px 10px;border-radius:4px;color:var(--text);line-height:1.4;">
          <b style="color:var(--gold);">CA AI:</b> High-materiality institutional event detected for <b>${esc(item.symbol || selectedSymbol() || 'the market')}</b>. What specific trade setups, option strikes, or risk parameters would you like to discuss?
        </div>
      `;
    }

    modal.style.display = 'flex';
  }

  $('newsDiscussionClose')?.addEventListener('click', () => {
    const m = $('newsDiscussionModal');
    if(m) m.style.display = 'none';
  });

  async function sendNewsChatMessage(){
    const inp = $('newsChatInput');
    const log = $('newsChatLog');
    if(!inp || !log || !currentDiscussNews) return;
    const msg = inp.value.trim();
    if(!msg) return;
    inp.value = '';

    const uMsg = document.createElement('div');
    uMsg.style.cssText = 'background:var(--surface-3);align-self:flex-end;padding:6px 10px;border-radius:6px;max-width:80%;color:var(--text);';
    uMsg.textContent = msg;
    log.appendChild(uMsg);

    const typing = document.createElement('div');
    typing.style.cssText = 'background:var(--surface);border-left:3px solid var(--gold);padding:8px 10px;border-radius:4px;color:var(--text-dim);';
    typing.innerHTML = '<b style="color:var(--gold);">CA AI:</b> Analyzing derivatives impact and risk profile...';
    log.appendChild(typing);
    log.scrollTop = log.scrollHeight;

    try {
      const res = await api('/api/news/discuss', {
        method: 'POST',
        body: JSON.stringify({
          headline: currentDiscussNews.headline,
          query: msg,
          symbol: currentDiscussNews.symbol || selectedSymbol() || 'NIFTY',
          sentiment: currentDiscussNews.sentiment,
          impact: currentDiscussNews.impact_pct
        })
      });
      typing.innerHTML = `<b style="color:var(--gold);">CA AI:</b> ${esc(res.reply).replace(/\n/g, '<br>')}`;
    } catch(err) {
      typing.innerHTML = `<b style="color:var(--sell);">CA AI:</b> Error: ${esc(err.message)}`;
    }
    log.scrollTop = log.scrollHeight;
  }

  $('newsChatSendBtn')?.addEventListener('click', sendNewsChatMessage);
  $('newsChatInput')?.addEventListener('keydown', (e) => {
    if(e.key === 'Enter') sendNewsChatMessage();
  });

  
  function updateOscSplitterPosition(){
    let sp = document.getElementById('chartOscSplitter');
    const curState = window.__CA_TRADER_STATE || window.state || {};
    const vp = document.getElementById('chartViewport');
    if(!vp) return;
    const hasOsc = curState.appliedIndicators && curState.appliedIndicators.some(i => isOscillator(i.name));
    if(!hasOsc){
      if(sp) sp.style.display = 'none';
      return;
    }
    if(!sp){
      sp = document.createElement('div');
      sp.id = 'chartOscSplitter';
      sp.style.cssText = 'position:absolute;left:0;right:0;height:8px;cursor:row-resize;z-index:30;display:flex;align-items:center;justify-content:center;transition:background .15s;';
      sp.innerHTML = '<div style="width:40px;height:3px;background:rgba(232,184,75,0.6);border-radius:2px;"></div>';
      sp.onmouseenter = () => sp.style.background = 'rgba(232,184,75,0.18)';
      sp.onmouseleave = () => sp.style.background = 'transparent';
      let isDragging = false, startY = 0, startRatio = 0.23;
      sp.onpointerdown = (e) => {
        isDragging = true;
        startY = e.clientY;
        startRatio = curState.oscHeightRatio || 0.23;
        sp.setPointerCapture(e.pointerId);
        e.stopPropagation();
      };
      sp.onpointermove = (e) => {
        if(!isDragging) return;
        const totalH = vp.clientHeight || 400;
        const dy = startY - e.clientY;
        const newRatio = Math.max(0.12, Math.min(0.48, startRatio + dy / totalH));
        curState.oscHeightRatio = newRatio;
        draw();
      };
      sp.onpointerup = (e) => {
        isDragging = false;
        try { sp.releasePointerCapture(e.pointerId); } catch(_) {}
      };
      vp.appendChild(sp);
    }
    const oscH = Math.max(60, Math.min(Math.floor(vp.clientHeight * 0.48), Math.floor(vp.clientHeight * (curState.oscHeightRatio || 0.23))));
    const oscTop = vp.clientHeight - oscH - 36;
    sp.style.top = `${oscTop - 4}px`;
    sp.style.display = 'flex';
  }
  window.updateOscSplitterPosition = updateOscSplitterPosition;

  
  function setupMcxAutocomplete(){
    const inp = $('mcxOptSymbol');
    const menu = $('mcxSymbolSuggestions');
    if(!inp || !menu || inp.dataset.autocompleteBound) return;
    inp.dataset.autocompleteBound = '1';

    const COMMODITIES = [
      { symbol: 'CRUDEOIL', name: 'Crude Oil', desc: 'MCX Energy · 100 bbl' },
      { symbol: 'NATURALGAS', name: 'Natural Gas', desc: 'MCX Energy · 1250 mmBtu' },
      { symbol: 'GOLD', name: 'Gold 1 Kg', desc: 'MCX Precious Metals' },
      { symbol: 'GOLDM', name: 'Gold Mini', desc: 'MCX 100 grams' },
      { symbol: 'SILVER', name: 'Silver 30 Kg', desc: 'MCX Precious Metals' },
      { symbol: 'SILVERM', name: 'Silver Mini', desc: 'MCX 5 Kg' },
      { symbol: 'COPPER', name: 'Copper', desc: 'MCX Base Metals 2.5 MT' },
      { symbol: 'ZINC', name: 'Zinc', desc: 'MCX Base Metals 5 MT' },
      { symbol: 'LEAD', name: 'Lead', desc: 'MCX Base Metals 5 MT' },
      { symbol: 'ALUMINIUM', name: 'Aluminium', desc: 'MCX Base Metals 5 MT' },
      { symbol: 'NICKEL', name: 'Nickel', desc: 'MCX Base Metals' }
    ];

    function renderList(query = ''){
      const q = String(query).trim().toUpperCase();
      const matches = COMMODITIES.filter(c => c.symbol.includes(q) || c.name.toUpperCase().includes(q) || c.desc.toUpperCase().includes(q));
      if(!matches.length){ menu.style.display = 'none'; return; }
      menu.innerHTML = matches.map(c => `
        <div class="mcx-suggestion-item" data-sym="${c.symbol}" style="padding:7px 10px;cursor:pointer;border-bottom:1px solid var(--border-soft);display:flex;flex-direction:column;gap:2px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <b style="font-size:12px;color:var(--text);">${c.symbol}</b>
            <span class="tag neutral" style="font-size:9.5px;padding:1px 5px;">MCX</span>
          </div>
          <div style="font-size:10.5px;color:var(--text-dim);">${c.name} · ${c.desc}</div>
        </div>
      `).join('');
      menu.style.display = 'block';

      menu.querySelectorAll('.mcx-suggestion-item').forEach(item => {
        item.onclick = (e) => {
          e.stopPropagation();
          inp.value = item.dataset.sym;
          menu.style.display = 'none';
          if(typeof fetchMcxOptionChain === 'function') fetchMcxOptionChain();
        };
      });
    }

    inp.addEventListener('input', () => renderList(inp.value));
    inp.addEventListener('focus', () => renderList(inp.value));
    document.addEventListener('click', (e) => {
      if(!e.target.closest('#mcxOptSymbol') && !e.target.closest('#mcxSymbolSuggestions')){
        menu.style.display = 'none';
      }
    });
  }

  window.openNewsDiscussionModal = openNewsDiscussionModal;

  // ---------------- Reports & Analytics (Item 26) ----------------
  async function loadReports(){
    const tf = document.getElementById('reportTimeframeSelect')?.value || '30d';
    try {
      const [pnlData, tradeData] = await Promise.all([
        api('/api/reports/pnl?range=' + encodeURIComponent(tf)).catch(() => ({})),
        api('/api/reports/trades?range=' + encodeURIComponent(tf)).catch(() => ({}))
      ]);
      const sum = pnlData.summary || {};
      const netPnl = Number(sum.net_pnl || 0);
      const netPnlEl = document.getElementById('repNetPnl');
      if(netPnlEl){
        netPnlEl.textContent = (netPnl >= 0 ? '+₹ ' : '-₹ ') + Math.abs(netPnl).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        netPnlEl.style.color = netPnl >= 0 ? 'var(--buy)' : 'var(--sell)';
      }
      if(document.getElementById('repNetPnlPct')){
        const retPct = Number(sum.return_pct || (netPnl / 100000 * 100));
        document.getElementById('repNetPnlPct').textContent = `${retPct >= 0 ? '+' : ''}${retPct.toFixed(2)}% on ₹1,00,000 capital`;
      }
      if(document.getElementById('repWinRate')){
        document.getElementById('repWinRate').textContent = `${Number(sum.win_rate || 0).toFixed(1)}%`;
      }
      if(document.getElementById('repWinLossRatio')){
        document.getElementById('repWinLossRatio').textContent = `${sum.win_trades || 0}W / ${sum.loss_trades || 0}L`;
      }
      if(document.getElementById('repTurnover')){
        document.getElementById('repTurnover').textContent = '₹ ' + Math.round(Number(sum.total_turnover || 0)).toLocaleString('en-IN');
      }
      if(document.getElementById('repTotalTrades')){
        document.getElementById('repTotalTrades').textContent = `${sum.total_trades || 0} Trades executed`;
      }
      if(document.getElementById('repTaxes')){
        document.getElementById('repTaxes').textContent = '₹ ' + Number(sum.total_charges || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2});
      }
      if(document.getElementById('repProfitFactor')){
        document.getElementById('repProfitFactor').textContent = Number(sum.profit_factor || 1.85).toFixed(2);
      }

      const items = tradeData.items || [];
      const tbody = document.getElementById('repTradeBookRows');
      if(document.getElementById('repTradeCountBadge')) document.getElementById('repTradeCountBadge').textContent = `${items.length} trades in ${tf}`;
      if(tbody){
        if(!items.length){
          tbody.innerHTML = '<tr><td colspan="10" class="muted" style="text-align:center;padding:18px;">No trades recorded in this period.</td></tr>';
        } else {
          tbody.innerHTML = items.map(t => {
            const p = Number(t.pnl || 0);
            const pCls = p > 0 ? 'cell-up' : p < 0 ? 'cell-down' : '';
            const sideCls = t.side === 'BUY' ? 'tag buy' : 'tag sell';
            return `<tr>
              <td style="font-family:var(--font-mono);font-size:11px;">#${esc(t.id || '—')}</td>
              <td>${esc(formatTime(t.created_at || t.entry_time))}</td>
              <td><b>${esc(t.symbol)}</b></td>
              <td><span class="${sideCls}" style="font-size:9.5px;padding:2px 6px;">${esc(t.side)}</span></td>
              <td class="cell-num">${fmt(t.qty || t.quantity)}</td>
              <td class="cell-num">₹ ${fmt(t.entry_price || t.price)}</td>
              <td class="cell-num">₹ ${fmt(t.exit_price || t.ltp || t.price)}</td>
              <td class="cell-num">₹ ${Math.round(Number(t.turnover || (t.price * t.qty) || 0)).toLocaleString('en-IN')}</td>
              <td class="cell-num ${pCls}"><b>${p >= 0 ? '+' : ''}${fmtMoney(p)}</b></td>
              <td><span class="tag neutral" style="font-size:9px;">${esc(t.status || 'CLOSED')}</span></td>
            </tr>`;
          }).join('');
        }
      }
      window.__caReportTradeItems = items;
    } catch(e) {
      console.debug('Error loading reports:', e);
    }
  }
  window.loadReports = loadReports;

  document.getElementById('reportExportCsvBtn')?.addEventListener('click', () => {
    const items = window.__caReportTradeItems || [];
    if(!items.length){ toast('No trade records to export.'); return; }
    let csv = 'Trade ID,Executed At,Symbol,Side,Quantity,Entry Price,Exit Price,Realized PnL,Status\n';
    items.forEach(t => {
      csv += `"${t.id || ''}","${t.created_at || t.entry_time || ''}","${t.symbol || ''}","${t.side || ''}",${t.qty || t.quantity || 0},${t.entry_price || t.price || 0},${t.exit_price || 0},${t.pnl || 0},"${t.status || 'CLOSED'}"\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `CATrader_TradeBook_${new Date().toISOString().slice(0,10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast('Trade book CSV exported successfully');
  });
  document.getElementById('reportRefreshBtn')?.addEventListener('click', loadReports);
  document.getElementById('reportTimeframeSelect')?.addEventListener('change', loadReports);

  // ---------------- Trader Quiz (Item 23) ----------------
  let quizScore = { correct: 0, total: 0 };
  let currentQuizQuestions = [];

  async function loadQuiz(category = 'all'){
    const container = document.getElementById('quizContainer');
    if(!container) return;
    container.innerHTML = '<div class="data-empty">Loading institutional quiz questions…</div>';
    try {
      const url = '/api/quiz/questions' + (category !== 'all' ? '?category=' + encodeURIComponent(category) : '');
      const res = await fetch(url);
      const data = await res.json();
      const questions = data.questions || [];
      currentQuizQuestions = questions;
      if(!questions.length){
        container.innerHTML = '<div class="data-empty">No quiz questions available for this category.</div>';
        return;
      }
      container.innerHTML = questions.map((q, qIdx) => `
        <div class="quiz-card" id="quizCard_${qIdx}">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <span class="tag neutral" style="font-size:10px;">${esc(q.category || 'General')}</span>
            <span class="muted" style="font-size:10px;">Question ${qIdx + 1} of ${questions.length}</span>
          </div>
          <div class="quiz-q-title">${esc(q.question)}</div>
          <div class="quiz-options">
            ${q.options.map((opt, optIdx) => `
              <button class="quiz-opt-btn" data-q="${qIdx}" data-opt="${optIdx}">
                <b>${['A', 'B', 'C', 'D'][optIdx] || optIdx + 1}.</b> ${esc(opt)}
              </button>
            `).join('')}
          </div>
          <div class="quiz-explanation" id="quizExp_${qIdx}">
            <b> Institutional Analysis:</b> ${esc(q.explanation || 'Option rationale confirmed by algorithmic trade rules.')}
          </div>
        </div>
      `).join('');

      container.querySelectorAll('.quiz-opt-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const qIdx = Number(btn.dataset.q);
          const optIdx = Number(btn.dataset.opt);
          const q = currentQuizQuestions[qIdx];
          if(!q || btn.dataset.answered) return;

          const card = document.getElementById('quizCard_' + qIdx);
          const allBtns = card.querySelectorAll('.quiz-opt-btn');
          allBtns.forEach(b => {
            b.dataset.answered = '1';
            b.disabled = true;
            b.style.cursor = 'default';
          });

          quizScore.total++;
          if(optIdx === q.answer_index){
            btn.classList.add('correct');
            quizScore.correct++;
          } else {
            btn.classList.add('wrong');
            const correctBtn = card.querySelector(`[data-opt="${q.answer_index}"]`);
            if(correctBtn) correctBtn.classList.add('correct');
          }

          const exp = document.getElementById('quizExp_' + qIdx);
          if(exp) exp.style.display = 'block';

          const badge = document.getElementById('quizScoreBadge');
          if(badge){
            const pct = Math.round((quizScore.correct / quizScore.total) * 100);
            badge.textContent = `Score: ${quizScore.correct} / ${quizScore.total} (${pct}%)`;
            badge.className = `tag ${pct >= 70 ? 'buy' : pct >= 40 ? 'gold' : 'sell'}`;
          }
        });
      });
    } catch(e) {
      container.innerHTML = `<div class="data-empty" style="color:var(--sell);">Failed to load quiz: ${esc(e.message)}</div>`;
    }
  }
  window.loadQuiz = loadQuiz;

  document.querySelectorAll('[data-quiz-cat]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-quiz-cat]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadQuiz(btn.dataset.quizCat);
    });
  });
  document.getElementById('quizResetBtn')?.addEventListener('click', () => {
    quizScore = { correct: 0, total: 0 };
    const badge = document.getElementById('quizScoreBadge');
    if(badge){
      badge.textContent = 'Score: 0 / 0 (0%)';
      badge.className = 'tag gold';
    }
    const activeCat = document.querySelector('[data-quiz-cat].active')?.dataset.quizCat || 'all';
    loadQuiz(activeCat);
  });

  // ---------------- E-Newspaper (Item 24) ----------------
  async function loadNewspaper(){
    const hero = document.getElementById('newspaperLeadStory');
    const grid = document.getElementById('newspaperGrid');
    const archives = document.getElementById('newspaperArchives');
    if(!hero || !grid) return;
    hero.innerHTML = '<div class="data-empty">Fetching Today\'s Financial Daily edition…</div>';
    try {
      const res = await fetch('/api/newspaper/feed');
      const data = await res.json();
      const today = data.today || {};
      const articles = today.articles || [];

      if(document.getElementById('newspaperHeaderSub') && today.edition_title){
        document.getElementById('newspaperHeaderSub').textContent = `${today.edition_title} · ${today.date || ''}`;
      }
      if(document.getElementById('newspaperDateTag') && today.date){
        document.getElementById('newspaperDateTag').textContent = today.date;
      }

      if(articles.length){
        const lead = articles[0];
        const leadImpactCls = lead.sentiment === 'BULLISH' ? 'buy' : lead.sentiment === 'BEARISH' ? 'sell' : 'neutral';
        hero.innerHTML = `
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <span class="tag gold" style="font-size:10px;font-weight:700;">★ LEAD FRONT PAGE STORY</span>
            <span class="tag ${leadImpactCls}" style="font-size:10px;">${esc(lead.impact || lead.sentiment || 'HIGH IMPACT')}</span>
            <span class="muted" style="font-size:10.5px;">By ${esc(lead.author || 'CA Institutional Intelligence')} · ${esc(lead.read_time || '3 min read')}</span>
          </div>
          <h2 style="font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px;line-height:1.35;">${esc(lead.title)}</h2>
          <p style="font-size:13px;line-height:1.6;color:var(--text-dim);margin-bottom:12px;">${esc(lead.summary)}</p>
          <div style="display:flex;gap:8px;">
            <button class="btn gold small" onclick="window.openNewsDiscussionModal({headline:'${esc(lead.title).replace(/'/g,"\\'")}', summary:'${esc(lead.summary).replace(/'/g,"\\'")}', sentiment:'${lead.sentiment||'NEUTRAL'}'})"> Discuss with CA AI</button>
          </div>
        `;
      }

      const rest = articles.slice(1);
      if(rest.length){
        grid.innerHTML = rest.map(art => {
          const artCls = art.sentiment === 'BULLISH' ? 'buy' : art.sentiment === 'BEARISH' ? 'sell' : 'neutral';
          return `
            <div class="newspaper-card">
              <div>
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                  <span class="tag neutral" style="font-size:9.5px;">${esc(art.category || 'Markets')}</span>
                  <span class="tag ${artCls}" style="font-size:9.5px;">${esc(art.sentiment || 'NEUTRAL')}</span>
                </div>
                <div class="newspaper-article-title">${esc(art.title)}</div>
                <div style="font-size:11.5px;color:var(--text-dim);line-height:1.5;margin-bottom:10px;">${esc(art.summary)}</div>
              </div>
              <div style="display:flex;align-items:center;justify-content:space-between;border-top:1px solid var(--border-soft);padding-top:8px;margin-top:8px;">
                <span class="muted" style="font-size:10px;">${esc(art.author || 'Desk')} · ${esc(art.read_time || '2 min')}</span>
                <button class="btn ghost small" style="font-size:10.5px;padding:3px 8px;" onclick="window.openNewsDiscussionModal({headline:'${esc(art.title).replace(/'/g,"\\'")}', summary:'${esc(art.summary).replace(/'/g,"\\'")}', sentiment:'${art.sentiment||'NEUTRAL'}'})">AI Analysis</button>
              </div>
            </div>
          `;
        }).join('');
      }

      if(archives && data.archives){
        archives.innerHTML = (data.archives || []).map(a => `
          <button class="chip-filter" style="white-space:nowrap;font-size:10.5px;" onclick="toast('Archived edition for ${a.date} loaded');">
             ${esc(a.date)} (${a.article_count || 5} articles)
          </button>
        `).join('');
      }
    } catch(e) {
      hero.innerHTML = `<div class="data-empty" style="color:var(--sell);">Failed to load Financial Daily edition: ${esc(e.message)}</div>`;
    }
  }
  window.loadNewspaper = loadNewspaper;
  document.getElementById('newspaperRefreshBtn')?.addEventListener('click', loadNewspaper);

  // ---------------- Tutorial Feature Tree (Item 22) ----------------
  function setupTutorialTrees(){
    document.querySelectorAll('.tut-header').forEach(hdr => {
      hdr.onclick = () => {
        const node = hdr.closest('.tut-node');
        if(!node) return;
        node.classList.toggle('open');
        const toggle = hdr.querySelector('.tut-toggle-btn');
        if(toggle) toggle.textContent = node.classList.contains('open') ? '[-]' : '[+]';
      };
    });

    document.getElementById('tutExpandAllBtn')?.addEventListener('click', () => {
      document.querySelectorAll('.tut-node').forEach(n => {
        n.classList.add('open');
        const t = n.querySelector('.tut-toggle-btn');
        if(t) t.textContent = '[-]';
      });
    });

    document.getElementById('tutCollapseAllBtn')?.addEventListener('click', () => {
      document.querySelectorAll('.tut-node').forEach(n => {
        n.classList.remove('open');
        const t = n.querySelector('.tut-toggle-btn');
        if(t) t.textContent = '[+]';
      });
    });
  }
  window.setupTutorialTrees = setupTutorialTrees;

  // ---------------- Backtest Controls (Item 17) ----------------
  document.getElementById('btChartModeToggle')?.addEventListener('click', (e) => {
    const btn = e.currentTarget;
    const isPan = btn.textContent === 'Pan';
    btn.textContent = isPan ? 'Crosshair' : 'Pan';
    toast(`Backtest chart set to ${btn.textContent} mode`);
  });
  document.getElementById('btResetViewBtn')?.addEventListener('click', () => {
    toast('Backtest chart reset to default view');
    if(typeof drawBacktestCanvas === 'function') drawBacktestCanvas();
  });
  document.getElementById('btDrawSel')?.addEventListener('change', (e) => {
    const val = e.target.value;
    if(!val) return;
    toast(`Selected ${val} for replay chart. Click replay chart to place.`);
    e.target.value = '';
  });

  // ---------------- Chart Toolbar & Timeframe Dropdown (Item 2) ----------------
  const btnTf = document.getElementById('btnTfDropdown');
  const tfMenu = document.getElementById('timeframeDropdownMenu');
  btnTf?.addEventListener('click', (e) => {
    e.stopPropagation();
    if(tfMenu) tfMenu.style.display = (tfMenu.style.display === 'none' || !tfMenu.style.display) ? 'block' : 'none';
  });
  document.querySelectorAll('#timeframeDropdownMenu .tf-dd-item').forEach(item => {
    item.addEventListener('click', (e) => {
      const tf = item.dataset.tf;
      if(!tf) return;
      state.tf = tf;
      const lbl = document.getElementById('selectedTfLabel');
      if(lbl) lbl.textContent = tf;
      document.querySelectorAll('#timeframeDropdownMenu .tf-dd-item').forEach(x => x.classList.toggle('active', x.dataset.tf === tf));
      if(tfMenu) tfMenu.style.display = 'none';
      state.zoom = 1;
      if(typeof loadChart === 'function') loadChart();
      toast(`Chart timeframe set to ${tf}`);
    });
  });
  document.addEventListener('click', (e) => {
    if(tfMenu && !e.target.closest('#btnTfDropdown') && !e.target.closest('#timeframeDropdownMenu')){
      tfMenu.style.display = 'none';
    }
  });

  // ---------------- 114 Studies & Indicators Modal (Item 2) ----------------
  const ALL_114_INDICATORS = [
    "ADX/DMS", "ATR Bands", "ATR Trailing Stops", "Accumulation/Distribution", "Accumulative Swing Index",
    "Alligator", "Anchored VWAP", "Aroon", "Aroon Oscillator", "Average True Range",
    "Awesome Oscillator", "Balance of Power", "Bollinger %b", "Bollinger Bands", "Bollinger Bandwidth",
    "Candlestick Patterns", "Center Of Gravity", "Central Pivot Range", "Chaikin Money Flow", "Chaikin Volatility",
    "Chande Forecast Oscillator", "Chande Momentum Oscillator", "Choppiness Index", "Commodity Channel Index", "Coppock Curve",
    "Correlation Coefficient", "Darvas Box", "Detrended Price Oscillator", "Disparity Index", "Donchian Channel",
    "Donchian Width", "Ease of Movement", "Ehler Fisher Transform", "Elder Force Index", "Elder Impulse System",
    "Elder Ray Index", "Fractal Chaos Bands", "Fractal Chaos Oscillator", "Gator Oscillator", "Guppy Multiple Moving Average",
    "High Low Bands", "High-Low Index", "Historical Volatility", "Hull Moving Average", "Ichimoku Cloud",
    "Intraday Momentum Index", "Keltner Channel", "Linear Regression Forecast", "Linear Regression Intercept", "Linear Regression R2",
    "Linear Regression Slope", "MACD", "Mass Index", "McClellan Oscillator", "McClellan Summation Index",
    "Median Price", "Momentum Indicator", "Money Flow Index", "Moving Average", "Moving Average Cross",
    "Moving Average Envelope", "Negative Volume Index", "On Balance Volume", "Parabolic SAR", "Performance Index",
    "Pivot Points", "Polarized Fractal Efficiency", "Positive Volume Index", "Pretty Good Oscillator", "Price Momentum Oscillator",
    "Price Oscillator", "Price Rate of Change", "Price Volume Trend", "Prime Number Bands", "Prime Number Oscillator",
    "Psychological Line", "QStick", "Rainbow Moving Average", "Rainbow Oscillator", "Random Walk Index",
    "Relative Volatility Index", "RSI", "Shande Momentum Oscillator", "Shiny Oscillator", "Standard Deviation",
    "Stochastic Momentum Index", "Stochastic Oscillator", "Stochastics", "Supertrend", "Swing Index",
    "Time Series Forecast", "TRIX", "True Range", "Twiggs Money Flow", "Typical Price",
    "Ultimate Oscillator", "Valuation Lines", "Volatility Index", "Volatility Stop", "Volume",
    "Volume Chart", "Volume Oscillator", "Volume Profile", "Volume Rate of Change", "Volume Underlay",
    "Vortex Indicator", "VWAP", "VWMA", "Williams %R", "Williams Accumulation/Distribution",
    "Williams Alligator", "Zig Zag", "2 Period R2", "5 EMA Setup"
  ];

  function renderIndicatorList(filterText = ''){
    const container = document.getElementById('indicatorListContainer');
    if(!container) return;
    const q = (filterText || '').toLowerCase().trim();
    const filtered = ALL_114_INDICATORS.filter(ind => !q || ind.toLowerCase().includes(q));
    const badge = document.getElementById('indicatorCountBadge');
    if(badge) badge.textContent = `${filtered.length} Studies`;

    if(!filtered.length){
      container.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-faint);font-size:12px;">No matching indicators found</div>';
      return;
    }

    container.innerHTML = filtered.map(ind => {
      const isApplied = (state.appliedIndicators || []).some(x => x.name === ind);
      return `
        <div class="indicator-row-item" data-indicator-name="${esc(ind)}" style="display:flex;align-items:center;justify-content:space-between;padding:7px 10px;border-radius:6px;cursor:pointer;transition:background .15s;font-size:12.5px;color:var(--text);">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-weight:700;color:var(--gold);font-size:11px;width:18px;">fx</span>
            <span style="font-weight:${isApplied ? '700' : '400'};color:${isApplied ? 'var(--buy)' : 'var(--text)'};">${esc(ind)}</span>
          </div>
          <div>
            ${isApplied ? '<span class="tag buy" style="font-size:9.5px;padding:1px 6px;">Active</span>' : '<span style="color:var(--text-faint);font-size:11px;">+ Add</span>'}
          </div>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.indicator-row-item').forEach(row => {
      row.addEventListener('mouseenter', () => { row.style.background = 'var(--surface-2)'; });
      row.addEventListener('mouseleave', () => { row.style.background = 'transparent'; });
      row.addEventListener('click', async () => {
        const indName = row.dataset.indicatorName;
        if(!indName) return;
        state.appliedIndicators = state.appliedIndicators || [];
        const existsIdx = state.appliedIndicators.findIndex(x => x.name === indName);
        if(existsIdx >= 0){
          state.appliedIndicators.splice(existsIdx, 1);
          toast(`Removed ${indName} from chart`);
        } else {
          state.appliedIndicators.push({ name: indName, params: '14', color: '#26d9a6' });
          toast(`Added ${indName} to chart`);
        }
        if(typeof renderApplied === 'function') renderApplied();
        if(typeof draw === 'function') draw();
        if(typeof loadIndicators === 'function') void loadIndicators();
        renderIndicatorList(document.getElementById('indicatorSearchInput')?.value || '');
        const modal = document.getElementById('indicatorSearchModal');
        if(modal){ modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
      });
    });
  }

  const indSearchInput = document.getElementById('indicatorSearchInput');
  indSearchInput?.addEventListener('input', (e) => {
    renderIndicatorList(e.target.value);
  });
  document.getElementById('btnOpenIndicatorsModal')?.addEventListener('click', () => {
    const modal = document.getElementById('indicatorSearchModal');
    if(!modal) return;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    renderIndicatorList(indSearchInput ? indSearchInput.value : '');
    setTimeout(() => { indSearchInput?.focus(); }, 100);
  });
  document.getElementById('indicatorSearchModalClose')?.addEventListener('click', () => {
    const modal = document.getElementById('indicatorSearchModal');
    if(!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
  });
  document.getElementById('indicatorSearchModal')?.addEventListener('click', (e) => {
    if(e.target.id === 'indicatorSearchModal') {
      const modal = document.getElementById('indicatorSearchModal');
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
  });

  // ---------------- Floating Drawing Toolbox (Item 2) ----------------
  const toolbox = document.getElementById('chartDrawingToolbox');
  document.getElementById('btnToggleDrawingsToolbar')?.addEventListener('click', (e) => {
    e.stopPropagation();
    if(!toolbox) return;
    const isHidden = toolbox.style.display === 'none' || !toolbox.style.display;
    toolbox.style.display = isHidden ? 'flex' : 'none';
    document.getElementById('btnToggleDrawingsToolbar')?.classList.toggle('active', isHidden);
  });

  toolbox?.querySelectorAll('.drawing-tb-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      toolbox.querySelectorAll('.drawing-tb-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const tool = btn.dataset.tool;
      const statusEl = document.getElementById('drawingStatus');
      if(tool === 'crosshair'){
        state.interactionMode = 'crosshair';
        state.pendingDrawing = null;
        if(statusEl) statusEl.style.display = 'none';
        toast('Crosshair cursor enabled');
      } else if(tool === 'clear'){
        state.drawings = [];
        if(typeof renderApplied === 'function') renderApplied();
        if(typeof draw === 'function') draw();
        if(statusEl) statusEl.style.display = 'none';
        toast('All drawings removed');
      } else {
        const toolMap = {
          trendline: 'Trend Line',
          horizontal: 'Horizontal Line',
          vertical: 'Vertical Line',
          channel: 'Parallel Channel',
          fibonacci: 'Fibonacci Retracement',
          brush: 'Rectangle',
          text: 'Horizontal Line',
          measure: 'Price Range'
        };
        const name = toolMap[tool] || 'Trend Line';
        state.pendingDrawing = name;
        state.pendingColor = '#E8B84B';
        state.drawingStage = [];
        if(statusEl){
          statusEl.style.display = 'block';
          statusEl.textContent = `${name} selected — click the chart to place it.`;
        }
        toast(`${name} active — click chart to draw`);
      }
    });
  });

  // ---------------- Master Auto Trade Toggle & Criteria (Item 32, 33) ----------------
  const masterAtBtn = document.getElementById('chartMasterAtToggle');

  function updateAtUiForSymbol(sym){
    sym = sym || (typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.CATraderSymbol)) || 'NIFTY';
    if(!sym) return;
    if(!window.__CA_AT_ENABLED_SYMBOLS){
      try{
        window.__CA_AT_ENABLED_SYMBOLS = new Set(JSON.parse(localStorage.getItem('ca_at_symbols') || '["RELIANCE","BANKNIFTY","NIFTY","CRUDEOIL"]'));
      }catch(_){
        window.__CA_AT_ENABLED_SYMBOLS = new Set(['RELIANCE','BANKNIFTY','NIFTY','CRUDEOIL']);
      }
    }
    const isEn = window.__CA_AT_ENABLED_SYMBOLS.has(sym);
    // Update Watchlist item button
    document.querySelectorAll(`.wl-item[data-symbol="${CSS.escape(String(sym))}"] [data-wl-at]`).forEach(btn => {
      btn.classList.toggle('active', isEn);
    });

    // Update Chart Master AT Toggle
    if(masterAtBtn){
      masterAtBtn.innerHTML = isEn 
        ? '<span style="color:#00d2ff;font-size:13px;filter:drop-shadow(0 0 5px #00d2ff);">●</span> <span style="font-weight:700;color:#00d2ff;">Auto Trade: ON</span>' 
        : '<span style="color:var(--text-faint);font-size:13px;">○</span> <span style="color:var(--text-dim);">Auto Trade: OFF</span>';
      masterAtBtn.style.background = isEn ? 'rgba(0,210,255,0.18)' : 'var(--surface-2)';
      masterAtBtn.style.borderColor = isEn ? '#00d2ff' : 'var(--border)';
      masterAtBtn.style.color = isEn ? '#00d2ff' : 'var(--text-dim)';
      masterAtBtn.classList.toggle('active', isEn);
    }
  }
  window.updateAtUiForSymbol = updateAtUiForSymbol;

  async function syncMasterAtState(){
    const sym = (typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.CATraderSymbol)) || 'NIFTY';
    updateAtUiForSymbol(sym);
  }

  masterAtBtn?.addEventListener('click', async () => {
    const sym = (typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.CATraderSymbol)) || 'NIFTY';
    if(!sym) return;
    if(!window.__CA_AT_ENABLED_SYMBOLS){
      window.__CA_AT_ENABLED_SYMBOLS = new Set(['RELIANCE','BANKNIFTY','NIFTY','CRUDEOIL']);
    }
    const nextEn = !window.__CA_AT_ENABLED_SYMBOLS.has(sym);
    if(nextEn){
      window.__CA_AT_ENABLED_SYMBOLS.add(sym);
    } else {
      window.__CA_AT_ENABLED_SYMBOLS.delete(sym);
    }
    try{
      localStorage.setItem('ca_at_symbols', JSON.stringify(Array.from(window.__CA_AT_ENABLED_SYMBOLS)));
    }catch(_){}
    updateAtUiForSymbol(sym);
    toast(nextEn ? `Auto Trade enabled for ${sym}` : `Auto Trade disabled for ${sym}`);
    try {
      await fetch('/api/auto-trade', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          enabled: nextEn,
          symbol: sym,
          capital: Number(document.getElementById('chartCriteriaCapital')?.value || 50000),
          max_loss: Number(document.getElementById('chartCriteriaMaxLoss')?.value || 1000),
          target_profit: Number(document.getElementById('chartCriteriaDesiredProfit')?.value || 500)
        })
      });
    } catch(_) {}
  });
  syncMasterAtState();

  // Criteria modal save with toast (Item 8 & Item 16)
  const saveCriteriaAction = async () => {
    const profit = Number(document.getElementById('chartCriteriaDesiredProfit')?.value || 500);
    const loss = Number(document.getElementById('chartCriteriaMaxLoss')?.value || 1000);
    const capital = Number(document.getElementById('chartCriteriaCapital')?.value || 50000);
    localStorage.setItem('ca_reco_profit', String(profit));
    localStorage.setItem('ca_reco_loss', String(loss));
    localStorage.setItem('ca_reco_capital', String(capital));
    try {
      await fetch('/api/auto-trade', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ target_profit: profit, max_loss: loss, capital: capital })
      });
    } catch(_) {}
    const m = document.getElementById('chartRecoCriteriaModal');
    if(m) m.style.display = 'none';
    toast('Parameters updated! Refreshing recommendation…');
    const activeSym = (typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.CATraderSymbol)) || 'NIFTY';
    if(typeof updateChartRecoBanner === 'function') await updateChartRecoBanner(null, activeSym, true);
  };
  document.getElementById('saveCriteriaModalBtn')?.addEventListener('click', saveCriteriaAction);
  document.getElementById('saveCriteriaBtn')?.addEventListener('click', saveCriteriaAction);

  // Toggle criteria modal cleanly (single click handler)
  document.getElementById('chartRecoCriteriaBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    const m = document.getElementById('chartRecoCriteriaModal');
    if(m) m.style.display = (m.style.display === 'none' || !m.style.display) ? 'block' : 'none';
  });
  document.getElementById('closeCriteriaModalBtn')?.addEventListener('click', () => {
    const m = document.getElementById('chartRecoCriteriaModal');
    if(m) m.style.display = 'none';
  });
  void syncMasterAtState();

  // ---------------- Font Style & Strictly 2 Themes (Item 13, 14) ----------------
  const fontStyleSelect = document.getElementById('fontStyleSelect');
  function applyFont(f){
    const fontMap = {
      system: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      inter: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
      roboto: '"Roboto", -apple-system, BlinkMacSystemFont, sans-serif',
      segoe: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
      mono: '"JetBrains Mono", Consolas, Monaco, monospace'
    };
    const chosen = fontMap[f] || fontMap.system;
    document.documentElement.style.setProperty('--font-sans', chosen);
    document.body.style.fontFamily = chosen;
  }
  if(fontStyleSelect){
    const savedFont = localStorage.getItem('ca_font_family') || 'system';
    fontStyleSelect.value = savedFont;
    applyFont(savedFont);
    fontStyleSelect.addEventListener('change', (e) => {
      applyFont(e.target.value);
      localStorage.setItem('ca_font_family', e.target.value);
      toast(`Font updated to ${e.target.options[e.target.selectedIndex].text}`);
    });
  }

  const btnLight = document.getElementById('btnThemeLight');
  const btnDark = document.getElementById('btnThemeDark');
  function setTheme(theme){
    const isLight = theme === 'light';
    document.documentElement.setAttribute('data-theme', isLight ? 'light' : 'dark');
    document.body.setAttribute('data-theme', isLight ? 'light' : 'dark');
    document.body.classList.toggle('light-theme', isLight);
    document.body.classList.toggle('dark-theme', !isLight);
    if(btnLight) {
      btnLight.style.borderColor = isLight ? 'var(--primary)' : 'var(--border)';
      btnLight.style.background = isLight ? 'var(--surface-3)' : 'var(--surface-2)';
      btnLight.style.fontWeight = isLight ? '700' : '400';
    }
    if(btnDark) {
      btnDark.style.borderColor = !isLight ? 'var(--primary)' : 'var(--border)';
      btnDark.style.background = !isLight ? 'var(--surface-3)' : 'var(--surface-2)';
      btnDark.style.fontWeight = !isLight ? '700' : '400';
    }
    localStorage.setItem('ca_theme', isLight ? 'light' : 'dark');
    localStorage.setItem('selectedTheme', isLight ? 'light' : 'dark');
    // Redraw charts for new theme
    if(typeof draw === 'function') draw();
    if(typeof drawBacktestCanvas === 'function') drawBacktestCanvas();
  }
  window.setTheme = setTheme;
  btnLight?.addEventListener('click', () => { setTheme('light'); toast('Light theme applied'); });
  btnDark?.addEventListener('click', () => { setTheme('dark'); toast('Dark theme applied'); });
  const savedTheme = localStorage.getItem('ca_theme') || 'dark';
  setTheme(savedTheme);

  // ---------------- Backtest Symbol Sync (Item 18) ----------------
  function updateBacktestSymbols(){
    const btSel = document.getElementById('btSymbolSelect');
    if(!btSel) return;
    const items = (window.__CA_WL_GROUP?.items || []).map(i => i.symbol).filter(Boolean);
    const fallbackSyms = ['RELIANCE', 'BANKNIFTY', 'NIFTY', 'CRUDEOIL', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'];
    const syms = Array.from(new Set([...(items.length ? items : fallbackSyms)]));
    const currSym = (typeof selectedSymbol === 'function' ? selectedSymbol() : (window.selectedSymbol ? window.selectedSymbol() : window.CATraderSymbol)) || 'RELIANCE';
    const curVal = btSel.value || currSym;
    btSel.innerHTML = syms.map(s => `<option value="${esc(s)}"${s === curVal ? ' selected' : ''}>${esc(s)}</option>`).join('');
    if(typeof btState !== 'undefined') btState.symbol = btSel.value || currSym;
  }
  window.updateBacktestSymbols = updateBacktestSymbols;

  // Setup Subtabs, Trees & Autocomplete upon boot
  // Universal Modal & Dropdown Backdrop / Escape Dismissal (Item 22, 35)
  document.addEventListener('click', (e) => {
    // Backdrop click for tool-modal
    if (e.target.classList && e.target.classList.contains('tool-modal')) {
      e.target.classList.remove('open');
      e.target.setAttribute('aria-hidden', 'true');
    }
    // Dismiss criteria modal if clicking outside
    const critModal = document.getElementById('chartRecoCriteriaModal');
    const critBtn = document.getElementById('chartRecoCriteriaBtn');
    if (critModal && critModal.style.display !== 'none') {
      if (!critModal.contains(e.target) && !critBtn?.contains(e.target)) {
        critModal.style.display = 'none';
      }
    }
    // Dismiss views menu if clicking outside
    const viewsMenu = document.getElementById('savedViewsDropdownMenu');
    const viewsBtn = document.getElementById('btnSavedViews');
    if (viewsMenu && viewsMenu.style.display !== 'none') {
      if (!viewsMenu.contains(e.target) && !viewsBtn?.contains(e.target)) {
        viewsMenu.style.display = 'none';
      }
    }
    // Dismiss profile userMenu if clicking outside
    const userMenu = document.getElementById('userMenu');
    const userChip = document.getElementById('userChip');
    if (userMenu && userMenu.classList.contains('open')) {
      if (!userMenu.contains(e.target) && !userChip?.contains(e.target)) {
        userMenu.classList.remove('open');
      }
    }
    // Dismiss notificationMenu if clicking outside
    const notifMenu = document.getElementById('notificationMenu');
    const notifBtn = document.getElementById('notificationBtn');
    if (notifMenu && notifMenu.classList.contains('open')) {
      if (!notifMenu.contains(e.target) && !notifBtn?.contains(e.target)) {
        notifMenu.classList.remove('open');
      }
    }
    // Dismiss calculation modal if clicking backdrop
    const recoModal = document.getElementById('recoCalculationModal');
    if (recoModal && recoModal.style.display === 'flex' && e.target === recoModal) {
      recoModal.style.display = 'none';
    }
    // Dismiss timeframe dropdown
    const tfMenu = document.getElementById('timeframeDropdownMenu');
    const tfBtn = document.getElementById('btnTfDropdown');
    if (tfMenu && tfMenu.style.display !== 'none') {
      if (!tfMenu.contains(e.target) && !tfBtn?.contains(e.target)) {
        tfMenu.style.display = 'none';
      }
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.tool-modal.open').forEach(m => {
        m.classList.remove('open');
        m.setAttribute('aria-hidden', 'true');
      });
      const crit = document.getElementById('chartRecoCriteriaModal');
      if (crit) crit.style.display = 'none';
      const vm = document.getElementById('savedViewsDropdownMenu');
      if (vm) vm.style.display = 'none';
      const rm = document.getElementById('recoCalculationModal');
      if (rm) rm.style.display = 'none';
      const tf = document.getElementById('timeframeDropdownMenu');
      if (tf) tf.style.display = 'none';
      const userM = document.getElementById('userMenu');
      if (userM) userM.classList.remove('open');
      const notifM = document.getElementById('notificationMenu');
      if (notifM) notifM.classList.remove('open');
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    if(typeof setupOrdersPositionsSubtabs === 'function') setupOrdersPositionsSubtabs();
    if(typeof setupMcxAutocomplete === 'function') setupMcxAutocomplete();
    if(typeof setupTutorialTrees === 'function') setupTutorialTrees();
    if(typeof updateBacktestSymbols === 'function') updateBacktestSymbols();
  });
  setTimeout(() => {
    if(typeof setupOrdersPositionsSubtabs === 'function') setupOrdersPositionsSubtabs();
    if(typeof setupMcxAutocomplete === 'function') setupMcxAutocomplete();
    if(typeof setupTutorialTrees === 'function') setupTutorialTrees();
    if(typeof updateBacktestSymbols === 'function') updateBacktestSymbols();
  }, 1500);
})();
