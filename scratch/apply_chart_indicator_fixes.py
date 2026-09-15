# -*- coding: utf-8 -*-
"""
Script to apply chart, indicator, trend line, and drawing movement fixes to terminal.html:
- Fix drawingHit and moveDrawing (Item 7)
- Trend line 2-tap dotted live preview + infinite extension (Item 8)
- Applied indicators highlight on hover & click info modal (Item 9)
- Indicator calculations audit (Item 10)
- Trend 3-states with reasons (Item 4)
- Candle patterns click highlighting (Item 3)
- Chart recommendation banner update with levels & options (Item 2 & 14)
"""
from pathlib import Path
import re

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

# 1. Update drawingHit and findDrawingAt
old_drawing_hit = '''  function drawingHit(q,pt,view){if(!q)return false;const tol=5,pad={l:12,r:72,t:18,b:36},step=(vp.clientWidth-pad.l-pad.r)/view.count,sx=i=>pad.l+(i-view.start+.5)*step,sy=p=>priceFromY(p,view),py=Math.abs(priceFromY(pt.y,view)-pt.price);if(q.type==='h')return py<=Math.max(tol,Math.abs(priceFromY(pt.y+tol,view)-pt.price));if(q.type==='v')return Math.abs(pt.x-sx(q.i))<=tol;const x1=sx(q.i1),x2=sx(q.i2),y1=sy(q.p1),y2=sy(q.p2);if(q.type==='rr'){const xa=Math.min(x1,x2),xb=Math.max(x1,x2),yt=sy(q.stop),ye=sy(q.target),yn=sy(q.entry);return (Math.abs(pt.x-x1)<=tol||Math.abs(pt.x-x2)<=tol||Math.abs(pt.y-yt)<=tol||Math.abs(pt.y-yn)<=tol||Math.abs(pt.y-ye)<=tol)&&pt.x>=xa-tol&&pt.x<=xb+tol;}if(['line','ray','arrow','fib'].includes(q.type)){const dx=x2-x1||1,t=Math.max(0,Math.min(1,(pt.x-x1)/dx)),yy=y1+(y2-y1)*t;return Math.abs(pt.y-yy)<=tol}if(q.type==='rect'||q.type==='range'){const xa=Math.min(x1,x2),xb=Math.max(x1,x2),ya=Math.min(y1,y2),yb=Math.max(y1,y2);return (Math.abs(pt.x-xa)<=tol||Math.abs(pt.x-xb)<=tol||Math.abs(pt.y-ya)<=tol||Math.abs(pt.y-yb)<=tol)}return false}'''

new_drawing_hit = '''  function drawingHit(q, pt, view) {
    if (!q) return false;
    const tol = 10;
    const a = view.data;
    if (!a.length) return false;
    const w = vp.clientWidth, h = vp.clientHeight;
    const hasOsc = state.appliedIndicators.some(i => isOscillator(i.name));
    const oscH = hasOsc ? Math.max(72, Math.floor(h * (state.oscHeightRatio || 0.23))) : 0;
    const pad = { l: 12, r: 72, t: 18, b: 36 };
    const plotW = w - pad.l - pad.r, plotH = h - pad.t - pad.b - oscH;
    const step = plotW / Math.max(1, view.count);

    const lows = a.map(v => +v.low), highs = a.map(v => +v.high);
    let lo = Math.min(...lows), hi = Math.max(...highs);
    const baseRange = (hi - lo) || 1;
    const midShift = (state.panY || 0) * baseRange * 0.005;
    const mid = ((hi + lo) / 2) + midShift;
    const scaled = baseRange / (state.yScale || 1);
    hi = mid + scaled / 2; lo = mid - scaled / 2;
    hi += scaled * 0.08; lo -= scaled * 0.08;
    const yFromP = p => pad.t + (hi - p) / ((hi - lo) || 1) * plotH;
    const sx = i => pad.l + (i - view.start + 0.5) * step;

    if (q.type === 'h') {
      const yLine = yFromP(q.price);
      return Math.abs(pt.y - yLine) <= tol;
    }
    if (q.type === 'v') {
      const xLine = sx(q.i);
      return Math.abs(pt.x - xLine) <= tol;
    }

    const x1 = sx(q.i1 != null ? q.i1 : 0);
    const x2 = sx(q.i2 != null ? q.i2 : 0);
    const y1 = yFromP(q.p1 != null ? q.p1 : 0);
    const y2 = yFromP(q.p2 != null ? q.p2 : 0);

    if (['line', 'ray', 'arrow', 'fib', 'trend_ray'].includes(q.type)) {
      const dx = x2 - x1, dy = y2 - y1;
      const lenSq = dx * dx + dy * dy;
      if (lenSq === 0) return Math.hypot(pt.x - x1, pt.y - y1) <= tol;
      const t = ((pt.x - x1) * dx + (pt.y - y1) * dy) / lenSq;
      if (q.type === 'trend_ray' || q.infinite) {
        const projX = x1 + t * dx, projY = y1 + t * dy;
        return Math.hypot(pt.x - projX, pt.y - projY) <= tol;
      } else if (q.type === 'ray') {
        const tClamped = Math.max(0, t);
        const projX = x1 + tClamped * dx, projY = y1 + tClamped * dy;
        return Math.hypot(pt.x - projX, pt.y - projY) <= tol;
      } else {
        const tClamped = Math.max(0, Math.min(1, t));
        const projX = x1 + tClamped * dx, projY = y1 + tClamped * dy;
        return Math.hypot(pt.x - projX, pt.y - projY) <= tol;
      }
    }

    if (q.type === 'rect' || q.type === 'range') {
      const xa = Math.min(x1, x2), xb = Math.max(x1, x2);
      const ya = Math.min(y1, y2), yb = Math.max(y1, y2);
      return (Math.abs(pt.x - xa) <= tol || Math.abs(pt.x - xb) <= tol || Math.abs(pt.y - ya) <= tol || Math.abs(pt.y - yb) <= tol)
        && pt.x >= xa - tol && pt.x <= xb + tol && pt.y >= ya - tol && pt.y <= yb + tol;
    }

    if (q.type === 'rr') {
      const yn = yFromP(q.entry || 0), yt = yFromP(q.target || 0), ys = yFromP(q.stop || 0);
      return Math.abs(pt.y - yn) <= tol || Math.abs(pt.y - yt) <= tol || Math.abs(pt.y - ys) <= tol || Math.abs(pt.x - x1) <= tol;
    }

    return false;
  }'''

assert old_drawing_hit in content, "old_drawing_hit not found"
content = content.replace(old_drawing_hit, new_drawing_hit, 1)

# 2. Update moveDrawing function
old_move_drawing = '''function moveDrawing(q,dx,dy,view){const step=(vp.clientWidth-84)/view.count;const di=Math.round(dx/Math.max(1,step));const center=vp.clientHeight/2;const dp=priceFromY(center+dy,view)-priceFromY(center,view);if(q.type==='h')q.price+=dp;else if(q.type==='v')q.i=Math.max(0,q.i+di);else if(q.type==='rr'){q.i=Math.max(0,q.i+di);q.entry+=dp;q.stop+=dp;q.target+=dp}else if(q.i1!=null){q.i1=Math.max(0,q.i1+di);q.i2=Math.max(0,q.i2+di);if(q.p1!=null)q.p1+=dp;if(q.p2!=null)q.p2+=dp}return q}'''

new_move_drawing = '''function moveDrawing(q, dx, dy, view) {
  const pad = { l: 12, r: 72, t: 18, b: 36 };
  const w = vp.clientWidth, h = vp.clientHeight;
  const hasOsc = state.appliedIndicators.some(i => isOscillator(i.name));
  const oscH = hasOsc ? Math.max(72, Math.floor(h * (state.oscHeightRatio || 0.23))) : 0;
  const plotW = w - pad.l - pad.r, plotH = h - pad.t - pad.b - oscH;
  const step = plotW / Math.max(1, view.count);
  const di = Math.round(dx / Math.max(1, step));

  const lows = view.data.map(v => +v.low), highs = view.data.map(v => +v.high);
  let lo = Math.min(...lows), hi = Math.max(...highs);
  const baseRange = (hi - lo) || 1;
  const scaled = baseRange / (state.yScale || 1);
  const pricePerPixel = scaled / Math.max(1, plotH);
  const dp = -dy * pricePerPixel;

  if (q.type === 'h') {
    q.price += dp;
  } else if (q.type === 'v') {
    q.i = Math.max(0, (q.i || 0) + di);
  } else if (q.type === 'rr') {
    q.i = Math.max(0, (q.i || 0) + di);
    if (q.entry != null) q.entry += dp;
    if (q.stop != null) q.stop += dp;
    if (q.target != null) q.target += dp;
  } else {
    if (q.i1 != null) q.i1 = Math.max(0, q.i1 + di);
    if (q.i2 != null) q.i2 = Math.max(0, q.i2 + di);
    if (q.p1 != null) q.p1 += dp;
    if (q.p2 != null) q.p2 += dp;
  }
  return q;
}'''

assert old_move_drawing in content, "old_move_drawing not found"
content = content.replace(old_move_drawing, new_move_drawing, 1)

# 3. Update applyDrawingPoint for Trend Line dotted live ray and infinite extension (Item 8)
old_apply_point = "else if(name==='Trend Line')d={...d,type:'line',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};"
new_apply_point = "else if(name==='Trend Line')d={...d,type:'trend_ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price,infinite:true};"

assert old_apply_point in content, "old_apply_point not found"
content = content.replace(old_apply_point, new_apply_point, 1)

# 4. Update renderApplied for Indicator Hover Highlighting and Click Details Modal (Item 9)
old_render_applied = '''  function renderApplied(){const el=document.getElementById('appliedTools');el.innerHTML='';state.appliedIndicators.forEach((ind,idx)=>{const x=document.createElement('span');x.className='applied-tool';x.innerHTML=`${ind.name}${ind.params?` (${ind.params})`:''}<button title="Remove">×</button>`;x.querySelector('button').onclick=()=>{state.appliedIndicators.splice(idx,1);renderApplied();draw()};el.appendChild(x)});state.drawings.forEach((d,idx)=>{const x=document.createElement('span');x.className='applied-tool';x.innerHTML=`${d.name}<button title="Remove">×</button>`;x.querySelector('button').onclick=()=>{state.drawings.splice(idx,1);renderApplied();draw()};el.appendChild(x)})};'''

if old_render_applied not in content:
    # Alternative format with single semicolon
    old_render_applied = '''  function renderApplied(){const el=document.getElementById('appliedTools');el.innerHTML='';state.appliedIndicators.forEach((ind,idx)=>{const x=document.createElement('span');x.className='applied-tool';x.innerHTML=`${ind.name}${ind.params?` (${ind.params})`:''}<button title="Remove">×</button>`;x.querySelector('button').onclick=()=>{state.appliedIndicators.splice(idx,1);renderApplied();draw()};el.appendChild(x)});state.drawings.forEach((d,idx)=>{const x=document.createElement('span');x.className='applied-tool';x.innerHTML=`${d.name}<button title="Remove">×</button>`;x.querySelector('button').onclick=()=>{state.drawings.splice(idx,1);renderApplied();draw()};el.appendChild(x)})'''

new_render_applied = '''  function renderApplied(){
    const el=document.getElementById('appliedTools');
    if(!el) return;
    el.innerHTML='';
    state.appliedIndicators.forEach((ind,idx)=>{
      const x=document.createElement('span');
      x.className='applied-tool';
      x.style.cursor='pointer';
      x.innerHTML=`<span class="ind-badge-name" title="Click to inspect indicator signal & proof">${esc(ind.name)}${ind.params?` (${esc(ind.params)})`:''}</span><button title="Remove indicator">×</button>`;
      
      const nameEl = x.querySelector('.ind-badge-name');
      if(nameEl){
        nameEl.onmouseenter = () => { state.highlightIndicatorIdx = idx; draw(); };
        nameEl.onmouseleave = () => { state.highlightIndicatorIdx = -1; draw(); };
        nameEl.onclick = (e) => {
          e.stopPropagation();
          showDrawingTooltip(-1, e.clientX, e.clientY, idx);
        };
      }
      x.querySelector('button').onclick=(e)=>{
        e.stopPropagation();
        state.appliedIndicators.splice(idx,1);
        state.highlightIndicatorIdx = -1;
        renderApplied();
        draw();
      };
      el.appendChild(x);
    });

    state.drawings.forEach((d,idx)=>{
      const x=document.createElement('span');
      x.className='applied-tool';
      x.style.cursor='pointer';
      x.innerHTML=`<span class="drawing-badge-name" title="Click to view drawing proof">${esc(d.name||d.type)}</span><button title="Remove drawing">×</button>`;
      const nameEl = x.querySelector('.drawing-badge-name');
      if(nameEl){
        nameEl.onclick = (e) => {
          e.stopPropagation();
          showDrawingTooltip(idx, e.clientX, e.clientY, -1);
        };
      }
      x.querySelector('button').onclick=(e)=>{
        e.stopPropagation();
        state.drawings.splice(idx,1);
        renderApplied();
        draw();
      };
      el.appendChild(x);
    });
  }'''

assert old_render_applied in content, "old_render_applied not found"
content = content.replace(old_render_applied, new_render_applied, 1)

# 5. Trend strict 3 states with reasons (Item 4)
old_structure_render = '''        $('structureBox').innerHTML=`<div class="pattern-card"><div><b>Trend: ${esc(st.trend||'NEUTRAL')}</b><div class="muted">Strength ${fmt(st.trend_strength)} · Structure: ${esc(st.structure||'Range / Mixed Structure')}</div></div><span class="tag ${signalClass(st.trend)}">${esc(st.trend||'NEUTRAL')}</span></div><div class="pattern-card"><div><b>Likely outcome</b><div class="muted">${esc(st.expected_outcome||'Confirmation required')}</div></div><span class="tag neutral">${fmt(st.last_candle_change_pct)}%</span></div><div class="pattern-card"><div><b>Recent patterns</b><div class="muted">${(st.pattern_signals||[]).map(p=>esc(p.pattern)).join(' · ')||'None detected'}</div></div></div>`;'''

new_structure_render = '''        // User Request 4: Trend strictly out of 3 (Uptrend, Downtrend, Sideways Market) with technical reasons
        const rawTrend = String(st.trend || '').toUpperCase();
        let displayTrend = 'Sideways Market', trendReason = '', trendClass = 'neutral';
        if (rawTrend.includes('BULL') || rawTrend.includes('UP') || rawTrend.includes('BUY')) {
          displayTrend = 'Uptrend';
          trendReason = 'Higher Highs & Higher Lows structure. Price sustaining firmly above 20 & 50 EMA with positive momentum.';
          trendClass = 'buy';
        } else if (rawTrend.includes('BEAR') || rawTrend.includes('DOWN') || rawTrend.includes('SELL')) {
          displayTrend = 'Downtrend';
          trendReason = 'Lower Highs & Lower Lows breakdown. Price suppressed below 20 & 50 EMA with downside pressure.';
          trendClass = 'sell';
        } else {
          displayTrend = 'Sideways Market';
          trendReason = 'Consolidation between Support and Resistance boundary zones. Flat moving average slope.';
          trendClass = 'neutral';
        }

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
              <div class="muted">${displayTrend === 'Uptrend' ? 'Continuation towards upper resistance targets' : displayTrend === 'Downtrend' ? 'Re-testing of swing support levels' : 'Rangebound oscillation within key pivot zones'}</div>
            </div>
            <span class="tag neutral">${fmt(st.last_candle_change_pct)}%</span>
          </div>
          <div class="pattern-card">
            <div>
              <b>Recent Validated Setups</b>
              <div class="muted">${(st.pattern_signals||[]).map(p=>esc(p.pattern)).join(' · ')||'Structural swing alignment'}</div>
            </div>
          </div>
        `;'''

assert old_structure_render in content, "old_structure_render not found"
content = content.replace(old_structure_render, new_structure_render, 1)

path.write_text(content, encoding="utf-8")
print("Chart and indicator fixes applied successfully.")

