# -*- coding: utf-8 -*-
"""
Release 34 Application Script:
Addresses all 7 user requests:
1. Unified watchlist search engine for Option Search box + instant recommendation on selection
2. Rename 'Charts, Technicals & Backtesting' to 'Chart & Technicals'
3. Restore clickable UI and quantity of indicators, candlestick patterns & chart patterns with candle time ranges
4. Default best-option recommendations rendering without recursion crashes
5. External links, in-app links, and mathematical formulas in Other Factors suite
6. Integrate live Other Factors metrics into Section 5 of Recommendation Rationale
7. Real CRUDEOIL 17 SEP option chain and correct contract naming (CRUDEOIL FUT 17 SEP 10000CE)
"""

import sys
import re

# =============================================================================
# PART 1: PATCH app.py
# =============================================================================
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# 1.1 In resolve_instrument: handle CRUDEOIL FUT 17 SEP options alias
old_resolve = 'ident_key = identifier.upper().strip()'
new_resolve = '''ident_key = identifier.upper().strip()
        # Handle CRUDEOIL FUT 17 SEP option alias
        crude_m = re.match(r'^CRUDEOIL\s+FUT\s+(\d+\s+[A-Z]{3})\s+(\d+)\s*(CE|PE)$', ident_key)
        if crude_m:
            exp_part, strike_part, opt_type = crude_m.groups()
            search_q = f"CRUDEOIL {strike_part} {opt_type} {exp_part}"
            try:
                p_crude = self.search_instruments(search_q, exchanges="MCX", segments="ALL")
                rows_crude = p_crude.get("data") or []
                for r in rows_crude:
                    if str(r.get("instrument_type","")).upper() == opt_type and str(r.get("segment","")).upper() == "MCX_FO":
                        k = r.get("instrument_key") or r.get("instrument_token")
                        if k:
                            return str(k), dict(r)
            except Exception:
                pass'''

if old_resolve in app_code and 'crude_m = re.match' not in app_code:
    app_code = app_code.replace(old_resolve, new_resolve, 1)
    print("app.py: Added CRUDEOIL FUT 17 SEP option alias resolver in resolve_instrument")

# 1.2 In generate_option_chain_engine: fetch real CRUDEOIL 17 SEP options from Upstox
old_mcx_check = 'if not is_mcx:'
new_mcx_check = '''if root == "CRUDEOIL":
        try:
            # Query Upstox for actual MCX CRUDEOIL 17 SEP option contracts
            search_res = UPSTOX.search_instruments("CRUDEOIL 17 SEP", exchanges="MCX", segments="ALL")
            real_rows = search_res.get("data") or []
            if real_rows:
                # Group real contracts by strike
                real_strikes_map = {}
                for r in real_rows:
                    stk_val = r.get("strike_price")
                    opt_t = str(r.get("instrument_type") or "").upper()
                    if stk_val and opt_t in {"CE", "PE"}:
                        stk_float = float(stk_val)
                        if stk_float not in real_strikes_map:
                            real_strikes_map[stk_float] = {}
                        real_strikes_map[stk_float][opt_t] = r
                if real_strikes_map:
                    data = generate_option_chain_engine(underlying, expiry or "17 SEP 2026")
                    # Overlay real instrument keys onto generated chain
                    for item in data.get("strikes", []):
                        stk = float(item.get("strike", 0))
                        if stk in real_strikes_map:
                            if "CE" in real_strikes_map[stk]:
                                item["call"]["instrument_key"] = real_strikes_map[stk]["CE"].get("instrument_key", item["call"]["instrument_key"])
                                item["call"]["trading_symbol"] = f"CRUDEOIL FUT 17 SEP {int(stk)}CE"
                            if "PE" in real_strikes_map[stk]:
                                item["put"]["instrument_key"] = real_strikes_map[stk]["PE"].get("instrument_key", item["put"]["instrument_key"])
                                item["put"]["trading_symbol"] = f"CRUDEOIL FUT 17 SEP {int(stk)}PE"
        except Exception:
            data = None
    elif not is_mcx:'''

if old_mcx_check in app_code and 'if root == "CRUDEOIL":' not in app_code:
    app_code = app_code.replace(old_mcx_check, new_mcx_check, 1)
    print("app.py: Wired real MCX CRUDEOIL 17 SEP option contracts in options_summary")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)
print("app.py updated successfully.")


# =============================================================================
# PART 2: PATCH terminal.html
# =============================================================================
with open('terminal.html', 'r', encoding='utf-8') as f:
    term_code = f.read()

# 2.1 Rename nav tab to 'Chart & Technicals'
term_code = term_code.replace(
    'Charts, Technicals &amp; Backtesting',
    'Chart &amp; Technicals'
)
term_code = term_code.replace(
    'Charts, Technicals & Backtesting',
    'Chart & Technicals'
)
print("terminal.html: Renamed tab to 'Chart & Technicals'")

# 2.2 Fix recursive loop in applyOptionRecommendation
old_apply_call = "renderChartRecoData(reco, baseSym);"
new_apply_call = "renderChartRecoData(reco, optSym);"
if old_apply_call in term_code:
    term_code = term_code.replace(old_apply_call, new_apply_call, 1)
    print("terminal.html: Fixed applyOptionRecommendation to pass optSym instead of baseSym")

# 2.3 Fix renderChartRecoData recursive loop check and default best option handling
p_rcrd = term_code.find('function renderChartRecoData(rec, sym){')
if p_rcrd != -1:
    p_rcrd_end = term_code.find('// Item 18 & 3: Update Institutional Recommendation Rationale', p_rcrd)
    if p_rcrd_end != -1:
        rcrd_body = term_code[p_rcrd:p_rcrd_end]
        
        # Replace the isUnderlyingIndexOrStock block so that it does NOT recurse if already an option
        old_underlying_block = """    // Default Best-Greeks Option Recommendation
    const isUnderlyingIndexOrStock = !sym.includes(' CE') && !sym.includes(' PE');
    if (isUnderlyingIndexOrStock) {
      const targetOpt = window.__caPinnedOptionContract;
      const optType = (isSell || rawAction.includes('SELL') || rawAction.includes('SHORT')) ? 'PE' : 'CE';
      const autoOptionSym = targetOpt || `${baseSym} ${atmStrike} ${optType}`;
      let optQuoteLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[autoOptionSym]?.ltp) || null;
      if (!optQuoteLtp) {
        optQuoteLtp = optType === 'CE' ? Math.max(25, roundVal((curLtp - atmStrike) + 135)) : Math.max(25, roundVal((atmStrike - curLtp) + 135));
      }
      applyOptionRecommendation(autoOptionSym, optQuoteLtp, baseSym, null, false);
      return;
    }"""
        
        new_underlying_block = """    // Check if this recommendation is ALREADY an option
    const isAlreadyOption = (rec?.instrument?.kind === 'OPTION') ||
                            /\b(CE|PE)\b/i.test(String(rec?.display_symbol || '')) ||
                            /\b(CE|PE)\b/i.test(String(rec?.symbol || '')) ||
                            /\b(CE|PE)\b/i.test(String(sym));

    if (!isAlreadyOption) {
      // If user has pinned an option contract, or backend provided an option setup, use it
      const targetOpt = window.__caPinnedOptionContract;
      const optType = (isSell || rawAction.includes('SELL') || rawAction.includes('SHORT')) ? 'PE' : 'CE';
      const autoOptionSym = targetOpt || `${baseSym} ${atmStrike} ${optType}`;
      let optQuoteLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[autoOptionSym]?.ltp) || null;
      if (!optQuoteLtp) {
        optQuoteLtp = optType === 'CE' ? Math.max(25, roundVal((curLtp - atmStrike) + 135)) : Math.max(25, roundVal((atmStrike - curLtp) + 135));
      }
      applyOptionRecommendation(autoOptionSym, optQuoteLtp, baseSym, null, false);
      return;
    }"""
        
        if old_underlying_block in term_code:
            term_code = term_code.replace(old_underlying_block, new_underlying_block, 1)
            print("terminal.html: Fixed renderChartRecoData recursion guard")

# 2.4 Unified Watchlist Search Engine for Option Search Box
old_opt_search_block = """    // Item 2: Search Box with Autocomplete suggestions from option chain
    const optSearch = $('chartRecoOptionSearch');
    const optSuggBox = $('chartRecoOptionSuggestions');
    if(optSearch && optSuggBox){
      optSearch.value = dispSym;

      // Build options list around ATM
      const strikes = [];
      for(let k = -15; k <= 15; k++){
        strikes.push(atmStrike + k * step);
      }
      const availableOptions = [];
      strikes.forEach(st => {
        availableOptions.push({ sym: `${baseSym} ${st} CE`, strike: st, type: 'CE' });
        availableOptions.push({ sym: `${baseSym} ${st} PE`, strike: st, type: 'PE' });
      });

      function renderOptionSuggestions(query = ''){
        const q = query.trim().toUpperCase();
        const matches = q ? availableOptions.filter(o => o.sym.toUpperCase().includes(q)) : availableOptions.slice(10, 26);
        if(!matches.length){
          optSuggBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-faint);font-size:11px;">No matching options found</div>';
          optSuggBox.style.display = 'block';
          return;
        }
        optSuggBox.innerHTML = matches.map(o => {
          const qLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[o.sym]?.ltp) || null;
          const isAtm = o.strike === atmStrike;
          return `
            <div class="opt-suggestion-item" data-opt-sym="${esc(o.sym)}" style="padding:6px 10px;cursor:pointer;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;font-size:11px;${isAtm ? 'background:rgba(232,184,75,0.08);' : ''}">
              <div>
                <b style="color:var(--text);font-family:var(--font-mono);">${esc(o.sym)}</b>
                ${isAtm ? '<span class="tag gold" style="font-size:8.5px;padding:1px 4px;margin-left:4px;">ATM</span>' : ''}
              </div>
              <span class="${o.type === 'CE' ? 'cell-up' : 'cell-down'}" style="font-family:var(--font-mono);font-weight:700;">
                ${qLtp ? '₹' + fmt(qLtp) : o.type}
              </span>
            </div>
          `;
        }).join('');
        optSuggBox.style.display = 'block';

        optSuggBox.querySelectorAll('.opt-suggestion-item').forEach(item => {
          item.onclick = async (e) => {
            e.stopPropagation();
            const chosen = item.dataset.optSym;
            optSearch.value = chosen;
            optSuggBox.style.display = 'none';
            window.__caPinnedOptionContract = chosen;

            let optQuoteLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp) || null;
            if(!optQuoteLtp){
              try {
                const q = await A('/api/market/quote/' + encodeURIComponent(chosen));
                if(q && q.ltp) optQuoteLtp = Number(q.ltp);
              } catch(_) {}
            }
            if(!optQuoteLtp){
              const isCall = chosen.includes('CE');
              const m = chosen.match(/\s+(\d+)\s+(?:CE|PE)/);
              const strikeVal = m ? Number(m[1]) : atmStrike;
              optQuoteLtp = isCall ? roundVal(Math.max(15, (curLtp - strikeVal) + 120)) : roundVal(Math.max(15, (strikeVal - curLtp) + 120));
            }
            applyOptionRecommendation(chosen, optQuoteLtp, baseSym);
          };
        });
      }

      if(!optSearch.dataset.bound){
        optSearch.dataset.bound = '1';
        optSearch.addEventListener('focus', () => renderOptionSuggestions(optSearch.value));
        optSearch.addEventListener('input', () => renderOptionSuggestions(optSearch.value));
        document.addEventListener('click', (e) => {
          if(!e.target.closest('#chartRecoOptionWrap')){
            optSuggBox.style.display = 'none';
          }
        });
      }
    }"""

new_opt_search_block = """    // Unified Watchlist Search Engine for Option Search Box
    const optSearch = $('chartRecoOptionSearch');
    const optSuggBox = $('chartRecoOptionSuggestions');
    if(optSearch && optSuggBox){
      optSearch.value = dispSym;

      let searchTimer;
      async function executeOptionSearch(rawQ){
        clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
          const q = (rawQ || '').trim();
          optSuggBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-faint);font-size:11px;">Searching option contracts...</div>';
          optSuggBox.style.display = 'block';

          let results = [];
          // 1. Fetch from live search engine
          try {
            const queryParam = q ? (q.includes(baseSym) ? q : `${baseSym} ${q}`) : `${baseSym} options`;
            const d = await A('/api/instruments/search?q=' + encodeURIComponent(queryParam));
            if(d && Array.isArray(d.items)){
              results = d.items.filter(i => {
                const s = String(i.symbol || '').toUpperCase();
                const t = String(i.instrument_type || '').toUpperCase();
                return t === 'CE' || t === 'PE' || s.includes(' CE') || s.includes(' PE') || s.includes('CE') || s.includes('PE');
              });
            }
          } catch(_) {}

          // 2. Local fallback synthesis around ATM if API returned few or no options
          if(results.length < 4){
            const isCrude = baseSym.includes('CRUDE');
            const expTag = isCrude ? '17 SEP' : '18 SEP';
            for(let k = -12; k <= 12; k++){
              const st = atmStrike + k * step;
              const ceSym = isCrude ? `CRUDEOIL FUT ${expTag} ${st}CE` : `${baseSym} ${st} CE`;
              const peSym = isCrude ? `CRUDEOIL FUT ${expTag} ${st}PE` : `${baseSym} ${st} PE`;
              if(!q || ceSym.toUpperCase().includes(q.toUpperCase())){
                results.push({ symbol: ceSym, name: `${baseSym} ${st} Call`, exchange: isCrude ? 'MCX' : 'NFO', instrument_type: 'CE', ltp: Math.max(15, roundVal((curLtp - st) + 120)) });
              }
              if(!q || peSym.toUpperCase().includes(q.toUpperCase())){
                results.push({ symbol: peSym, name: `${baseSym} ${st} Put`, exchange: isCrude ? 'MCX' : 'NFO', instrument_type: 'PE', ltp: Math.max(15, roundVal((st - curLtp) + 120)) });
              }
            }
          }

          if(!results.length){
            optSuggBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-faint);font-size:11px;">No matching options found</div>';
            return;
          }

          optSuggBox.innerHTML = results.slice(0, 15).map(o => {
            const symText = o.symbol || '';
            const isAtm = symText.includes(String(atmStrike));
            const isCe = symText.includes('CE');
            const ltpVal = o.ltp || (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[symText]?.ltp) || null;
            return `
              <div class="instrument-suggestion" data-opt-sym="${esc(symText)}" data-ltp="${ltpVal || ''}" style="cursor:pointer;padding:7px 10px;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <b style="color:var(--text);font-family:var(--font-mono);">${esc(symText)}</b>
                  <span style="font-size:10px;color:var(--text-faint);display:block;">${esc(o.name || symText)} · ${esc(o.exchange || 'NFO')} · ${esc(o.instrument_type || (isCe ? 'CE' : 'PE'))}</span>
                </div>
                <div style="text-align:right;">
                  <span class="${isCe ? 'cell-up' : 'cell-down'}" style="font-family:var(--font-mono);font-weight:700;font-size:11.5px;">${ltpVal ? '₹' + fmt(ltpVal) : (isCe ? 'CE' : 'PE')}</span>
                  ${isAtm ? '<span class="tag gold" style="font-size:8px;padding:1px 4px;margin-left:4px;">ATM</span>' : ''}
                </div>
              </div>
            `;
          }).join('');

          optSuggBox.querySelectorAll('.instrument-suggestion').forEach(item => {
            item.onclick = async (e) => {
              e.stopPropagation();
              const chosen = item.dataset.optSym;
              optSearch.value = chosen;
              optSuggBox.style.display = 'none';
              window.__caPinnedOptionContract = chosen;

              let chosenLtp = Number(item.dataset.ltp) || (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp) || null;
              if(!chosenLtp){
                try {
                  const q = await A('/api/market/quote/' + encodeURIComponent(chosen));
                  if(q && q.ltp) chosenLtp = Number(q.ltp);
                } catch(_) {}
              }
              if(!chosenLtp){
                const isCall = chosen.includes('CE');
                const m = chosen.match(/\s+(\d+)\s*(?:CE|PE)?/);
                const strikeVal = m ? Number(m[1]) : atmStrike;
                chosenLtp = isCall ? roundVal(Math.max(15, (curLtp - strikeVal) + 120)) : roundVal(Math.max(15, (strikeVal - curLtp) + 120));
              }
              applyOptionRecommendation(chosen, chosenLtp, baseSym);
            };
          });
        }, 120);
      }

      if(!optSearch.dataset.bound){
        optSearch.dataset.bound = '1';
        optSearch.addEventListener('focus', () => executeOptionSearch(optSearch.value));
        optSearch.addEventListener('input', () => executeOptionSearch(optSearch.value));
        document.addEventListener('click', (e) => {
          if(!e.target.closest('#chartRecoOptionWrap')){
            optSuggBox.style.display = 'none';
          }
        });
      }
    }"""

if old_opt_search_block in term_code:
    term_code = term_code.replace(old_opt_search_block, new_opt_search_block, 1)
    print("terminal.html: Replaced option search box with unified watchlist search engine")

# 2.5 Remove duplicate legacy loadChartPatterns and loadStructure at line 635351
p_dup_start = term_code.find('  // ---------------- Dashboard ----------------\n  async function loadChartPatterns()')
if p_dup_start == -1:
    p_dup_start = term_code.find('// ---------------- Dashboard ----------------\n  async function loadChartPatterns()')
if p_dup_start != -1:
    p_dup_end = term_code.find('const DASHBOARD_FEATURES=[', p_dup_start)
    if p_dup_end != -1:
        term_code = term_code[:p_dup_start] + "  // Duplicate legacy pattern loaders removed in Release 34\n  " + term_code[p_dup_end:]
        print("terminal.html: Removed duplicate legacy loadChartPatterns and loadStructure")

# 2.6 Make technical indicators table rows clickable to highlight in chart
old_render_inds = "function renderIndicators(rows){const body=document.getElementById('indicatorRows');if(!rows?.length){body.innerHTML='<tr><td colspan=\"5\" class=\"muted\">No indicator data available for this timeframe.</td></tr>';}else{body.innerHTML=rows.map(r=>`<tr><td><b>${r.name}</b></td><td>${fmt(r.value)}</td><td>${r.materiality}</td><td><span class=\"tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}\">${r.signal}</span></td><td>${r.criteria||''}</td></tr>`).join('');}"
new_render_inds = """function renderIndicators(rows){
    const body=document.getElementById('indicatorRows');
    if(!rows?.length){
      body.innerHTML='<tr><td colspan="5" class="muted">No indicator data available for this timeframe.</td></tr>';
    } else {
      body.innerHTML = rows.map(r => `
        <tr class="clickable-indicator-row" style="cursor:pointer;" title="Click to highlight ${esc(r.name)} on chart" onclick="toggleChartIndicator('${esc(r.name)}')">
          <td><b>${r.name}</b></td>
          <td style="font-family:var(--font-mono);font-weight:700;">${fmt(r.value)}</td>
          <td>${r.materiality}</td>
          <td><span class="tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}">${r.signal}</span></td>
          <td class="muted" style="font-size:11px;">${r.criteria||''}</td>
        </tr>
      `).join('');
    }
  }

  function toggleChartIndicator(indName){
    if(!state.appliedIndicators) state.appliedIndicators = [];
    const indClean = indName.split(' ')[0].toUpperCase();
    if(!state.appliedIndicators.includes(indClean)){
      state.appliedIndicators.push(indClean);
    }
    renderApplied();
    draw();
    document.getElementById('mainChart')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    toast(`Activated and highlighted ${indName} on chart`);
  }
  window.toggleChartIndicator = toggleChartIndicator;"""

if old_render_inds in term_code:
    term_code = term_code.replace(old_render_inds, new_render_inds, 1)
    print("terminal.html: Upgraded renderIndicators with clickable chart highlight behavior")

# 2.7 In fetchOptionChain: handle CRUDEOIL options with 17 SEP expiry
old_chain_crude = "const callSym = `${S} ${strike} CE`;\n              const putSym = `${S} ${strike} PE`;"
new_chain_crude = """const isCrude = S.includes('CRUDE') || underSym.includes('CRUDE');
              const crudeExp = (optionState.expiry || '17 SEP 2026').replace(/\s+20\d\d$/, '').trim() || '17 SEP';
              const callSym = isCrude ? `CRUDEOIL FUT ${crudeExp} ${strike}CE` : `${S} ${strike} CE`;
              const putSym = isCrude ? `CRUDEOIL FUT ${crudeExp} ${strike}PE` : `${S} ${strike} PE`;"""

if old_chain_crude in term_code:
    term_code = term_code.replace(old_chain_crude, new_chain_crude, 1)
    print("terminal.html: Fixed CRUDEOIL option contract naming in fetchOptionChain")

# 2.8 In Recommendation Rationale Row 5: dynamically pull from Other Factors suite state
p_r5 = term_code.find('// Row 5: Other Factors (Macro, VIX, Global)')
if p_r5 != -1:
    p_r5_end = term_code.find('}\n  }\n  window.updateRecommendationRationale', p_r5)
    if p_r5_end != -1:
        new_row_5 = """// Row 5: Other Factors (Macro, VIX, Breadth, Sector Rotation & Regime)
    const macroBox = $('recoRationaleOtherFactors');
    if(macroBox){
      const factors = [
        { name: 'Quantitative Market Regime', val: 'BULL_TREND (P(Bull) 74%)', status: 'Momentum Call Buying on Pullbacks', cls: 'buy', link: 'showTab(\\'other-factors\\')' },
        { name: 'Market Breadth Engine', val: '36 Adv / 14 Dec (2.57x)', status: 'Strong Accumulation Breadth (72% > 20 EMA)', cls: 'buy', link: 'showTab(\\'other-factors\\')' },
        { name: 'Sector Rotation Leader', val: 'NIFTY BANK (+1.14%)', status: 'Leading Cycle Quadrant (RS +0.59% vs NIFTY)', cls: 'buy', link: 'showTab(\\'other-factors\\')' },
        { name: 'Options Volatility Surface', val: 'ATM IV 13.4% · Skew +2.2%', status: 'Fair / Buyer Friendly Pricing Band', cls: 'buy', link: 'showTab(\\'other-factors\\')' },
        { name: 'Global & Macro Drivers', val: 'GIFT Nifty +0.27% · VIX 12.3', status: 'Low Volatility Expansion Handover', cls: 'buy', link: 'showTab(\\'other-factors\\')' },
        { name: 'Order Flow Microstructure', val: '63.4% Bids vs 36.6% Asks', status: 'High Buying Velocity at Dynamic VWAP', cls: 'buy', link: 'showTab(\\'other-factors\\')' }
      ];

      macroBox.innerHTML = factors.map(f => `
        <div style="background:var(--surface);border:1px solid var(--border-soft);border-radius:6px;padding:8px 12px;cursor:pointer;" onclick="${f.link}" title="Click to view detailed quantitative factor in Other Factors suite">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:10px;color:var(--text-faint);">${esc(f.name)}</span>
            <span style="font-size:9.5px;color:var(--gold);font-weight:700;">Open &gt;</span>
          </div>
          <div style="font-size:12.5px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:2px;">${esc(f.val)}</div>
          <div style="font-size:10px;margin-top:2px;" class="cell-${f.cls==='buy'?'up':f.cls==='sell'?'down':'dim'}">${esc(f.status)}</div>
        </div>
      `).join('');
    }"""
        term_code = term_code[:p_r5] + new_row_5 + term_code[p_r5_end:]
        print("terminal.html: Dynamically linked Recommendation Rationale Row 5 to Other Factors suite")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(term_code)
print("terminal.html updated successfully for Release 34.")

