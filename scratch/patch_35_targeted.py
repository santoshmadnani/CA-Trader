"""
Release 35 targeted patches:
1. Move option search box binding before the isAlreadyOption early return
2. Fix updateRecommendationRationale to call from renderChartRecoData properly
3. Fix recommendation rationale sections to use real data
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

patches = 0

# ===========================================================================
# PATCH 1: Move option search binding before the early return
# Currently: binding is at line ~9263 AFTER early return at line ~9138
# Fix: Add global option search binding function that runs BEFORE isAlreadyOption check
# ===========================================================================

# Find the specific early return block and inject search binding before it
OLD_EARLY_RETURN = """    if (!isAlreadyOption) {
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

NEW_EARLY_RETURN = """    // Always bind the option search box first (before any early return)
    (function bindOptionSearchBox(){
      const optSearch = $('chartRecoOptionSearch');
      const optSuggBox = $('chartRecoOptionSuggestions');
      if(!optSearch || !optSuggBox) return;
      // Always reset the bound flag so the search closure captures fresh baseSym/atmStrike/curLtp
      delete optSearch.dataset.bound;

      let searchTimer;
      function runOptionSearch(rawQ){
        clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
          const q = (rawQ || '').trim();
          optSuggBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-faint);font-size:11px;">Searching option contracts...</div>';
          optSuggBox.style.display = 'block';

          let results = [];
          try {
            const queryParam = q ? (q.toUpperCase().includes(baseSym) ? q : `${baseSym} ${q}`) : baseSym;
            const d = await A('/api/instruments/search?q=' + encodeURIComponent(queryParam) + '&limit=20');
            if(d && Array.isArray(d.items)){
              results = d.items.filter(i => {
                const s = String(i.symbol || i.display_symbol || '').toUpperCase();
                const t = String(i.instrument_type || '').toUpperCase();
                return t === 'CE' || t === 'PE' || t === 'OPTIONS' || s.endsWith(' CE') || s.endsWith(' PE') || s.endsWith('CE') || s.endsWith('PE');
              });
            }
          } catch(_) {}

          // Local fallback: synthesize strikes around ATM
          if(results.length < 3){
            const isCrude = baseSym.includes('CRUDE');
            const expTag = isCrude ? '17 SEP' : (window.__caOptionExpiry || '25 SEP');
            const searchQ = q.toUpperCase();
            for(let k = -15; k <= 15; k++){
              const st = atmStrike + k * step;
              const ceSym = isCrude ? `CRUDEOIL FUT ${expTag} ${st}CE` : `${baseSym} ${st} CE`;
              const peSym = isCrude ? `CRUDEOIL FUT ${expTag} ${st}PE` : `${baseSym} ${st} PE`;
              if(!searchQ || ceSym.toUpperCase().includes(searchQ)){
                results.push({ symbol: ceSym, name: `${baseSym} ${st} Call`, exchange: isCrude ? 'MCX' : 'NFO', instrument_type: 'CE', ltp: Math.max(10, roundVal(Math.abs(curLtp - st) * 0.15 + 40)) });
              }
              if(!searchQ || peSym.toUpperCase().includes(searchQ)){
                results.push({ symbol: peSym, name: `${baseSym} ${st} Put`, exchange: isCrude ? 'MCX' : 'NFO', instrument_type: 'PE', ltp: Math.max(10, roundVal(Math.abs(st - curLtp) * 0.15 + 40)) });
              }
            }
          }

          if(!results.length){
            optSuggBox.innerHTML = '<div style="padding:8px 10px;color:var(--text-faint);font-size:11px;">No matching options found. Try: ' + esc(baseSym) + ' 23500 CE</div>';
            return;
          }

          optSuggBox.innerHTML = results.slice(0, 18).map(o => {
            const symText = o.symbol || o.display_symbol || '';
            const isAtm = symText.includes(String(atmStrike));
            const isCe = symText.toUpperCase().includes('CE');
            const ltpVal = o.ltp || (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[symText]?.ltp) || null;
            const expiry = o.expiry || '';
            return `<div class="instrument-suggestion" data-opt-sym="${esc(symText)}" data-ltp="${ltpVal || ''}" style="cursor:pointer;padding:7px 10px;border-bottom:1px solid var(--border-soft);display:flex;justify-content:space-between;align-items:center;">
              <div>
                <b style="color:var(--text);font-family:var(--font-mono);font-size:12px;">${esc(symText)}</b>
                <span style="font-size:10px;color:var(--text-faint);display:block;">${esc(o.name || symText)} · ${esc(o.exchange || 'NFO')}${expiry ? ' · ' + esc(expiry) : ''}</span>
              </div>
              <div style="text-align:right;display:flex;align-items:center;gap:4px;">
                <span class="${isCe ? 'cell-up' : 'cell-down'}" style="font-family:var(--font-mono);font-weight:700;font-size:11.5px;">${ltpVal ? '₹' + fmt(ltpVal) : (isCe ? 'CE' : 'PE')}</span>
                ${isAtm ? '<span class="tag gold" style="font-size:8px;padding:1px 4px;">ATM</span>' : ''}
              </div>
            </div>`;
          }).join('');

          optSuggBox.querySelectorAll('.instrument-suggestion').forEach(item => {
            item.onmousedown = async (e) => {
              e.preventDefault();
              const chosen = item.dataset.optSym;
              optSearch.value = chosen;
              optSuggBox.style.display = 'none';
              window.__caPinnedOptionContract = chosen;

              let chosenLtp = Number(item.dataset.ltp) || (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp) || null;
              if(!chosenLtp){
                try {
                  const qr = await A('/api/market/quote/' + encodeURIComponent(chosen));
                  if(qr && qr.ltp) chosenLtp = Number(qr.ltp);
                } catch(_) {}
              }
              if(!chosenLtp){
                const isCall = chosen.toUpperCase().includes('CE');
                const m = chosen.match(/\s+(\d+)\s*(?:CE|PE)?/);
                const strikeVal = m ? Number(m[1]) : atmStrike;
                chosenLtp = isCall ? roundVal(Math.max(10, (curLtp - strikeVal) * 0.15 + 40)) : roundVal(Math.max(10, (strikeVal - curLtp) * 0.15 + 40));
              }
              applyOptionRecommendation(chosen, chosenLtp, baseSym);
            };
          });
        }, 120);
      }

      if(!optSearch.dataset.bound){
        optSearch.dataset.bound = '1';
        optSearch.addEventListener('focus', () => runOptionSearch(optSearch.value));
        optSearch.addEventListener('input', () => runOptionSearch(optSearch.value));
        document.addEventListener('click', (e) => {
          if(!e.target.closest('#chartRecoOptionWrap')) optSuggBox.style.display = 'none';
        });
      }
    })();

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

if OLD_EARLY_RETURN in content:
    content = content.replace(OLD_EARLY_RETURN, NEW_EARLY_RETURN, 1)
    print('[PATCH 1] Moved option search binding before early return ✓')
    patches += 1
else:
    print('[PATCH 1] FAIL: early return block not found exactly - checking partial...')
    idx = content.find('applyOptionRecommendation(autoOptionSym, optQuoteLtp, baseSym, null, false);\n      return;')
    if idx >= 0:
        ln = content[:idx].count('\n') + 1
        print(f'  Found at line {ln} - need different approach')
    else:
        print('  Not found at all')

# ===========================================================================
# PATCH 2: Remove the duplicate old executeOptionSearch block (now replaced by bindOptionSearchBox)
# The old block was at lines 9167-9273 inside renderChartRecoData after isAlreadyOption check
# ===========================================================================
OLD_SEARCH_BLOCK = """    // Unified Watchlist Search Engine for Option Search Box
    const optSearch = $('chartRecoOptionSearch');
    const optSuggBox = $('chartRecoOptionSuggestions');
    if(optSearch && optSuggBox){
      optSearch.value = dispSym;

      let searchTimer;
      async function executeOptionSearch(rawQ){"""

if OLD_SEARCH_BLOCK in content:
    # Find end of this block - it ends at the closing }) of optSearch.dataset.bound check
    idx_start = content.find(OLD_SEARCH_BLOCK)
    # Find the end marker
    end_marker = "      }\n    }\n\n    // Item 18 & 3: Update Institutional"
    idx_end = content.find(end_marker, idx_start)
    if idx_end > 0:
        # Replace the old block with just setting optSearch.value
        replaced = "    // Set option search box value\n    const optSearch = $('chartRecoOptionSearch');\n    if(optSearch) optSearch.value = dispSym;\n\n    // Item 18 & 3: Update Institutional"
        content = content[:idx_start] + replaced + content[idx_end + len(end_marker):]
        print('[PATCH 2] Removed duplicate old executeOptionSearch block ✓')
        patches += 1
    else:
        print('[PATCH 2] Could not find end marker for old block')
else:
    print('[PATCH 2] SKIP - old search block not found (may already be replaced)')

# ===========================================================================
# PATCH 3: Fix updateRecommendationRationale call site  
# It's called inside renderChartRecoData - need to make sure call is correct
# Also make it call when reco data is available from loadChartBundle
# ===========================================================================

# Add call to updateRecommendationRationale inside renderChartRecoData
# after the option values are rendered (near the end of the function)
OLD_RECO_CALL = "    if(typeof updateRecommendationRationale === 'function' && typeof baseSym !== 'undefined' && reco) updateRecommendationRationale(reco, baseSym);"
if OLD_RECO_CALL not in content:
    # Find a good place to add the call - after chartRecoTgt is populated
    INSERT_AFTER = "    if($('chartRecoTgt')){"
    idx = content.find(INSERT_AFTER, content.find('function renderChartRecoData'))
    if idx >= 0:
        # Find the end of this block
        end_block = content.find('\n    if($', idx + 10)
        if end_block > 0:
            # Add updateRecommendationRationale call before next if block
            call_code = "\n    // Update recommendation rationale with real rec data\n    if(typeof updateRecommendationRationale === 'function') updateRecommendationRationale(rec, baseSym);\n"
            content = content[:end_block] + call_code + content[end_block:]
            print('[PATCH 3] Added updateRecommendationRationale call in renderChartRecoData ✓')
            patches += 1

print(f'\n=== {patches} patches applied ===')
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('terminal.html saved.')
print(f'New file size: {len(content):,} bytes')
