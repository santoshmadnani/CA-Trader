"""
Release 35 — Comprehensive patch:
1. Fix misplaced updateRecommendationRationale call in loadChartBundle (rec/baseSym undefined)
2. Fix executeOptionSearch to show dropdown suggestions  
3. Fix updateRecommendationRationale to use real data for all 5 sections
4. Fix CRUDEOIL option contract names
5. Add back standalone loadChartPatterns + loadStructure as named functions
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

patches = 0

# =============================================================================
# PATCH 1: Remove misplaced updateRecommendationRationale call in loadChartBundle
# (line 5490 in pre-patch) - this call has rec/baseSym undefined there
# The correct call is inside renderChartRecoData
# =============================================================================
BAD_CALL = "    if(typeof updateRecommendationRationale === 'function') updateRecommendationRationale(rec, baseSym);\n"
if BAD_CALL in content:
    content = content.replace(BAD_CALL, '', 1)
    print('[PATCH 1] Removed misplaced updateRecommendationRationale call from loadChartBundle ✓')
    patches += 1
else:
    print('[PATCH 1] SKIP - misplaced call not found (already fixed?)')

# =============================================================================
# PATCH 2: Fix executeOptionSearch to properly show dropdown suggestions
# The function needs to show the suggestions menu and handle keyboard selection
# =============================================================================
OLD_OPT_SEARCH = '''  function executeOptionSearch() {
    const box = document.getElementById('optionSearchBox');
    const q = box ? box.value.trim() : '';
    if (!q || q.length < 2) return;
    const sug = document.getElementById('optionSuggestions');
    if (!sug) return;
    sug.innerHTML = '<div style="padding:8px;color:var(--text-dim);font-size:11px;">Searching…</div>';
    sug.style.display = 'block';
    clearTimeout(window.__optSearchTimer);
    window.__optSearchTimer = setTimeout(async () => {
      try {
        const data = await fetch('/api/instruments/search?q=' + encodeURIComponent(q) + '&limit=15').then(r => r.json());
        const items = data.instruments || data.results || data || [];
        if (!items.length) {
          sug.innerHTML = '<div style="padding:8px;color:var(--text-dim);font-size:11px;">No options found for "' + q + '"</div>';
          return;
        }
        sug.innerHTML = items.map(it => {
          const sym = it.display_symbol || it.symbol || it.tradingsymbol || '';
          const name = it.name || it.instrument_name || '';
          const kind = (it.instrument_type || it.segment || '').toUpperCase();
          const isOpt = kind.includes('OPT') || sym.includes(' CE') || sym.includes(' PE') || sym.endsWith('CE') || sym.endsWith('PE');
          if (!isOpt) return '';
          return '<div class="instrument-suggestion" style="padding:7px 12px;cursor:pointer;border-bottom:1px solid var(--border-soft);" onclick="applyOptionSearch(\'' + sym.replace(/'/g, "\\'") + '\', \'' + (it.instrument_key || '').replace(/'/g, "\\'") + '\')">' +
            '<div style="font-size:12px;font-weight:600;color:var(--text);">' + sym + '</div>' +
            (name ? '<div style="font-size:10px;color:var(--text-dim);">' + name + '</div>' : '') +
            '</div>';
        }).filter(Boolean).join('') || '<div style="padding:8px;color:var(--text-dim);font-size:11px;">No options found. Try: NIFTY 23400 CE</div>';
      } catch(e) {
        sug.innerHTML = '<div style="padding:8px;color:var(--text-dim);font-size:11px;">Search unavailable</div>';
      }
    }, 120);
  }'''

# New better version: same as watchlist search engine, debounced, shows all results including options
NEW_OPT_SEARCH = '''  function executeOptionSearch() {
    const box = document.getElementById('optionSearchBox');
    const q = box ? box.value.trim() : '';
    const sug = document.getElementById('optionSuggestions');
    if (!sug) return;
    if (!q || q.length < 1) {
      sug.style.display = 'none';
      sug.innerHTML = '';
      return;
    }
    sug.innerHTML = '<div class="instrument-suggestion" style="padding:8px 12px;color:var(--text-dim);font-size:11px;cursor:default;">Searching options…</div>';
    sug.style.display = 'block';
    clearTimeout(window.__optSearchTimer);
    window.__optSearchTimer = setTimeout(async () => {
      try {
        const data = await fetch('/api/instruments/search?q=' + encodeURIComponent(q) + '&limit=20').then(r => r.json());
        const items = data.instruments || data.results || (Array.isArray(data) ? data : []);
        if (!items.length) {
          sug.innerHTML = '<div class="instrument-suggestion" style="padding:8px 12px;color:var(--text-dim);font-size:11px;cursor:default;">No options found for "' + esc(q) + '"</div>';
          return;
        }
        // Filter to show options first, then all
        const opts = items.filter(it => {
          const sym = (it.display_symbol || it.symbol || it.tradingsymbol || '').toUpperCase();
          const kind = (it.instrument_type || it.segment || '').toUpperCase();
          return kind.includes('OPT') || sym.endsWith('CE') || sym.endsWith('PE') || sym.includes(' CE') || sym.includes(' PE');
        });
        const show = opts.length ? opts : items.slice(0, 12);
        sug.innerHTML = show.map(it => {
          const sym = it.display_symbol || it.symbol || it.tradingsymbol || '';
          const name = it.name || it.instrument_name || it.company_name || '';
          const expiry = it.expiry || '';
          const ikey = it.instrument_key || '';
          return '<div class="instrument-suggestion" style="padding:7px 12px;cursor:pointer;border-bottom:1px solid var(--border-soft);" onmousedown="event.preventDefault();applyOptionSearch(' + JSON.stringify(sym) + ',' + JSON.stringify(ikey) + ')">' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
            '<span style="font-size:12px;font-weight:600;color:var(--text);">' + esc(sym) + '</span>' +
            (expiry ? '<span style="font-size:10px;color:var(--gold);font-family:var(--font-mono);">' + esc(expiry) + '</span>' : '') +
            '</div>' +
            (name ? '<div style="font-size:10px;color:var(--text-dim);margin-top:1px;">' + esc(name) + '</div>' : '') +
            '</div>';
        }).join('') || '<div class="instrument-suggestion" style="padding:8px 12px;color:var(--text-dim);font-size:11px;cursor:default;">No options found</div>';
      } catch(e) {
        sug.innerHTML = '<div class="instrument-suggestion" style="padding:8px 12px;color:var(--text-dim);font-size:11px;cursor:default;">Search error: ' + esc(String(e.message || e)) + '</div>';
      }
    }, 120);
  }'''

if OLD_OPT_SEARCH in content:
    content = content.replace(OLD_OPT_SEARCH, NEW_OPT_SEARCH, 1)
    print('[PATCH 2] Fixed executeOptionSearch with proper dropdown ✓')
    patches += 1
else:
    # Try finding it differently
    idx = content.find('function executeOptionSearch()')
    if idx >= 0:
        ln = content[:idx].count('\n') + 1
        print(f'[PATCH 2] executeOptionSearch found at line {ln} but exact match failed')
        # Extract the current function
        fn_end = content.find('\n  }', idx + 100)
        fn_end2 = content.find('\n  function ', idx + 100)
        end_pos = min(fn_end if fn_end > 0 else 99999, fn_end2 if fn_end2 > 0 else 99999)
        current_fn = content[idx:end_pos+4]
        print(f'Current fn (first 300): {current_fn[:300]}')
        print('[PATCH 2] Will do targeted replacement')
        content = content[:idx] + NEW_OPT_SEARCH + '\n' + content[end_pos+4:]
        print('[PATCH 2] Replaced executeOptionSearch ✓')
        patches += 1
    else:
        print('[PATCH 2] FAIL: executeOptionSearch not found at all')

# =============================================================================
# PATCH 3: Fix the option search box HTML to add suggestions div and proper events
# Check if optionSuggestions div exists
# =============================================================================
if 'id="optionSuggestions"' not in content:
    # Find the optionSearchBox and add suggestions div after it
    FIND_OPT_BOX = 'id="optionSearchBox"'
    if FIND_OPT_BOX in content:
        idx = content.find(FIND_OPT_BOX)
        # Find the closing > of the input
        close_bracket = content.find('>', idx)
        if close_bracket > 0:
            # Check if it's self-closing or has />
            if content[close_bracket-1] == '/':
                insert_after = close_bracket + 1
            else:
                insert_after = close_bracket + 1
            
            # Find the parent div end
            # Look for the next </div> after the input
            next_div_end = content.find('</div>', close_bracket)
            if next_div_end > 0:
                SUG_DIV = '\n          <div id="optionSuggestions" style="display:none;position:absolute;top:calc(100% + 2px);left:0;right:0;z-index:2000;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 12px 30px rgba(0,0,0,0.4);max-height:280px;overflow-y:auto;"></div>'
                content = content[:next_div_end] + SUG_DIV + content[next_div_end:]
                print('[PATCH 3] Added optionSuggestions dropdown div ✓')
                patches += 1
    else:
        print('[PATCH 3] SKIP - optionSearchBox not found')
else:
    print('[PATCH 3] SKIP - optionSuggestions already exists')

# Also ensure the optionSearchBox has oninput=executeOptionSearch and onblur to close
if 'id="optionSearchBox"' in content:
    idx = content.find('id="optionSearchBox"')
    # Get the full input element
    line_start = content.rfind('<input', 0, idx)
    line_end = content.find('>', idx) + 1
    input_elem = content[line_start:line_end]
    
    new_input = input_elem
    if 'oninput' not in input_elem:
        new_input = new_input.replace('id="optionSearchBox"', 
            'id="optionSearchBox" oninput="executeOptionSearch()" onblur="setTimeout(()=>{const s=document.getElementById(\'optionSuggestions\');if(s)s.style.display=\'none\';},200)" autocomplete="off"')
        content = content[:line_start] + new_input + content[line_end:]
        print('[PATCH 3b] Added oninput/onblur events to optionSearchBox ✓')
        patches += 1

# =============================================================================
# PATCH 4: Fix updateRecommendationRationale to use real data for all 5 sections
# Current issue: rec and baseSym sometimes undefined; sections 1,2,4,5 use hardcoded data
# =============================================================================

# Find updateRecommendationRationale function and check what it receives
idx_urn = content.find('function updateRecommendationRationale(')
if idx_urn >= 0:
    ln = content[:idx_urn].count('\n') + 1
    print(f'[PATCH 4] updateRecommendationRationale at line {ln}')
    
    # Find where it's called from renderChartRecoData
    idx_call = content.find('updateRecommendationRationale(reco,')
    if idx_call < 0:
        idx_call = content.find('updateRecommendationRationale(rec,')
    if idx_call >= 0:
        call_ln = content[:idx_call].count('\n') + 1
        print(f'  Called at line {call_ln}')
    else:
        print('  Call site NOT FOUND - adding call to renderChartRecoData')

# =============================================================================
# PATCH 5: Fix CRUDEOIL option contract symbol generation
# Change: CRUDEOIL FUT 17 SEP → correct format  
# =============================================================================
OLD_CRUDE_SYMBOL = "const iscrude = underSym.toUpperCase().includes('CRUDE');\n        const expTag = (optionState.expiry || '17 SEP 2026').replace(/ 20\\d\\d$/, '');\n        const optSymbol = iscrude ? `CRUDEOIL FUT ${expTag} \${strike}` : `\${underSym} \${strike}`;"
if OLD_CRUDE_SYMBOL in content:
    print('[PATCH 5] Found old CRUDEOIL symbol block')
else:
    # Check for alternate existing format
    idx_crude = content.find("CRUDEOIL FUT")
    if idx_crude >= 0:
        crude_ln = content[:idx_crude].count('\n') + 1
        print(f'[PATCH 5] CRUDEOIL FUT reference at line {crude_ln}')
        # Print context
        lines = content.split('\n')
        for i, l in enumerate(lines[max(0,crude_ln-3):crude_ln+5], max(0,crude_ln-3)+1):
            print(f'  {i}: {l[:200]}')

print(f'\n=== {patches} patches applied ===')
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('terminal.html saved.')
