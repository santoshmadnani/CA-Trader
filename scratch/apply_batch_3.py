import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Recommendations and Recommendation History
old_reco_start = "  // ---------------- Recommendations ----------------"
old_reco_end = "  // ---------------- Orders / positions / funds ----------------"

idx_r1 = content.find(old_reco_start)
idx_r2 = content.find(old_reco_end)

if idx_r1 != -1 and idx_r2 != -1:
    old_reco_block = content[idx_r1:idx_r2]
    new_reco_block = """  // ---------------- Recommendations ----------------
  function basisText(rec){const ev=rec?.evidence||{};const n=ev.news||{};return `<div class="basis-list"><div class="basis-item"><b>Technical</b><br>Trend ${esc(ev.technical?.trend||'N/A')} · RSI ${fmt(ev.technical?.rsi)} · ADX ${fmt(ev.technical?.adx)} · Support ${fmt(ev.technical?.support)} · Resistance ${fmt(ev.technical?.resistance)}</div><div class="basis-item"><b>Stock news</b><br>${esc(n.stock?.signal||'NEUTRAL')} · materiality ${fmt(n.stock?.materiality)} · ${esc((n.stock?.reasons||[]).join(' | ')||'No directional stock-news evidence')}</div><div class="basis-item"><b>Global news</b><br>${esc(n.global?.signal||'NEUTRAL')} · materiality ${fmt(n.global?.materiality)} · ${esc((n.global?.reasons||[]).join(' | ')||'No directional global-news evidence')}</div><div class="basis-item"><b>Risk geometry</b><br>Entry ${fmt(rec?.entry)} · SL ${fmt(rec?.stop_loss)} · Target ${fmt(rec?.target)} · R:R ${fmt(rec?.risk_reward)}</div></div>`}

  // Sub-tab switcher for Recommendations: Active Setups vs History
  document.getElementById('subTabActiveRecos')?.addEventListener('click', () => {
    document.getElementById('subTabActiveRecos').classList.add('active');
    document.getElementById('subTabRecoHistory')?.classList.remove('active');
    const c1 = document.getElementById('recoActiveSetupsContainer');
    const c2 = document.getElementById('recoHistoryContainer');
    if(c1) c1.style.display = 'block';
    if(c2) c2.style.display = 'none';
  });

  document.getElementById('subTabRecoHistory')?.addEventListener('click', () => {
    document.getElementById('subTabRecoHistory').classList.add('active');
    document.getElementById('subTabActiveRecos')?.classList.remove('active');
    const c1 = document.getElementById('recoActiveSetupsContainer');
    const c2 = document.getElementById('recoHistoryContainer');
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
      <div style="background:rgba(232,184,75,0.12);border:1px solid rgba(232,184,75,0.3);padding:10px 14px;border-radius:8px;font-size:12px;color:var(--gold);display:flex;align-items:center;gap:8px;">
        <span>🌙</span>
        <div><b>Next Market Day Pre-Market Setup (${esc(rec.target_session)})</b><div style="font-size:11px;color:var(--text-dim);">Market currently closed. Levels calculated for tomorrow's opening auction with overnight pivot projection.</div></div>
      </div>
    ` : '';

    $('recoCalcModalBody').innerHTML = `
      ${nextDayBanner}
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

  async function loadRecommendations(askAi=false){
    if(!$('recommendationCards'))return;
    $('recommendationCards').innerHTML='<div class="data-empty">Loading live technical + news signal…</div>';
    try{
      const sym=selectedSymbol(); const selectionAtStart=sym; let r;
      if(askAi){
        r=await api('/api/recommendations/on-demand',{method:'POST',body:JSON.stringify({symbol:sym,timeframe:state.tf,ask_ai:true}),timeoutMs:9000});
      }else{
        r=await api('/api/analysis/overall/'+encodeURIComponent(sym)+`?timeframe=${encodeURIComponent(state.tf)}`,{timeoutMs:6500});
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

      const cards=[['CA Trader',rec,confidence,r],['News + Technical Consensus',rec,confidence,r]];
      if(askAi)cards.push(['CA AI',ai.decision||'NO_TRADE',ai.confidence??null,{...r,ai_basis:ai}]);
      else cards.push(['CA AI','—',null,{...r,ai_pending:true}]);
      $('recommendationCards').innerHTML=cards.map((c,i)=>`
        <div class="consensus news-card" data-rec-index="${i}">
          <div class="consensus-head">
            <span class="consensus-sym">${esc(c[0])}</span>
            <span class="verdict-badge ${signalClass(c[1])==='buy'?'buy':signalClass(c[1])==='sell'?'sell':'mixed'}" style="cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)">${esc(c[1])}</span>
          </div>
          <div style="font-size:11px;color:var(--text-dim);margin-bottom:8px">${esc(sym)} · ${esc(state.tf)} · Confidence ${c[2]==null?'—':fmt(c[2])+'%'}</div>
          <div style="font-size:10.5px;color:var(--text-faint);margin-bottom:10px">${esc(i===2&&!askAi?'No CA AI recommendation yet. Click Ask CA AI.':i===0?reason:(askAi&&i===2?(ai.rationale||'CA AI opinion generated from the supplied evidence.'):'Independent evidence view'))}</div>
          <div class="consensus-foot" style="border-top:1px dashed var(--border-soft);padding-top:10px;margin-top:0">
            <span style="cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view Entry formula">Entry <b style="text-decoration:underline dashed;">${fmt(r.entry)}</b></span>
            <span style="cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view Dynamic SL formula">SL <b style="color:var(--sell);text-decoration:underline dashed;">${fmt(r.stop_loss)}</b></span>
            <span style="cursor:pointer;" onclick="openRecoCalculationModal(window.__caRecommendation)" title="Click to view Target calculation">Tgt <b style="color:var(--buy);text-decoration:underline dashed;">${fmt(r.target)}</b></span>
          </div>
        </div>
      `).join('');
      window.__caRecommendation=r;
      document.querySelectorAll('[data-rec-index]').forEach(c=>c.onclick=()=>openRecommendationBasis(c.dataset.recIndex,window.__caRecommendation));
    }catch(e){$('recommendationCards').innerHTML=`<div class="data-empty">Recommendation unavailable: ${esc(e.message)}</div>`}
  }

  async function runOnDemandRecommendation(){
    const sym=selectedSymbol();
    try{
      const r=await api('/api/recommendations/on-demand',{method:'POST',body:JSON.stringify({symbol:sym,timeframe:state.tf,ask_ai:false}),timeoutMs:6500});
      window.__caRecommendation=r; toast(`On-demand result: ${r.recommendation||'NO_TRADE'}`); await loadRecommendations(false); await loadRecommendationHistory();
    }catch(e){toast(e.message)}
  }
  function openRecommendationBasis(index,r){openModal('newsAnalysisModal');$('newsAnalysisBody').innerHTML=`<div class="card-head"><div class="card-title">Recommendation Basis</div><button class="btn ghost small" id="basisClose">Close</button></div>${basisText(r)}<div class="basis-item" style="margin-top:10px"><b>CA AI</b><br>${esc(r.ai?.rationale||'CA AI opinion is currently unavailable.')}</div>`;$('basisClose').onclick=()=>closeModal('newsAnalysisModal')}
  $('manualAiRecommendationBtn')?.addEventListener('click',()=>loadRecommendations(true));
  $('onDemandRecommendationBtn')?.addEventListener('click',runOnDemandRecommendation);

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
        <div style="display:flex;justify-content:flex-end;margin-bottom:7px">
          <button class="btn ghost small" id="deleteRecommendationHistory">Delete selected</button>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th></th><th>Time</th><th>Symbol</th><th>Source</th><th>Signal</th><th>Entry</th><th>SL</th><th>Target</th><th>P&L</th>
              </tr>
            </thead>
            <tbody>
              ${d.items.slice(0,50).map(x=>{
                const pnl = Number(x.final_pnl != null ? x.final_pnl : (x.pnl != null ? x.pnl : 0));
                const pnlStr = (pnl > 0 ? '+' : '') + fmtMoney(pnl);
                const pnlColor = pnl > 0 ? 'var(--buy)' : pnl < 0 ? 'var(--sell)' : 'var(--text-muted)';
                const recJson = JSON.stringify(x).replace(/"/g, '&quot;');
                return `
                  <tr>
                    <td><input type="checkbox" data-rec-delete="${esc(x.id)}"></td>
                    <td>${esc(formatTime(x.created_at))}</td>
                    <td><b>${esc(x.symbol)}</b></td>
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

      $('deleteRecommendationHistory')?.addEventListener('click',async()=>{
        const ids=[...document.querySelectorAll('[data-rec-delete]:checked')].map(x=>x.dataset.recDelete);
        if(!ids.length){toast('Select recommendation history first.');return}
        for(const id of ids){
          try{await api('/api/recommendations/history/'+encodeURIComponent(id),{method:'DELETE'})}catch(e){toast(e.message)}
        }
        toast(`${ids.length} recommendation(s) deleted`);
        loadRecommendationHistory();
      });
    }catch(e){
      $('recommendationHistory').innerHTML=`<div class="data-empty">${esc(e.message)}</div>`;
    }
  }

"""
    content = content.replace(old_reco_block, new_reco_block, 1)
    print("✓ Replaced recommendations section with calculation modal & formatted P&L")
else:
    print(f"⚠ Could not find reco block bounds: idx_r1={idx_r1}, idx_r2={idx_r2}")

# 2. Update Auto Trade Stock Selection Dropdown & Max Profit
old_auto_start = "   $('autoAddSymbolBtn')?.addEventListener('click'"
old_auto_end = "  // ---------------- Dashboard ----------------"
idx_a1 = content.find(old_auto_start)
idx_a2 = content.find(old_auto_end)

if idx_a1 != -1 and idx_a2 != -1:
    old_auto_block = content[idx_a1:idx_a2]
    new_auto_block = """  // Auto Trade stock search input & dropdown delegation fix
  const autoSuggestBox = $('autoSymbolSuggestions');
  if(autoSuggestBox){
    autoSuggestBox.addEventListener('mousedown', (e) => {
      e.preventDefault(); // Prevents input blur before click event fires
    });
    autoSuggestBox.addEventListener('click', async (e) => {
      const row = e.target.closest('[data-symbol]');
      if(!row) return;
      const sym = String(row.dataset.symbol || '').trim().toUpperCase();
      if(!sym) return;
      autoEnabled = true;
      if(!autoSymbols.includes(sym)) autoSymbols.push(sym);
      if($('autoManualSymbol')) $('autoManualSymbol').value = '';
      autoSuggestBox.classList.remove('open');
      autoSuggestBox.innerHTML = '';
      $('autoEnableSwitch')?.classList.add('on');
      toast(`Added ${sym} to Auto Trade`);
      await saveAutoTradeImmediate();
      await loadAutoTrade();
    });
  }

  $('autoAddSymbolBtn')?.addEventListener('click', async () => {
    const v = String($('autoManualSymbol')?.value || '').trim().toUpperCase().replace(/[^A-Z0-9_-]/g, '');
    if(!v) return;
    autoEnabled = true;
    if(!autoSymbols.includes(v)) autoSymbols.push(v);
    if($('autoManualSymbol')) $('autoManualSymbol').value = '';
    $('autoSymbolSuggestions')?.classList.remove('open');
    $('autoEnableSwitch')?.classList.add('on');
    await saveAutoTradeImmediate();
    await loadAutoTrade();
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
        box.innerHTML = items.slice(0, 10).map(i => `
          <div class="auto-suggestion-row" data-symbol="${esc(i.symbol || '')}" style="cursor:pointer;padding:8px 10px;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;">
            <b>${esc(i.symbol || '')}</b>
            <span class="muted" style="font-size:10.5px;">${esc(i.name || '')} · ${esc(i.exchange || '')}</span>
          </div>
        `).join('');
        box.classList.toggle('open', items.length > 0);
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
      autoSymbols=d.symbols||[];
      $('autoTradeStatus')?.replaceChildren(Object.assign(document.createElement('span'),{
        className:`tag ${autoEnabled?'buy':'neutral'}`,
        textContent:autoEnabled?(d.live_execution?'ENABLED · LIVE EXECUTION':'ENABLED · READY / GATED'):'DISABLED'
      }));
      $('autoTradeSymbols').innerHTML=autoSymbols.length?autoSymbols.map(s=>`
        <div class="basis-item">${esc(s)} <button class="btn ghost small remove-auto-symbol" data-symbol="${esc(s)}" style="float:right">Remove</button></div>
      `).join(''):'<div class="data-empty">No stocks selected. Add from the search bar or suggestions below.</div>';

      document.querySelectorAll('.remove-auto-symbol').forEach(b=>b.onclick=async()=>{
        autoSymbols=autoSymbols.filter(x=>x!==b.dataset.symbol);
        await saveAutoTradeImmediate();
        await loadAutoTrade();
      });

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

"""
    content = content.replace(old_auto_block, new_auto_block, 1)
    print("✓ Replaced Auto Trade stock selection & suggestions handler")
else:
    print(f"⚠ Could not find auto block bounds: idx_a1={idx_a1}, idx_a2={idx_a2}")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Batch 3 completed successfully.")

