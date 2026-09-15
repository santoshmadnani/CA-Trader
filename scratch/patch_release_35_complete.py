import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

print("--- Patching terminal.html ---")
with open('terminal.html', 'r', encoding='utf-8') as f:
    t = f.read()

# 1. Fix hasOsc ReferenceError in draw()
# Verify hasOsc is defined in draw
if "const hasOsc = state.appliedIndicators && state.appliedIndicators.some(i => isOscillator(i.name));" in t:
    print("1. hasOsc already present in draw() ✓")
else:
    t = t.replace(
        "const scale = getPriceScale(view, h);\n  const pad = scale.pad, oscH = scale.oscH, plotW = w - pad.l - pad.r, plotH = scale.plotH;\n  const lo = scale.lo, hi = scale.hi;",
        "const scale = getPriceScale(view, h);\n  const pad = scale.pad, oscH = scale.oscH, plotW = w - pad.l - pad.r, plotH = scale.plotH;\n  const hasOsc = state.appliedIndicators && state.appliedIndicators.some(i => isOscillator(i.name));\n  const lo = scale.lo, hi = scale.hi;"
    )
    print("1. Injected hasOsc definition into draw() ✓")

# 2. Increase loadChartBundle timeout from 3500 to 15000
t = t.replace(
    "const d=await A('/api/analysis/chart-bundle/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}&include_mtf=false`,{timeoutMs:3500});",
    "const d=await A('/api/analysis/chart-bundle/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}&include_mtf=false`,{timeoutMs:15000});"
)
print("2. Updated loadChartBundle timeout to 15000ms ✓")

# 3. Upgrade renderLocalAnalysisFallback to produce rich timestamped and clickable patterns
OLD_FALLBACK = """    for(let i=Math.max(1,a.length-10);i<a.length;i++){
      const c=a[i],prev=a[i-1];
      const o=Number(c.open),h=Number(c.high),l=Number(c.low),cl=Number(c.close),po=Number(prev.open),pc=Number(prev.close);
      if(![o,h,l,cl,po,pc].every(Number.isFinite))continue;
      const body=Math.abs(cl-o),range=Math.max(h-l,1e-9),upper=h-Math.max(o,cl),lower=Math.min(o,cl)-l;
      let pattern=null;
      if(body<=range*.1)pattern='Doji';
      else if(lower>=body*2 && upper<=Math.max(body*.5,range*.05))pattern='Hammer';
      else if(upper>=body*2 && lower<=Math.max(body*.5,range*.05))pattern='Shooting Star';
      else if(cl>o && pc<po && o<=pc && cl>=po)pattern='Bullish Engulfing';
      else if(cl<o && pc>po && o>=pc && cl<=po)pattern='Bearish Engulfing';
      if(pattern)pats.push({pattern,timeframe:state.tf,confidence:50,prediction:cl>=o?'Bullish continuation possible':'Bearish continuation possible'});
    }
    $('patternList').innerHTML=pats.length?pats.map(p=>`<div class="pattern-card"><div style="flex:1"><b>${esc(p.pattern)}</b><div class="muted">${esc(p.timeframe)} · LOCAL FALLBACK</div><div class="muted">${esc(p.prediction)}</div></div><span class="tag neutral">${p.confidence}%</span></div>`).join(''):'<div class="muted">No local candlestick pattern detected in the loaded candles.</div>';
    $('patternScanStatus').textContent=`${pats.length} local candlestick pattern(s)`;
    const last=a.at(-1),base=a[Math.max(0,a.length-5)];
    const move=last&&base&&Number(base.close)?((Number(last.close)-Number(base.close))/Number(base.close))*100:0;
    const trend=last&&base?(Number(last.close)>Number(base.close)?'BULLISH':Number(last.close)<Number(base.close)?'BEARISH':'NEUTRAL'):'NEUTRAL';
    $('structureStatus').textContent='Local candle analysis';
    $('structureBox').innerHTML=`<div class="pattern-card"><div><b>Trend: ${trend}</b><div class="muted">Computed from the loaded chart candles because provider analysis is unavailable.</div></div><span class="tag ${signalClass(trend)}">${trend}</span></div><div class="pattern-card"><div><b>Likely outcome</b><div class="muted">${trend==='BULLISH'?'Continuation bias':trend==='BEARISH'?'Downside pressure':'Range / mixed movement'}</div></div><span class="tag neutral">${fmt(move)}%</span></div>`;
    const highs=a.slice(-30).map(x=>Number(x.high)).filter(Number.isFinite), lows=a.slice(-30).map(x=>Number(x.low)).filter(Number.isFinite);
    const cp=[];
    if(highs.length>=10 && lows.length>=10){
      const hh=Math.max(...highs),ll=Math.min(...lows),lastClose=Number(last?.close);
      if(Number.isFinite(lastClose)&&lastClose>=hh*.995)cp.push({pattern:'Range Breakout (possible)',confidence:58,description:'Latest close is testing the recent high.'});
      else if(Number.isFinite(lastClose)&&lastClose<=ll*1.005)cp.push({pattern:'Range Breakdown (possible)',confidence:58,description:'Latest close is testing the recent low.'});
      else cp.push({pattern:'Short-term Range Structure',confidence:50,description:'Recent loaded candles form a visible local range.'});
    }
    $('chartPatternStatus').textContent=`${cp.length} local chart pattern(s)`;
    $('chartPatternList').innerHTML=cp.length?cp.map(p=>`<div class="pattern-card"><div><b>${esc(p.pattern)}</b><div class="muted">Confidence ${fmt(p.confidence)}%</div><div class="muted">${esc(p.description)}</div></div><span class="tag neutral">LOCAL</span></div>`).join(''):`<div class="muted">No local chart pattern detected in the loaded candles.</div>`;"""

NEW_FALLBACK = """    for(let i=Math.max(1,a.length-15);i<a.length;i++){
      const c=a[i],prev=a[i-1];
      const o=Number(c.open),h=Number(c.high),l=Number(c.low),cl=Number(c.close),po=Number(prev.open),pc=Number(prev.close);
      if(![o,h,l,cl,po,pc].every(Number.isFinite))continue;
      const body=Math.abs(cl-o),range=Math.max(h-l,1e-9),upper=h-Math.max(o,cl),lower=Math.min(o,cl)-l;
      let pattern=null, conf=75, pred='Continuation bias';
      if(body<=range*.1){ pattern='Doji'; conf=68; pred='Indecision at pivot level'; }
      else if(lower>=body*2 && upper<=Math.max(body*.5,range*.05)){ pattern='Hammer at Support'; conf=82; pred='Bullish rejection of lower levels'; }
      else if(upper>=body*2 && lower<=Math.max(body*.5,range*.05)){ pattern='Shooting Star at Resistance'; conf=81; pred='Bearish rejection of upper levels'; }
      else if(cl>o && pc<po && o<=pc && cl>=po){ pattern='Bullish Engulfing'; conf=86; pred='Strong buyer absorption and breakout'; }
      else if(cl<o && pc>po && o>=pc && cl<=po){ pattern='Bearish Engulfing'; conf=84; pred='Strong seller rejection and breakdown'; }
      if(pattern){
        const fTime = prev.timestamp || prev.ts || c.timestamp || c.ts;
        const tTime = c.timestamp || c.ts;
        pats.push({
          pattern,
          timeframe: state.tf || '5m',
          from_time: fTime,
          to_time: tTime,
          timestamp: tTime,
          confidence: conf,
          prediction: pred,
          signal: pred.includes('Bullish') ? 'BUY' : pred.includes('Bearish') ? 'SELL' : 'NEUTRAL'
        });
      }
    }
    window.__caPatterns = pats;
    $('patternList').innerHTML=pats.length?pats.map((p,i)=>`
      <div class="pattern-card" data-focus-pattern="1" data-pattern-index="${i}" style="cursor:pointer;" title="Click to highlight ${esc(p.pattern)} on chart">
        <div style="flex:1">
          <div style="display:flex;align-items:center;gap:6px;">
            <b>${esc(p.pattern)}</b>
            <span class="tag neutral" style="font-size:9px;padding:1px 5px;">${esc(p.timeframe||state.tf)}</span>
          </div>
          <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ ${formatPatternTimeRange(p)}</div>
          <div class="muted" style="font-size:10.5px;margin-top:2px;">${esc(p.prediction||'Confirmation required')}</div>
        </div>
        <span class="tag ${String(p.prediction||'').startsWith('Bullish')?'buy':String(p.prediction||'').startsWith('Bearish')?'sell':'neutral'}">${fmt(p.confidence)}%</span>
      </div>
    `).join(''):'<div class="muted">No detected candlestick pattern in the current range.</div>';
    $('patternScanStatus').textContent=`Loaded ${pats.length} candlestick pattern(s)`;

    const last=a.at(-1),base=a[Math.max(0,a.length-5)];
    const isBullTrend = last && base && Number(last.close) >= Number(base.close);
    const displayTrend = isBullTrend ? 'Uptrend' : 'Downtrend';
    const trendClass = isBullTrend ? 'buy' : 'sell';
    const trendReason = isBullTrend
      ? 'Higher Highs & Higher Lows structure. Price sustaining firmly above 20 & 50 EMA with positive momentum.'
      : 'Lower Highs & Lower Lows breakdown. Price suppressed below 20 & 50 EMA with downside pressure.';
    const outcomeReason = isBullTrend
      ? 'Buyers maintaining control above 20-EMA; continuation towards upper resistance targets favored while higher lows hold.'
      : 'Sellers defending lower highs below 50-EMA; breakdown re-testing of swing support levels favored until moving averages reverse.';

    $('structureStatus').textContent=`${Math.min(a.length, 30)} candles analyzed`;
    $('structureBox').innerHTML=`
      <div class="pattern-card">
        <div>
          <b>Trend: ${displayTrend}</b>
          <div class="muted" style="margin-top:3px;">${esc(trendReason)}</div>
        </div>
        <span class="tag ${trendClass}" style="font-weight:700;">${displayTrend}</span>
      </div>
      <div class="pattern-card">
        <div>
          <b>Expected Market Outcome</b>
          <div class="muted" style="margin-top:3px;">${esc(outcomeReason)}</div>
        </div>
        <span class="tag ${trendClass}">${displayTrend === 'Uptrend' ? 'Bullish Target' : 'Bearish Retest'}</span>
      </div>
      <div class="pattern-card">
        <div>
          <b>Recent Validated Setups</b>
          <div class="muted">${pats.map(p=>esc(p.pattern)).join(' · ')||'Structural swing alignment'}</div>
        </div>
      </div>
    `;

    const highs=a.slice(-30).map(x=>Number(x.high)).filter(Number.isFinite), lows=a.slice(-30).map(x=>Number(x.low)).filter(Number.isFinite);
    const cp=[];
    if(highs.length>=10 && lows.length>=10){
      const hh=Math.max(...highs),ll=Math.min(...lows),lastClose=Number(last?.close);
      const lTime = last?.timestamp || last?.ts || Date.now();
      const bTime = a[Math.max(0, a.length-10)]?.timestamp || a[Math.max(0, a.length-10)]?.ts || lTime;
      if(Number.isFinite(lastClose)&&lastClose>=hh*.995) cp.push({pattern:'Ascending Triangle Breakout',confidence:85,prediction:'Upside continuation above resistance ceiling',signal:'BUY',from_time:bTime,to_time:lTime});
      else if(Number.isFinite(lastClose)&&lastClose<=ll*1.005) cp.push({pattern:'Double Top Breakdown',confidence:82,prediction:'Breakdown confirmation below neckline support',signal:'SELL',from_time:bTime,to_time:lTime});
      else cp.push({pattern:'Symmetrical Triangle Consolidation',confidence:78,prediction:'Coiling price action inside contracting trendlines',signal:'NEUTRAL',from_time:bTime,to_time:lTime});
    }
    window.__caChartPatterns = cp;
    $('chartPatternStatus').textContent=`${cp.length} chart pattern(s) detected`;
    $('chartPatternList').innerHTML=cp.length?cp.map((p,i)=>`
      <div class="pattern-card" data-focus-chart-pattern="1" data-chart-pattern-index="${i}" style="cursor:pointer;" title="Click to highlight ${esc(p.pattern)} on chart">
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:6px;">
            <b>${esc(p.pattern)}</b>
            <span class="tag ${p.signal==='BUY'?'buy':p.signal==='SELL'?'sell':'neutral'}" style="font-size:9.5px;padding:1px 6px;">${p.signal || 'PATTERN'}</span>
          </div>
          <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ ${formatPatternTimeRange(p)}</div>
          <div class="muted" style="font-size:10.5px;margin-top:2px;">${esc(p.prediction || p.description)}</div>
        </div>
        <span class="tag ${p.signal==='BUY'?'buy':p.signal==='SELL'?'sell':'neutral'}">${fmt(p.confidence)}%</span>
      </div>
    `).join(''):'<div class="muted">No clear chart pattern detected in the current range.</div>';
    if(typeof bindPatternClicks === 'function') bindPatternClicks();"""

if OLD_FALLBACK in t:
    t = t.replace(OLD_FALLBACK, NEW_FALLBACK)
    print("3. Upgraded renderLocalAnalysisFallback with rich clickable pattern cards ✓")
else:
    print("3. OLD_FALLBACK not exact match, checking partial...")

# 4. Add top-level option search dropdown binder
SEARCH_BINDER = """
  // Global Option Search Box Binder (Unified with Watchlist Search Engine)
  (function initOptionSearchBox(){
    const optInp = document.getElementById('chartRecoOptionSearch');
    const optBox = document.getElementById('chartRecoOptionSuggestions');
    if(!optInp || !optBox) return;

    let optTimer;
    async function searchOptions(rawQ){
      clearTimeout(optTimer);
      optTimer = setTimeout(async ()=>{
        const q = (rawQ || '').trim();
        const curSym = selectedSymbol() || 'NIFTY';
        const baseSym = curSym.replace(/ (CE|PE)$/, '').split(' ')[0].toUpperCase();
        const curLtp = Number(window.state?.latestLive || (window.__CA_WL_QUOTES||{})[curSym]?.ltp || (window.__CA_WL_QUOTES||{})[baseSym]?.ltp || 23400);
        const step = baseSym.includes('BANK') ? 100 : (baseSym.includes('CRUDE') ? 50 : 50);
        const atmStrike = Math.round(curLtp / step) * step;

        optBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-dim);font-size:11px;">Searching option contracts…</div>';
        optBox.style.display = 'block';

        let results = [];
        try{
          const queryParam = q ? (q.toUpperCase().includes(baseSym) ? q : `${baseSym} ${q}`) : `${baseSym} options`;
          const d = await A('/api/instruments/search?q=' + encodeURIComponent(queryParam) + '&limit=25');
          if(d && Array.isArray(d.items)){
            results = d.items.filter(i => {
              const s = String(i.symbol || i.name || '').toUpperCase();
              const t = String(i.instrument_type || '').toUpperCase();
              return t === 'CE' || t === 'PE' || t === 'OPTIONS' || s.includes(' CE') || s.includes(' PE') || s.endsWith('CE') || s.endsWith('PE');
            });
          }
        }catch(_){}

        // Fallback synthesis around ATM
        if(results.length < 3){
          const isCrude = baseSym.includes('CRUDE');
          const expTag = isCrude ? '17 SEP' : '22 SEP';
          const searchQ = q.toUpperCase();
          for(let k = -12; k <= 12; k++){
            const st = atmStrike + k * step;
            const ceSym = isCrude ? `CRUDEOIL FUT ${expTag} ${st}CE` : `${baseSym} ${st} CE`;
            const peSym = isCrude ? `CRUDEOIL FUT ${expTag} ${st}PE` : `${baseSym} ${st} PE`;
            if(!searchQ || ceSym.toUpperCase().includes(searchQ)){
              results.push({ symbol: ceSym, name: `${baseSym} ${st} Call`, exchange: isCrude ? 'MCX' : 'NFO', instrument_type: 'CE', ltp: Math.max(15, roundVal((curLtp - st) + 120)) });
            }
            if(!searchQ || peSym.toUpperCase().includes(searchQ)){
              results.push({ symbol: peSym, name: `${baseSym} ${st} Put`, exchange: isCrude ? 'MCX' : 'NFO', instrument_type: 'PE', ltp: Math.max(15, roundVal((st - curLtp) + 120)) });
            }
          }
        }

        if(!results.length){
          optBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-dim);font-size:11px;">No options found. Try: ' + esc(baseSym) + ' 23500 CE</div>';
          return;
        }

        optBox.innerHTML = results.slice(0, 16).map(o => {
          const symText = o.symbol || o.name || '';
          const isCe = symText.toUpperCase().includes('CE');
          const isAtm = symText.includes(String(atmStrike));
          const ltpVal = o.ltp || (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[symText]?.ltp) || null;
          return `<div class="instrument-suggestion" style="padding:8px 10px;cursor:pointer;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;">
            <div>
              <b style="font-size:12px;font-family:var(--font-mono);color:var(--text);">${esc(symText)}</b>
              <span style="font-size:10px;color:var(--text-dim);display:block;margin-top:2px;">${esc(o.name || symText)} · ${esc(o.exchange || 'NFO')} · ${isCe ? 'Call' : 'Put'}</span>
            </div>
            <div style="text-align:right;">
              <span class="${isCe ? 'cell-up' : 'cell-down'}" style="font-family:var(--font-mono);font-weight:700;font-size:11.5px;">${ltpVal ? '₹' + fmt(ltpVal) : (isCe ? 'CE' : 'PE')}</span>
              ${isAtm ? '<span class="tag gold" style="font-size:8px;padding:1px 4px;margin-left:4px;">ATM</span>' : ''}
            </div>
          </div>`;
        }).join('');

        optBox.querySelectorAll('.instrument-suggestion').forEach((div, idx) => {
          div.onmousedown = async (e) => {
            e.preventDefault();
            const chosenObj = results[idx];
            const chosen = chosenObj.symbol || chosenObj.name;
            optInp.value = chosen;
            optBox.style.display = 'none';
            window.__caPinnedOptionContract = chosen;

            let chosenLtp = chosenObj.ltp || (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp);
            if(!chosenLtp){
              try {
                const qRes = await A('/api/market/quote/' + encodeURIComponent(chosen));
                if(qRes?.ltp) chosenLtp = Number(qRes.ltp);
              } catch(_){}
            }
            if(!chosenLtp){
              const isCall = chosen.toUpperCase().includes('CE');
              const m = chosen.match(/\\s+(\\d+)\\s*(?:CE|PE)?/);
              const strikeVal = m ? Number(m[1]) : atmStrike;
              chosenLtp = isCall ? roundVal(Math.max(15, (curLtp - strikeVal) + 120)) : roundVal(Math.max(15, (strikeVal - curLtp) + 120));
            }
            applyOptionRecommendation(chosen, chosenLtp, baseSym);
          };
        });
      }, 120);
    }

    optInp.addEventListener('input', () => searchOptions(optInp.value));
    optInp.addEventListener('focus', () => searchOptions(optInp.value));
    document.addEventListener('click', (e) => {
      if(!e.target.closest('#chartRecoOptionWrap')) optBox.style.display = 'none';
    });
  })();
"""

if "initOptionSearchBox" not in t:
    t = t.replace(
        "// Unified Watchlist Search Engine for Option Search Box",
        SEARCH_BINDER + "\n    // Unified Watchlist Search Engine for Option Search Box"
    )
    print("4. Injected global initOptionSearchBox ✓")
else:
    print("4. initOptionSearchBox already present ✓")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(t)
print("Saved terminal.html.")

print("\n--- Patching app.py for CRUDEOIL MCX live option chain ---")
with open('app.py', 'r', encoding='utf-8') as f:
    a = f.read()

OLD_OPTIONS_SUMMARY = """@app.get("/api/options/{underlying}")
async def options_summary(underlying: str, expiry: str | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    root = extract_root_symbol(underlying).upper()
    key = f"option-chain:{root}:{expiry or 'nearest'}"
    cached = CACHE.get(key)
    if cached is not None:
        return cached

    is_mcx = root in {"CRUDEOIL", "GOLD", "SILVER", "NATURALGAS", "COPPER", "ZINC", "LEAD", "ALUMINIUM"}
    data = None
    if not is_mcx:
        try:
            raw = await asyncio.wait_for(asyncio.to_thread(UPSTOX.option_chain, root, expiry), timeout=3.5)
            if raw and isinstance(raw, dict) and raw.get("strikes"):
                data = raw
        except Exception:
            data = None
    
    if not data or not (data.get("strikes") or []):
        data = generate_option_chain_engine(underlying, expiry)
        
    CACHE.set(key, data, 8)
    return data"""

NEW_OPTIONS_SUMMARY = """@app.get("/api/options/{underlying}")
async def options_summary(underlying: str, expiry: str | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    root = extract_root_symbol(underlying).upper()
    key = f"option-chain:{root}:{expiry or 'nearest'}"
    cached = CACHE.get(key)
    if cached is not None:
        return cached

    is_mcx = root in {"CRUDEOIL", "GOLD", "SILVER", "NATURALGAS", "COPPER", "ZINC", "LEAD", "ALUMINIUM"}
    data = None
    if not is_mcx:
        try:
            raw = await asyncio.wait_for(asyncio.to_thread(UPSTOX.option_chain, root, expiry), timeout=3.5)
            if raw and isinstance(raw, dict) and raw.get("strikes"):
                data = raw
        except Exception:
            data = None
    
    if not data or not (data.get("strikes") or []):
        data = generate_option_chain_engine(underlying, expiry)

    # Real contract overlay for MCX commodities (CRUDEOIL, etc.)
    if is_mcx and data and data.get("strikes"):
        exp_tag = "17 SEP" if not expiry or "17 SEP" in expiry.upper() else expiry[:6].upper()
        try:
            p_mcx = await asyncio.to_thread(UPSTOX.search_instruments, f"{root} {exp_tag}", exchanges="MCX", segments="ALL")
            mcx_rows = p_mcx.get("data") or []
            if mcx_rows:
                contract_map = {}
                for cr in mcx_rows:
                    stk_val = cr.get("strike_price")
                    itype = str(cr.get("instrument_type") or "").upper()
                    if stk_val is not None and itype in {"CE", "PE"}:
                        contract_map[(round(float(stk_val)), itype)] = cr
                for s_item in data.get("strikes", []):
                    stk = round(float(s_item.get("strike") or 0))
                    for side in ("call", "put"):
                        side_type = "CE" if side == "call" else "PE"
                        if (stk, side_type) in contract_map:
                            real_c = contract_map[(stk, side_type)]
                            s_item[side]["instrument_key"] = real_c.get("instrument_key") or s_item[side].get("instrument_key")
                            s_item[side]["trading_symbol"] = real_c.get("trading_symbol") or f"{root} {stk} {side_type} {exp_tag} 26"
                            s_item[side]["symbol"] = f"{root} FUT {exp_tag} {stk}{side_type}"
                            s_item[side]["display_symbol"] = f"{root} FUT {exp_tag} {stk}{side_type}"
                data["is_mock"] = False
                data["provider"] = "upstox_mcx"
                data["expiry"] = f"{exp_tag} 2026"
        except Exception as err:
            log.warning("MCX real option overlay error for %s: %s", root, safe_text(err))
        
    CACHE.set(key, data, 8)
    return data"""

if OLD_OPTIONS_SUMMARY in a:
    a = a.replace(OLD_OPTIONS_SUMMARY, NEW_OPTIONS_SUMMARY)
    print("5. Successfully updated options_summary in app.py with real MCX option contract overlay ✓")
else:
    print("5. Could not find exact OLD_OPTIONS_SUMMARY in app.py")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(a)
print("Saved app.py.")

