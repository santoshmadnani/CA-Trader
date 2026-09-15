import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace computeLocalChartAiSuggestions
old_fn_start = "function computeLocalChartAiSuggestions(candles){"
old_fn_end = "summary: `CA AI: ${trendlines.length} trendlines, ${horizontal_levels.length} key S/R levels, and ${indicators.length} indicators recommended.`\n    };\n  }"

idx_start = content.find(old_fn_start)
idx_end = content.find(old_fn_end)

if idx_start != -1 and idx_end != -1:
    old_full_fn = content[idx_start:idx_end + len(old_fn_end)]
    new_fn = """function computeLocalChartAiSuggestions(candles){
    if(!candles || candles.length < 10) return { trendlines: [], horizontal_levels: [], indicators: [], summary: 'Insufficient candles for AI chart analysis' };
    const n = candles.length;
    const windowLen = Math.min(n, 70);
    const offset = n - windowLen;
    const highs = candles.map(c => Number(c.high != null ? c.high : c.close != null ? c.close : 0));
    const lows = candles.map(c => Number(c.low != null ? c.low : c.close != null ? c.close : 0));
    const closes = candles.map(c => Number(c.close || 0));
    const timestamps = candles.map(c => c.timestamp || c.ts || '');
    const k = windowLen >= 30 ? 3 : 2;
    const swingHighs = [], swingLows = [];

    for(let i = offset + k; i < n - k; i++){
      let isH = true, isL = true;
      for(let j = 1; j <= k; j++){
        if(highs[i] < highs[i-j] || highs[i] < highs[i+j]) isH = false;
        if(lows[i] > lows[i-j] || lows[i] > lows[i+j]) isL = false;
      }
      if(isH) swingHighs.push(i);
      if(isL) swingLows.push(i);
    }
    if(swingHighs.length < 2){
      const mid = offset + Math.floor(windowLen / 2);
      let h1 = offset, h2 = mid;
      for(let i = offset; i < mid; i++) if(highs[i] > highs[h1]) h1 = i;
      for(let i = mid; i < n; i++) if(highs[i] > highs[h2]) h2 = i;
      if(h2 !== h1) swingHighs.push(h1, h2);
    }
    if(swingLows.length < 2){
      const mid = offset + Math.floor(windowLen / 2);
      let l1 = offset, l2 = mid;
      for(let i = offset; i < mid; i++) if(lows[i] < lows[l1]) l1 = i;
      for(let i = mid; i < n; i++) if(lows[i] < lows[l2]) l2 = i;
      if(l2 !== l1) swingLows.push(l1, l2);
    }

    const trendlines = [];

    // 1. CA AI Dynamic Support Vector (Ascending Support / Base)
    let bestSup = null, bestSupScore = -1e9;
    for(let a = 0; a < swingLows.length; a++){
      const i1 = swingLows[a];
      for(let b = a + 1; b < swingLows.length; b++){
        const i2 = swingLows[b];
        if(i2 - i1 < 4) continue;
        const p1 = lows[i1], p2 = lows[i2];
        const slope = (p2 - p1) / (i2 - i1);
        let touches = 0, violations = 0;
        for(let ci = i1; ci < n; ci++){
          const ep = p1 + slope * (ci - i1);
          const tol = Math.max(ep * 0.003, 0.5);
          if(Math.abs(lows[ci] - ep) <= tol) touches++;
          if(closes[ci] < ep - tol) violations++;
        }
        const score = touches * 3 - violations * 5;
        if(score > bestSupScore){
          bestSupScore = score;
          const endP = p1 + slope * (n - 1 - i1);
          bestSup = { i1, i2: n - 1, p1, p2: Math.max(0.1, endP), slope, touches, t1: timestamps[i1], t2: timestamps[n - 1] };
        }
      }
    }
    if(bestSup){
      const slopePct = bestSup.p1 ? ((bestSup.p2 - bestSup.p1) / bestSup.p1) * 100 : 0;
      trendlines.push({
        name: 'CA AI Dynamic Support Vector',
        type: 'line',
        category: 'ca_ai_dynamic_support',
        i1: bestSup.i1, p1: Number(bestSup.p1.toFixed(2)), t1: bestSup.t1,
        i2: bestSup.i2, p2: Number(bestSup.p2.toFixed(2)), t2: bestSup.t2,
        slope_pct: Number(slopePct.toFixed(2)),
        touches: bestSup.touches,
        color: '#26D9A6',
        description: `CA AI Dynamic Support: ₹${fmt(bestSup.p1)} → ₹${fmt(bestSup.p2)} (${slopePct >= 0 ? '+' : ''}${slopePct.toFixed(2)}%, projected to latest candle)`
      });
    }

    // 2. CA AI Dynamic Resistance Vector (Descending Ceiling / Supply)
    let bestRes = null, bestResScore = -1e9;
    for(let a = 0; a < swingHighs.length; a++){
      const i1 = swingHighs[a];
      for(let b = a + 1; b < swingHighs.length; b++){
        const i2 = swingHighs[b];
        if(i2 - i1 < 4) continue;
        const p1 = highs[i1], p2 = highs[i2];
        const slope = (p2 - p1) / (i2 - i1);
        let touches = 0, violations = 0;
        for(let ci = i1; ci < n; ci++){
          const ep = p1 + slope * (ci - i1);
          const tol = Math.max(ep * 0.003, 0.5);
          if(Math.abs(highs[ci] - ep) <= tol) touches++;
          if(closes[ci] > ep + tol) violations++;
        }
        const score = touches * 3 - violations * 5 + (p1 + p2) * 0.001;
        if(score > bestResScore){
          bestResScore = score;
          const endP = p1 + slope * (n - 1 - i1);
          bestRes = { i1, i2: n - 1, p1, p2: Math.max(0.1, endP), slope, touches, t1: timestamps[i1], t2: timestamps[n - 1] };
        }
      }
    }
    if(bestRes){
      const slopePct = bestRes.p1 ? ((bestRes.p2 - bestRes.p1) / bestRes.p1) * 100 : 0;
      trendlines.push({
        name: 'CA AI Dynamic Resistance Vector',
        type: 'line',
        category: 'ca_ai_dynamic_resistance',
        i1: bestRes.i1, p1: Number(bestRes.p1.toFixed(2)), t1: bestRes.t1,
        i2: bestRes.i2, p2: Number(bestRes.p2.toFixed(2)), t2: bestRes.t2,
        slope_pct: Number(slopePct.toFixed(2)),
        touches: bestRes.touches,
        color: '#FF5C72',
        description: `CA AI Dynamic Resistance: ₹${fmt(bestRes.p1)} → ₹${fmt(bestRes.p2)} (${slopePct >= 0 ? '+' : ''}${slopePct.toFixed(2)}%, projected to latest candle)`
      });
    }

    // 3. CA AI Channel & Breakout Vector
    if(swingLows.length && swingHighs.length){
      const lastPivotL = swingLows[swingLows.length - 1];
      const lastPivotH = swingHighs[swingHighs.length - 1];
      const startIdx = Math.min(lastPivotL, lastPivotH);
      if(n - 1 - startIdx >= 4){
        const p1 = (lows[startIdx] + highs[startIdx]) / 2;
        const p2 = closes[n - 1];
        const slopePct = p1 ? ((p2 - p1) / p1) * 100 : 0;
        trendlines.push({
          name: 'CA AI Channel & Breakout Vector',
          type: 'line',
          category: 'ca_ai_channel',
          i1: startIdx, p1: Number(p1.toFixed(2)), t1: timestamps[startIdx],
          i2: n - 1, p2: Number(p2.toFixed(2)), t2: timestamps[n - 1],
          slope_pct: Number(slopePct.toFixed(2)),
          touches: 2,
          color: '#EFFBF5',
          description: `CA AI Directional Vector: ₹${fmt(p1)} → ₹${fmt(p2)} (${slopePct >= 0 ? '+' : ''}${slopePct.toFixed(2)}%)`
        });
      }
    }

    // Horizontal Levels from visible window
    const recentHighs = highs.slice(offset);
    const recentLows = lows.slice(offset);
    const maxH = Math.max(...recentHighs);
    const minL = Math.min(...recentLows);
    const lastC = closes[closes.length - 1] || 0;
    const pivot = (maxH + minL + lastC) / 3;
    const horizontal_levels = [
      {
        name: 'Key Resistance Line',
        type: 'h',
        price: Number(maxH.toFixed(2)),
        color: '#FF5C72',
        description: `Visible session resistance ceiling at ₹${fmt(maxH)}`
      },
      {
        name: 'Key Support Line',
        type: 'h',
        price: Number(minL.toFixed(2)),
        color: '#26D9A6',
        description: `Visible session support base at ₹${fmt(minL)}`
      },
      {
        name: 'Session Pivot Line',
        type: 'h',
        price: Number(pivot.toFixed(2)),
        color: '#EFFBF5',
        description: `Central inflection pivot at ₹${fmt(pivot)}`
      }
    ];

    // Indicator recommendations
    let rsiVal = 50;
    if(closes.length >= 15){
      let gains = 0, losses = 0;
      for(let i = closes.length - 14; i < closes.length; i++){
        const diff = closes[i] - closes[i-1];
        if(diff >= 0) gains += diff; else losses -= diff;
      }
      const avgG = gains / 14, avgL = Math.max(losses / 14, 1e-6);
      rsiVal = 100 - (100 / (1 + avgG / avgL));
    }
    const indicators = [
      {
        name: 'RSI',
        params: '14',
        color: '#FFB84D',
        value: Number(rsiVal.toFixed(1)),
        reason: `RSI is ${rsiVal.toFixed(1)} (${rsiVal >= 65 ? 'Overbought zone / watch pullback' : rsiVal <= 35 ? 'Oversold zone / watch bounce' : 'Balanced momentum oscillation'})`
      },
      {
        name: 'Supertrend',
        params: '10,3',
        color: lastC >= pivot ? '#26D9A6' : '#FF5C72',
        value: null,
        reason: `Adaptive trailing trend stop (${lastC >= pivot ? 'Bullish posture above pivot' : 'Bearish posture below pivot'})`
      },
      {
        name: 'EMA',
        params: '20',
        color: '#EFFBF5',
        value: null,
        reason: 'Dynamic 20 EMA pullback and trailing trend reference'
      },
      {
        name: 'VWAP',
        params: '',
        color: '#9FE0C2',
        value: null,
        reason: 'Volume Weighted Average Price institutional benchmark'
      },
      {
        name: 'Bollinger Bands',
        params: '20,2',
        color: '#7C8598',
        value: null,
        reason: 'Volatility squeeze envelope and standard deviation band'
      }
    ];

    return {
      trendlines,
      horizontal_levels,
      indicators,
      summary: `CA AI: ${trendlines.length} dynamic visible trendlines, ${horizontal_levels.length} key S/R levels, and ${indicators.length} indicators recommended.`
    };
  }"""
    content = content.replace(old_full_fn, new_fn, 1)
    print("✓ Replaced computeLocalChartAiSuggestions with visible window & dynamic path")
else:
    print(f"⚠ Could not find computeLocalChartAiSuggestions bounds: start={idx_start}, end={idx_end}")

# 2. Update Edit UI Controller
old_edit_start = "// ===== EDIT UI SYSTEM ====="
old_edit_end = "// ===== SIDEBAR RESIZE ====="
idx_e1 = content.find(old_edit_start)
idx_e2 = content.find(old_edit_end)

if idx_e1 != -1 and idx_e2 != -1:
    old_edit_block = content[idx_e1:idx_e2]
    new_edit_block = """// ===== EDIT UI SYSTEM =====
let caEditMode = false;
const caEditBar = document.createElement('div');
caEditBar.className = 'ca-edit-bar';
caEditBar.innerHTML = `
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
    <span style="font-weight:700;color:var(--gold);">✦ Edit UI Mode</span>
    <span class="muted" style="font-size:11px;">Drag cards (⠿) to reposition · Use 1 Col / 2 Col / Full to resize boxes</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <button id="caToggleCompactButtons" class="btn small" style="background:var(--surface-2);color:var(--text);border:1px solid var(--border-soft);font-size:11px;">🔘 Compact Buttons</button>
    <button id="caResetLayout" class="btn ghost small" style="font-size:11px;">↺ Reset Layout</button>
    <button id="caEditDone" style="background:#0B2A1E;color:#26D9A6;border:none;padding:5px 14px;border-radius:6px;font-weight:700;cursor:pointer;font-size:11.5px;">✓ Done</button>
  </div>
`;
document.body.appendChild(caEditBar);

// Initialize compact buttons mode from localStorage
if(localStorage.getItem('ca_compact_buttons') === '1'){
  document.body.classList.add('compact-ui-buttons');
  const btn = document.getElementById('caToggleCompactButtons');
  if(btn) btn.textContent = '🔘 Normal Buttons';
}

function applySavedCardLayouts(){
  try {
    const saved = JSON.parse(localStorage.getItem('ca_card_layouts') || '{}');
    document.querySelectorAll('.card[id]').forEach(card => {
      const info = saved[card.id];
      if(info){
        card.classList.remove('ca-col-1', 'ca-col-2', 'ca-col-full', 'card-compact');
        if(info.colClass) card.classList.add(info.colClass);
        if(info.isCompact) card.classList.add('card-compact');
      }
    });
  } catch(_) {}
}

function saveCardLayouts(){
  try {
    const saved = {};
    document.querySelectorAll('.card[id]').forEach(card => {
      let colClass = '';
      if(card.classList.contains('ca-col-1')) colClass = 'ca-col-1';
      else if(card.classList.contains('ca-col-2')) colClass = 'ca-col-2';
      else if(card.classList.contains('ca-col-full')) colClass = 'ca-col-full';
      const isCompact = card.classList.contains('card-compact');
      if(colClass || isCompact){
        saved[card.id] = { colClass, isCompact };
      }
    });
    localStorage.setItem('ca_card_layouts', JSON.stringify(saved));
  } catch(_) {}
}

function enableEditMode(){
  caEditMode = true;
  document.body.classList.add('ca-edit-mode');
  caEditBar.classList.add('active');

  const btn = document.getElementById('caToggleCompactButtons');
  if(btn){
    btn.textContent = document.body.classList.contains('compact-ui-buttons') ? '🔘 Normal Buttons' : '🔘 Compact Buttons';
  }

  // Add drag handles & resize controls to cards
  document.querySelectorAll('.panel.active .card, #panel-charts .card').forEach((card, idx) => {
    if(!card.id) card.id = 'ca-card-auto-' + idx;

    if(!card.querySelector('.ca-drag-handle')){
      const handle = document.createElement('div');
      handle.className = 'ca-drag-handle';
      handle.title = 'Drag to reposition card';
      handle.innerHTML = '⠿';
      handle.draggable = true;

      handle.ondragstart = (e) => {
        e.dataTransfer.setData('text/plain', card.id);
        card.classList.add('ca-card-dragging');
      };
      handle.ondragend = () => {
        card.classList.remove('ca-card-dragging');
        saveCardLayouts();
      };
      card.appendChild(handle);
    }

    if(!card.querySelector('.ca-card-size-ctrl')){
      const ctrl = document.createElement('div');
      ctrl.className = 'ca-card-size-ctrl';
      ctrl.innerHTML = `
        <button type="button" class="ca-size-btn" data-ca-size="1col" title="Single Column">1 Col</button>
        <button type="button" class="ca-size-btn" data-ca-size="2col" title="Half Width (2 Columns)">2 Col</button>
        <button type="button" class="ca-size-btn" data-ca-size="full" title="Full Width">Full</button>
        <button type="button" class="ca-size-btn" data-ca-size="compact" title="Compact Padding">Tighter</button>
      `;
      ctrl.querySelectorAll('[data-ca-size]').forEach(b => {
        b.onclick = (e) => {
          e.stopPropagation();
          const sz = b.dataset.caSize;
          if(sz === '1col'){
            card.classList.toggle('ca-col-1');
            card.classList.remove('ca-col-2', 'ca-col-full');
          } else if(sz === '2col'){
            card.classList.toggle('ca-col-2');
            card.classList.remove('ca-col-1', 'ca-col-full');
          } else if(sz === 'full'){
            card.classList.toggle('ca-col-full');
            card.classList.remove('ca-col-1', 'ca-col-2');
          } else if(sz === 'compact'){
            card.classList.toggle('card-compact');
          }
          saveCardLayouts();
        };
      });
      card.appendChild(ctrl);
    }

    card.ondragover = (e) => { e.preventDefault(); };
    card.ondrop = (e) => {
      e.preventDefault();
      const dragging = document.querySelector('.ca-card-dragging');
      if(dragging && dragging !== card && card.parentNode === dragging.parentNode){
        card.parentNode.insertBefore(dragging, card);
        saveCardLayouts();
      }
    };
  });

  document.getElementById('userMenu')?.classList.remove('open');
}

function disableEditMode(){
  caEditMode = false;
  document.body.classList.remove('ca-edit-mode');
  caEditBar.classList.remove('active');
  saveCardLayouts();
  toast('Edit UI mode closed · Layout saved');
}

document.getElementById('caEditDone')?.addEventListener('click', disableEditMode);
document.getElementById('editUIBtn')?.addEventListener('click', enableEditMode);

document.getElementById('caToggleCompactButtons')?.addEventListener('click', () => {
  const isCompact = document.body.classList.toggle('compact-ui-buttons');
  localStorage.setItem('ca_compact_buttons', isCompact ? '1' : '0');
  const btn = document.getElementById('caToggleCompactButtons');
  if(btn) btn.textContent = isCompact ? '🔘 Normal Buttons' : '🔘 Compact Buttons';
  toast(isCompact ? 'Compact buttons enabled across UI' : 'Standard button sizing restored');
});

document.getElementById('caResetLayout')?.addEventListener('click', () => {
  if(!confirm('Reset all customized card sizes and layouts to default?')) return;
  localStorage.removeItem('ca_card_layouts');
  document.querySelectorAll('.card').forEach(card => {
    card.classList.remove('ca-col-1', 'ca-col-2', 'ca-col-full', 'card-compact');
    card.style.width = '';
    card.style.height = '';
  });
  toast('UI layouts reset to defaults');
});

// Auto-restore saved card layouts on load
applySavedCardLayouts();

"""
    content = content.replace(old_edit_block, new_edit_block, 1)
    print("✓ Replaced Edit UI controller with sizing, compact buttons, drag-reorder, and persistence")
else:
    print(f"⚠ Could not find Edit UI block bounds: idx_e1={idx_e1}, idx_e2={idx_e2}")

# 3. Remove duplicate Edit UI listener at lines 5010-5054
old_dupe_edit_listener = """// 7. Edit UI Drag & Drop and Sizing Wiring
document.getElementById('editUIBtn')?.addEventListener('click', function(){
  document.body.classList.toggle('ca-edit-mode');
  const isEditing = document.body.classList.contains('ca-edit-mode');
  showLiveToast('✦ Edit UI Mode', isEditing ? 'Drag handles (⠿) to reorder, use 1 Col / 50% / 100% to resize' : 'Edit mode exited and layout saved', isEditing ? 'gold' : 'buy');
  if(isEditing){
    document.querySelectorAll('.card').forEach(card => {
      if(!card.querySelector('.ca-drag-handle')){
        const handle = document.createElement('div');
        handle.className = 'ca-drag-handle';
        handle.innerHTML = '⠿';
        handle.title = 'Drag to reorder card';
        handle.draggable = true;
        handle.ondragstart = (e) => {
          e.dataTransfer.setData('text/plain', card.id || 'card');
          card.classList.add('ca-card-dragging');
        };
        handle.ondragend = () => card.classList.remove('ca-card-dragging');
        card.appendChild(handle);
      }
      if(!card.querySelector('.ca-size-controls')){
        const ctrl = document.createElement('div');
        ctrl.className = 'ca-size-controls';
        ctrl.innerHTML = `
          <button class="ca-size-btn" title="Single column">1 Col</button>
          <button class="ca-size-btn" title="Half width">◫ 50%</button>
          <button class="ca-size-btn" title="Full width">▬ 100%</button>
        `;
        const btns = ctrl.querySelectorAll('.ca-size-btn');
        btns[0].onclick = (e) => { e.stopPropagation(); card.style.gridColumn = 'span 1'; };
        btns[1].onclick = (e) => { e.stopPropagation(); card.style.gridColumn = 'span 6'; };
        btns[2].onclick = (e) => { e.stopPropagation(); card.style.gridColumn = '1 / -1'; };
        card.appendChild(ctrl);
      }
      card.ondragover = (e) => { e.preventDefault(); };
      card.ondrop = (e) => {
        e.preventDefault();
        const dragging = document.querySelector('.ca-card-dragging');
        if(dragging && dragging !== card && card.parentNode === dragging.parentNode){
          card.parentNode.insertBefore(dragging, card);
        }
      };
    });
  }
});"""

if old_dupe_edit_listener in content:
    content = content.replace(old_dupe_edit_listener, "// Duplicate editUIBtn listener removed - handled centrally by Edit UI controller", 1)
    print("✓ Removed duplicate editUIBtn listener")
else:
    print("⚠ Could not find old_dupe_edit_listener")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Batch 2 completed successfully.")

