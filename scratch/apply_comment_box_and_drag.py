# -*- coding: utf-8 -*-
import os

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update CSS for drawing-tooltip
old_css = """.drawing-tooltip{position:fixed;z-index:500;display:none;max-width:260px;background:var(--surface-3);border:1px solid var(--border);border-radius:6px;padding:6px 8px;box-shadow:0 8px 22px rgba(0,0,0,.24);font:10px var(--font-mono);color:var(--text);pointer-events:none}.drawing-tooltip b{font-family:var(--font-body)}.chart-area-pro.pan-mode{cursor:grab}.chart-area-pro.pan-mode:active{cursor:grabbing}.chart-area-pro.drawing-hover{cursor:pointer}@keyframes caAlertIn{from{opacity:0;transform:translateX(12px)}to{opacity:1;transform:none}}"""

new_css = """.drawing-tooltip{position:fixed;z-index:9999;display:none;min-width:220px;max-width:320px;background:var(--surface-2);border:1px solid var(--border);border-left:3.5px solid var(--gold);border-radius:8px;padding:9px 12px;box-shadow:0 12px 30px rgba(0,0,0,.45);font:11px var(--font-mono);color:var(--text);pointer-events:none;line-height:1.4;backdrop-filter:blur(6px)}.drawing-tooltip::before{content:'';position:absolute;left:-7px;top:14px;width:0;height:0;border-top:6px solid transparent;border-bottom:6px solid transparent;border-right:7px solid var(--gold)}.drawing-tooltip.buy{border-left-color:var(--buy)}.drawing-tooltip.buy::before{border-right-color:var(--buy)}.drawing-tooltip.sell{border-left-color:var(--sell)}.drawing-tooltip.sell::before{border-right-color:var(--sell)}.drawing-tooltip .dt-title{display:flex;align-items:center;gap:6px;font-family:var(--font-display);font-weight:700;font-size:12px;color:var(--text);margin-bottom:3px}.drawing-tooltip .dt-params{font-size:10.5px;color:var(--text-dim);margin-bottom:4px}.drawing-tooltip .dt-signal-box{margin-top:6px;padding:6px 8px;border-radius:6px;border:1px solid rgba(255,255,255,.08);font-size:10.5px;display:flex;flex-direction:column;gap:2px}.drawing-tooltip .dt-signal-box.buy{background:rgba(38,217,166,.12);border-color:rgba(38,217,166,.35);color:var(--buy)}.drawing-tooltip .dt-signal-box.sell{background:rgba(255,92,114,.12);border-color:rgba(255,92,114,.35);color:var(--sell)}.drawing-tooltip .dt-signal-tag{font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:0.5px}.drawing-tooltip .dt-signal-info{font-size:10px;color:var(--text);line-height:1.3}.chart-area-pro.pan-mode{cursor:grab}.chart-area-pro.pan-mode:active{cursor:grabbing}.chart-area-pro.drawing-hover{cursor:pointer}@keyframes caAlertIn{from{opacity:0;transform:translateX(12px)}to{opacity:1;transform:none}}"""

assert old_css in html, "old_css not found"
html = html.replace(old_css, new_css, 1)

# 2. Update pointermove & pointerdown for drawing drag
old_pointermove = """    if(state.dragDrawing){
      const md=Math.hypot(e.clientX-state.dragDrawing.startX,e.clientY-state.dragDrawing.startY);
      if(md>=4) state.dragDrawing.moved=true;
      if(!state.dragDrawing.moved){ updateCross(e); return; }
      const dx=e.clientX-state.dragDrawing.x,dy=e.clientY-state.dragDrawing.y;
      moveDrawing(state.drawings[state.dragDrawing.idx],dx,dy,getView());
      state.dragDrawing.x=e.clientX; state.dragDrawing.y=e.clientY;
      vp.classList.add('drawing-hover');
      showDrawingTooltip(state.dragDrawing.idx,e.clientX,e.clientY);
      draw();
      return;
    }"""

new_pointermove = """    if(state.dragDrawing){
      const totalDx=e.clientX-state.dragDrawing.startX, totalDy=e.clientY-state.dragDrawing.startY;
      if(Math.hypot(totalDx,totalDy)>=3) state.dragDrawing.moved=true;
      if(!state.dragDrawing.moved){ updateCross(e); return; }
      const view=getView();
      const step=(vp.clientWidth-84)/Math.max(1,view.count);
      const di=Math.round(totalDx/Math.max(1,step));
      const center=vp.clientHeight/2;
      const dp=priceFromY(center+totalDy,view)-priceFromY(center,view);
      const orig=state.dragDrawing.orig;
      const q=state.drawings[state.dragDrawing.idx];
      if(q&&orig){
        if(orig.type==='h') q.price=orig.price+dp;
        else if(orig.type==='v') q.i=Math.max(0,orig.i+di);
        else if(orig.type==='rr'){
          q.i=Math.max(0,orig.i+di);
          q.entry=orig.entry+dp;
          q.stop=orig.stop+dp;
          q.target=orig.target+dp;
        } else {
          if(orig.i1!=null) q.i1=Math.max(0,orig.i1+di);
          if(orig.i2!=null) q.i2=Math.max(0,orig.i2+di);
          if(orig.p1!=null) q.p1=orig.p1+dp;
          if(orig.p2!=null) q.p2=orig.p2+dp;
        }
      }
      vp.classList.add('drawing-hover');
      vp.style.cursor='move';
      showDrawingTooltip(state.dragDrawing.idx,e.clientX,e.clientY);
      draw();
      return;
    }"""

assert old_pointermove in html, "old_pointermove not found"
html = html.replace(old_pointermove, new_pointermove, 1)

old_pointerdown = """    const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:findDrawingAt(x,y);
    if(hit>=0&&!state.panArmed&&!state.yPanArmed&&state.interactionMode!=='pan'){
      state.dragDrawing={idx:hit,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,moved:false};
      showDrawingTooltip(hit,e.clientX,e.clientY);
      vp.setPointerCapture(e.pointerId);
      return;
    }"""

new_pointerdown = """    const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:findDrawingAt(x,y);
    if(hit>=0&&!state.panArmed&&!state.yPanArmed&&state.interactionMode!=='pan'){
      state.dragDrawing={idx:hit,startX:e.clientX,startY:e.clientY,orig:JSON.parse(JSON.stringify(state.drawings[hit])),moved:false};
      showDrawingTooltip(hit,e.clientX,e.clientY);
      vp.setPointerCapture(e.pointerId);
      return;
    }"""

assert old_pointerdown in html, "old_pointerdown not found"
html = html.replace(old_pointerdown, new_pointerdown, 1)

# Cursor update on hover in pointermove
old_hover = """    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;
    state.hoverDrawing=hit;
    if(hit>=0){ vp.classList.add('drawing-hover'); showDrawingTooltip(hit,e.clientX,e.clientY); }
    else if(ih>=0){ vp.classList.add('drawing-hover'); showDrawingTooltip(-1,e.clientX,e.clientY,ih); }
    else { vp.classList.remove('drawing-hover'); showDrawingTooltip(-1,0,0); }"""

new_hover = """    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;
    state.hoverDrawing=hit;
    if(hit>=0){ vp.classList.add('drawing-hover'); vp.style.cursor='move'; showDrawingTooltip(hit,e.clientX,e.clientY); }
    else if(ih>=0){ vp.classList.add('drawing-hover'); vp.style.cursor='crosshair'; showDrawingTooltip(-1,e.clientX,e.clientY,ih); }
    else { vp.classList.remove('drawing-hover'); vp.style.cursor=state.interactionMode==='pan'?'grab':'crosshair'; showDrawingTooltip(-1,0,0); }"""

assert old_hover in html, "old_hover not found"
html = html.replace(old_hover, new_hover, 1)

# 3. Update drawingHit, indicatorHit, showDrawingTooltip
old_tooltip_block = """function indicatorHit(x,y){const view=getView(),a=view.data;if(!a.length||!state.appliedIndicators.length)return -1;const step=(vp.clientWidth-84)/view.count;let best=-1,dist=Infinity;state.appliedIndicators.forEach((ind,idx)=>{const series=appliedOverlaySeries(ind.name,ind.params);if(!series)return;const i=Math.max(0,Math.min(view.count-1,Math.floor((x-12)/Math.max(1,step))));const val=series[view.start+i];if(val==null)return;const py=indicatorValueToY(val,view),d=Math.abs(y-py);if(d<dist){dist=d;best=idx}});return dist<=10?best:-1}
function showDrawingTooltip(idx,x,y,indicatorIdx=-1){const el=document.getElementById('drawingTooltip');if(!el)return;if(idx<0&&indicatorIdx<0){el.style.display='none';return}let html='';if(indicatorIdx>=0){const ind=state.appliedIndicators[indicatorIdx],series=appliedOverlaySeries(ind.name,ind.params),view=getView(),r=vp.getBoundingClientRect(),i=Math.max(0,Math.min(view.count-1,Math.floor((x-r.left-12)/Math.max(1,(vp.clientWidth-84)/view.count)))),val=series?.[view.start+i];html=`<b>${esc(ind.name)}</b><div style="margin-top:3px">Parameters ${esc(ind.params||'Default')} · Value ${fmt(val)}</div><div style="margin-top:3px">LTP ${fmt(currentLtp())}</div>`}else{const q=state.drawings[idx];html=`<b>${esc(q.name||q.type)}</b><div style="margin-top:3px">${esc(drawingParams(q))}</div><div style="margin-top:3px">LTP ${fmt(currentLtp())}</div><div style="margin-top:3px;color:var(--text-faint)">Click + drag to move</div>`}el.innerHTML=html;el.style.left=Math.min(window.innerWidth-300,Math.max(8,x+12))+'px';el.style.top=Math.min(window.innerHeight-110,Math.max(8,y+12))+'px';el.style.display='block'}"""

new_tooltip_block = """function indicatorHit(x,y){
  const view=getView(),a=view.data;
  if(!a.length||!state.appliedIndicators.length)return -1;
  const w=vp.clientWidth,h=vp.clientHeight;
  const hasOsc=state.appliedIndicators.some(i=>isOscillator(i.name));
  const oscH=hasOsc?Math.max(72,Math.floor(h*0.23)):0;
  const pad={l:12,r:72,t:18,b:36};
  const plotW=w-pad.l-pad.r,plotH=h-pad.t-pad.b-oscH;
  const step=plotW/view.count;
  const i=Math.max(0,Math.min(view.count-1,Math.floor((x-pad.l)/Math.max(1,step))));

  const lows=a.map(v=>+v.low),highs=a.map(v=>+v.high);
  let lo=Math.min(...lows),hi=Math.max(...highs);
  const baseRange=(hi-lo)||1;
  const midShift=(state.panY||0)*baseRange*0.005;
  const mid=((hi+lo)/2)+midShift;
  const scaled=baseRange/state.yScale;
  hi=mid+scaled/2;lo=mid-scaled/2;
  hi+=scaled*.08;lo-=scaled*.08;
  const yPrice=p=>pad.t+(hi-p)/((hi-lo)||1)*plotH;
  const oscTop=pad.t+plotH+8,oscPlotH=Math.max(20,oscH-16);

  let best=-1,dist=Infinity;
  state.appliedIndicators.forEach((ind,idx)=>{
    const series=appliedOverlaySeries(ind.name,ind.params);
    if(!series)return;
    const isOsc=isOscillator(ind.name);
    const val=series[view.start+i];
    if(val==null)return;

    if(isOsc){
      if(typeof val==='number'){
        const py=oscTop+(1-Math.max(0,Math.min(100,val))/100)*oscPlotH;
        const d=Math.abs(y-py);
        if(d<dist){dist=d;best=idx;}
      }
    } else {
      if(typeof val==='number'){
        const py=yPrice(val);
        const d=Math.abs(y-py);
        if(d<dist){dist=d;best=idx;}
      } else if(typeof val==='object'&&val){
        ['upper','mid','lower'].forEach(k=>{
          if(val[k]!=null){
            const py=yPrice(val[k]);
            const d=Math.abs(y-py);
            if(d<dist){dist=d;best=idx;}
          }
        });
      }
    }
  });
  return dist<=16?best:-1;
}

function getIndicatorSignal(ind, val, ltp){
  const name = ind.name || '';
  const ltpVal = Number(ltp) || (state.candles.length ? Number(state.candles[state.candles.length - 1].close) : 0);

  if (name === 'Supertrend') {
    const num = typeof val === 'number' ? val : ltpVal;
    if (ltpVal >= num) {
      return { signal: 'BUY', info: `Bullish trend; trigger SELL if price crosses below ₹${fmt(num)}` };
    } else {
      return { signal: 'SELL', info: `Bearish trend; trigger BUY if price crosses above ₹${fmt(num)}` };
    }
  }

  if (name === 'Bollinger Bands' && typeof val === 'object' && val) {
    if (ltpVal >= val.upper) {
      return { signal: 'SELL', info: `Overbought at Upper Band (₹${fmt(val.upper)}); trigger SELL on rejection` };
    } else if (ltpVal <= val.lower) {
      return { signal: 'BUY', info: `Oversold at Lower Band (₹${fmt(val.lower)}); trigger BUY on rebound` };
    } else if (ltpVal >= val.mid) {
      return { signal: 'BUY', info: `Above Midline (₹${fmt(val.mid)}); trigger SELL if crosses below ₹${fmt(val.mid)}` };
    } else {
      return { signal: 'SELL', info: `Below Midline (₹${fmt(val.mid)}); trigger BUY if crosses above ₹${fmt(val.mid)}` };
    }
  }

  if (['SMA', 'EMA', 'WMA', 'VWMA', 'HMA', 'VWAP', 'Keltner Channels'].includes(name)) {
    const num = typeof val === 'number' ? val : ltpVal;
    if (ltpVal >= num) {
      return { signal: 'BUY', info: `Above ${name} (₹${fmt(num)}); trigger SELL if price crosses below ₹${fmt(num)}` };
    } else {
      return { signal: 'SELL', info: `Below ${name} (₹${fmt(num)}); trigger BUY if price crosses above ₹${fmt(num)}` };
    }
  }

  if (['RSI', 'Stoch RSI'].includes(name)) {
    const rsi = typeof val === 'number' ? val : 50;
    if (rsi >= 70) {
      return { signal: 'SELL', info: `Overbought (RSI ${fmt(rsi)}); trigger SELL if RSI crosses below 70` };
    } else if (rsi <= 30) {
      return { signal: 'BUY', info: `Oversold (RSI ${fmt(rsi)}); trigger BUY if RSI crosses above 30` };
    } else if (rsi >= 50) {
      return { signal: 'BUY', info: `Bullish momentum (RSI ${fmt(rsi)}); trigger SELL if RSI crosses below 50` };
    } else {
      return { signal: 'SELL', info: `Bearish momentum (RSI ${fmt(rsi)}); trigger BUY if RSI crosses above 50` };
    }
  }

  if (['Stochastic', 'Williams %R'].includes(name)) {
    const stoch = typeof val === 'number' ? val : 50;
    if (stoch >= 80) {
      return { signal: 'SELL', info: `Overbought (${fmt(stoch)}%); trigger SELL if crosses below 80` };
    } else if (stoch <= 20) {
      return { signal: 'BUY', info: `Oversold (${fmt(stoch)}%); trigger BUY if crosses above 20` };
    } else if (stoch >= 50) {
      return { signal: 'BUY', info: `Bullish bias (${fmt(stoch)}%); trigger SELL if falls below 50` };
    } else {
      return { signal: 'SELL', info: `Bearish bias (${fmt(stoch)}%); trigger BUY if rises above 50` };
    }
  }

  if (name === 'MACD') {
    const m = typeof val === 'number' ? val : 50;
    if (m >= 50) {
      return { signal: 'BUY', info: `MACD bullish momentum; trigger SELL if crosses below baseline` };
    } else {
      return { signal: 'SELL', info: `MACD bearish momentum; trigger BUY if crosses above baseline` };
    }
  }

  const num = typeof val === 'number' ? val : ltpVal;
  return ltpVal >= num
    ? { signal: 'BUY', info: `Bullish bias; trigger SELL if price crosses below ₹${fmt(num)}` }
    : { signal: 'SELL', info: `Bearish bias; trigger BUY if price crosses above ₹${fmt(num)}` };
}

function getDrawingSignal(q, ltp){
  const ltpVal = Number(ltp) || (state.candles.length ? Number(state.candles[state.candles.length - 1].close) : 0);

  if (q.type === 'h') {
    if (ltpVal >= q.price) {
      return { signal: 'BUY', info: `Above Support (₹${fmt(q.price)}); trigger SELL if price crosses below ₹${fmt(q.price)}` };
    } else {
      return { signal: 'SELL', info: `Below Resistance (₹${fmt(q.price)}); trigger BUY if price crosses above ₹${fmt(q.price)}` };
    }
  }

  if (['line', 'ray', 'arrow'].includes(q.type) && q.i1 != null && q.i2 != null) {
    const lastIdx = Math.max(0, state.candles.length - 1);
    const slope = (q.p2 - q.p1) / (q.i2 - q.i1 || 1);
    const proj = q.p1 + slope * (lastIdx - q.i1);
    if (ltpVal >= proj) {
      return { signal: 'BUY', info: `Above Trendline (₹${fmt(proj)}); trigger SELL if price crosses below ₹${fmt(proj)}` };
    } else {
      return { signal: 'SELL', info: `Below Trendline (₹${fmt(proj)}); trigger BUY if price crosses above ₹${fmt(proj)}` };
    }
  }

  if (q.type === 'rr') {
    const isLong = (q.target || 0) >= (q.entry || 0);
    if (isLong) {
      return { signal: 'BUY', info: `Long setup (Target ₹${fmt(q.target)}, SL ₹${fmt(q.stop)}); trigger SELL if price falls below ₹${fmt(q.stop)}` };
    } else {
      return { signal: 'SELL', info: `Short setup (Target ₹${fmt(q.target)}, SL ₹${fmt(q.stop)}); trigger BUY if price rises above ₹${fmt(q.stop)}` };
    }
  }

  if (q.type === 'rect' || q.type === 'range') {
    const upper = Math.max(q.p1, q.p2), lower = Math.min(q.p1, q.p2);
    if (ltpVal >= upper) {
      return { signal: 'BUY', info: `Breakout above ₹${fmt(upper)}; trigger SELL if falls below ₹${fmt(upper)}` };
    } else if (ltpVal <= lower) {
      return { signal: 'SELL', info: `Breakdown below ₹${fmt(lower)}; trigger BUY if climbs above ₹${fmt(lower)}` };
    } else {
      return { signal: 'BUY', info: `In Channel [₹${fmt(lower)} - ₹${fmt(upper)}]; trigger BUY if breaks above ₹${fmt(upper)}, SELL if breaks below ₹${fmt(lower)}` };
    }
  }

  if (q.type === 'fib') {
    const minP = Math.min(q.p1, q.p2), maxP = Math.max(q.p1, q.p2);
    return ltpVal >= minP
      ? { signal: 'BUY', info: `Above Fib support ₹${fmt(minP)}; trigger SELL if price breaks below ₹${fmt(minP)}` }
      : { signal: 'SELL', info: `Below Fib resistance ₹${fmt(maxP)}; trigger BUY if price crosses above ₹${fmt(maxP)}` };
  }

  return { signal: 'BUY', info: `Level ₹${fmt(ltpVal)}; trigger SELL if price breaks down` };
}

function showDrawingTooltip(idx,x,y,indicatorIdx=-1){
  const el=document.getElementById('drawingTooltip');
  if(!el) return;
  if(idx<0 && indicatorIdx<0){
    el.style.display='none';
    return;
  }

  const ltp = currentLtp();
  let title = '', paramsText = '', valText = '', sig = null, isDrawing = false;

  if (indicatorIdx >= 0) {
    const ind = state.appliedIndicators[indicatorIdx];
    if (!ind) { el.style.display = 'none'; return; }
    title = `💬 ${ind.name}`;
    paramsText = `Parameters: ${ind.params || 'Default'}`;
    const series = appliedOverlaySeries(ind.name, ind.params);
    const view = getView();
    const r = vp.getBoundingClientRect();
    const i = Math.max(0, Math.min(view.count - 1, Math.floor((x - r.left - 12) / Math.max(1, (vp.clientWidth - 84) / view.count))));
    const val = series ? series[view.start + i] : null;
    if (typeof val === 'object' && val) {
      valText = `Upper ₹${fmt(val.upper)} · Mid ₹${fmt(val.mid)} · Lower ₹${fmt(val.lower)}`;
    } else {
      valText = `Value: ${val != null ? fmt(val) : '—'}`;
    }
    sig = getIndicatorSignal(ind, val, ltp);
  } else {
    const q = state.drawings[idx];
    if (!q) { el.style.display = 'none'; return; }
    isDrawing = true;
    title = `💬 ${q.name || q.type}`;
    paramsText = drawingParams(q);
    valText = '';
    sig = getDrawingSignal(q, ltp);
  }

  const sigClass = sig.signal.toLowerCase();
  el.className = `drawing-tooltip ${sigClass}`;
  el.innerHTML = `
    <div class="dt-title">${esc(title)}</div>
    <div class="dt-params">${esc(paramsText)}</div>
    ${valText ? `<div style="font-size:10px;color:var(--text);margin-bottom:3px">${esc(valText)}</div>` : ''}
    <div style="font-size:10px;color:var(--text-faint)">LTP: ₹${fmt(ltp)}</div>
    <div class="dt-signal-box ${sigClass}">
      <span class="dt-signal-tag">${sig.signal} SIGNAL</span>
      <span class="dt-signal-info">${esc(sig.info)}</span>
    </div>
    ${isDrawing ? `<div style="margin-top:5px;font-size:9.5px;color:var(--text-faint)">Click & drag to move</div>` : ''}
  `;

  const tooltipW = 270, tooltipH = 140;
  let left = x + 16;
  let top = y - 20;
  if (left + tooltipW > window.innerWidth - 12) left = x - tooltipW - 16;
  if (top + tooltipH > window.innerHeight - 12) top = window.innerHeight - tooltipH - 12;
  if (top < 12) top = 12;

  el.style.left = Math.max(8, left) + 'px';
  el.style.top = Math.max(8, top) + 'px';
  el.style.display = 'block';
}"""

assert old_tooltip_block in html, "old_tooltip_block not found"
html = html.replace(old_tooltip_block, new_tooltip_block, 1)

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Applied comment-box popup and drawing drag updates successfully!")

