# -*- coding: utf-8 -*-
"""
Execute comprehensive wiring on terminal.html for all 23 items.
"""
from pathlib import Path
import re

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

# 1. Item 1: Topbar overflow & z-index
content = re.sub(
    r'(\.topbar\s*\{[^}]*?)overflow:\s*hidden\s*!important;',
    r'\1overflow: visible !important;',
    content
)
content = re.sub(
    r'(\.topbar\s*\{[^}]*?)z-index:\s*1200\s*!important;',
    r'\1z-index: 2500 !important;',
    content
)
content = re.sub(
    r'(\.(user|notification)-menu\s*\{[^}]*?)z-index:\s*2200;',
    r'\1z-index: 2600 !important;',
    content
)

# 2. Item 8: Trend Line Drawing & Pointerdown / Pointermove
old_pointer_down_pending = '''    if(state.pendingDrawing){
      applyDrawingPoint(x,y);
      state.pendingDrawing=null;
      state.drawingStage=[];
      state.hoverDrawing=-1;
      state.interactionMode='crosshair';
      vp.classList.remove('pan-mode','drawing-hover');
      return;
    }'''

new_pointer_down_pending = '''    if(state.pendingDrawing){
      const finished = applyDrawingPoint(x,y);
      if(finished){
        state.pendingDrawing=null;
        state.drawingStage=[];
        state.hoverDrawing=-1;
        state.interactionMode='crosshair';
        vp.classList.remove('pan-mode','drawing-hover');
      }
      draw();
      return;
    }'''

if old_pointer_down_pending in content:
    content = content.replace(old_pointer_down_pending, new_pointer_down_pending, 1)

old_pointer_move_cross = '''    updateCross(e);
    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;'''

new_pointer_move_cross = '''    updateCross(e);
    if(state.pendingDrawing && state.drawingStage && state.drawingStage.length > 0){
      state.cursorPoint = chartPoint({clientX: e.clientX, clientY: e.clientY});
      draw();
      return;
    }
    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;'''

if old_pointer_move_cross in content:
    content = content.replace(old_pointer_move_cross, new_pointer_move_cross, 1)

# In draw(), add live dotted preview and trend_ray infinite rendering
old_draw_drawings = '''state.drawings.forEach(q=>{x.save();x.strokeStyle=q.color||css('--gold');x.fillStyle=q.fill||'rgba(38,217,166,.12)';x.lineWidth=1.2;if(q.type==='h'){const yy=y(q.price);x.beginPath();x.moveTo(pad.l,yy);x.lineTo(w-pad.r,yy);x.stroke();if(q.price!=null && yy>=pad.t-4 && yy<=h-pad.b+4){const txt=fmt(q.price);x.font='bold 9.5px IBM Plex Mono,monospace';const tw=x.measureText(txt).width+8;const by=Math.max(pad.t,Math.min(h-pad.b-16,yy-8));x.fillStyle=q.color||css('--gold');x.beginPath();x.roundRect(w-pad.r+2,by,tw,16,3);x.fill();x.fillStyle='#0A0D12';x.fillText(txt,w-pad.r+6,by+11);}}else if(q.type==='v'){const xx=pad.l+(q.i-view.start+.5)*step;x.beginPath();x.moveTo(xx,pad.t);x.lineTo(xx,h-pad.b);x.stroke();}else if(['line','ray','arrow'].includes(q.type)){const x1=pad.l+(q.i1-view.start+.5)*step,y1=y(q.p1),x2=pad.l+(q.i2-view.start+.5)*step,y2=y(q.p2);x.beginPath();x.moveTo(x1,y1);x.lineTo(x2,y2);if(q.type==='ray')x.lineTo(x2+(x2-x1)*20,y2+(y2-y1)*20);x.stroke();if(q.p1!=null && q.p2!=null){[{px:x1,py:y1,pr:q.p1,isStart:true},{px:x2,py:y2,pr:q.p2,isStart:false}].forEach(pt=>{if(pt.px>=pad.l-10 && pt.px<=w-pad.r+10 && pt.py>=pad.t-10 && pt.py<=h-pad.b+10){x.beginPath();x.arc(pt.px,pt.py,3.5,0,Math.PI*2);x.fillStyle=q.color||css('--gold');x.fill();const txt=fmt(pt.pr);x.font='bold 9px IBM Plex Mono,monospace';const tw=x.measureText(txt).width+8;const tagY=pt.isStart?Math.max(pad.t+14,pt.py-7):Math.min(h-pad.b-6,pt.py+15);const tagX=Math.max(pad.l+2,Math.min(w-pad.r-tw-2,pt.px-tw/2));x.fillStyle='rgba(10,13,18,0.88)';x.strokeStyle=q.color||css('--gold');x.lineWidth=1;x.beginPath();x.roundRect(tagX,tagY-11,tw,15,3);x.fill();x.stroke();x.fillStyle=q.color||css('--gold');x.fillText(txt,tagX+4,tagY);}});}if(q.type==='arrow'){x.beginPath();x.moveTo(x2,y2);x.lineTo(x2-7,y2-4);x.lineTo(x2-7,y2+4);x.closePath();x.fillStyle=q.color||css('--gold');x.fill();}}'''

new_draw_drawings = '''// Live Dotted Ray Preview while drawing trend line
  if(state.pendingDrawing && state.drawingStage && state.drawingStage.length === 1 && state.cursorPoint){
    const pt1 = state.drawingStage[0];
    const cur = state.cursorPoint;
    const x1 = pad.l + (pt1.i - view.start + 0.5) * step, y1 = y(pt1.price);
    const x2 = pad.l + (cur.i - view.start + 0.5) * step, y2 = y(cur.price);
    x.save();
    x.strokeStyle = state.pendingColor || css('--gold');
    x.lineWidth = 1.8;
    x.setLineDash([5, 4]);
    x.beginPath();
    x.moveTo(x1, y1);
    x.lineTo(x2, y2);
    x.stroke();
    x.setLineDash([]);
    x.beginPath();
    x.arc(x1, y1, 4, 0, Math.PI * 2);
    x.fillStyle = state.pendingColor || css('--gold');
    x.fill();
    x.restore();
  }

  state.drawings.forEach(q=>{
    x.save();
    x.strokeStyle=q.color||css('--gold');
    x.fillStyle=q.fill||'rgba(38,217,166,.12)';
    x.lineWidth=1.5;
    if(q.type==='h'){
      const yy=y(q.price);
      x.beginPath();x.moveTo(pad.l,yy);x.lineTo(w-pad.r,yy);x.stroke();
      if(q.price!=null && yy>=pad.t-4 && yy<=h-pad.b+4){
        const txt=fmt(q.price);
        x.font='bold 9.5px IBM Plex Mono,monospace';
        const tw=x.measureText(txt).width+8;
        const by=Math.max(pad.t,Math.min(h-pad.b-16,yy-8));
        x.fillStyle=q.color||css('--gold');
        x.beginPath();x.roundRect(w-pad.r+2,by,tw,16,3);x.fill();
        x.fillStyle='#0A0D12';x.fillText(txt,w-pad.r+6,by+11);
      }
    } else if(q.type==='v'){
      const xx=pad.l+(q.i-view.start+.5)*step;
      x.beginPath();x.moveTo(xx,pad.t);x.lineTo(xx,h-pad.b);x.stroke();
    } else if(q.type==='trend_ray'){
      const x1=pad.l+(q.i1-view.start+.5)*step,y1=y(q.p1);
      const x2=pad.l+(q.i2-view.start+.5)*step,y2=y(q.p2);
      const dx=x2-x1, dy=y2-y1;
      x.beginPath();
      if(Math.abs(dx)>0.001){
        const yL = y1 + ((pad.l - x1) / dx) * dy;
        const yR = y1 + ((w - pad.r - x1) / dx) * dy;
        x.moveTo(pad.l, yL);
        x.lineTo(w - pad.r, yR);
      } else {
        x.moveTo(x1, pad.t);
        x.lineTo(x1, h - pad.b);
      }
      x.stroke();
      // Anchor dots
      [ {px:x1, py:y1, pr:q.p1}, {px:x2, py:y2, pr:q.p2} ].forEach(pt => {
        if(pt.px >= pad.l-10 && pt.px <= w-pad.r+10 && pt.py >= pad.t-10 && pt.py <= h-pad.b+10){
          x.beginPath(); x.arc(pt.px, pt.py, 3.5, 0, Math.PI * 2);
          x.fillStyle = q.color || css('--gold'); x.fill();
        }
      });
    } else if(['line','ray','arrow'].includes(q.type)){
      const x1=pad.l+(q.i1-view.start+.5)*step,y1=y(q.p1),x2=pad.l+(q.i2-view.start+.5)*step,y2=y(q.p2);
      x.beginPath();x.moveTo(x1,y1);x.lineTo(x2,y2);
      if(q.type==='ray')x.lineTo(x2+(x2-x1)*20,y2+(y2-y1)*20);
      x.stroke();
      if(q.p1!=null && q.p2!=null){
        [{px:x1,py:y1,pr:q.p1,isStart:true},{px:x2,py:y2,pr:q.p2,isStart:false}].forEach(pt=>{
          if(pt.px>=pad.l-10 && pt.px<=w-pad.r+10 && pt.py>=pad.t-10 && pt.py<=h-pad.b+10){
            x.beginPath();x.arc(pt.px,pt.py,3.5,0,Math.PI*2);
            x.fillStyle=q.color||css('--gold');x.fill();
            const txt=fmt(pt.pr);x.font='bold 9px IBM Plex Mono,monospace';
            const tw=x.measureText(txt).width+8;
            const tagY=pt.isStart?Math.max(pad.t+14,pt.py-7):Math.min(h-pad.b-6,pt.py+15);
            const tagX=Math.max(pad.l+2,Math.min(w-pad.r-tw-2,pt.px-tw/2));
            x.fillStyle='rgba(10,13,18,0.88)';x.strokeStyle=q.color||css('--gold');
            x.lineWidth=1;x.beginPath();x.roundRect(tagX,tagY-11,tw,15,3);
            x.fill();x.stroke();x.fillStyle=q.color||css('--gold');
            x.fillText(txt,tagX+4,tagY);
          }
        });
      }
      if(q.type==='arrow'){
        x.beginPath();x.moveTo(x2,y2);x.lineTo(x2-7,y2-4);x.lineTo(x2-7,y2+4);x.closePath();
        x.fillStyle=q.color||css('--gold');x.fill();
      }
    }'''

if old_draw_drawings in content:
    content = content.replace(old_draw_drawings, new_draw_drawings, 1)

# In draw(), highlight indicator line when state.highlightIndicatorIdx === indIdx
old_draw_indicators = '''state.appliedIndicators.forEach(ind=>{
    if(isOscillator(ind.name)) return;
    const series=appliedOverlaySeries(ind.name,ind.params);'''

new_draw_indicators = '''state.appliedIndicators.forEach((ind, indIdx)=>{
    if(isOscillator(ind.name)) return;
    const series=appliedOverlaySeries(ind.name,ind.params);
    const isHighlighted = state.highlightIndicatorIdx === indIdx;'''

if old_draw_indicators in content:
    content = content.replace(old_draw_indicators, new_draw_indicators, 1)

old_ind_stroke = '''x.strokeStyle=ind.color||css('--accent');x.lineWidth=1.5;x.stroke()});'''
new_ind_stroke = '''x.strokeStyle=ind.color||css('--accent');
      x.lineWidth=isHighlighted ? 3.5 : 1.5;
      if(isHighlighted){ x.shadowColor=ind.color||'#E8B84B'; x.shadowBlur=12; }
      x.stroke();
      if(isHighlighted){ x.shadowBlur=0; }
    });'''

if old_ind_stroke in content:
    content = content.replace(old_ind_stroke, new_ind_stroke, 1)

# 3. Item 10: Indicator calculation audit (Supertrend, ATR, Keltner)
old_applied_overlay = '''function appliedOverlaySeries(name,param){
    const p=String(param||'20').split(',').map(Number);
    if(name==='SMA')return lineSeries('SMA',p[0]);
    if(name==='WMA'||name==='VWMA')return lineSeries('WMA',p[0]);
    if(name==='EMA'||name==='HMA')return emaSeries(p[0]||20);
    if(name==='Supertrend')return emaSeries(p[0]||10);
    if(name==='VWAP')return vwapSeries();
    if(name==='Bollinger Bands'){return stdSeries(p[0]||20,p[1]||2)}
    if(name==='Keltner Channels'){return emaSeries(p[0]||20)}
    if(name==='Ichimoku Cloud'){const n1=p[0]||9,n2=p[1]||26,a=state.candles;return a.map((c,i)=>{if(i<n2-1)return null;const s=a.slice(i-n2+1,i+1),hh=Math.max(...s.map(x=>+x.high)),ll=Math.min(...s.map(x=>+x.low));return (hh+ll)/2})}
    if(name==='RSI'||name==='Stoch RSI')return rsiSeries(p[0]||14);
    if(name==='Stochastic'||name==='Williams %R')return stochSeries(p[0]||14);
    if(name==='MACD')return macdSeries(p[0]||12,p[1]||26,p[2]||9);
    if(name==='CCI'||name==='ADX'||name==='ATR'||name==='MFI'||name==='OBV')return rsiSeries(p[0]||14);
    return null;
  }'''

new_applied_overlay = '''function supertrendSeries(period = 10, multiplier = 3) {
    const n = Number(period) || 10, m = Number(multiplier) || 3;
    const a = state.candles;
    if (a.length < 2) return a.map(() => null);
    const tr = [Number(a[0].high) - Number(a[0].low)];
    for (let i = 1; i < a.length; i++) {
      const h = Number(a[i].high), l = Number(a[i].low), pc = Number(a[i - 1].close);
      tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
    }
    const atr = [];
    let sum = 0;
    for (let i = 0; i < a.length; i++) {
      sum += tr[i];
      if (i < n - 1) { atr.push(sum / (i + 1)); continue; }
      if (i === n - 1) { atr.push(sum / n); continue; }
      atr.push((atr[i - 1] * (n - 1) + tr[i]) / n);
    }
    const st = [];
    let inUptrend = true, prevLower = 0, prevUpper = 0;
    for (let i = 0; i < a.length; i++) {
      const h = Number(a[i].high), l = Number(a[i].low), c = Number(a[i].close);
      const hl2 = (h + l) / 2;
      const basicUpper = hl2 + m * atr[i];
      const basicLower = hl2 - m * atr[i];
      let finalLower = basicLower, finalUpper = basicUpper;
      if (i > 0) {
        const prevC = Number(a[i - 1].close);
        finalLower = (basicLower > prevLower || prevC < prevLower) ? basicLower : prevLower;
        finalUpper = (basicUpper < prevUpper || prevC > prevUpper) ? basicUpper : prevUpper;
        if (inUptrend && c < finalLower) inUptrend = false;
        else if (!inUptrend && c > finalUpper) inUptrend = true;
      }
      prevLower = finalLower;
      prevUpper = finalUpper;
      st.push(inUptrend ? finalLower : finalUpper);
    }
    return st;
  }

  function atrSeries(period = 14) {
    const n = Number(period) || 14, a = state.candles;
    if (a.length < 2) return a.map(() => 0);
    const tr = [Number(a[0].high) - Number(a[0].low)];
    for (let i = 1; i < a.length; i++) {
      const h = Number(a[i].high), l = Number(a[i].low), pc = Number(a[i - 1].close);
      tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
    }
    const out = [];
    let sum = 0;
    for (let i = 0; i < a.length; i++) {
      sum += tr[i];
      if (i < n - 1) { out.push(sum / (i + 1)); continue; }
      if (i === n - 1) { out.push(sum / n); continue; }
      out.push((out[i - 1] * (n - 1) + tr[i]) / n);
    }
    return out;
  }

  function keltnerSeries(period = 20, mult = 1.5) {
    const ema = emaSeries(period);
    const atr = atrSeries(period);
    return ema.map((mVal, i) => {
      if (mVal == null) return null;
      const aVal = atr[i] || 0;
      return { mid: mVal, upper: mVal + mult * aVal, lower: mVal - mult * aVal };
    });
  }

  function appliedOverlaySeries(name,param){
    const p=String(param||'20').split(',').map(Number);
    if(name==='SMA')return lineSeries('SMA',p[0]);
    if(name==='WMA'||name==='VWMA')return lineSeries('WMA',p[0]);
    if(name==='EMA'||name==='HMA')return emaSeries(p[0]||20);
    if(name==='Supertrend')return supertrendSeries(p[0]||10, p[1]||3);
    if(name==='VWAP')return vwapSeries();
    if(name==='Bollinger Bands'){return stdSeries(p[0]||20,p[1]||2)}
    if(name==='Keltner Channels'){return keltnerSeries(p[0]||20,p[1]||1.5)}
    if(name==='Ichimoku Cloud'){const n1=p[0]||9,n2=p[1]||26,a=state.candles;return a.map((c,i)=>{if(i<n2-1)return null;const s=a.slice(i-n2+1,i+1),hh=Math.max(...s.map(x=>+x.high)),ll=Math.min(...s.map(x=>+x.low));return (hh+ll)/2})}
    if(name==='RSI'||name==='Stoch RSI')return rsiSeries(p[0]||14);
    if(name==='Stochastic'||name==='Williams %R')return stochSeries(p[0]||14);
    if(name==='MACD')return macdSeries(p[0]||12,p[1]||26,p[2]||9);
    if(name==='ATR')return atrSeries(p[0]||14);
    if(name==='CCI'||name==='ADX'||name==='MFI'||name==='OBV')return rsiSeries(p[0]||14);
    return null;
  }'''

if old_applied_overlay in content:
    content = content.replace(old_applied_overlay, new_applied_overlay, 1)

# In draw(), use state.oscHeightRatio
content = re.sub(
    r'oscH\s*=\s*hasOsc\s*\?\s*Math\.max\(72,\s*Math\.floor\(h\s*\*\s*0\.23\)\)\s*:\s*0;',
    r'oscH = hasOsc ? Math.max(60, Math.min(Math.floor(h * 0.48), Math.floor(h * (state.oscHeightRatio || 0.23)))) : 0;',
    content
)

# 4. Item 2: Recommendation Banner above chart update & option price levels
old_update_chart_reco = '''  function updateChartRecoBanner(rec){
    if(!rec) rec = window.__caRecommendation || window.__caCurrentChartReco;
    if(!rec) return;
    window.__caCurrentChartReco = rec;

    const banner = $('chartRecoBanner');
    if(!banner) return;

    const sym = rec.symbol || selectedSymbol() || 'NIFTY';
    const action = String(rec.recommendation || rec.signal || rec.action || 'ACCUMULATE').toUpperCase();
    const isBuy = action.includes('BUY') || action.includes('ACCUMULATE') || action.includes('LONG');
    const isSell = action.includes('SELL') || action.includes('SHORT');

    const actionEl = $('chartRecoAction');
    if(actionEl){
      actionEl.textContent = action;
      actionEl.className = `tag ${isBuy ? 'buy' : isSell ? 'sell' : 'neutral'}`;
      actionEl.style.cursor = 'pointer';
      actionEl.onclick = () => openRecoCalculationModal(rec);
    }

    if($('chartRecoSymbol')) $('chartRecoSymbol').textContent = sym;
    if($('chartRecoConfidence')){
      const conf = rec.confidence != null ? `${Math.round(rec.confidence)}% Conviction` : '85% Conviction';
      $('chartRecoConfidence').textContent = conf;
    }
    if($('chartRecoRationale')){
      const rat = (rec.evidence?.news?.stock?.reasons || []).join(' · ') || rec.rationale || rec.reason || 'Multi-factor alignment verified across moving average structure, volume confirmation, and news materiality.';
      $('chartRecoRationale').textContent = rat;
      $('chartRecoRationale').onclick = () => openRecoCalculationModal(rec);
      $('chartRecoRationale').style.cursor = 'pointer';
    }

    const entry = Number(rec.entry || 0);
    const sl = Number(rec.stop_loss || 0);
    const tgt = Number(rec.target || 0);

    if($('chartRecoEntry')) $('chartRecoEntry').textContent = entry ? `₹${fmt(entry)}` : '₹--';
    if($('chartRecoSl')) $('chartRecoSl').textContent = sl ? `₹${fmt(sl)}` : '₹--';
    if($('chartRecoTgt')) $('chartRecoTgt').textContent = tgt ? `₹${fmt(tgt)}` : '₹--';

    const risk = Math.abs(entry - sl) || 1;
    const reward = Math.abs(tgt - entry) || 1;
    const rr = (reward / risk).toFixed(2);
    if($('chartRecoRr')) $('chartRecoRr').textContent = entry ? `1:${rr}` : '1:2.0';
  }'''

new_update_chart_reco = '''  async function updateChartRecoBanner(rec, targetSymbol){
    const sym = targetSymbol || (rec ? rec.symbol : null) || selectedSymbol() || 'NIFTY';
    if(!rec || (rec.symbol && rec.symbol !== sym)){
      try {
        const d = await api(`/api/analysis/overall/${encodeURIComponent(sym)}?timeframe=${encodeURIComponent(state.tf||'5m')}`);
        if(d) rec = d;
      } catch(_) {}
    }
    if(!rec) return;
    window.__caCurrentChartReco = rec;
    window.__caRecommendation = rec;

    const banner = $('chartRecoBanner');
    if(!banner) return;

    const action = String(rec.recommendation || rec.signal || rec.action || 'ACCUMULATE').toUpperCase();
    const isBuy = action.includes('BUY') || action.includes('ACCUMULATE') || action.includes('LONG');
    const isSell = action.includes('SELL') || action.includes('SHORT');

    const actionEl = $('chartRecoAction');
    if(actionEl){
      actionEl.textContent = action;
      actionEl.className = `tag ${isBuy ? 'buy' : isSell ? 'sell' : 'neutral'}`;
      actionEl.style.cursor = 'pointer';
      actionEl.onclick = () => openRecoCalculationModal(rec);
    }

    if($('chartRecoSymbol')) $('chartRecoSymbol').textContent = sym;
    if($('chartRecoConfidence')){
      const conf = rec.confidence != null ? `${Math.round(rec.confidence)}% Conviction` : '85% Conviction';
      $('chartRecoConfidence').textContent = conf;
    }
    if($('chartRecoRationale')){
      const rat = (rec.evidence?.news?.stock?.reasons || []).join(' · ') || rec.rationale || rec.reason || 'Multi-factor alignment verified across moving average structure, volume confirmation, and news materiality.';
      $('chartRecoRationale').textContent = rat;
      $('chartRecoRationale').onclick = () => openRecoCalculationModal(rec);
      $('chartRecoRationale').style.cursor = 'pointer';
    }

    // Extract price levels: prioritize options contract if available, otherwise equity
    const opt = rec.evidence?.options || {};
    let entry = Number(rec.entry || 0);
    let sl = Number(rec.stop_loss || 0);
    let tgt = Number(rec.target || 0);

    if(!entry && opt.available && opt.entry){
      entry = Number(opt.entry);
      sl = Number(opt.stop_loss || (entry * 0.7));
      tgt = Number(opt.target || (entry * 1.5));
    }
    if(!entry){
      const ltp = currentLtp();
      if(ltp > 0){
        entry = ltp;
        const atr = Number(rec.evidence?.technical?.atr) || (entry * 0.01);
        sl = isBuy ? Number((entry - atr * 1.5).toFixed(2)) : Number((entry + atr * 1.5).toFixed(2));
        tgt = isBuy ? Number((entry + atr * 2.2).toFixed(2)) : Number((entry - atr * 2.2).toFixed(2));
      }
    }

    if($('chartRecoEntry')) $('chartRecoEntry').textContent = entry ? `₹${fmt(entry)}` : '₹--';
    if($('chartRecoSl')) $('chartRecoSl').textContent = sl ? `₹${fmt(sl)}` : '₹--';
    if($('chartRecoTgt')) $('chartRecoTgt').textContent = tgt ? `₹${fmt(tgt)}` : '₹--';

    const risk = Math.abs(entry - sl) || 1;
    const reward = Math.abs(tgt - entry) || 1;
    const rr = (reward / risk).toFixed(2);
    if($('chartRecoRr')) $('chartRecoRr').textContent = entry ? `1:${rr}` : '1:2.0';
  }'''

if old_update_chart_reco in content:
    content = content.replace(old_update_chart_reco, new_update_chart_reco, 1)

# In onSymbolChanged, call updateChartRecoBanner(null, S)
old_on_symbol_changed = '''async function onSymbolChanged(sym){
    S=sym||''; window.CATraderSymbol=S; selectionSeq++; const localSeq=selectionSeq;
    window.__CA_SELECTED_SYMBOL=S;
    if(typeof tabLoadedAt!=='undefined' && tabLoadedAt.clear) tabLoadedAt.clear();
    const cached=(window.__CA_WL_QUOTES||{})[String(S).toUpperCase()]; if(cached) updateHeader(cached);
    document.querySelectorAll('.wl-item').forEach(v=>v.classList.toggle('selected',(v.dataset.symbol||'')===S));
    const tab=document.querySelector('.navtab.active')?.dataset.tab;'''

new_on_symbol_changed = '''async function onSymbolChanged(sym){
    S=sym||''; window.CATraderSymbol=S; selectionSeq++; const localSeq=selectionSeq;
    window.__CA_SELECTED_SYMBOL=S;
    if(typeof tabLoadedAt!=='undefined' && tabLoadedAt.clear) tabLoadedAt.clear();
    const cached=(window.__CA_WL_QUOTES||{})[String(S).toUpperCase()]; if(cached) updateHeader(cached);
    document.querySelectorAll('.wl-item').forEach(v=>v.classList.toggle('selected',(v.dataset.symbol||'')===S));
    const tab=document.querySelector('.navtab.active')?.dataset.tab;
    void updateChartRecoBanner(null, S);'''

if old_on_symbol_changed in content:
    content = content.replace(old_on_symbol_changed, new_on_symbol_changed, 1)

path.write_text(content, encoding="utf-8")
print("Executed wiring batch 1.")

