
(async()=>{
  const A=async(u,o={})=>{const timeoutMs=Math.max(25000,Number(o.timeoutMs||35000)),ctrl=o.signal?null:new AbortController(),timer=ctrl?setTimeout(()=>ctrl.abort(),timeoutMs):null;try{const r=await fetch(u,{credentials:'include',headers:{'Content-Type':'application/json',...(o.headers||{})},...o,signal:o.signal||ctrl?.signal});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b?.error?.message||b?.detail?.message||b?.detail||`HTTP ${r.status}`);return b}catch(e){if(e?.name==='AbortError'){if(!o._retried)return A(u,{...o,_retried:true,timeoutMs:45000,headers:{...(o.headers||{}),'Cache-Control':'no-cache'}});throw new Error(`Request timed out after ${Math.round(timeoutMs/1000)} seconds`);}throw e}finally{if(timer)clearTimeout(timer)}};
  // Shared DOM helpers for the chart-analysis IIFE. Do not depend on helpers from later IIFEs.
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const signalClass = s => String(s||'').toUpperCase().includes('BUY') || String(s||'').toUpperCase().includes('POSITIVE') ? 'buy' : String(s||'').toUpperCase().includes('SELL') || String(s||'').toUpperCase().includes('NEGATIVE') ? 'sell' : 'neutral';
  const toast=(m)=>{const el=document.getElementById('toast')||(()=>{const x=document.createElement('div');x.id='toast';x.style.cssText='position:fixed;right:18px;bottom:18px;z-index:300;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:8px;padding:9px 12px;font-size:11px;box-shadow:0 12px 30px rgba(0,0,0,.25);opacity:0;transition:.2s';document.body.appendChild(x);return x})();el.textContent=m;el.style.opacity='1';clearTimeout(el._t);el._t=setTimeout(()=>el.style.opacity='0',2200)};
  const fmt=v=>v==null||!isFinite(Number(v))?'—':Number(v).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2});
  const css=n=>getComputedStyle(document.body).getPropertyValue(n)||getComputedStyle(document.documentElement).getPropertyValue(n);
  const today=()=>new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Kolkata'});
  const state={candles:[],tf:'5m',history:7,visible:90,zoom:1,panX:0,panY:0,yScale:1,cross:null,drag:null,panArmed:false,yPanArmed:false,pendingDrawing:null,drawingStage:[],drawings:[],appliedIndicators:[],indicatorValues:{},currentKey:null,latestLive:null,fullscreen:false,interactionMode:'crosshair',hoverDrawing:null,dragDrawing:null};
  window.__CA_TRADER_STATE = state;
  const APP_CACHE = window.__CA_TRADER_CACHE = window.__CA_TRADER_CACHE || {quote:null,technical:null,mtf:null,newsStock:null,newsGlobal:null,fundamentals:null,options:null,movers:null};
  let W=[],G=null,S='',F='all',market={nse:false,mcx:false};
  let autoEnabled=false, autoOptions=true, autoSymbols=[];
  const subscribedSymbols=new Set();
  const indicators=[
    ['SMA','20','period'],['EMA','20','period'],['WMA','20','period'],['HMA','20','period'],['VWAP','line','color'],['VWMA','20','period'],
    ['RSI','14','period'],['MACD','12,26,9','fast,slow,signal'],['Stochastic','14,3','k,d'],['Stoch RSI','14,14,3,3','rsi,stoch,k,d'],['CCI','20','period'],['ADX','14','period'],['ATR','14','period'],['Bollinger Bands','20,2','period,multiplier'],['Keltner Channels','20,2','period,multiplier'],['Ichimoku Cloud','9,26,52','conversion,base,span'],['Supertrend','10,3','atr,multiplier'],['OBV','20','period'],['MFI','14','period'],['Williams %R','14','period']
  ];
  const drawings=['Horizontal Line','Trend Line','Ray','Vertical Line','Rectangle','Risk / Reward','Fibonacci Retracement','Parallel Channel','Arrow','Price Range'];
  const indSel=document.getElementById('indicatorSelect'),drawSel=document.getElementById('drawingSelect');
  indicators.forEach(([n,d])=>{const o=document.createElement('option');o.value=n;o.textContent=n;indSel.appendChild(o)});
  drawings.forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n;drawSel.appendChild(o)});

  function openModal(id){const m=document.getElementById(id);if(m){m.classList.add('open');m.setAttribute('aria-hidden','false')}}
  function closeModal(id){const m=document.getElementById(id);if(m){m.classList.remove('open');m.setAttribute('aria-hidden','true')}}
  window.openModal = openModal;
  window.closeModal = closeModal;
  function openToolModal(name,kind,defaults){return new Promise(resolve=>{const m=document.getElementById('toolModal'),field=document.getElementById('toolParameterField'),label=document.getElementById('toolParameterLabel'),input=document.getElementById('toolParams'),color=document.getElementById('toolColor'); const originalParent=m.parentElement; if(document.fullscreenElement&&document.fullscreenElement.id==='chartShell') document.fullscreenElement.appendChild(m);document.getElementById('toolModalTitle').textContent=`Configure ${name}`;field.style.display=kind==='indicator'?'block':'none';document.getElementById('toolColorField').style.display='block';label.textContent='Simple parameter';input.placeholder=kind==='indicator'?'e.g. 20 or 12,26,9':'';input.value=defaults||'';color.value='#E8B84B';m.classList.add('open');m.setAttribute('aria-hidden','false');const done=v=>{closeModal('toolModal'); if(originalParent&&!originalParent.contains(m)) originalParent.appendChild(m); ['toolModalSave','toolModalCancel','toolModalClose'].forEach(id=>document.getElementById(id).onclick=null);resolve(v)};document.getElementById('toolModalSave').onclick=()=>done({params:input.value.trim(),color:color.value});document.getElementById('toolModalCancel').onclick=()=>done(null);document.getElementById('toolModalClose').onclick=()=>done(null)})}

  function resizeCanvas(){const c=document.getElementById('upstoxCandles'),v=document.getElementById('chartViewport');if(!c||!v)return;const d=devicePixelRatio||1;c.width=Math.max(1,v.clientWidth)*d;c.height=Math.max(1,v.clientHeight)*d;c.style.width=v.clientWidth+'px';c.style.height=v.clientHeight+'px'}
  let __chartLayoutRetry=0;
  function ensureChartLayout(){const v=document.getElementById('chartViewport'),c=document.getElementById('upstoxCandles');if(!v||!c)return false;const ok=v.clientWidth>20&&v.clientHeight>120;if(ok){resizeCanvas();return true;}if(__chartLayoutRetry<12){__chartLayoutRetry++;setTimeout(()=>{ensureChartLayout();if(state.candles.length)draw()},150)}return false;}
  if(window.ResizeObserver){const ro=new ResizeObserver(()=>{if(ensureChartLayout()&&state.candles.length)draw()});const v0=document.getElementById('chartViewport');if(v0)ro.observe(v0);}

  function candleIntervalMs(){if(state.tf==='1D')return 86400000;if(state.tf==='60m')return 3600000;return Number(state.tf.replace('m',''))*60000}
  function xTickLabel(ts){const d=new Date(ts);if(state.tf==='1D')return d.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'2-digit',timeZone:'Asia/Kolkata'});return d.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'})}
  function xLabel(ts){const d=new Date(ts);return d.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'2-digit',timeZone:'Asia/Kolkata'})+' · '+d.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'})+' IST'}
  function getView(){const a=state.candles||[],count=Math.max(20,Math.min(a.length,Math.floor(state.visible/state.zoom)));const start=Math.max(0,Math.min(Math.max(0,a.length-count),Math.round(state.panX)));return {a,count,start,data:a.slice(start,start+count)}}
  function priceFromY(y,view){const v=document.getElementById('chartViewport'),h=v.clientHeight,pad={t:18,b:36};const data=view.data;if(!data.length)return null;const lo=Math.min(...data.map(c=>+c.low)),hi=Math.max(...data.map(c=>+c.high));const range=(hi-lo)||1;return hi-((y-pad.t)/Math.max(1,h-pad.t-pad.b))*range-state.panY*range*.005}
  function indexFromX(x,view){const padL=12,padR=72,step=(document.getElementById('chartViewport').clientWidth-padL-padR)/view.count;return Math.max(0,Math.min(view.count-1,Math.floor((x-padL)/step)))}
  function updateFastForward(view){const b=document.getElementById('chartFastForward');if(!b)return;const latest=view.start+view.count>=state.candles.length-1;b.classList.toggle('show',!latest||!!state.cross)}
  function axisLabels(x,y,price,label){const vp=document.getElementById('chartViewport'),p=document.getElementById('crosshairPriceLabel'),t=document.getElementById('crosshairTimeLabel');if(!p||!t)return;p.textContent=fmt(price);p.style.display='block';p.style.right='4px';p.style.top=Math.max(4,Math.min(vp.clientHeight-26,y-10))+'px';t.textContent=label;t.style.display='block';t.style.left=Math.max(4,Math.min(vp.clientWidth-150,x-75))+'px';t.style.minWidth='150px';t.style.textAlign='center';t.style.bottom='3px'}
  function hideAxisLabels(){['crosshairPriceLabel','crosshairTimeLabel'].forEach(id=>{const e=document.getElementById(id);if(e)e.style.display='none'})}

  function lineSeries(type,period){const a=state.candles;const n=Number(period)||20;return a.map((c,i)=>{if(i<n-1)return null;const vals=a.slice(i-n+1,i+1).map(x=>+x.close);if(type==='SMA')return vals.reduce((x,y)=>x+y,0)/vals.length;const w=vals.map((x,j)=>(j+1)*x);return w.reduce((x,y)=>x+y,0)/((n*(n+1))/2)})}
  function emaSeries(period){const n=Number(period)||20,a=state.candles,out=[];let e=null;const k=2/(n+1);a.forEach((c,i)=>{const v=+c.close;if(i===n-1)e=a.slice(0,n).reduce((x,y)=>x+Number(y.close),0)/n;else if(i>=n)e=v*k+e*(1-k);out.push(i>=n-1?e:null)});return out}
  function vwapSeries(){let pv=0,vol=0;return state.candles.map(c=>{const v=Number(c.volume)||0;const tp=(+c.high+(+c.low)+(+c.close))/3;pv+=tp*v;vol+=v;return vol?pv/vol:null})}
  function isOscillator(name){
    return /RSI|STOCH|MACD|CCI|ADX|ATR|WILLIAMS|MFI/i.test(name || '');
  }

  function rsiSeries(period = 14) {
    const n = Number(period) || 14, a = state.candles;
    if (a.length < 2) return a.map(() => 50);
    const out = [];
    let gains = 0, losses = 0;
    for (let i = 1; i <= Math.min(n, a.length - 1); i++) {
      const diff = Number(a[i].close) - Number(a[i - 1].close);
      if (diff >= 0) gains += diff; else losses -= diff;
    }
    let avgGain = gains / Math.max(1, n), avgLoss = losses / Math.max(1, n);
    for (let i = 0; i < a.length; i++) {
      if (i < n) { out.push(50); continue; }
      const diff = Number(a[i].close) - Number(a[i - 1].close);
      const gain = diff > 0 ? diff : 0, loss = diff < 0 ? -diff : 0;
      avgGain = (avgGain * (n - 1) + gain) / n;
      avgLoss = (avgLoss * (n - 1) + loss) / n;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      const rsi = avgLoss === 0 ? 100 : Math.round(100 - (100 / (1 + rs)));
      out.push(Math.max(0, Math.min(100, rsi)));
    }
    return out;
  }

  function stochSeries(period = 14) {
    const n = Number(period) || 14, a = state.candles;
    return a.map((c, i) => {
      if (i < n - 1) return 50;
      const sub = a.slice(i - n + 1, i + 1);
      const hh = Math.max(...sub.map(x => +x.high));
      const ll = Math.min(...sub.map(x => +x.low));
      const cl = +c.close;
      return hh === ll ? 50 : Math.round(((cl - ll) / (hh - ll)) * 100);
    });
  }

  function macdSeries(fast = 12, slow = 26, signal = 9) {
    const eFast = emaSeries(fast), eSlow = emaSeries(slow);
    return state.candles.map((c, i) => {
      if (eFast[i] == null || eSlow[i] == null) return 50;
      const diff = eFast[i] - eSlow[i];
      return Math.max(0, Math.min(100, 50 + diff * 2));
    });
  }

  function stdSeries(period,mult=2){const n=Number(period)||20,a=state.candles,out=[];for(let i=0;i<a.length;i++){if(i<n-1){out.push(null);continue}const vals=a.slice(i-n+1,i+1).map(c=>+c.close),ma=vals.reduce((x,y)=>x+y,0)/n,sd=Math.sqrt(vals.reduce((x,y)=>x+(y-ma)**2,0)/n);out.push({mid:ma,upper:ma+mult*sd,lower:ma-mult*sd})}return out}
  function supertrendSeries(period = 10, multiplier = 3) {
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
  }

  function draw(){const c=document.getElementById('upstoxCandles'),v=document.getElementById('chartViewport');if(!c||!v)return;ensureChartLayout();resizeCanvas();const x=c.getContext('2d'),d=devicePixelRatio||1,w=v.clientWidth,h=v.clientHeight;x.setTransform(d,0,0,d,0,0);x.clearRect(0,0,w,h);const view=getView(),a=view.data;if(!a.length){x.fillStyle=css('--text-dim');x.font='12px IBM Plex Sans, sans-serif';x.fillText('Candlestick data unavailable',24,30);hideAxisLabels();return}
  const hasOsc=state.appliedIndicators.some(i=>isOscillator(i.name));
  const oscH = hasOsc ? Math.max(60, Math.min(Math.floor(h * 0.48), Math.floor(h * (state.oscHeightRatio || 0.23)))) : 0;
  // Update live OHLC values (Item 8: crosshair hover or latest candle)
  const hoverCandle = (state.cross && state.cross.index != null && state.candles && state.candles[state.cross.index])
    ? state.candles[state.cross.index]
    : a[a.length - 1];
  if(hoverCandle){
    const elO = document.getElementById('chartOhlcO');
    const elH = document.getElementById('chartOhlcH');
    const elL = document.getElementById('chartOhlcL');
    const elC = document.getElementById('chartOhlcC');
    if(elO) elO.textContent = fmt(hoverCandle.open);
    if(elH) elH.textContent = fmt(hoverCandle.high);
    if(elL) elL.textContent = fmt(hoverCandle.low);
    if(elC) elC.textContent = fmt(hoverCandle.close);
  }
  const pad={l:12,r:72,t:18,b:36},plotW=w-pad.l-pad.r,plotH=h-pad.t-pad.b-oscH;
  const lows=a.map(v=>+v.low),highs=a.map(v=>+v.high);let lo=Math.min(...lows),hi=Math.max(...highs);const baseRange=(hi-lo)||1;const midShift=(state.panY||0)*baseRange*0.005;const mid=((hi+lo)/2)+midShift;const scaled=baseRange/state.yScale;hi=mid+scaled/2;lo=mid-scaled/2;hi+=scaled*.08;lo-=scaled*.08;const y=p=>pad.t+(hi-p)/((hi-lo)||1)*plotH;const step=plotW/view.count;x.fillStyle=css('--surface-2');x.fillRect(0,0,w,h);x.strokeStyle='rgba(128,138,155,.12)';x.lineWidth=1;x.font='10px IBM Plex Mono,monospace';
  for(let g=0;g<=6;g++){const yy=pad.t+g*plotH/6;x.beginPath();x.moveTo(pad.l,yy);x.lineTo(w-pad.r,yy);x.stroke();const val=hi-(hi-lo)*g/6;x.fillStyle=css('--text-faint');x.fillText(fmt(val),w-pad.r+8,yy+3)}
  a.forEach((v,i)=>{const xx=pad.l+(i+.5)*step;x.strokeStyle='rgba(128,138,155,.08)';x.beginPath();x.moveTo(xx,pad.t);x.lineTo(xx,pad.t+plotH);x.stroke();if(i%Math.max(1,Math.floor(view.count/8))===0){x.fillStyle=css('--text-faint');x.fillText(xTickLabel(v.timestamp||v.ts||Date.now()),Math.max(pad.l,xx-24),h-12)}});
  // Candlestick Pattern / Trend Highlight Zone Overlay
  if(state.highlightedPattern && state.candles && state.candles.length){
    const hp = state.highlightedPattern;
    const sIdx = Math.max(view.start, hp.startIdx != null ? hp.startIdx : 0);
    const eIdx = Math.min(view.start + view.count - 1, hp.endIdx != null ? hp.endIdx : state.candles.length - 1);
    if(sIdx <= eIdx && eIdx >= view.start && sIdx < view.start + view.count){
      const x1 = pad.l + (sIdx - view.start + 0.5) * step;
      const x2 = pad.l + (eIdx - view.start + 0.5) * step;
      const bw = Math.max(3, step * 0.7);
      const zoneLeft = Math.max(pad.l, Math.min(x1, x2) - bw / 2 - 4);
      const zoneRight = Math.min(w - pad.r, Math.max(x1, x2) + bw / 2 + 4);
      const zoneW = Math.max(16, zoneRight - zoneLeft);

      x.save();
      const pName = String(hp.name || '').toLowerCase();
      const visibleSlice = a.slice(Math.max(0, sIdx - view.start), Math.min(a.length, eIdx - view.start + 1));
      
      if(pName.includes('double top')){
        // Genuine Double Top: Two distinct mountain peaks separated by an intervening trough (valley/neckline)
        let bestP1 = -1, bestP2 = -1, bestTrough = Infinity;
        const n = visibleSlice.length;
        if(n >= 8){
          // Find local swing highs
          const peaks = [];
          for(let i = 1; i < n - 1; i++){
            const h = Number(visibleSlice[i].high);
            if(h >= Number(visibleSlice[i-1].high) && h >= Number(visibleSlice[i+1].high)){
              peaks.push({ i, h, candle: visibleSlice[i] });
            }
          }
          // Pick two highest peaks separated by at least 4 candles with a lower trough between them
          let bestScore = -Infinity;
          for(let j = 0; j < peaks.length; j++){
            for(let k = j + 1; k < peaks.length; k++){
              const p1 = peaks[j], p2 = peaks[k];
              if(p2.i - p1.i >= 4){
                let minTrough = Infinity;
                for(let m = p1.i; m <= p2.i; m++){
                  minTrough = Math.min(minTrough, Number(visibleSlice[m].low));
                }
                const drop = Math.min(p1.h, p2.h) - minTrough;
                if(drop > 0){
                  const symmetry = -Math.abs(p1.h - p2.h);
                  const score = (p1.h + p2.h) + symmetry * 3 + drop * 2;
                  if(score > bestScore){
                    bestScore = score;
                    bestP1 = p1.i;
                    bestP2 = p2.i;
                    bestTrough = minTrough;
                  }
                }
              }
            }
          }
        }
        if(bestP1 < 0 || bestP2 < 0){
          bestP1 = Math.floor(n * 0.25);
          bestP2 = Math.floor(n * 0.75);
          bestTrough = Math.min(...visibleSlice.map(c => Number(c.low)));
        }
        const pkCandles = [visibleSlice[bestP1], visibleSlice[bestP2]].filter(Boolean);
        pkCandles.forEach(pk => {
          const idx = a.indexOf(pk);
          if(idx >= 0){
            const px = pad.l + (idx + 0.5) * step;
            const py = y(Number(pk.high)) - 8;
            x.fillStyle = '#ef4444';
            x.font = 'bold 15px sans-serif';
            x.textAlign = 'center';
            x.fillText('▼', px, py);
            // Draw small mountain peak dot
            x.beginPath();
            x.arc(px, y(Number(pk.high)), 3.5, 0, Math.PI * 2);
            x.fillStyle = '#ef4444';
            x.fill();
          }
        });
        // Draw dashed neckline at intervening trough
        if(bestTrough < Infinity){
          const nlY = y(bestTrough);
          x.strokeStyle = 'rgba(239, 68, 68, 0.6)';
          x.setLineDash([4, 4]);
          x.lineWidth = 1.2;
          x.beginPath();
          x.moveTo(zoneLeft, nlY);
          x.lineTo(zoneRight, nlY);
          x.stroke();
          x.setLineDash([]);
        }
      } else if(pName.includes('double bottom')){
        // Genuine Double Bottom: Two distinct mountain troughs separated by an intervening crest
        let bestV1 = -1, bestV2 = -1, bestCrest = -Infinity;
        const n = visibleSlice.length;
        if(n >= 8){
          const troughs = [];
          for(let i = 1; i < n - 1; i++){
            const l = Number(visibleSlice[i].low);
            if(l <= Number(visibleSlice[i-1].low) && l <= Number(visibleSlice[i+1].low)){
              troughs.push({ i, l, candle: visibleSlice[i] });
            }
          }
          let bestScore = Infinity;
          for(let j = 0; j < troughs.length; j++){
            for(let k = j + 1; k < troughs.length; k++){
              const v1 = troughs[j], v2 = troughs[k];
              if(v2.i - v1.i >= 4){
                let maxCrest = -Infinity;
                for(let m = v1.i; m <= v2.i; m++){
                  maxCrest = Math.max(maxCrest, Number(visibleSlice[m].high));
                }
                const rise = maxCrest - Math.max(v1.l, v2.l);
                if(rise > 0){
                  const symmetry = Math.abs(v1.l - v2.l);
                  const score = (v1.l + v2.l) + symmetry * 3 - rise * 2;
                  if(score < bestScore){
                    bestScore = score;
                    bestV1 = v1.i;
                    bestV2 = v2.i;
                    bestCrest = maxCrest;
                  }
                }
              }
            }
          }
        }
        if(bestV1 < 0 || bestV2 < 0){
          bestV1 = Math.floor(n * 0.25);
          bestV2 = Math.floor(n * 0.75);
          bestCrest = Math.max(...visibleSlice.map(c => Number(c.high)));
        }
        const vlCandles = [visibleSlice[bestV1], visibleSlice[bestV2]].filter(Boolean);
        vlCandles.forEach(vl => {
          const idx = a.indexOf(vl);
          if(idx >= 0){
            const px = pad.l + (idx + 0.5) * step;
            const py = y(Number(vl.low)) + 18;
            x.fillStyle = '#10b981';
            x.font = 'bold 15px sans-serif';
            x.textAlign = 'center';
            x.fillText('▲', px, py);
            x.beginPath();
            x.arc(px, y(Number(vl.low)), 3.5, 0, Math.PI * 2);
            x.fillStyle = '#10b981';
            x.fill();
          }
        });
        if(bestCrest > -Infinity){
          const nlY = y(bestCrest);
          x.strokeStyle = 'rgba(16, 185, 129, 0.6)';
          x.setLineDash([4, 4]);
          x.lineWidth = 1.2;
          x.beginPath();
          x.moveTo(zoneLeft, nlY);
          x.lineTo(zoneRight, nlY);
          x.stroke();
          x.setLineDash([]);
        }
      } else if(pName.includes('triangle') || pName.includes('compression')){
        // Converging upper resistance line and lower support line across swing pivots
        if(visibleSlice.length >= 4){
          const n = visibleSlice.length;
          // Find peak 1 in first half, peak 2 in second half
          let p1 = { h: -Infinity, i: 0 }, p2 = { h: -Infinity, i: n - 1 };
          let v1 = { l: Infinity, i: 0 }, v2 = { l: Infinity, i: n - 1 };
          const midIdx = Math.floor(n / 2);
          for(let i = 0; i < midIdx; i++){
            const ch = Number(visibleSlice[i].high), cl = Number(visibleSlice[i].low);
            if(ch > p1.h) p1 = { h: ch, i };
            if(cl < v1.l) v1 = { l: cl, i };
          }
          for(let i = midIdx; i < n; i++){
            const ch = Number(visibleSlice[i].high), cl = Number(visibleSlice[i].low);
            if(ch > p2.h) p2 = { h: ch, i };
            if(cl < v2.l) v2 = { l: cl, i };
          }
          const p1x = pad.l + (sIdx - view.start + p1.i + 0.5) * step;
          const p1y = y(p1.h);
          const p2x = pad.l + (sIdx - view.start + p2.i + 0.5) * step;
          const p2y = y(p2.h);
          x.strokeStyle = '#f59e0b';
          x.lineWidth = 2;
          x.beginPath(); x.moveTo(p1x, p1y); x.lineTo(p2x, p2y); x.stroke();

          const v1x = pad.l + (sIdx - view.start + v1.i + 0.5) * step;
          const v1y = y(v1.l);
          const v2x = pad.l + (sIdx - view.start + v2.i + 0.5) * step;
          const v2y = y(v2.l);
          x.beginPath(); x.moveTo(v1x, v1y); x.lineTo(v2x, v2y); x.stroke();

          // Connect endpoints to form a closed triangle
          x.setLineDash([2, 2]);
          x.strokeStyle = 'rgba(245, 158, 11, 0.4)';
          x.beginPath(); x.moveTo(p1x, p1y); x.lineTo(v1x, v1y); x.stroke();
          x.setLineDash([]);
        }
      } else {
        // Outline candles cleanly without massive vertical background fill
        const maxH = Math.max(...visibleSlice.map(c=>Number(c.high)));
        const minL = Math.min(...visibleSlice.map(c=>Number(c.low)));
        const boxTop = y(maxH) - 4;
        const boxBottom = y(minL) + 4;
        x.strokeStyle = hp.border || '#1890ff';
        x.lineWidth = 1.5;
        x.strokeRect(zoneLeft, boxTop, zoneW, Math.max(12, boxBottom - boxTop));
      }

      // Clean top pattern tag badge
      const labelText = `✦ ${hp.name || 'Pattern'} (${hp.confidence || 75}%)`;
      x.font = 'bold 9.5px IBM Plex Mono, monospace';
      x.textAlign = 'left';
      const tw = x.measureText(labelText).width + 12;
      const tagLeft = Math.max(pad.l + 2, Math.min(w - pad.r - tw - 2, zoneLeft));
      x.fillStyle = hp.border || '#1890ff';
      x.beginPath();
      x.roundRect(tagLeft, pad.t + 4, tw, 18, 4);
      x.fill();
      x.fillStyle = '#ffffff';
      x.fillText(labelText, tagLeft + 6, pad.t + 16.5);
      x.restore();
    }
  }

  a.forEach((v,i)=>{const xx=pad.l+(i+.5)*step,yo=y(+v.open),yc=y(+v.close);const up=+v.close>=+v.open;x.strokeStyle=x.fillStyle=up?css('--buy'):css('--sell');x.beginPath();x.moveTo(xx,y(+v.high));x.lineTo(xx,y(+v.low));x.stroke();const bw=Math.max(2,step*.55);x.fillRect(xx-bw/2,Math.min(yo,yc),bw,Math.max(1,Math.abs(yc-yo)))});

  // Overlays (Bollinger Bands, Supertrend, SMA, EMA, VWAP)
  state.appliedIndicators.forEach((ind, indIdx)=>{
    if(isOscillator(ind.name)) return;
    const series=appliedOverlaySeries(ind.name,ind.params);
    const isHighlighted = state.highlightIndicatorIdx === indIdx;
    if(!series)return;

    // Multi-band Bollinger Bands
    if(ind.name==='Bollinger Bands'&&Array.isArray(series)&&series[0]&&typeof series[0]==='object'){
      const sub=series.slice(view.start,view.start+view.count);
      x.save();
      x.beginPath();
      let started=false;
      sub.forEach((val,i)=>{if(!val||val.upper==null)return;const xx=pad.l+(i+.5)*step,yy=y(val.upper);if(!started){x.moveTo(xx,yy);started=true}else x.lineTo(xx,yy)});
      for(let i=sub.length-1;i>=0;i--){const val=sub[i];if(!val||val.lower==null)continue;const xx=pad.l+(i+.5)*step,yy=y(val.lower);x.lineTo(xx,yy)}
      x.closePath();
      x.fillStyle='rgba(232,184,75,0.06)';
      x.fill();
      ['upper','mid','lower'].forEach((bandKey,bIdx)=>{
        x.beginPath(); let bStarted=false;
        sub.forEach((val,i)=>{if(!val||val[bandKey]==null)return;const xx=pad.l+(i+.5)*step,yy=y(val[bandKey]);if(!bStarted){x.moveTo(xx,yy);bStarted=true}else x.lineTo(xx,yy)});
        x.strokeStyle=bIdx===1?(ind.color||css('--gold')):'rgba(232,184,75,0.45)';
        x.lineWidth=bIdx===1?1.4:1;
        x.stroke();
      });
      x.restore();
      return;
    }

    // Standard Overlay Line (SMA, EMA, VWAP, Supertrend)
    x.beginPath();let started=false;
    const sub=series.slice(view.start,view.start+view.count);
    sub.forEach((val,i)=>{if(val==null)return;const xx=pad.l+(i+.5)*step,yy=y(val);if(!started){x.moveTo(xx,yy);started=true}else x.lineTo(xx,yy)});
    if(ind.name==='Supertrend'){
      const lastVal=sub[sub.length-1], curPrice=+a[a.length-1]?.close||0;
      x.strokeStyle=curPrice>=lastVal?css('--buy'):css('--sell');
    } else {
      x.strokeStyle=ind.color||css('--gold');
    }
    x.lineWidth=1.5;x.stroke();
  });

  // Dedicated Oscillator Sub-Pane (RSI, Stochastic, MACD, etc.)
  if(hasOsc&&oscH>30){
    const oscTop=pad.t+plotH+8, oscPlotH=oscH-16;
    x.save();
    x.fillStyle='rgba(10,13,18,0.45)';
    x.fillRect(pad.l,oscTop,plotW,oscPlotH);
    x.strokeStyle='rgba(128,138,155,0.22)';
    x.lineWidth=1;
    x.beginPath();x.moveTo(pad.l,oscTop);x.lineTo(w-pad.r,oscTop);x.stroke();

    const y70=oscTop+(1-0.70)*oscPlotH, y30=oscTop+(1-0.30)*oscPlotH;
    x.strokeStyle='rgba(128,138,155,0.22)';
    x.setLineDash([3,3]);
    x.beginPath();x.moveTo(pad.l,y70);x.lineTo(w-pad.r,y70);x.moveTo(pad.l,y30);x.lineTo(w-pad.r,y30);x.stroke();
    x.setLineDash([]);
    x.fillStyle='rgba(128,138,155,0.6)';
    x.font='9px IBM Plex Mono,monospace';
    x.fillText('70',w-pad.r+8,y70+3);x.fillText('30',w-pad.r+8,y30+3);

    state.appliedIndicators.filter(i=>isOscillator(i.name)).forEach((ind,oIdx)=>{
      const series=appliedOverlaySeries(ind.name,ind.params);
      if(!series)return;
      x.beginPath();let started=false;
      const sub=series.slice(view.start,view.start+view.count);
      sub.forEach((val,i)=>{if(val==null)return;const xx=pad.l+(i+.5)*step,yy=oscTop+(1-Math.max(0,Math.min(100,val))/100)*oscPlotH;if(!started){x.moveTo(xx,yy);started=true}else x.lineTo(xx,yy)});
      x.strokeStyle=ind.color||'#E8B84B';x.lineWidth=1.6;x.stroke();
      const curVal=sub[sub.length-1];
      x.fillStyle=ind.color||'#E8B84B';x.font='bold 9.5px IBM Plex Mono,monospace';
      x.fillText(`${ind.name}: ${curVal!=null?fmt(curVal):'—'}`,pad.l+8+oIdx*115,oscTop+14);
    });
    x.restore();
  }
    state.drawings.forEach((q,dIdx)=>{
      x.save();
      const isSelected = (state.selectedDrawingIdx === dIdx);
      const isHovered = (state.hoverDrawing === dIdx);
      if(isSelected || isHovered){
        x.shadowColor = isSelected ? '#00e5ff' : '#26D9A6';
        x.shadowBlur = isSelected ? 12 : 6;
        x.lineWidth = isSelected ? 2.6 : 1.8;
      } else {
        x.lineWidth = 1.2;
      }
      x.strokeStyle = isSelected ? '#00e5ff' : (q.color||css('--gold'));
      x.fillStyle = q.fill||'rgba(38,217,166,.12)';
      if(q.type==='h'){
        const yy=y(q.price);x.beginPath();x.moveTo(pad.l,yy);x.lineTo(w-pad.r,yy);x.stroke();
        if(q.price!=null && yy>=pad.t-4 && yy<=h-pad.b+4){
          const txt=fmt(q.price);x.font='bold 9.5px IBM Plex Mono,monospace';
          const tw=x.measureText(txt).width+8;const by=Math.max(pad.t,Math.min(h-pad.b-16,yy-8));
          x.fillStyle=isSelected ? '#00e5ff' : (q.color||css('--gold'));
          x.beginPath();x.roundRect(w-pad.r+2,by,tw,16,3);x.fill();
          x.fillStyle='#0A0D12';x.fillText(txt,w-pad.r+6,by+11);
        }
      }else if(q.type==='v'){
        const xx=pad.l+(q.i-view.start+.5)*step;x.beginPath();x.moveTo(xx,pad.t);x.lineTo(xx,h-pad.b);x.stroke();
      }else if(['line','ray','arrow','trend_ray'].includes(q.type)){
        const x1=pad.l+(q.i1-view.start+.5)*step,y1=y(q.p1),x2=pad.l+(q.i2-view.start+.5)*step,y2=y(q.p2);
        x.beginPath();
        if(q.type==='trend_ray'||q.infinite){
          const dx=x2-x1, dy=y2-y1;
          x.moveTo(x1 - dx*30, y1 - dy*30);
          x.lineTo(x2 + dx*30, y2 + dy*30);
        }else if(q.type==='ray'){
          x.moveTo(x1,y1);
          x.lineTo(x2+(x2-x1)*20, y2+(y2-y1)*20);
        }else{
          x.moveTo(x1,y1);
          x.lineTo(x2,y2);
        }
        x.stroke();
        if(q.p1!=null && q.p2!=null){
          [{px:x1,py:y1,pr:q.p1,isStart:true},{px:x2,py:y2,pr:q.p2,isStart:false}].forEach(pt=>{
            if(pt.px>=pad.l-10 && pt.px<=w-pad.r+10 && pt.py>=pad.t-10 && pt.py<=h-pad.b+10){
              x.beginPath();
              x.arc(pt.px,pt.py,isSelected?6:3.5,0,Math.PI*2);
              x.fillStyle=isSelected ? '#ffffff' : (q.color||css('--gold'));
              if(isSelected){
                x.strokeStyle = '#00e5ff';
                x.lineWidth = 2.5;
                x.shadowColor = '#00e5ff';
                x.shadowBlur = 8;
                x.fill();
                x.stroke();
              } else {
                x.fill();
              }
              const txt=fmt(pt.pr);x.font='bold 9px IBM Plex Mono,monospace';
              const tw=x.measureText(txt).width+8;
              const tagY=pt.isStart?Math.max(pad.t+14,pt.py-7):Math.min(h-pad.b-6,pt.py+15);
              const tagX=Math.max(pad.l+2,Math.min(w-pad.r-tw-2,pt.px-tw/2));
              x.fillStyle='rgba(10,13,18,0.88)';x.strokeStyle=isSelected ? '#00e5ff' : (q.color||css('--gold'));
              x.lineWidth=1;x.beginPath();x.roundRect(tagX,tagY-11,tw,15,3);x.fill();x.stroke();
              x.fillStyle=isSelected ? '#00e5ff' : (q.color||css('--gold'));x.fillText(txt,tagX+4,tagY);
            }
          });
        }
        if(q.type==='arrow'){x.beginPath();x.moveTo(x2,y2);x.lineTo(x2-7,y2-4);x.lineTo(x2-4,y2-10);x.closePath();x.fill();}
      }else if(q.type==='rect'||q.type==='range'){
        const x1=pad.l+(Math.min(q.i1,q.i2)-view.start+.5)*step,x2=pad.l+(Math.max(q.i1,q.i2)-view.start+.5)*step,y1=y(Math.max(q.p1,q.p2)),y2=y(Math.min(q.p1,q.p2));
        x.fillRect(x1,y1,x2-x1,y2-y1);x.strokeRect(x1,y1,x2-x1,y2-y1);
      }else if(q.type==='rr'){
        const xx=pad.l+(q.i-view.start+.5)*step,xe=w-pad.r,ye=y(q.entry),ys=y(q.stop),yt=y(q.target);
        x.fillStyle='rgba(255,92,114,.18)';x.fillRect(xx,Math.min(ye,ys),xe-xx,Math.abs(ys-ye));
        x.fillStyle='rgba(38,217,166,.18)';x.fillRect(xx,Math.min(ye,yt),xe-xx,Math.abs(yt-ye));
        x.strokeStyle=css('--sell');x.beginPath();x.moveTo(xx,ys);x.lineTo(xe,ys);x.stroke();
        x.strokeStyle=css('--buy');x.beginPath();x.moveTo(xx,yt);x.lineTo(xe,yt);x.stroke();
      }else if(q.type==='fib'){
        const x1=pad.l+(q.i1-view.start+.5)*step,x2=pad.l+(q.i2-view.start+.5)*step;
        [0,.236,.382,.5,.618,.786,1].forEach(r=>{
          const py=q.p1+(q.p2-q.p1)*r,yy=y(py);x.beginPath();x.moveTo(x1,yy);x.lineTo(x2,yy);x.stroke();
        });
      }
      x.restore();
    });

    // Interactive Trendline Drawing Preview (Item 30: Point 1 dot + dotted line till cursor)
    if(state.pendingDrawing && state.drawingStage && state.drawingStage.length >= 1){
      const p1 = state.drawingStage[0];
      const p1x = pad.l + (p1.i - view.start + 0.5) * step;
      const p1y = y(p1.price);
      x.save();
      x.beginPath();
      x.arc(p1x, p1y, 6, 0, Math.PI * 2);
      x.fillStyle = '#00e5ff';
      x.shadowColor = '#00e5ff';
      x.shadowBlur = 10;
      x.fill();
      x.strokeStyle = '#ffffff';
      x.lineWidth = 2;
      x.stroke();

      if(state.cursorPoint){
        const p2x = pad.l + (state.cursorPoint.i - view.start + 0.5) * step;
        const p2y = y(state.cursorPoint.price);
        x.beginPath();
        x.setLineDash([4, 4]);
        x.strokeStyle = '#00e5ff';
        x.lineWidth = 1.8;
        x.moveTo(p1x, p1y);
        x.lineTo(p2x, p2y);
        x.stroke();

        x.setLineDash([]);
        x.beginPath();
        x.arc(p2x, p2y, 4.5, 0, Math.PI * 2);
        x.fillStyle = 'rgba(0, 229, 255, 0.85)';
        x.fill();
        x.strokeStyle = '#ffffff';
        x.lineWidth = 1.5;
        x.stroke();
      }
      x.restore();
    }
    if(Number.isFinite(Number(state.latestLive))){
      const lp=Number(state.latestLive), ly=y(lp);
      if(ly>=pad.t-2 && ly<=h-pad.b+2){
        x.save(); x.strokeStyle=css('--gold'); x.globalAlpha=0.78; x.setLineDash([3,4]); x.beginPath(); x.moveTo(pad.l,ly); x.lineTo(w-pad.r,ly); x.stroke(); x.setLineDash([]);
        x.fillStyle=css('--surface-3'); x.strokeStyle=css('--gold'); x.lineWidth=1;
        const txt=fmt(lp); const tw=x.measureText(txt).width+12; x.beginPath(); x.roundRect(w-pad.r+3,Math.max(pad.t,Math.min(h-pad.b-20,ly-10)),tw,20,5); x.fill(); x.stroke();
        x.fillStyle=css('--text'); x.font='10px IBM Plex Mono,monospace'; x.fillText(txt,w-pad.r+9,Math.max(pad.t+13,Math.min(h-pad.b-7,ly+3)));
        x.restore();
      }
    }
    if(state.cross){const cx=state.cross.x,cy=state.cross.y;x.save();x.strokeStyle=css('--text-dim');x.setLineDash([4,4]);x.beginPath();x.moveTo(pad.l,cy);x.lineTo(w-pad.r,cy);x.moveTo(cx,pad.t);x.lineTo(cx,h-pad.b);x.stroke();x.restore();axisLabels(cx,cy,state.cross.price,state.cross.label)}else hideAxisLabels();updateFastForward(view);
  }

  function updateCross(e){const r=document.getElementById('chartViewport').getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,view=getView();if(!view.data.length)return;const i=indexFromX(x,view),c=view.data[i];const price=priceFromY(y,view);state.cross={x:Math.max(12,Math.min(r.width-72,x)),y:Math.max(18,Math.min(r.height-36,y)),price,label:xLabel(c?.timestamp||Date.now()),index:view.start+i};draw()}
  const vp=document.getElementById('chartViewport');
  vp.addEventListener('contextmenu',e=>e.preventDefault());
  vp.addEventListener('selectstart',e=>e.preventDefault());
  vp.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'||e.pointerType==='pen')e.preventDefault()},{passive:false});
  function setChartInteractionMode(mode){
    state.interactionMode = mode;
    const b = document.getElementById('chartModeToggle');
    const isPan = mode === 'pan';
    if(b){
      b.innerHTML = isPan ? '<span id="chartModeToggleIcon" style="font-size:14px;">✛</span>' : '<span id="chartModeToggleIcon" style="font-size:14px;">✋</span>';
      b.classList.toggle('active', isPan);
      b.title = isPan ? 'Currently in Pan mode — Click to switch to Crosshair (✛)' : 'Currently in Crosshair mode — Click to switch to Pan (✋)';
    }
    vp.classList.toggle('pan-mode', isPan);
    vp.style.cursor = isPan ? 'grab' : 'crosshair';
    if(isPan){
      state.cross = null;
      hideAxisLabels();
    }
    draw();
  }

  function getDrawingHandleAt(idx, x, y, view){
    if(idx < 0 || idx >= state.drawings.length) return null;
    const q = state.drawings[idx];
    if(!q || q.p1 == null || q.p2 == null) return null;
    const pad = { l: 12, r: 72, t: 18, b: 36 };
    const hasOsc = state.appliedIndicators.some(i => isOscillator(i.name));
    const oscH = hasOsc ? Math.max(60, Math.min(Math.floor(vp.clientHeight * 0.48), Math.floor(vp.clientHeight * (state.oscHeightRatio || 0.23)))) : 0;
    const plotW = vp.clientWidth - pad.l - pad.r, plotH = vp.clientHeight - pad.t - pad.b - oscH;
    const step = plotW / Math.max(1, view.count);

    const lows = view.data.map(v => +v.low), highs = view.data.map(v => +v.high);
    let lo = Math.min(...lows), hi = Math.max(...highs);
    const baseRange = (hi - lo) || 1;
    const midShift = (state.panY || 0) * baseRange * 0.005;
    const mid = ((hi + lo) / 2) + midShift;
    const scaled = baseRange / (state.yScale || 1);
    hi = mid + scaled / 2; lo = mid - scaled / 2;
    hi += scaled * 0.08; lo -= scaled * 0.08;
    const yFromP = p => pad.t + (hi - p) / ((hi - lo) || 1) * plotH;
    const sx = i => pad.l + (i - view.start + 0.5) * step;

    const x1 = sx(q.i1 != null ? q.i1 : 0), y1 = yFromP(q.p1);
    const x2 = sx(q.i2 != null ? q.i2 : 0), y2 = yFromP(q.p2);

    const tol = 16;
    if(Math.hypot(x - x1, y - y1) <= tol) return 'p1';
    if(Math.hypot(x - x2, y - y2) <= tol) return 'p2';
    return 'body';
  }

  vp.addEventListener('pointermove',e=>{
    const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    if(state.dragDrawing){
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
      const handle = state.dragDrawing.handle || 'body';
      if(q&&orig){
        if(handle === 'p1'){
          if(orig.i1!=null) q.i1 = Math.max(0, orig.i1 + di);
          if(orig.p1!=null) q.p1 = orig.p1 + dp;
        } else if(handle === 'p2'){
          if(orig.i2!=null) q.i2 = Math.max(0, orig.i2 + di);
          if(orig.p2!=null) q.p2 = orig.p2 + dp;
        } else {
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
      }
      vp.classList.add('drawing-hover');
      vp.style.cursor=(handle === 'p1' || handle === 'p2') ? 'crosshair' : 'move';
      showDrawingTooltip(state.dragDrawing.idx,e.clientX,e.clientY);
      draw();
      return;
    }
    if(state.drag){
      const dx=e.clientX-state.drag.x, dy=e.clientY-state.drag.y, view=getView();
      if(state.drag.axis==='y'){
        state.yScale=Math.max(.5,Math.min(5,state.drag.startScale*Math.exp(-dy/Math.max(1,vp.clientHeight))));
      } else if(state.drag.axis==='both'){
        const step=(vp.clientWidth-84)/Math.max(1,view.count);
        state.panX=Math.max(0,Math.min(state.candles.length-view.count,Math.round(state.drag.startX-dx/Math.max(1,step))));
        state.panY=(state.drag.startY||0)+(dy*0.4);
      } else {
        const step=(vp.clientWidth-84)/Math.max(1,view.count);
        state.panX=Math.max(0,Math.min(state.candles.length-view.count,Math.round(state.drag.startX-dx/Math.max(1,step))));
      }
      draw();
      return;
    }
    if(state.interactionMode==='pan'){
      vp.style.cursor = 'grab';
      state.cross = null;
      hideAxisLabels();
      return;
    }
    updateCross(e);
    if(state.pendingDrawing && state.drawingStage && state.drawingStage.length > 0){
      state.cursorPoint = chartPoint({clientX: e.clientX, clientY: e.clientY});
      draw();
      return;
    }
    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;
    state.hoverDrawing=hit;
    const hoverHandle = hit >= 0 ? getDrawingHandleAt(hit, x, y, getView()) : null;
    if(hit>=0){
      vp.classList.add('drawing-hover');
      vp.style.cursor=(hoverHandle === 'p1' || hoverHandle === 'p2') ? 'crosshair' : 'move';
      showDrawingTooltip(hit,e.clientX,e.clientY);
    }
    else if(ih>=0){ vp.classList.add('drawing-hover'); vp.style.cursor='crosshair'; showDrawingTooltip(-1,e.clientX,e.clientY,ih); }
    else { vp.classList.remove('drawing-hover'); vp.style.cursor=state.interactionMode==='pan'?'grab':'crosshair'; showDrawingTooltip(-1,0,0); }
  });

  vp.addEventListener('pointerdown',e=>{
    if(e.button!==0) return;
    const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    const view=getView();
    if(x>vp.clientWidth-72 && !state.pendingDrawing && state.interactionMode!=='pan'){
      state.drag={x:e.clientX,y:e.clientY,startX:state.panX,startY:state.panY,startScale:state.yScale,axis:'y'};
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if(state.pendingDrawing){
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
    }
    const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:findDrawingAt(x,y);
    const ih = hit < 0 ? indicatorHit(x, y) : -1;
    state.selectedDrawingIdx = hit;
    state.selectedIndicatorIdx = ih;
    draw();
    if(hit>=0&&!state.panArmed&&!state.yPanArmed&&state.interactionMode!=='pan'){
      const handle = getDrawingHandleAt(hit, x, y, view) || 'body';
      state.dragDrawing={
        idx:hit,
        handle:handle,
        startX:e.clientX,
        startY:e.clientY,
        orig:JSON.parse(JSON.stringify(state.drawings[hit])),
        moved:false
      };
      showDrawingTooltip(hit,e.clientX,e.clientY);
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if(state.yPanArmed||state.panArmed||state.interactionMode==='pan'){
      state.drag={
        x:e.clientX,
        y:e.clientY,
        startX:state.panX,
        startY:state.panY||0,
        startScale:state.yScale||1,
        axis:state.yPanArmed?'y':(state.interactionMode==='pan'?'both':'x')
      };
      state.yPanArmed=false;
      state.panArmed=false;
      vp.style.cursor='grabbing';
      vp.setPointerCapture(e.pointerId);
      return;
    }
  });

  vp.addEventListener('pointerup',e=>{
    state.drag=null;
    state.dragDrawing=null;
    state.panArmed=false;
    state.yPanArmed=false;
    vp.classList.remove('drawing-hover');
    if(state.interactionMode==='pan'){
      vp.classList.add('pan-mode');
      vp.style.cursor='grab';
    } else {
      vp.classList.remove('pan-mode');
      vp.style.cursor='crosshair';
    }
    showDrawingTooltip(-1,0,0);
    draw();
    try{vp.releasePointerCapture(e.pointerId)}catch(_){}
  });

  vp.addEventListener('pointerleave',()=>{
    if(!state.drag&&!state.dragDrawing){
      state.cross=null;
      vp.classList.remove('drawing-hover');
      draw();
      showDrawingTooltip(-1,0,0);
    }
  });

  window.addEventListener('keydown', e => {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (state.selectedDrawingIdx != null && state.selectedDrawingIdx >= 0 && state.selectedDrawingIdx < (state.drawings || []).length) {
        state.drawings.splice(state.selectedDrawingIdx, 1);
        state.selectedDrawingIdx = -1;
        state.hoverDrawing = -1;
        showDrawingTooltip(-1, 0, 0);
        renderApplied();
        draw();
        toast('Drawing deleted');
      } else if (state.selectedIndicatorIdx != null && state.selectedIndicatorIdx >= 0 && state.selectedIndicatorIdx < (state.appliedIndicators || []).length) {
        state.appliedIndicators.splice(state.selectedIndicatorIdx, 1);
        state.selectedIndicatorIdx = -1;
        showDrawingTooltip(-1, 0, 0);
        renderApplied();
        draw();
        toast('Indicator removed');
      }
    }
  });

  vp.addEventListener('dblclick',e=>{
    const r=vp.getBoundingClientRect(),x=e.clientX-r.left;
    if(x>vp.clientWidth-72){
      state.yPanArmed=true; state.panArmed=false;
      toast('Y-axis pan armed — drag vertically');
    } else if(!state.pendingDrawing){
      setChartInteractionMode('pan');
      toast('Pan mode enabled: Drag chart horizontally and vertically');
    }
  });

  vp.addEventListener('wheel',e=>{
    if(!e.ctrlKey) return;
    e.preventDefault();
    const view=getView(),r=vp.getBoundingClientRect(),x=e.clientX-r.left,i=indexFromX(x,view),ratio=i/Math.max(1,view.count-1),old=state.zoom;
    state.zoom=Math.max(.45,Math.min(6,old*(e.deltaY<0?1.12:.89)));
    const nc=Math.max(20,Math.min(state.candles.length,Math.floor(state.visible/state.zoom)));
    state.panX=Math.max(0,Math.min(state.candles.length-nc,Math.round(view.start+ratio*(view.count-nc))));
    draw();
  },{passive:false});

  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){
      state.pendingDrawing=null; state.drawingStage=[]; state.dragDrawing=null; state.drag=null;
      state.panArmed=false; state.yPanArmed=false;
      setChartInteractionMode('crosshair');
      hideAxisLabels(); draw();
    }
  });

  document.getElementById('chartFullscreen').onclick=async()=>{
    try{ const shell=document.getElementById('chartShell'); if(!document.fullscreenElement) await shell.requestFullscreen(); else await document.exitFullscreen(); }
    catch(e){ toast('Full screen is unavailable in this browser'); }
  };

  document.addEventListener('fullscreenchange',()=>{ state.fullscreen=!!document.fullscreenElement; setTimeout(draw,50); });

  document.getElementById('chartModeToggle')?.addEventListener('click',()=>{
    const next = state.interactionMode === 'pan' ? 'crosshair' : 'pan';
    setChartInteractionMode(next);
    toast(next === 'pan' ? 'Pan mode enabled: Drag chart freely across time & price' : 'Crosshair inspection mode enabled');
  });
  document.getElementById('chartFastForward').onclick=()=>{state.panX=Math.max(0,state.candles.length-Math.floor(state.visible/state.zoom));state.cross=null;hideAxisLabels();draw()};
  let __liveChartPollBusy=false, __lastLiveCandleFetch=0, __nextCandleRetryAt=0;
  async function refreshLiveChart(){
    if(__liveChartPollBusy||!S)return;
    const tab=document.querySelector('.navtab.active')?.dataset.tab; if(tab!=='charts')return;
    __liveChartPollBusy=true;
    try{
      const q=(window.__CA_WL_QUOTES||{})[String(S||'').toUpperCase()] || APP_CACHE.quote || await loadHeaderQuote();
      if(q?.ltp!=null){
        state.latestLive=Number(q.ltp); state.priceState=(q?.market_session?.active || market.nse)?'LIVE':'EOD';
        if(state.candles.length && state.priceState==='LIVE'){updateLiveCandle(Number(q.ltp),q.timestamp||Date.now());}
        const st=document.getElementById('signalUpdated'); if(st) st.textContent=`${state.priceState} · ${formatTime(q.timestamp||Date.now())}`; draw();
      }
      const now=Date.now();
      if(now-__lastLiveCandleFetch>=60000 && now>=__nextCandleRetryAt){
        __lastLiveCandleFetch=now;
        // Refresh from a sufficiently wide recent range. Never replace a newer
        // candle series with a shorter/staler response (the old days=1 refresh
        // was overwriting a valid Aug 26 series with Aug 25 data after close).
        const d=await A('/api/market/candles/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}&days=${Math.max(7,state.history)}&_=${Date.now()}`,{timeoutMs:12000,cache:'no-store'});
        const candles=Array.isArray(d.candles)?d.candles:[];
        if(candles.length){
          const fresh=candles.map(c=>({...c}));
          const lastTs=x=>{const v=x?.timestamp;if(v==null)return 0;const n=Number(v);if(Number.isFinite(n))return n>1e12?n:n*1000;const t=Date.parse(String(v));return Number.isFinite(t)?t:0};
          const oldLast=lastTs(state.candles[state.candles.length-1]), newLast=lastTs(fresh[fresh.length-1]);
          if(!oldLast || newLast>=oldLast){
            state.candles=fresh;
            candleCache.set(`${S}|${state.tf}|${state.history}`,{candles:fresh.map(c=>({...c})),timestamp:d.timestamp||new Date().toISOString()});
            state.panX=Math.max(0,state.candles.length-Math.floor(state.visible/state.zoom));
            draw();
          }
        }
        void loadChartBundle(false);
      }
    }catch(e){console.debug('[CA Trader live chart]',e)} finally{__liveChartPollBusy=false}
  }
  setInterval(()=>{if(document.visibilityState==='visible' && document.querySelector('.navtab.active')?.dataset.tab==='charts') refreshLiveChart()},12000);

  function updateHeader(q){
    if(!q)return;
    const rawLtp = q.ltp != null ? Number(q.ltp) : null;
    if(rawLtp == null || !Number.isFinite(rawLtp) || rawLtp <= 0) return;
    const l = rawLtp;
    const ch = q.session_change!=null?Number(q.session_change):(q.net_change==null?null:Number(q.net_change));
    const pct = q.session_change_pct!=null?Number(q.session_change_pct):(q.change_pct==null?null:Number(q.change_pct));
    const sym=q.symbol||S||'—';
    const ltpText=fmt(l);
    const chText=ch==null?'—':`${ch>0?'+':''}${fmt(ch)}${pct==null?'':` (${pct>0?'+':''}${fmt(pct)}%)`}`;
    const chClass='chart-symbol-change '+(ch>0?'up':ch<0?'down':'');
    const compName=q.metadata?.name||q.metadata?.short_name||q.symbol||S||'Select an instrument';

    const panels=[
      ['chartSymbolTitle','chartSymbolLtp','chartSymbolChange','chartCompanyName'],
      ['dashSymbol','dashLtp','dashChange',null],
      ['optionsSymbol','optionsLtp','optionsChange','optionsCompany'],
      ['recoSymbol','recoLtp','recoChange',null],
      ['newsSymbol','newsLtp','newsChange',null],
      ['fundSymbol','fundLtp','fundChange',null],
      ['autoSymbolTitle','autoLtp','autoChange',null]
    ];
    panels.forEach(([tId,lId,cId,nId])=>{
      const t=document.getElementById(tId); if(t) t.textContent=sym;
      const elL=document.getElementById(lId); if(elL) elL.textContent=ltpText;
      const elC=document.getElementById(cId); if(elC){ elC.textContent=chText; elC.className=chClass; }
      if(nId){ const elN=document.getElementById(nId); if(elN) elN.textContent=compName; }
    });

    const dsl=document.getElementById('dashboardSelectedLtp'); if(dsl){ dsl.textContent=ltpText; dsl.style.fontWeight='700'; }
    const dsc=document.getElementById('dashboardSelectedChange'); if(dsc){ dsc.textContent=chText; dsc.style.fontWeight='700'; dsc.style.color=ch>0?'var(--buy)':ch<0?'var(--sell)':'var(--text-dim)'; }
  }
  function updateOptionHeader(q){ updateHeader(q); }
  async function subscribeInstrument(symbol){if(!symbol||subscribedSymbols.has(symbol))return null;try{const r=await A('/api/market/stream/subscribe',{method:'POST',body:JSON.stringify({instrument:symbol})});if(r.instrument_key){state.currentKey=r.instrument_key;keyToSymbol[r.instrument_key]=symbol;subscribedSymbols.add(symbol)}return r}catch(e){console.debug(e);return null}}

  function updateLiveCandle(ltp,ts){
    if(!state.candles.length||!Number.isFinite(Number(ltp)))return;
    const interval=candleIntervalMs(),now=Number(ts)||Date.now();
    const parts=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now));
    const get=k=>Number(parts.find(p=>p.type===k)?.value||0);
    const y=get('year'),m=get('month'),day=get('day');
    const anchor=Date.UTC(y,m-1,day,3,45,0,0); // 09:15 IST
    let bucket=anchor;
    if(state.tf==='1D') bucket=anchor;
    else if(now>=anchor) bucket=anchor+Math.floor((now-anchor)/interval)*interval;
    else bucket=anchor-86400000;
    let last=state.candles[state.candles.length-1];
    const lastTs=new Date(last.timestamp||last.ts||now).getTime();
    if(!Number.isFinite(lastTs)||Math.floor(lastTs/interval)!==Math.floor(bucket/interval)){
      last={timestamp:new Date(bucket).toISOString(),open:Number(ltp),high:Number(ltp),low:Number(ltp),close:Number(ltp),volume:0};
      state.candles.push(last);
    }else{
      last.close=Number(ltp);last.high=Math.max(Number(last.high)||Number(ltp),Number(ltp));last.low=Math.min(Number(last.low)||Number(ltp),Number(ltp));
    }
    state.latestLive=Number(ltp);draw();
  }

  let ws=null,wsTimer=null;
  const keyToSymbol={};
  window.__CA_WS_CONNECTED=false;
  window.__CA_WS_TICKS=window.__CA_WS_TICKS||{};
  function playLowNotificationTone(){try{const C=window.AudioContext||window.webkitAudioContext;if(!C)return;const ctx=new C(),o=ctx.createOscillator(),g=ctx.createGain();o.frequency.value=620;g.gain.setValueAtTime(0.0001,ctx.currentTime);g.gain.exponentialRampToValueAtTime(0.018,ctx.currentTime+0.02);g.gain.exponentialRampToValueAtTime(0.0001,ctx.currentTime+0.18);o.connect(g).connect(ctx.destination);o.start();o.stop(ctx.currentTime+0.2)}catch(_){}}
  async function subscribeAllLive(){
    const group=window.__CA_WATCHLIST_GROUP; const items=group?.items||[];
    const instruments=items.map(i=>({symbol:String(i.symbol||'').trim(),instrument_key:String(i.instrument_key||'').trim()})).filter(x=>x.symbol||x.instrument_key);
    if(S&&!instruments.some(x=>String(x.symbol||'').toUpperCase()===String(S).toUpperCase()))instruments.push({symbol:S});
    if(!instruments.length)return;
    try{const d=await A('/api/market/stream/subscribe-batch',{method:'POST',body:JSON.stringify({instruments})});for(const x of (d.subscribed||[])){if(x.instrument_key)keyToSymbol[x.instrument_key]=x.symbol||x.instrument_key;if(x.symbol)subscribedSymbols.add(x.symbol);}}catch(e){console.debug('[CA Trader stream subscribe]',e)}
  }
  function applyLiveTick(d){
    const rawSym=String(d.symbol||keyToSymbol[d.instrument_key]||d.instrument_key||'').trim();
    const key=rawSym.toUpperCase();
    const ltp=Number(d.ltp);
    if(!key||!Number.isFinite(ltp)||ltp<=0)return;
    if(d.instrument_key)keyToSymbol[d.instrument_key]=rawSym;
    window.__CA_WS_TICKS=window.__CA_WS_TICKS||{};
    window.__CA_WL_QUOTES=window.__CA_WL_QUOTES||{};
    window.__CA_WS_TICKS[key]=Date.now();
    const cached=window.__CA_WL_QUOTES[key]||{};
    // Displayed intraday change is always LTP versus today's session open.
    // The broker's cp/net_change may refer to previous close and must never overwrite this.
    const sessionOpenRaw=d.session_open ?? d.open ?? cached.session_open ?? cached.open ?? null;
    const sessionOpen=Number(sessionOpenRaw);
    const net=(Number.isFinite(sessionOpen)&&sessionOpen>0)?(ltp-sessionOpen):(cached.session_change!=null?Number(cached.session_change):null);
    const pct=(Number.isFinite(sessionOpen)&&sessionOpen>0)?(net/sessionOpen*100):(cached.session_change_pct!=null?Number(cached.session_change_pct):null);
    const q={...cached,symbol:rawSym,ltp,open:Number.isFinite(sessionOpen)&&sessionOpen>0?sessionOpen:cached.open,session_open:Number.isFinite(sessionOpen)&&sessionOpen>0?sessionOpen:cached.session_open,session_change:net,session_change_pct:pct,cp:d.cp??cached.cp,net_change:cached.net_change,change_pct:cached.change_pct,instrument_key:d.instrument_key||cached.instrument_key,timestamp:d.ltt||d.timestamp||Date.now(),source:d.source||'websocket',market_session:{active:true}};
    window.__CA_WL_QUOTES[key]=q;

    document.querySelectorAll('.wl-item').forEach(row=>{
      if(String(row.dataset.symbol||'').toUpperCase()!==key)return;
      const l=row.querySelector('.wl-ltp');if(l)l.textContent=fmt(ltp);
      const c=row.querySelector('.wl-chg');if(c){c.textContent=net==null?'—':`${net>0?'+':''}${fmt(net)}${pct!=null?` (${pct>0?'+':''}${fmt(pct)}%)`:''}`;c.className='wl-chg '+(net>0?'up':net<0?'down':'')}
    });
    document.querySelectorAll('[data-pos-symbol]').forEach(row=>{
      if(String(row.dataset.posSymbol||'').toUpperCase()!==key)return;
      const l=row.querySelector('.pos-ltp');if(l)l.textContent=fmt(ltp);
      const avg=Number(row.dataset.avg||0),qty=Number(row.dataset.qty||0),side=String(row.dataset.side||'BUY').toUpperCase();
      const pnl=(side==='BUY'?(ltp-avg):(avg-ltp))*qty;const pe=row.querySelector('.pos-pnl');if(pe){pe.textContent=fmtMoney(pnl);pe.className='pos-pnl '+(pnl>=0?'cell-up':'cell-down')}
    });
    document.querySelectorAll('[data-order-symbol]').forEach(row=>{if(String(row.dataset.orderSymbol||'').toUpperCase()===key){const el=row.querySelector('.order-ltp');if(el)el.textContent=fmt(ltp)}});
    document.querySelectorAll('[data-mover-symbol]').forEach(row=>{
      if(String(row.dataset.moverSymbol||'').toUpperCase()!==key)return;const l=row.querySelector('.mover-ltp')||row.querySelector('td:nth-child(2)');if(l)l.textContent=fmt(ltp);
      if(cp){const ch=ltp-cp,p=ch/cp*100,ce=row.querySelector('.mover-change')||row.querySelector('td:nth-child(3)'),pe=row.querySelector('.mover-pct')||row.querySelector('td:nth-child(4)');if(ce){ce.textContent=`${ch>0?'+':''}${fmt(ch)}`;ce.className='cell-num '+(ch>=0?'cell-up':'cell-down')}if(pe){pe.textContent=`${p>0?'+':''}${fmt(p)}%`;pe.className='cell-num '+(p>=0?'cell-up':'cell-down')}}
    });
    document.querySelectorAll('#dashboardOptionMini [data-option-key],[data-option-key]').forEach(row=>{if(d.instrument_key&&row.dataset.optionKey===d.instrument_key){const el=row.querySelector('.option-live-ltp')||row.querySelector('[data-option-ltp]');if(el)el.textContent=fmt(ltp);row.dataset.ltp=ltp;}});
    document.querySelectorAll('#optionChainTable [data-call-key],#optionChainTable [data-put-key]').forEach(row=>{if(d.instrument_key===row.dataset.callKey){const el=row.querySelector('.call-ltp');if(el)el.textContent=fmt(ltp)}if(d.instrument_key===row.dataset.putKey){const el=row.querySelector('.put-ltp');if(el)el.textContent=fmt(ltp)}});
    if(key===String(S||'').toUpperCase()){
      APP_CACHE.quote=q;state.latestLive=ltp;state.priceState='LIVE';updateHeader(q);
      if(state.candles?.length&&document.querySelector('.navtab.active')?.dataset.tab==='charts')updateLiveCandle(ltp,q.timestamp);
      const de=document.getElementById('dashboardSelectedLtp');if(de)de.textContent=fmt(ltp);const oe=document.getElementById('optionsLtp');if(oe)oe.textContent=fmt(ltp);
    }
  }
  // Public bridge for the independent continuous quote lane.
  // The bridge stays inside this IIFE so it can update the private chart state safely.
  window.__CA_APPLY_LIVE_TICK = applyLiveTick;
  window.__CA_LIVE_QUOTE_BRIDGE_READY = true;
  function applyMarketStreamState(d){for(const [k,v] of Object.entries(d.mapping||{})){keyToSymbol[k]=v;subscribedSymbols.add(v);}for(const q of (d.snapshots||[]))applyLiveTick(q);if(d.connected!=null)window.__CA_WS_CONNECTED=!!d.connected;}
  function connectWS(){
    if(ws&&(ws.readyState===WebSocket.OPEN||ws.readyState===WebSocket.CONNECTING))return;
    try{ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/events`);}catch(_){setTimeout(connectWS,2500);return;}
    ws.onopen=async()=>{window.__CA_WS_CONNECTED=true;window.__CA_WS_LAST_TICK=Date.now();clearInterval(wsTimer);wsTimer=setInterval(()=>{try{ws.send('ping')}catch(_){ }},20000);await subscribeAllLive()};
    ws.onmessage=e=>{try{const d=JSON.parse(e.data);if(d.type==='market_stream_state'){applyMarketStreamState(d);return}if(d.type==='notification'){showLiveAlert(d.title||'Market alert',d.body||'',String(d.severity||'').toLowerCase().includes('high')?'sell':'neutral');return}if(d.type==='market_tick')applyLiveTick(d)}catch(err){console.debug('[CA Trader WS]',err)}};
    ws.onclose=()=>{window.__CA_WS_CONNECTED=false;clearInterval(wsTimer);setTimeout(connectWS,6000)};ws.onerror=()=>{window.__CA_WS_CONNECTED=false;try{ws.close()}catch(_){}};
  }
  async function subscribeInstrument(symbol){if(!symbol||subscribedSymbols.has(symbol))return null;try{const r=await A('/api/market/stream/subscribe',{method:'POST',body:JSON.stringify({instrument:symbol})});if(r.instrument_key){state.currentKey=r.instrument_key;keyToSymbol[r.instrument_key]=symbol;subscribedSymbols.add(symbol)}return r}catch(e){console.debug(e);return null}}
  function updateLiveCandle(ltp,ts){
    if(!state.candles.length||!Number.isFinite(Number(ltp)))return;
    const interval=candleIntervalMs(),now=Number(ts)||Date.now(); const parts=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now)); const get=k=>Number(parts.find(p=>p.type===k)?.value||0); const y=get('year'),m=get('month'),day=get('day'); const anchor=Date.UTC(y,m-1,day,3,45,0,0); let bucket=anchor;if(state.tf==='1D')bucket=anchor;else if(now>=anchor)bucket=anchor+Math.floor((now-anchor)/interval)*interval;else bucket=anchor-86400000; let last=state.candles[state.candles.length-1]; const lastTs=new Date(last.timestamp||last.ts||now).getTime(); if(!Number.isFinite(lastTs)||Math.floor(lastTs/interval)!==Math.floor(bucket/interval)){last={timestamp:new Date(bucket).toISOString(),open:Number(ltp),high:Number(ltp),low:Number(ltp),close:Number(ltp),volume:0};state.candles.push(last)}else{last.close=Number(ltp);last.high=Math.max(Number(last.high)||Number(ltp),Number(ltp));last.low=Math.min(Number(last.low)||Number(ltp),Number(ltp))}state.latestLive=Number(ltp);draw();
  }
  async function loadHeaderQuote(){if(!S)return null;const key=String(S).toUpperCase();const cached=(window.__CA_WL_QUOTES||{})[key]||(window.__CA_WL_QUOTES||{})[S];if(cached?.ltp!=null){APP_CACHE.quote=cached;state.latestLive=Number(cached.ltp);updateHeader(cached);return cached;}let q=null;try{const bulk=await A('/api/market/quotes?instruments='+encodeURIComponent(S),{timeoutMs:6000,cache:'no-store'});q=(bulk.items||[])[0]||null;}catch(e){}if(!q){try{q=await A('/api/market/quote/'+encodeURIComponent(S),{timeoutMs:6000,cache:'no-store'});}catch(e){}}if(!q){const streamTick=window.CATraderLiveMarket?.getLastLtp?.(S)||(window.__CA_WL_QUOTES||{})[key]?.ltp;if(streamTick!=null&&Number(streamTick)>0){q={symbol:S,ltp:Number(streamTick),net_change:0,change_pct:0};}}if(q&&q.ltp!=null){
      APP_CACHE.quote=q; state.latestLive=Number(q.ltp);
      state.priceState=(market?.nse||q?.market_session?.active)?'LIVE':'EOD';
      updateHeader(q); document.documentElement.dataset.quoteState='ok';
      const st=document.getElementById('signalUpdated');
      if(st && Number.isFinite(Number(state.latestLive))) st.textContent=`${state.priceState} · ${formatTime(q.timestamp||Date.now())}`;
    }else{document.documentElement.dataset.quoteState='unavailable';setTimeout(loadHeaderQuote,1200);}
    draw();
    return q}
  const candleCache = window.__CA_CANDLE_CACHE = window.__CA_CANDLE_CACHE || new Map();
  const analysisCache = window.__CA_ANALYSIS_CACHE = window.__CA_ANALYSIS_CACHE || new Map();
  const analysisInflight = window.__CA_ANALYSIS_INFLIGHT = window.__CA_ANALYSIS_INFLIGHT || new Map();
  // Shared analysis/tab state. This script is a separate IIFE from the UI/tab-loader script below,
  // so its state must be read through window-backed values rather than cross-IIFE lexical variables.
  const tabLoadedAt = window.__CA_TAB_LOADED_AT = window.__CA_TAB_LOADED_AT || new Map();
  const TAB_TTL = 120000;
  // Keep a local formatter in this IIFE; the later utility IIFE has its own scope.
  const formatTime = v => { if(!v) return 'Time unavailable'; let d; if(typeof v==='number' || /^\d+$/.test(String(v))) d=new Date(Number(v)); else d=new Date(v); if(isNaN(d)) return String(v); return d.toLocaleString('en-IN',{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hour12:false})+' IST'; };
  let chartRequestSeq=0;
  let selectionSeq=0;
  function analysisKey(name){return `${name}|${S}|${state.tf}|${state.history}`;}
  async function runCachedAnalysis(name, fn, ttl=60000){
    if(!S)return null;
    const key=analysisKey(name), now=Date.now(), hit=analysisCache.get(key);
    if(hit && now-hit.ts<ttl) return hit.data;
    if(analysisInflight.has(key)) return analysisInflight.get(key);
    const promise=Promise.resolve().then(fn).then(data=>{analysisCache.set(key,{ts:Date.now(),data});return data}).finally(()=>analysisInflight.delete(key));
    analysisInflight.set(key,promise); return promise;
  }

  function renderLocalAnalysisFallback(reason='Provider analysis unavailable'){
    const rows=fallbackTechnicalRows();
    renderIndicators(rows);
    const pats=[];
    const a=state.candles||[];
    for(let i=Math.max(1,a.length-10);i<a.length;i++){
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
    $('chartPatternList').innerHTML=cp.length?cp.map(p=>`<div class="pattern-card"><div><b>${esc(p.pattern)}</b><div class="muted">Confidence ${fmt(p.confidence)}%</div><div class="muted">${esc(p.description)}</div></div><span class="tag neutral">LOCAL</span></div>`).join(''):`<div class="muted">No local chart pattern detected in the loaded candles.</div>`;
    const selected=rows.length?rows[0]:null;
    $('mtfTable').innerHTML=`<div class="mtf-cell"><div class="mtf-tf">${esc(state.tf)}</div><span class="tag ${selected?.signal==='BUY'?'buy':selected?.signal==='SELL'?'sell':'neutral'}">${esc(selected?.signal||'NEUTRAL')}</span><div class="muted" style="margin-top:4px">Local evidence · other timeframes loading separately</div>${newsAiBadge(e)}</div></div>`;
    $('mtfNote').textContent='Fallback evidence shown from loaded candles; multi-timeframe provider scan will continue separately.';
    if($('signalUpdated'))$('signalUpdated').textContent=`Analysis fallback · ${reason}`;
  }

  async function loadChartMtf(){
    if(!S)return null;
    const key=`mtf:${S}|${state.tf}`;
    const cached=analysisCache.get(key), now=Date.now();
    if(cached && now-cached.ts<20000)return cached.data;
    if(analysisInflight.has(key))return analysisInflight.get(key);
    const promise=(async()=>{
      try{
        const d=await A('/api/analysis/chart-mtf/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}`,{timeoutMs:12000});
        const items=d.items||[];
        $('mtfTable').innerHTML=items.map((r,i)=>`<div class="mtf-cell" data-mtf-index="${i}"><div class="mtf-tf">${esc(r.timeframe)}</div><span class="tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}">${esc(r.signal)}</span><div class="muted" style="margin-top:4px">RSI ${fmt(r.technical?.rsi)} · ADX ${fmt(r.technical?.adx)}${r.error?` · ${esc(r.error)}`:''}</div></div>`).join('')||'<div class="muted">No multi-timeframe evidence returned.</div>';
        $('mtfNote').textContent='Multi-timeframe evidence updated from the selected symbol.';
        analysisCache.set(key,{ts:Date.now(),data:d}); APP_CACHE.mtf=d; return d;
      }catch(e){
        $('mtfTable').innerHTML=`<div class="muted">Multi-timeframe evidence unavailable: ${esc(e.message)}</div>`;
        $('mtfNote').textContent='Selected-timeframe technical and pattern analysis remains available.'; return null;
      }
    })().finally(()=>analysisInflight.delete(key));
    analysisInflight.set(key,promise); return promise;
  }

  async function loadChartBundle(force=false){
    if(!S)return null;
    const key=`bundle:${S}|${state.tf}`;
    const cached=analysisCache.get(key), now=Date.now();
    if(!force&&cached&&now-cached.ts<20000)return cached.data;
    if(analysisInflight.has(key))return analysisInflight.get(key);
    const status=$('signalUpdated');
    if(status)status.textContent='Loading technical & pattern analysis…';
    if($('patternScanStatus'))$('patternScanStatus').textContent='Loading candlestick patterns…';
    if($('structureStatus'))$('structureStatus').textContent='Loading trend & structure…';
    if($('chartPatternStatus'))$('chartPatternStatus').textContent='Loading chart patterns…';
    const promise=(async()=>{
      try{
        const d=await A('/api/analysis/chart-bundle/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}&include_mtf=false`,{timeoutMs:15000});
        analysisCache.set(key,{ts:Date.now(),data:d}); window.__CA_CHART_BUNDLE={key:S+'|'+state.tf,ts:Date.now(),data:d};
        APP_CACHE.technical=d.technical||null;APP_CACHE.mtf=d.mtf||null;
        const rows=d.technical?.technical?.indicators||[];renderIndicators(rows);
        const items=d.mtf?.items||[];
        $('mtfTable').innerHTML=items.length?items.map((r,i)=>`<div class="mtf-cell" data-mtf-index="${i}"><div class="mtf-tf">${esc(r.timeframe)}</div><span class="tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}">${esc(r.signal)}</span><div class="muted" style="margin-top:4px">RSI ${fmt(r.technical?.rsi)} · ADX ${fmt(r.technical?.adx)}</div></div>`).join(''):'<div class="muted">Loading multi-timeframe evidence separately…</div>';
        $('mtfNote').textContent='Selected-timeframe analysis loads first; multi-timeframe evidence is fetched independently.';
        void loadChartMtf();
        const patterns=d.patterns?.patterns||[];
        const patternRows = patterns.slice(-20).reverse();
        window.__caPatterns = patternRows;
        $('patternList').innerHTML=patternRows.length?patternRows.map((p,i)=>`
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
        if(typeof bindPatternClicks === 'function') bindPatternClicks();
        $('patternScanStatus').textContent=`Loaded ${patterns.length} candlestick pattern(s)`;
        const st=d.structure||{};
        $('structureStatus').textContent=`${st.candles_used||0} candles analyzed`;
        // User Request 4: Trend strictly out of 3 (Uptrend, Downtrend, Sideways Market) with technical reasons
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

        const outcomeReason = displayTrend === 'Uptrend'
          ? 'Buyers maintaining control above 20-EMA; continuation towards upper resistance targets favored while higher lows hold.'
          : displayTrend === 'Downtrend'
          ? 'Sellers defending lower highs below 50-EMA; breakdown re-testing of swing support levels favored until moving averages reverse.'
          : 'Price consolidating between key pivot zones; flat 20 & 50 EMA slopes and ADX indicate balanced supply/demand and rangebound oscillation.';

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
            <span class="tag ${trendClass}">${displayTrend === 'Uptrend' ? 'Bullish Target' : displayTrend === 'Downtrend' ? 'Bearish Retest' : 'Rangebound'}</span>
          </div>
          <div class="pattern-card">
            <div>
              <b>Recent Validated Setups</b>
              <div class="muted">${(st.pattern_signals||[]).map(p=>esc(p.pattern)).join(' · ')||'Structural swing alignment'}</div>
            </div>
          </div>
        `;
        const cp=d.chart_patterns?.patterns||[];
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
        if(typeof bindPatternClicks === 'function') bindPatternClicks();
        if(status)status.textContent=`Analysis updated ${formatTime(Date.now())}`;
        return d;
      }catch(e){renderLocalAnalysisFallback(e.message);void loadChartMtf();return null;}
    })().finally(()=>analysisInflight.delete(key));
    analysisInflight.set(key,promise); return promise;
  }

  async function loadChart(){if(!S)return;const seq=++chartRequestSeq;const key=`${S}|${state.tf}|${state.history}`;let q=null;
    const cached=candleCache.get(key);
    const cacheAge = cached?.fetchedAt ? Date.now()-cached.fetchedAt : Infinity;
    if(cached?.candles?.length && cacheAge < 15000){state.candles=cached.candles.map(c=>({...c}));state.panX=Math.max(0,state.candles.length-Math.floor(state.visible/state.zoom));draw();document.getElementById('signalUpdated').textContent=`Refreshing · ${formatTime(cached.timestamp)}`;}
    else {draw();document.getElementById('signalUpdated').textContent='Loading latest candles…';}
    const quotePromise=loadHeaderQuote().catch(()=>null);
    const candleUrl='/api/market/candles/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}&days=${state.history}&_=${Date.now()}`;
    const candlePromise=A(candleUrl,{timeoutMs:15000,cache:'no-store'}).catch(e=>({__error:e}));
    const subPromise=(window.__CA_MARKET_STREAM_ENABLED!==false?subscribeInstrument(S):Promise.resolve(null)).catch(()=>null);
    const [quoteRes,candleRes]=await Promise.all([quotePromise,candlePromise]);
    if(candleRes?.__error){const msg=String(candleRes.__error.message||'Market data unavailable');document.getElementById('signalUpdated').textContent=cached?.candles?.length?`Live refresh failed · showing cached data · ${msg}`:`Retrying candle data… ${msg}`;setTimeout(async()=>{if(seq!==chartRequestSeq||!S)return;try{const retry=await A(candleUrl,{timeoutMs:15000,cache:'no-store'});const rc=Array.isArray(retry?.candles)?retry.candles:[];if(rc.length){state.candles=rc.map(c=>({...c}));state.panX=Math.max(0,state.candles.length-Math.floor(state.visible/state.zoom));draw();document.getElementById('signalUpdated').textContent=`Updated · ${retry.latest_candle_ist||formatTime(Date.now())} IST`;if(retry.live_quote?.ltp!=null){state.latestLive=Number(retry.live_quote.ltp);updateHeader(retry.live_quote);}}}catch(_){}},1200);}
    else {const candles=Array.isArray(candleRes?.candles)?candleRes.candles:[];const stale=!!candleRes?.stale;const expected=candleRes?.latest_session_ist||'';if(candles.length){state.candles=candles.map(c=>({...c}));candleCache.set(key,{candles:state.candles.map(c=>({...c})),timestamp:candleRes.timestamp||new Date().toISOString(),fetchedAt:Date.now(),latestSession:candleRes.latest_candle_ist||expected});state.panX=Math.max(0,state.candles.length-Math.floor(state.visible/state.zoom));state.panY=0;draw();document.getElementById('signalUpdated').textContent=stale?`EOD · ${candleRes.latest_candle_ist||expected} IST`:`Updated · ${candleRes.latest_candle_ist||expected} IST`;}else if(!state.candles.length){draw();document.getElementById('signalUpdated').textContent='Retrying latest candle data…';setTimeout(async()=>{if(seq!==chartRequestSeq||!S)return;try{const retry=await A('/api/market/candles/'+encodeURIComponent(S)+`?timeframe=${encodeURIComponent(state.tf)}&days=${state.history}&_=${Date.now()}`,{timeoutMs:15000,cache:'no-store'});const rc=Array.isArray(retry?.candles)?retry.candles:[];if(rc.length){state.candles=rc.map(c=>({...c}));state.panX=Math.max(0,state.candles.length-Math.floor(state.visible/state.zoom));draw();document.getElementById('signalUpdated').textContent=`Updated · ${retry.latest_candle_ist||formatTime(Date.now())} IST`;if(retry.live_quote?.ltp!=null){state.latestLive=Number(retry.live_quote.ltp);updateLiveCandle(Number(retry.live_quote.ltp),retry.live_quote.timestamp||Date.now())}}else document.getElementById('signalUpdated').textContent='No candle data returned by Upstox.'}catch(e){document.getElementById('signalUpdated').textContent='Market candle data unavailable.'}},700);}}
    if(candleRes?.live_quote?.ltp!=null){
      state.latestLive=Number(candleRes.live_quote.ltp); state.priceState=candleRes.live?'LIVE':'EOD'; updateHeader(candleRes.live_quote);
      if(candleRes.live) updateLiveCandle(Number(candleRes.live_quote.ltp),candleRes.live_quote.timestamp||Date.now()); else { const st=document.getElementById('signalUpdated'); if(st) st.textContent=`EOD · ${candleRes.latest_candle_ist||formatTime(candleRes.live_quote.timestamp||Date.now())} IST`; draw(); }
    }
    if(q)updateOptionHeader(q);
    // Always start the consolidated analysis after candles resolve.
    // Do not gate this on panel visibility: the selected instrument can change while
    // the chart panel is being activated, and the old visibility guard could prevent
    // the analysis request from ever being sent, leaving all analysis cards stuck.
    if(seq===chartRequestSeq && S) {
      void loadChartBundle(false);
      void loadChartAiSuggestions(false);
      if(typeof updateChartRecoBanner === 'function') void updateChartRecoBanner();
    }
    if(seq===chartRequestSeq && q)updateOptionHeader(q);
    if(typeof updateOscSplitterPosition === 'function') updateOscSplitterPosition();
  }

  // ================= CA AI CHART ASSISTANT (Trendlines, Horizontal S/R & Indicators) =================
  let __currentChartAiData = null;

  function computeLocalChartAiSuggestions(candles){
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
  }

  async function loadChartAiSuggestions(forceOpen = false){
    const panel = document.getElementById('chartAiPanel');
    const content = document.getElementById('chartAiContent');
    const badge = document.getElementById('chartAiBadge');
    if(!panel || !content) return;
    if(forceOpen) panel.style.display = 'block';

    const localData = computeLocalChartAiSuggestions(state.candles);
    __currentChartAiData = localData;
    renderChartAiPanel(localData);
    const totalCount = localData.trendlines.length + localData.horizontal_levels.length + localData.indicators.length;
    if(badge) badge.textContent = String(totalCount);

    if(S){
      try {
        const d = await A(`/api/analysis/chart-ai-suggestions/${encodeURIComponent(S)}?timeframe=${encodeURIComponent(state.tf)}&days=${state.history || 7}`, {timeoutMs: 12000});
        if(d && (d.trendlines?.length || d.horizontal_levels?.length)){
          __currentChartAiData = d;
          renderChartAiPanel(d);
          const serverCount = (d.trendlines?.length || 0) + (d.horizontal_levels?.length || 0) + (d.indicators?.length || 0);
          if(badge) badge.textContent = String(serverCount);
        }
      } catch(err){
        console.debug('[CA AI chart suggestions]', err);
      }
    }
  }

  function renderChartAiPanel(data){
    const content = document.getElementById('chartAiContent');
    if(!content || !data) return;
    const trendlines = data.trendlines || [];
    const horizontal = data.horizontal_levels || [];
    const indicators = data.indicators || [];

    let html = `
      <!-- TRENDLINES BOX -->
      <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px 12px;">
        <div style="font-weight:700;font-size:11.5px;color:var(--text);margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
          <span>▲ Algorithmic Trend Lines</span>
          <span class="tag neutral" style="font-size:8.5px;">${trendlines.length} Available</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:7px;">
          ${trendlines.length ? trendlines.map((t, idx) => `
            <div style="border:1px solid var(--border-soft);background:var(--surface);border-radius:6px;padding:7px 9px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">
                <b style="font-size:11px;color:${t.color || 'var(--gold)'};">${esc(t.name)}</b>
                <span class="tag ${t.category==='top_to_top'?'sell':'buy'}" style="font-size:8.5px;">${t.slope_pct >= 0 ? '+' : ''}${t.slope_pct}%</span>
              </div>
              <div style="font-family:var(--font-mono);font-size:10.5px;color:var(--text);margin-bottom:4px;">
                <span style="color:var(--text-dim);">Coordinates:</span> <b>₹${fmt(t.p1)}</b> → <b>₹${fmt(t.p2)}</b>
              </div>
              <div style="font-size:9.5px;color:var(--text-dim);margin-bottom:6px;">${esc(t.description || '')} · ${t.touches} touch validation(s)</div>
              <button class="btn ghost small" data-apply-trendline="${idx}" style="width:100%;justify-content:center;font-size:10px;padding:3px 6px;border-color:var(--border);font-weight:600;">+ Apply Trendline to Chart</button>
            </div>
          `).join('') : '<div class="muted" style="font-size:10px;">No trendlines identified for current candles.</div>'}
        </div>
      </div>

      <!-- HORIZONTAL S/R BOX -->
      <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px 12px;">
        <div style="font-weight:700;font-size:11.5px;color:var(--text);margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
          <span> Structural Support & Resistance</span>
          <span class="tag neutral" style="font-size:8.5px;">${horizontal.length} Levels</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:7px;">
          ${horizontal.length ? horizontal.map((h, idx) => `
            <div style="border:1px solid var(--border-soft);background:var(--surface);border-radius:6px;padding:7px 9px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">
                <b style="font-size:11px;color:${h.color || 'var(--gold)'};">${esc(h.name)}</b>
                <span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--text);">₹${fmt(h.price)}</span>
              </div>
              <div style="font-size:9.5px;color:var(--text-dim);margin-bottom:6px;">${esc(h.description || '')}</div>
              <button class="btn ghost small" data-apply-horizontal="${idx}" style="width:100%;justify-content:center;font-size:10px;padding:3px 6px;border-color:var(--border);font-weight:600;">+ Apply Level to Chart</button>
            </div>
          `).join('') : '<div class="muted" style="font-size:10px;">No S/R levels identified.</div>'}
        </div>
      </div>

      <!-- INDICATORS BOX -->
      <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px 12px;">
        <div style="font-weight:700;font-size:11.5px;color:var(--text);margin-bottom:8px;display:flex;align-items:center;justify-content:space-between;">
          <span>■ Context-Aware Indicators</span>
          <span class="tag neutral" style="font-size:8.5px;">${indicators.length} Suggestions</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:7px;">
          ${indicators.length ? indicators.map((ind, idx) => `
            <div style="border:1px solid var(--border-soft);background:var(--surface);border-radius:6px;padding:7px 9px;">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:3px;">
                <b style="font-size:11px;color:var(--text);">${esc(ind.name)}${ind.params ? ` (${esc(ind.params)})` : ''}</b>
                <span class="tag neutral" style="font-size:8.5px;">Indicator</span>
              </div>
              <div style="font-size:9.5px;color:var(--text-dim);margin-bottom:6px;">${esc(ind.reason || '')}</div>
              <button class="btn ghost small" data-apply-indicator="${idx}" style="width:100%;justify-content:center;font-size:10px;padding:3px 6px;border-color:var(--border);font-weight:600;">+ Apply ${esc(ind.name)} to Chart</button>
            </div>
          `).join('') : '<div class="muted" style="font-size:10px;">No indicator suggestions available.</div>'}
        </div>
      </div>
    `;

    content.innerHTML = html;

    content.querySelectorAll('[data-apply-trendline]').forEach(btn => {
      btn.onclick = () => {
        const idx = Number(btn.dataset.applyTrendline);
        const t = trendlines[idx];
        if(!t) return;
        state.drawings.push({
          name: t.name,
          type: 'line',
          i1: t.i1,
          i2: t.i2,
          p1: t.p1,
          p2: t.p2,
          color: t.color || '#26D9A6',
          showLabels: true
        });
        renderApplied();
        draw();
        toast(`✦ Applied ${t.name}: ₹${fmt(t.p1)} → ₹${fmt(t.p2)}`);
      };
    });

    content.querySelectorAll('[data-apply-horizontal]').forEach(btn => {
      btn.onclick = () => {
        const idx = Number(btn.dataset.applyHorizontal);
        const h = horizontal[idx];
        if(!h) return;
        state.drawings.push({
          name: h.name,
          type: 'h',
          price: h.price,
          color: h.color || '#26D9A6',
          showLabels: true
        });
        renderApplied();
        draw();
        toast(`✦ Applied ${h.name} at ₹${fmt(h.price)}`);
      };
    });

    content.querySelectorAll('[data-apply-indicator]').forEach(btn => {
      btn.onclick = () => {
        const idx = Number(btn.dataset.applyIndicator);
        const ind = indicators[idx];
        if(!ind) return;
        if(duplicateIndicator(ind.name, ind.params)){
          toast(`${ind.name} is already applied`);
          return;
        }
        state.appliedIndicators.push({
          name: ind.name,
          params: ind.params,
          color: ind.color || '#EFFBF5'
        });
        renderApplied();
        draw();
        toast(`✦ Applied ${ind.name} indicator to chart`);
      };
    });
  }

  function applyAllChartAiSuggestions(){
    if(!__currentChartAiData) return;
    let addedCount = 0;
    (__currentChartAiData.trendlines || []).forEach(t => {
      state.drawings.push({
        name: t.name,
        type: 'line',
        i1: t.i1, i2: t.i2, p1: t.p1, p2: t.p2,
        color: t.color || '#26D9A6',
        showLabels: true
      });
      addedCount++;
    });
    (__currentChartAiData.horizontal_levels || []).forEach(h => {
      state.drawings.push({
        name: h.name,
        type: 'h',
        price: h.price,
        color: h.color || '#26D9A6',
        showLabels: true
      });
      addedCount++;
    });
    (__currentChartAiData.indicators || []).slice(0, 3).forEach(ind => {
      if(!duplicateIndicator(ind.name, ind.params)){
        state.appliedIndicators.push({
          name: ind.name,
          params: ind.params,
          color: ind.color || '#EFFBF5'
        });
        addedCount++;
      }
    });
    renderApplied();
    draw();
    toast(`✦ Applied ${addedCount} CA AI overlays & indicators to chart`);
  }

  function renderIndicators(rows){const body=document.getElementById('indicatorRows');if(!rows?.length){body.innerHTML='<tr><td colspan="5" class="muted">No indicator data available for this timeframe.</td></tr>';}else{body.innerHTML=rows.map(r=>`<tr><td><b>${r.name}</b></td><td>${fmt(r.value)}</td><td>${r.materiality}</td><td><span class="tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}">${r.signal}</span></td><td>${r.criteria||''}</td></tr>`).join('');} const pane=document.getElementById('indicatorAppliedPane'); if(pane){const selected=state.appliedIndicators||[];const wanted=selected.length?rows.filter(r=>selected.some(i=>i.name===r.name)):[];pane.innerHTML=wanted.length?wanted.map(r=>`<span class="indicator-live-chip"><b>${r.name}</b><span>${fmt(r.value)}</span><span class="tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}">${r.signal}</span></span>`).join(''):(selected.length?selected.map(i=>`<span class="indicator-live-chip"><b>${esc(i.name)}</b><span>Applied · waiting for value</span></span>`).join(''):'');} document.getElementById('signalUpdated').textContent=`Updated ${new Date().toLocaleTimeString('en-IN',{hour12:false})}`}
  function fallbackTechnicalRows(){const a=(state.candles||[]).map(c=>({o:Number(c.open),h:Number(c.high),l:Number(c.low),c:Number(c.close),v:Number(c.volume)||0})).filter(x=>[x.o,x.h,x.l,x.c].every(Number.isFinite));if(a.length<5)return [];const closes=a.map(x=>x.c),n=Math.min(14,Math.max(5,closes.length-1)),sma=p=>closes.slice(-Math.min(p,closes.length)).reduce((x,y)=>x+y,0)/Math.min(p,closes.length);let gains=0,losses=0;for(let i=Math.max(1,closes.length-n);i<closes.length;i++){const d=closes[i]-closes[i-1];if(d>=0)gains+=d;else losses+=-d}const rsi=losses===0?100:100-(100/(1+(gains/Math.max(losses,1e-9))));const ema=p=>{const k=2/(p+1),st=Math.max(0,closes.length-p);let e=closes.slice(st,st+p).reduce((x,y)=>x+y,0)/Math.max(1,Math.min(p,closes.length-st));for(let i=st+p;i<closes.length;i++)e=closes[i]*k+e*(1-k);return e};const e20=ema(Math.min(20,closes.length)),last=closes.at(-1),prev=closes.at(-2),trs=[];for(let i=Math.max(1,a.length-14);i<a.length;i++)trs.push(Math.max(a[i].h-a[i].l,Math.abs(a[i].h-a[i-1].c),Math.abs(a[i].l-a[i-1].c)));const atr=trs.reduce((x,y)=>x+y,0)/Math.max(1,trs.length);return [['SMA 20',sma(20),last>=sma(20)?'BUY':'SELL',`Price ${last>=sma(20)?'above':'below'} SMA 20`],['EMA 20',e20,last>=e20?'BUY':'SELL',`Price ${last>=e20?'above':'below'} EMA 20`],['RSI 14',rsi,rsi>=55?'BUY':rsi<=45?'SELL':'NEUTRAL',`RSI ${rsi>=55?'≥55 bullish':rsi<=45?'≤45 bearish':'45–55 neutral'}`],['ATR 14',atr,'NEUTRAL','Volatility range'],['Momentum',last-prev,last>=prev?'BUY':'SELL',`Last close ${last>=prev?'higher':'lower'} than prior close`]].map(([name,value,signal,criteria])=>({name,value,materiality:'LOCAL FALLBACK',signal,criteria}))}
  async function loadIndicators(){const d=await loadChartBundle(false);return d?.technical?.technical?.indicators||[];}
  async function loadMTF(){const d=await loadChartBundle(false);return d?.mtf?.items||[];}

  function formatPatternTimeRange(p){
    const f = p.from_time ? formatTime(p.from_time) : '';
    const t = p.to_time ? formatTime(p.to_time) : (p.timestamp ? formatTime(p.timestamp) : '');
    if(f && t && f !== t) return `${f} → ${t} (${p.timeframe || state.tf})`;
    if(t) return `${t} (${p.timeframe || state.tf})`;
    return `${p.timeframe || state.tf} formation`;
  }

  function bindPatternClicks(){
    const chartEl = $('mainChart') || $('chartCanvas') || $('chartViewport') || document.querySelector('.chart-wrap');

    document.querySelectorAll('[data-focus-pattern]').forEach(el=>el.onclick=async()=>{
      const p=(window.__caPatterns||[])[Number(el.dataset.patternIndex)];
      if(!p) return;
      const tf = p.timeframe;
      if(tf && tf !== state.tf){
        state.tf = tf;
        document.querySelectorAll('#timeframeGroup .tf-btn[data-tf]').forEach(x => x.classList.toggle('active', x.dataset.tf === tf));
        await loadChart();
      }
      const fromTs = p.from_time ? new Date(p.from_time).getTime() : 0;
      const toTs = (p.to_time || p.timestamp) ? new Date(p.to_time || p.timestamp).getTime() : Date.now();
      let startIdx = -1, endIdx = -1, bestFromDiff = Infinity, bestToDiff = Infinity;
      (state.candles || []).forEach((c, i) => {
        const cTs = new Date(c.timestamp || c.ts).getTime();
        if(fromTs > 0){
          const df = Math.abs(cTs - fromTs);
          if(df < bestFromDiff){ bestFromDiff = df; startIdx = i; }
        }
        const dt = Math.abs(cTs - toTs);
        if(dt < bestToDiff){ bestToDiff = dt; endIdx = i; }
      });
      if(endIdx < 0) endIdx = (state.candles || []).length - 1;
      if(startIdx < 0 || startIdx > endIdx) startIdx = Math.max(0, endIdx - 2);

      const isBull = p.signal === 'BUY' || String(p.prediction || '').toLowerCase().includes('bull') || String(p.pattern || '').toLowerCase().includes('bull');
      const isBear = p.signal === 'SELL' || String(p.prediction || '').toLowerCase().includes('bear') || String(p.pattern || '').toLowerCase().includes('bear');
      const color = isBull ? 'rgba(38,217,166,0.22)' : isBear ? 'rgba(255,92,114,0.22)' : 'rgba(232,184,75,0.22)';
      const border = isBull ? '#26D9A6' : isBear ? '#FF5C72' : '#E8B84B';

      state.highlightedPattern = {
        startIdx,
        endIdx,
        name: p.pattern,
        timeLabel: formatPatternTimeRange(p),
        color,
        border,
        confidence: p.confidence
      };

      const patternLen = Math.max(1, endIdx - startIdx + 1);
      if(state.visible < patternLen + 10) state.visible = patternLen + 15;
      const view = getView();
      const mid = Math.round((startIdx + endIdx) / 2);
      state.panX = Math.max(0, Math.min((state.candles || []).length - view.count, mid - Math.floor(view.count / 2)));
      draw();

      // Scroll smoothly to chart
      document.getElementById('chartViewport')?.scrollIntoView({ behavior: 'smooth', block: 'center' });

      if(window.__highlightTimeout) clearTimeout(window.__highlightTimeout);
      window.__highlightTimeout = setTimeout(() => {
        state.highlightedPattern = null;
        draw();
      }, 15000);

      toast(`✦ Highlighted ${p.pattern} (${formatPatternTimeRange(p)})`);
    });

    // Also bind Chart Patterns (Double Top, Double Bottom, Triangle, etc.)
    document.querySelectorAll('[data-focus-chart-pattern]').forEach(el => el.onclick = async () => {
      const p = (window.__caChartPatterns || [])[Number(el.dataset.chartPatternIndex)];
      if(!p) return;
      if(p.timeframe && p.timeframe !== state.tf){
        state.tf = p.timeframe;
        await loadChart();
      }
      const fromTs = p.from_time ? new Date(p.from_time).getTime() : 0;
      const toTs = (p.to_time || p.timestamp) ? new Date(p.to_time || p.timestamp).getTime() : Date.now();
      let startIdx = -1, endIdx = -1, bestFromDiff = Infinity, bestToDiff = Infinity;
      (state.candles || []).forEach((c, i) => {
        const cTs = new Date(c.timestamp || c.ts).getTime();
        if(fromTs > 0){
          const df = Math.abs(cTs - fromTs);
          if(df < bestFromDiff){ bestFromDiff = df; startIdx = i; }
        }
        const dt = Math.abs(cTs - toTs);
        if(dt < bestToDiff){ bestToDiff = dt; endIdx = i; }
      });
      if(endIdx < 0) endIdx = (state.candles || []).length - 1;
      if(startIdx < 0 || startIdx > endIdx) startIdx = Math.max(0, endIdx - 8);

      const isBull = p.signal === 'BUY' || String(p.pattern || '').toLowerCase().includes('bottom');
      const isBear = p.signal === 'SELL' || String(p.pattern || '').toLowerCase().includes('top') || String(p.pattern || '').toLowerCase().includes('head');
      const color = isBull ? 'rgba(38,217,166,0.22)' : isBear ? 'rgba(255,92,114,0.22)' : 'rgba(232,184,75,0.22)';
      const border = isBull ? '#26D9A6' : isBear ? '#FF5C72' : '#E8B84B';

      state.highlightedPattern = {
        startIdx,
        endIdx,
        name: p.pattern,
        timeLabel: formatPatternTimeRange(p),
        color,
        border,
        confidence: p.confidence
      };

      const patternLen = Math.max(1, endIdx - startIdx + 1);
      if(state.visible < patternLen + 10) state.visible = patternLen + 15;
      const view = getView();
      const mid = Math.round((startIdx + endIdx) / 2);
      state.panX = Math.max(0, Math.min((state.candles || []).length - view.count, mid - Math.floor(view.count / 2)));
      draw();

      // Scroll smoothly to chart
      document.getElementById('chartViewport')?.scrollIntoView({ behavior: 'smooth', block: 'center' });

      if(window.__highlightTimeout) clearTimeout(window.__highlightTimeout);
      window.__highlightTimeout = setTimeout(() => {
        state.highlightedPattern = null;
        draw();
      }, 15000);

      toast(`✦ Highlighted ${p.pattern} on chart`);
    });
  }

  async function scanPatterns(){return runCachedAnalysis('scanPatterns',async()=>{
    if(!S) return;
    const tfEl = document.getElementById('patternTimeframe');
    const fromEl = document.getElementById('patternFrom');
    const toEl = document.getElementById('patternTo');

    // Default to previous day 09:15 and current day 15:30 if empty
    if(fromEl && !fromEl.value){
      const y = new Date(Date.now() - 86400000);
      fromEl.value = `${y.getFullYear()}-${String(y.getMonth()+1).padStart(2,'0')}-${String(y.getDate()).padStart(2,'0')}T09:15`;
    }
    if(toEl && !toEl.value){
      const t = new Date();
      toEl.value = `${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}T15:30`;
    }

    const tf = tfEl?.value || 'all';
    const from = fromEl?.value || '';
    const to = toEl?.value || '';
    const qs = new URLSearchParams();
    if(tf && tf !== 'all') qs.set('timeframe', tf);
    if(from){ qs.set('from_date', from.slice(0,10)); qs.set('from_time', from); }
    if(to){ qs.set('to_date', to.slice(0,10)); qs.set('to_time', to); }
    document.getElementById('patternScanStatus').textContent='Scanning across timeframes…';
    try{
      const d = await A('/api/analysis/patterns/'+encodeURIComponent(S)+'?'+qs.toString());
      const rows = (d.patterns || []).slice(-30).reverse();
      document.getElementById('patternList').innerHTML = rows.length ? rows.map((p,i)=>`
        <div class="pattern-card" data-focus-pattern="1" data-pattern-index="${i}" style="cursor:pointer;" title="Click to highlight ${p.pattern} on chart">
          <div style="flex:1">
            <div style="display:flex;align-items:center;gap:6px;">
              <b>${p.pattern}</b>
              <span class="tag neutral" style="font-size:9px;padding:1px 5px;">${p.timeframe || state.tf}</span>
            </div>
            <div class="muted" style="font-size:10.5px;color:var(--gold);margin-top:2px;">⏱ ${formatPatternTimeRange(p)}</div>
            <div class="muted" style="font-size:10.5px;margin-top:2px;">${p.prediction || 'Confirmation required'}</div>
          </div>
          <span class="tag ${p.signal==='BUY'||String(p.prediction||'').toLowerCase().includes('bull')?'buy':p.signal==='SELL'||String(p.prediction||'').toLowerCase().includes('bear')?'sell':'neutral'}">${p.confidence}%</span>
        </div>
      `).join('') : '<div class="muted">No detected candlestick pattern in the selected range.</div>';
      window.__caPatterns = rows;
      bindPatternClicks();
      document.getElementById('patternScanStatus').textContent = `Observed ${rows.length} pattern(s) across ${d.timeframes?.length||1} timeframe(s)`;
      // Also refresh structure and chart patterns
      void loadChartBundle(true);
    }catch(e){
      const a=state.candles||[],rows=[];
      for(let i=Math.max(1,a.length-20);i<a.length;i++){
        const c=a[i],body=Math.abs(Number(c.close)-Number(c.open)),range=Math.max(1,Number(c.high)-Number(c.low));
        if(body/range>.65)rows.push({pattern:Number(c.close)>=Number(c.open)?'Bullish Body':'Bearish Body',timeframe:state.tf,prediction:Number(c.close)>=Number(c.open)?'Bullish continuation possible':'Bearish continuation possible',confidence:55,timestamp:c.timestamp||c.ts});
      }
      const use=rows.slice(-20).reverse();
      document.getElementById('patternList').innerHTML=use.length?use.map(p=>`
        <div class="pattern-card">
          <div style="flex:1">
            <b>${p.pattern}</b>
            <div class="muted" style="font-size:10.5px;margin-top:2px;">${p.prediction}</div>
          </div>
          <span class="tag ${p.prediction.startsWith('Bullish')?'buy':'sell'}">${p.confidence}%</span>
        </div>
      `).join(''):'<div class="muted">Patterns unavailable.</div>';
    }
  });}

  // 1-minute auto-refresh for pattern & structure scanner
  setInterval(() => {
    const activeTab = document.querySelector('.navtab.active')?.dataset.tab;
    if(activeTab === 'charts' && S) {
      scanPatterns();
    }
  }, 60000);

  // Saved Views System (Item 7)
  const btnSavedViews = document.getElementById('btnSavedViews');
  const savedViewsDropdownMenu = document.getElementById('savedViewsDropdownMenu');
  const btnSaveCurrentView = document.getElementById('btnSaveCurrentView');
  const savedViewsList = document.getElementById('savedViewsList');

  function renderSavedViewsList(){
    if(!savedViewsList) return;
    try {
      const views = JSON.parse(localStorage.getItem('ca_chart_views') || '[]');
      savedViewsList.innerHTML = views.length ? views.map((v, i) => `
        <div class="view-item" data-view-idx="${i}" style="padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;display:flex;align-items:center;justify-content:space-between;">
          <span>${esc(v.name)}</span>
          <span class="muted" style="font-size:9.5px;">${(v.indicators||[]).length} inds</span>
        </div>
      `).join('') : '<div class="muted" style="font-size:10.5px;padding:4px 8px;">No custom views yet</div>';
      savedViewsList.querySelectorAll('[data-view-idx]').forEach(item => {
        item.onclick = () => {
          const idx = Number(item.dataset.viewIdx);
          const v = views[idx];
          if(v && v.indicators){
            state.appliedIndicators = v.indicators;
            renderApplied();
            draw();
            toast(`Loaded view "${v.name}"`);
            if(savedViewsDropdownMenu) savedViewsDropdownMenu.style.display = 'none';
          }
        };
      });
    } catch(_) {}
  }

  btnSavedViews?.addEventListener('click', (e) => {
    e.stopPropagation();
    if(savedViewsDropdownMenu){
      const isClosed = savedViewsDropdownMenu.style.display === 'none' || !savedViewsDropdownMenu.style.display;
      savedViewsDropdownMenu.style.display = isClosed ? 'block' : 'none';
      if(isClosed) renderSavedViewsList();
    }
  });

  btnSaveCurrentView?.addEventListener('click', (e) => {
    e.stopPropagation();
    const name = prompt('Enter a name for this chart view:', `View ${new Date().toLocaleDateString()}`);
    if(!name) return;
    try {
      const views = JSON.parse(localStorage.getItem('ca_chart_views') || '[]');
      views.unshift({
        name: name.trim(),
        indicators: state.appliedIndicators || [],
        timeframe: state.tf || '5m',
        savedAt: new Date().toISOString()
      });
      localStorage.setItem('ca_chart_views', JSON.stringify(views.slice(0, 15)));
      renderSavedViewsList();
      toast(`Saved view "${name}"`);
    } catch(err) {
      toast('Failed to save view');
    }
  });

  function renderApplied(){
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
  }
  function duplicateIndicator(name,params){return state.appliedIndicators.some(x=>x.name===name&&x.params===params)}
  indSel.onchange=async e=>{const name=e.target.value;e.target.value='';if(!name)return;const def=indicators.find(x=>x[0]===name);const kind=name==='VWAP'?'drawing-like':'indicator';const cfg=await openToolModal(name,kind,def?.[1]);if(!cfg)return;if(duplicateIndicator(name,cfg.params)){toast('This indicator with the same parameters is already applied.');return}state.appliedIndicators.push({name,params:cfg.params,color:cfg.color});renderApplied();draw();await loadIndicators()};

  function chartPoint(e){const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,view=getView(),i=indexFromX(x,view),c=view.data[i];return {x,y,i:view.start+i,price:priceFromY(y,view),timestamp:c?.timestamp}}
  function drawingParams(q){if(!q)return '';if(q.type==='h')return `Price ${fmt(q.price)}`;if(q.type==='v')return `Candle ${q.i+1}`;if(q.type==='rr')return `Entry ${fmt(q.entry)} · SL ${fmt(q.stop)} · Target ${fmt(q.target)}`;if(['line','ray','arrow','fib','rect','range'].includes(q.type))return `${fmt(q.p1)} → ${fmt(q.p2)}`;return ''}
function currentLtp(){return APP_CACHE.quote?.ltp!=null?Number(APP_CACHE.quote.ltp):state.latestLive!=null?Number(state.latestLive):null}
  function drawingHit(q, pt, view) {
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
  }

function indicatorValueToY(val,view){const h=vp.clientHeight,pad={t:18,b:36},a=view.data;if(!a.length)return null;let lo=Math.min(...a.map(c=>+c.low)),hi=Math.max(...a.map(c=>+c.high));const baseRange=(hi-lo)||1,mid=(hi+lo)/2,scaled=baseRange/state.yScale;hi=mid+scaled/2;lo=mid-scaled/2;hi+=scaled*.08;lo-=scaled*.08;return pad.t+(hi-val)/Math.max(1,hi-lo)*(h-pad.t-pad.b)}
function indicatorHit(x,y){
  const view=getView(),a=view.data;
  if(!a.length||!state.appliedIndicators.length)return -1;
  const w=vp.clientWidth,h=vp.clientHeight;
  const hasOsc=state.appliedIndicators.some(i=>isOscillator(i.name));
  const oscH = hasOsc ? Math.max(60, Math.min(Math.floor(h * 0.48), Math.floor(h * (state.oscHeightRatio || 0.23)))) : 0;
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

  const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
  if(fsEl){
    if(el.parentNode !== fsEl) fsEl.appendChild(el);
  } else {
    if(el.parentNode !== document.body) document.body.appendChild(el);
  }

  const ltp = currentLtp();
  let title = '', paramsText = '', valText = '', sig = null, isDrawing = false;

  if (indicatorIdx >= 0) {
    const ind = state.appliedIndicators[indicatorIdx];
    if (!ind) { el.style.display = 'none'; return; }
    title = ` ${ind.name}`;
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
    title = ` ${q.name || q.type}`;
    paramsText = drawingParams(q);
    valText = '';
    sig = getDrawingSignal(q, ltp);
    sig = null; // Suppress buy/sell suggestion on drawings hover (Item 25b)
  }

  const sigClass = sig.signal.toLowerCase();
  el.className = `drawing-tooltip ${sigClass}`;
  const sigClass = sig ? sig.signal.toLowerCase() : 'neutral';
  el.className = isDrawing ? 'drawing-tooltip drawing-info' : `drawing-tooltip ${sigClass}`;
  el.innerHTML = `
    <div class="dt-title">${esc(title)}</div>
    <div class="dt-params">${esc(paramsText)}</div>
    ${valText ? `<div style="font-size:10px;color:var(--text);margin-bottom:3px">${esc(valText)}</div>` : ''}
    <div style="font-size:10px;color:var(--text-faint)">LTP: ₹${fmt(ltp)}</div>
    ${(!isDrawing && sig) ? `
    <div class="dt-signal-box ${sigClass}">
      <span class="dt-signal-tag">${sig.signal} SIGNAL</span>
      <span class="dt-signal-info">${esc(sig.info)}</span>
    </div>
    ` : ''}
    ${isDrawing ? `<div style="margin-top:5px;font-size:9.5px;color:var(--text-faint)">Click & drag to move · Del to remove</div>` : ''}
  `;

  const tooltipW = 270, tooltipH = 140;
  let relX = x, relY = y;
  let maxW = window.innerWidth, maxH = window.innerHeight;
  if(fsEl){
    const fsRect = fsEl.getBoundingClientRect();
    relX = x - fsRect.left;
    relY = y - fsRect.top;
    maxW = fsRect.width;
    maxH = fsRect.height;
  }
  let left = relX + 16;
  let top = relY - 20;
  if (left + tooltipW > maxW - 12) left = relX - tooltipW - 16;
  if (top + tooltipH > maxH - 12) top = maxH - tooltipH - 12;
  if (top < 12) top = 12;

  el.style.left = Math.max(8, left) + 'px';
  el.style.top = Math.max(8, top) + 'px';
  el.style.display = 'block';
}
function findDrawingAt(x,y){const view=getView(),pt={x,y,price:priceFromY(y,view)};for(let i=state.drawings.length-1;i>=0;i--)if(drawingHit(state.drawings[i],pt,view))return i;return -1}
function moveDrawing(q, dx, dy, view) {
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
}
function applyDrawingPoint(x,y){const r=vp.getBoundingClientRect(),pt=chartPoint({clientX:r.left+x,clientY:r.top+y});const name=state.pendingDrawing;state.drawingStage.push(pt);const stage=state.drawingStage.length;const need=name==='Horizontal Line'||name==='Vertical Line'?1:name==='Risk / Reward'?3:name==='Parallel Channel'?3:2;if(stage<need){document.getElementById('drawingStatus').textContent=stage===1?'Click again to set the second point.':`Click ${need-stage} more time(s) to finish.`;return}const color=state.pendingColor||css('--gold');let d={name,color,type:''};if(name==='Horizontal Line')d={...d,type:'h',price:pt.price};else if(name==='Vertical Line')d={...d,type:'v',i:pt.i};else if(name==='Trend Line')d={...d,type:'trend_ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price,infinite:true};else if(name==='Ray')d={...d,type:'ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Arrow')d={...d,type:'arrow',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Rectangle'||name==='Price Range')d={...d,type:name==='Rectangle'?'rect':'range',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price,fill:name==='Rectangle'?`${color}22`:'transparent'};else if(name==='Fibonacci Retracement')d={...d,type:'fib',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Risk / Reward'){d={...d,type:'rr',i:state.drawingStage[0].i,entry:state.drawingStage[0].price,stop:state.drawingStage[1].price,target:pt.price,fill:'transparent'}}else if(name==='Parallel Channel'){const a=state.drawingStage[0],b=state.drawingStage[1],c3=pt;const delta=c3.price-(a.price+(b.price-a.price));d={...d,type:'line',i1:a.i,i2:b.i,p1:a.price,p2:b.price,channelOffset:delta}}state.drawings.push(d);state.pendingDrawing=null;state.pendingColor=null;state.drawingStage=[];state.panArmed=false;state.yPanArmed=false;if(typeof setChartInteractionMode==='function'){setChartInteractionMode('crosshair');}else{state.interactionMode='crosshair';vp.classList.remove('pan-mode','drawing-hover');}document.getElementById('drawingStatus').style.display='none';renderApplied();draw()}
  drawSel.onchange=async e=>{const name=e.target.value;e.target.value='';if(!name)return;const cfg=await openToolModal(name,'drawing','');if(!cfg)return;state.pendingDrawing=name;state.pendingColor=cfg.color;state.drawingStage=[];document.getElementById('drawingStatus').style.display='block';document.getElementById('drawingStatus').textContent=`${name} selected — click the chart using the crosshair to place it.`};
  document.getElementById('clearDrawings').onclick=()=>{state.drawings=[];renderApplied();draw()};
  document.getElementById('chartAiSuggestBtn')?.addEventListener('click', () => {
    const panel = document.getElementById('chartAiPanel');
    if(!panel) return;
    const isClosed = panel.style.display === 'none' || !panel.style.display;
    panel.style.display = isClosed ? 'block' : 'none';
    if(isClosed) loadChartAiSuggestions(true);
  });
  document.getElementById('chartAiCloseBtn')?.addEventListener('click', () => {
    const panel = document.getElementById('chartAiPanel');
    if(panel) panel.style.display = 'none';
  });
  document.getElementById('chartAiApplyAllBtn')?.addEventListener('click', applyAllChartAiSuggestions);
  // Duplicate chartModeToggle removed
  document.getElementById('resetChartView')?.addEventListener('click',()=>{state.zoom=1;state.panX=Math.max(0,state.candles.length-state.visible);state.panY=0;state.yScale=1;draw()});
  document.querySelectorAll('#timeframeGroup .tf-btn[data-tf]').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('#timeframeGroup .tf-btn[data-tf]').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.tf=b.dataset.tf;state.zoom=1;loadChart()}));
  document.querySelectorAll('#timeframeGroup .tf-range-btn').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('#timeframeGroup .tf-range-btn').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.history=Number(b.dataset.history);state.zoom=1;loadChart()}));

  async function renderWatchlistQuotes(items){
    const symbols=items.map(i=>i.symbol).filter(Boolean); if(!symbols.length)return;
    window.__CA_WL_QUOTES=window.__CA_WL_QUOTES||{};
    const applyQuote=(q)=>{const sym=q?.symbol||q?.instrument;if(!sym)return;const ltp=Number(q?.ltp),so=Number(q?.session_open??q?.open);const sessionOpen=Number.isFinite(so)&&so>0?so:null;const sessionChange=sessionOpen!=null&&Number.isFinite(ltp)?ltp-sessionOpen:(q?.session_change==null?null:Number(q.session_change));const sessionPct=sessionOpen!=null&&Number.isFinite(ltp)?sessionChange/sessionOpen*100:(q?.session_change_pct==null?null:Number(q.session_change_pct));window.__CA_WL_QUOTES[sym]={...q,ltp:q?.ltp,open:q?.open,session_open:sessionOpen,session_change:sessionChange,session_change_pct:sessionPct,change_pct:q?.change_pct,net_change:q?.net_change,instrument_key:q?.instrument_key};const row=document.querySelector(`.wl-item[data-symbol="${CSS.escape(String(sym))}"]`);if(!row)return;const l=row.querySelector('.wl-ltp');if(l)l.textContent=q?.ltp==null?'—':fmt(q.ltp);row.dataset.ltp=q?.ltp??'';let c=row.querySelector('.wl-chg');if(!c){c=document.createElement('div');c.className='wl-chg';row.querySelector('.wl-right')?.appendChild(c)}const pct=q?.session_change_pct!=null?Number(q.session_change_pct):(q?.change_pct==null?null:Number(q.change_pct));const net=q?.session_change!=null?Number(q.session_change):(q?.net_change==null?null:Number(q.net_change));c.textContent=(net!=null&&Number.isFinite(net))?`${net>0?'+':''}${fmt(net)}${pct!=null&&Number.isFinite(pct)?` (${pct>0?'+':''}${fmt(pct)}%)`:''}`:'—';c.className='wl-chg '+(pct>0||net>0?'up':pct<0||net<0?'down':'');if(q?.instrument_key)keyToSymbol[q.instrument_key]=sym};
    try{const d=await A('/api/market/quotes?instruments='+encodeURIComponent(symbols.join(',')));(d.items||[]).forEach(applyQuote);}
    catch(_){for(const sym of symbols){try{const q=await A('/api/market/quote/'+encodeURIComponent(sym));applyQuote(q)}catch(_){}}}
  }
  async function R(){const l=document.getElementById('wl-list');l.innerHTML='';if(!G)return; window.__CA_WL_GROUP=G;const groups={index:'Indices',equity:'Equity',fno:'F&O',mcx:'MCX'};const items=[...(G.items||[])].sort((a,b)=>(Number(a.position??0)-Number(b.position??0))||((a.id||0)-(b.id||0)));const atOnly=document.getElementById('wlAtOnlyFilter')?.checked;if(atOnly){if(!window.__CA_AT_ENABLED_SYMBOLS){try{window.__CA_AT_ENABLED_SYMBOLS=new Set(JSON.parse(localStorage.getItem('ca_at_symbols')||'["RELIANCE","BANKNIFTY","NIFTY","CRUDEOIL"]'));}catch(_){window.__CA_AT_ENABLED_SYMBOLS=new Set(['RELIANCE','BANKNIFTY','NIFTY','CRUDEOIL']);}}items=items.filter(i=>window.__CA_AT_ENABLED_SYMBOLS.has(i.symbol));}['index','equity','fno','mcx'].forEach(t=>{const z=items.filter(i=>{const tt=(i.instrument_type||'').toUpperCase(),ee=(i.exchange||'').toUpperCase(),ss=(i.symbol||'').toUpperCase();const k=ee.includes('MCX')||tt.includes('COM')?'mcx':tt.includes('INDEX')||/NIFTY|SENSEX/.test(ss)?'index':tt.includes('FUT')||tt.includes('OPT')||i.option_type||i.expiry?'fno':'equity';return k===t&&(F==='all'||F===t)});if(!z.length)return;const q=document.createElement('div');q.className='wl-sub';q.textContent=groups[t];l.appendChild(q);z.forEach(i=>{const x=document.createElement('div');x.className='wl-item'+(i.symbol===S?' selected':'');x.dataset.symbol=i.symbol;const prevQuote=(window.__CA_WL_QUOTES||{})[i.symbol]||{}; x.innerHTML=`<div class="wl-left"><div class="wl-sym">${i.symbol}</div><div class="wl-ex">${i.exchange||''} · ${i.instrument_type||t}</div></div><div class="wl-right"><div class="wl-ltp">${prevQuote.ltp==null?'—':fmt(prevQuote.ltp)}</div><div class="wl-chg">${(()=>{const n=prevQuote.session_change!=null?Number(prevQuote.session_change):Number(prevQuote.net_change);const pc=prevQuote.session_change_pct!=null?Number(prevQuote.session_change_pct):Number(prevQuote.change_pct);return Number.isFinite(n)?`${n>0?'+':''}${fmt(n)}${Number.isFinite(pc)?` (${pc>0?'+':''}${fmt(pc)}%)`:''}`:'—'})()}</div><div class="wl-actions"><button type="button" class="wl-bs at ${((window.__CA_AT_ENABLED_SYMBOLS||new Set()).has(i.symbol))?'active':''}" data-wl-at="${esc(i.symbol)}" title="Auto Trade for ${esc(i.symbol)}">AT</button><button type="button" class="wl-bs buy" data-wl-buy="${esc(i.symbol)}">B</button><button type="button" class="wl-bs sell" data-wl-sell="${esc(i.symbol)}">S</button></div></div>`;x.onclick=async(e)=>{if(e.target.closest('.wl-actions'))return;S=i.symbol;window.CATraderSymbol=S;selectionSeq++;document.querySelectorAll('.wl-item').forEach(v=>v.classList.remove('selected'));x.classList.add('selected');await onSymbolChanged(S);};x.querySelector('[data-wl-at]')?.addEventListener('click',e=>{e.stopPropagation();if(!window.__CA_AT_ENABLED_SYMBOLS) window.__CA_AT_ENABLED_SYMBOLS=new Set(['RELIANCE','BANKNIFTY','NIFTY','CRUDEOIL']);if(window.__CA_AT_ENABLED_SYMBOLS.has(i.symbol)){window.__CA_AT_ENABLED_SYMBOLS.delete(i.symbol);e.currentTarget.classList.remove('active');toast(`Auto Trade OFF for ${i.symbol}`);}else{window.__CA_AT_ENABLED_SYMBOLS.add(i.symbol);e.currentTarget.classList.add('active');toast(`Auto Trade ON for ${i.symbol}`);}try{localStorage.setItem('ca_at_symbols',JSON.stringify(Array.from(window.__CA_AT_ENABLED_SYMBOLS)));}catch(_){}if(typeof updateAtUiForSymbol==='function') updateAtUiForSymbol(i.symbol);if(document.getElementById('wlAtOnlyFilter')?.checked)void R();});x.querySelector('[data-wl-buy]')?.addEventListener('click',e=>{e.stopPropagation();S=i.symbol;(window.openOrder||openOrder)('BUY',i.instrument_key||i.symbol,Number(i.lot_size)||1,i.symbol)});x.querySelector('[data-wl-sell]')?.addEventListener('click',e=>{e.stopPropagation();S=i.symbol;(window.openOrder||openOrder)('SELL',i.instrument_key||i.symbol,Number(i.lot_size)||1,i.symbol)});l.appendChild(x)});});if(items.length){void renderWatchlistQuotes(items); if(window.__CA_MARKET_STREAM_ENABLED!==false){
      void (async()=>{try{const d=await A('/api/market/stream/subscribe-batch',{method:'POST',body:JSON.stringify({instruments:items.map(i=>({symbol:i.symbol,instrument_key:i.instrument_key||''}))})});(d.subscribed||[]).forEach(x=>{keyToSymbol[x.instrument_key]=x.symbol;subscribedSymbols.add(x.symbol)});if(S){const key=d.subscribed?.find(x=>x.symbol===S)?.instrument_key;if(key){state.currentKey=key;keyToSymbol[key]=S}}}catch(e){console.debug('[CA Trader stream batch]',e)}})();}} if(S)void subscribeInstrument(S)}

  async function onSymbolChanged(sym){
    S=sym||''; window.CATraderSymbol=S; selectionSeq++; const localSeq=selectionSeq;
    window.__CA_SELECTED_SYMBOL=S;
    if(typeof tabLoadedAt!=='undefined' && tabLoadedAt.clear) tabLoadedAt.clear();
    const cached=(window.__CA_WL_QUOTES||{})[String(S).toUpperCase()]; if(cached) updateHeader(cached);
    document.querySelectorAll('.wl-item').forEach(v=>v.classList.toggle('selected',(v.dataset.symbol||'')===S));
    const tab=document.querySelector('.navtab.active')?.dataset.tab;
    void updateChartRecoBanner(null, S);
    if(typeof updateAtUiForSymbol === 'function') updateAtUiForSymbol(S);

    // Immediate quote fetch to update all section headers
    void Promise.resolve().then(()=>loadHeaderQuote()).catch(()=>{});
    await new Promise(requestAnimationFrame);
    if(localSeq!==selectionSeq) return;

    // Hydrate current tab immediately without background network blast
    if(tab==='charts') void loadChart();
    else if(tab==='options') void loadOptions();
    else if(tab==='news') void loadNews(newsMode);
    else if(tab==='reco') void Promise.allSettled([loadRecommendations(false),loadRecommendationHistory()]);
    else if(tab==='fundamentals') void loadFundamentals();
    else if(tab==='funds') void (typeof loadFundsTab === 'function' && loadFundsTab());
    else if(tab==='auto') void (window.loadAutoTrade || (typeof loadAutoTrade === 'function' ? loadAutoTrade : null))?.();
    else if(tab==='backtest') void (typeof initBacktest === 'function' && initBacktest());
    else if(tab==='reports') void (typeof loadReports === 'function' && loadReports());
    else if(tab==='quiz') void (typeof loadQuiz === 'function' && loadQuiz());
    else if(tab==='newspaper') void (typeof loadNewspaper === 'function' && loadNewspaper());
    else if(window.CATraderActions?.refreshActiveTab) void window.CATraderActions.refreshActiveTab(tab);
  }
  async function prefetchSelectedData(){
    const tab=document.querySelector('.navtab.active')?.dataset.tab;
    if(!tab)return;
    if(tab==='charts'){void loadDepth();void (window.CATraderAnalysis?.loadChartBundle?.()||Promise.resolve());return;}
    if(tab==='news'){void loadNews(newsMode);return;}
    if(tab==='options'){void loadOptions();return;}
    if(tab==='fundamentals'){void loadFundamentals();return;}
  }
  let __selectionRefreshTimer=null; async function refreshSelectionDependent(){clearTimeout(__selectionRefreshTimer);__selectionRefreshTimer=setTimeout(()=>{const tab=document.querySelector('.navtab.active')?.dataset.tab;if(tab==='news'){APP_CACHE.newsStock=null;APP_CACHE.newsGlobal=null;tabLoadedAt.delete('news');void loadNews(newsMode)}else if(tab==='charts'){void loadDepth();void (window.CATraderAnalysis?.loadChart?.()||Promise.resolve())}},150);}
  async function W0(selectId=null){const d=await A('/api/watchlists');W=d.items||[];const s=document.getElementById('watchlistSelect');s.innerHTML=W.map(w=>`<option value="${w.id}">${w.name}</option>`).join('');G=W.find(w=>w.id===(selectId||G?.id))||W[0]||null;window.__CA_WATCHLIST_GROUP=G;if(G?.items?.length)S=G.items[0].symbol;else if(!S)S='NIFTY'; s.value=G?.id||'';await R();void subscribeAllLive();}
  document.getElementById('watchlistSelect').onchange=async e=>{G=W.find(w=>w.id==e.target.value)||null;if(G?.items?.length)S=G.items[0].symbol||'';await R();if(S)await onSymbolChanged(S)};

  // Sidebar search: clicking a result selects it as the main instrument and offers Add to Watchlist without forcing the add.
  const inp=document.getElementById('instrumentSearch'),box=document.getElementById('instrumentSuggestions');let st;
  async function searchInstruments(q,targetBox,autoAdd=false){clearTimeout(st);st=setTimeout(async()=>{try{const d=await A('/api/instruments/search?q='+encodeURIComponent(q||''));targetBox.innerHTML='';(d.items||[]).slice(0,12).forEach(i=>{const x=document.createElement('div');x.className='instrument-suggestion';x.innerHTML=`<b>${i.symbol||''}</b><span>${i.name||''} · ${i.exchange||''} · ${i.instrument_type||''}</span>`;x.onclick=async()=>{S=i.symbol||'';targetBox.classList.remove('open');if(autoAdd&&G){await A('/api/watchlists/'+G.id+'/items',{method:'POST',body:JSON.stringify(i)});S=i.symbol||S;await W0(G.id);await onSymbolChanged(S)}else{await onSymbolChanged(i.symbol||'')} };targetBox.appendChild(x)});targetBox.classList.toggle('open',!!targetBox.children.length)}catch(_){}},q?180:0)}
  inp.oninput=()=>searchInstruments(inp.value.trim(),box,true);inp.onfocus=()=>searchInstruments(inp.value.trim()||'NIFTY',box,true);document.addEventListener('click',e=>{if(!e.target.closest('.wl-search'))box.classList.remove('open')});

  // Top search: main instrument only; optional Add to Watchlist action.
  const topInp=document.getElementById('topSymbolSearch'),topBox=document.getElementById('topSearchSuggestions');
  topInp.oninput=()=>searchInstruments(topInp.value.trim(),topBox,false);topInp.onfocus=()=>searchInstruments(topInp.value.trim()||'NIFTY',topBox,false);document.addEventListener('click',e=>{if(!e.target.closest('.top-search'))topBox.classList.remove('open')});
  topBox.addEventListener('click',async e=>{const row=e.target.closest('.instrument-suggestion');if(!row)return;const symbol=row.dataset?.symbol;if(symbol){await onSymbolChanged(symbol)}});
  const originalSearchInstruments=searchInstruments;
  // Rebind top suggestions with a dedicated Add button.
  function askWatchlistForInstrument(item){
    if(!W.length)return Promise.resolve(null);
    if(W.length===1)return Promise.resolve(W[0]);
    return new Promise(resolve=>{
      const modal=document.getElementById('watchlistChoiceModal'); if(!modal){resolve(W.find(w=>w.id==G?.id)||W[0]);return}
      const sel=document.getElementById('watchlistChoiceSelect'); sel.innerHTML=W.map(w=>`<option value="${w.id}">${esc(w.name)}</option>`).join(''); sel.value=G?.id||W[0].id;
      modal.classList.add('open'); modal.setAttribute('aria-hidden','false');
      const done=(v)=>{modal.classList.remove('open');modal.setAttribute('aria-hidden','true');document.getElementById('watchlistChoiceCancel').onclick=null;document.getElementById('watchlistChoiceSave').onclick=null;resolve(v)};
      document.getElementById('watchlistChoiceCancel').onclick=()=>done(null);
      document.getElementById('watchlistChoiceSave').onclick=()=>done(W.find(w=>String(w.id)===String(sel.value))||null);
    });
  }
  async function topSearch(q){clearTimeout(st);st=setTimeout(async()=>{try{const d=await A('/api/instruments/search?q='+encodeURIComponent(q||''));topBox.innerHTML='';(d.items||[]).slice(0,12).forEach(i=>{const x=document.createElement('div');x.className='instrument-suggestion';x.dataset.symbol=i.symbol||'';x.dataset.instrument=JSON.stringify(i);x.innerHTML=`<div style="display:flex;align-items:center;gap:8px"><div style="flex:1;min-width:0"><b>${esc(i.symbol||'')}</b><span>${esc(i.name||'')} · ${esc(i.exchange||'')} · ${esc(i.instrument_type||'')}</span></div><button type="button" class="btn gold small top-add" title="Add to watchlist" data-symbol="${esc(i.symbol||'')}">+</button></div>`;x.querySelector('div').addEventListener('click',async e=>{if(e.target.closest('.top-add'))return;window.__caPendingSymbol=i.symbol||'';topBox.classList.remove('open');topInp.value='';await onSymbolChanged(i.symbol||'')});x.querySelector('.top-add').onclick=async e=>{e.stopPropagation();const w=await askWatchlistForInstrument(i);if(!w)return;await A('/api/watchlists/'+w.id+'/items',{method:'POST',body:JSON.stringify(i)});await W0(w.id);await onSymbolChanged(i.symbol||'');topBox.classList.remove('open');topInp.value='';toast(`${i.symbol} added to ${w.name}`)};topBox.appendChild(x)});topBox.classList.toggle('open',!!topBox.children.length)}catch(_){}},q?180:0)}
  topInp.oninput=()=>topSearch(topInp.value.trim());topInp.onfocus=()=>topSearch(topInp.value.trim()||'NIFTY');


  // Watchlist editor and create modal are already present in the page.
  async function openWatchlistEditor(){if(!G)return;document.getElementById('watchlistModalTitle').textContent='Manage Watchlist';document.getElementById('watchlistRenameBtn').style.display='';document.getElementById('watchlistNameInput').value=G.name||'';const list=document.getElementById('watchlistManageList');const items=[...(G.items||[])].sort((a,b)=>(Number(a.position??0)-Number(b.position??0))||((a.id||0)-(b.id||0)));list.innerHTML=items.map((i,idx)=>`<div class="watchlist-manage-item" data-symbol="${i.symbol}"><div class="watchlist-manage-name"><b>${i.symbol}</b><span>${i.display_name||i.exchange||''}</span></div><div class="watchlist-manage-actions"><button type="button" data-action="up" ${idx===0?'disabled':''}>↑</button><button type="button" data-action="down" ${idx===items.length-1?'disabled':''}>↓</button><button type="button" data-action="delete">×</button></div></div>`).join('')||'<div class="muted">No instruments in this watchlist.</div>';list.querySelectorAll('button').forEach(btn=>btn.onclick=async()=>{const row=btn.closest('.watchlist-manage-item'),sym=row?.dataset.symbol,act=btn.dataset.action;if(!sym)return;if(act==='delete')await A('/api/watchlists/'+G.id+'/items/'+encodeURIComponent(sym),{method:'DELETE'});else await A('/api/watchlists/'+G.id+'/reorder',{method:'POST',body:JSON.stringify({symbol:sym,direction:act})});await W0(G.id);openWatchlistEditor()});const m=document.getElementById('watchlistModal');m.classList.add('open');m.setAttribute('aria-hidden','false')}
  function closeWatchlistEditor(){const m=document.getElementById('watchlistModal');m.classList.remove('open');m.setAttribute('aria-hidden','true')}
  document.getElementById('editWatchlistBtn').onclick=openWatchlistEditor;document.getElementById('watchlistModalClose').onclick=closeWatchlistEditor;document.getElementById('watchlistDoneBtn').onclick=closeWatchlistEditor;document.getElementById('watchlistRenameBtn').onclick=async()=>{const n=document.getElementById('watchlistNameInput').value.trim();if(G&&n){await A('/api/watchlists/'+G.id,{method:'PATCH',body:JSON.stringify({name:n})});await W0(G.id);openWatchlistEditor()}};
  document.getElementById('addWatchlistBtn').onclick=()=>{const m=document.getElementById('watchlistModal');document.getElementById('watchlistModalTitle').textContent='Create Watchlist';document.getElementById('watchlistRenameBtn').style.display='none';document.getElementById('watchlistNameInput').value='';document.getElementById('watchlistManageList').innerHTML='<div class="muted">Create a new watchlist.</div><button type="button" class="btn gold" id="createWatchlistConfirm" style="margin-top:8px">Create</button>';m.classList.add('open');m.setAttribute('aria-hidden','false');document.getElementById('createWatchlistConfirm').onclick=async()=>{const n=document.getElementById('watchlistNameInput').value.trim();if(!n)return;await A('/api/watchlists',{method:'POST',body:JSON.stringify({name:n})});await W0();closeWatchlistEditor()}};

  // Market boxes: one initial session fetch, then local clock/session state; no 1-second API polling.
  async function initMarketState(){try{const [n,m]=await Promise.all([A('/api/market/session?segment=NSE_EQ'),A('/api/market/session?segment=MCX')]);market.nse=!!n.active;market.mcx=!!m.active;renderMarketState()}catch(_){renderMarketState()}}
  function isWeekday(){const d=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Kolkata'}));return d.getDay()>=1&&d.getDay()<=5}
  function minutesIST(){const d=new Date(new Date().toLocaleString('en-US',{timeZone:'Asia/Kolkata'}));return d.getHours()*60+d.getMinutes()}
  function renderMarketState(){const min=minutesIST(),wd=isWeekday();market.nse=wd&&min>=555&&min<=930;market.mcx=wd&&min>=555&&min<=1380;const set=(dot,text,open)=>{const d=document.getElementById(dot),t=document.getElementById(text);if(d){d.style.background=open?'var(--buy)':'var(--sell)';d.classList.toggle('pulse',open);d.classList.toggle('market-closed',!open)}if(t)t.textContent=open?'Open':'Closed'};set('nseStatusDot','nseStatusText',market.nse);set('mcxStatusDot','mcxStatusText',market.mcx);document.getElementById('marketClock').textContent=new Date().toLocaleTimeString('en-IN',{hour12:false,timeZone:'Asia/Kolkata'})+' IST'}
  setInterval(()=>{renderMarketState();},1000);

  function applyNotifFilter(filter){
    const rows = document.querySelectorAll('#notificationListBody .notif-item, #notificationListBody > div.notification-row');
    rows.forEach(r => {
      if(!filter || filter === 'all') { r.style.display = ''; return; }
      const cat = (r.dataset.category || '').toLowerCase();
      const txt = (r.textContent || '').toLowerCase();
      let match = false;
      if(cat && (cat === filter || (filter === 'reco' && (cat === 'reco' || cat === 'recommendation')))) match = true;
      else if(filter === 'news' && (cat.includes('news') || txt.includes('news') || txt.includes('article') || txt.includes('rbi') || txt.includes('inflation') || txt.includes('budget') || txt.includes('rates'))) match = true;
      else if(filter === 'technicals' && (cat.includes('tech') || txt.includes('rsi') || txt.includes('breakout') || txt.includes('candle') || txt.includes('macd') || txt.includes('ema') || txt.includes('supertrend'))) match = true;
      else if(filter === 'orders' && (cat.includes('order') || cat.includes('position') || txt.includes('order') || txt.includes('filled') || txt.includes('bought') || txt.includes('sold') || txt.includes('trade') || txt.includes('squared'))) match = true;
      else if(filter === 'reco' && (cat.includes('reco') || txt.includes('reco') || txt.includes('target') || txt.includes('conviction') || txt.includes('ca ai'))) match = true;
      r.style.display = match ? '' : 'none';
    });
  }
  window.applyNotifFilter = applyNotifFilter;

  // Notifications and move-to-top.
  document.getElementById('notificationBtn').onclick=async()=>{
    if('Notification' in window&&Notification.permission==='default'){try{await Notification.requestPermission()}catch(_){}}
    const menu=document.getElementById('notificationMenu');
    menu.classList.toggle('open');
    if(!menu.classList.contains('open'))return;
    const listBody=document.getElementById('notificationListBody')||menu;
    listBody.innerHTML='<div class="muted" style="padding:12px;">Loading recent notifications…</div>';
    try{
      const d=await A('/api/notifications');
      const rows=d.items||[];
      if(!rows.length){
        listBody.innerHTML='<div class="muted" style="padding:12px;">No notifications since your last session.</div>';
      } else {
        const catIcons = {news:'', technicals:'▲', orders:'⚡', reco:'✦', risk_event:'️', position_closed:'₹'};
        listBody.innerHTML=rows.map(n=>{
          const cat = String(n.category||'').toLowerCase();
          const icon = catIcons[cat] || '';
          const timeStr = n.created_at ? new Date(n.created_at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Kolkata'}) : '';
          return `<div class="notification-row notif-item" data-category="${esc(cat)}" style="padding:10px 12px;border-bottom:1px solid var(--border-soft);display:flex;flex-direction:column;gap:3px;cursor:default;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">
              <span style="font-weight:700;font-size:12px;color:var(--text);">${icon} ${esc(n.title||'Notification')}</span>
              <span class="muted" style="font-size:10px;font-family:var(--font-mono);">${timeStr}</span>
            </div>
            <div class="muted" style="font-size:11px;line-height:1.4;">${esc(n.body||'')}</div>
          </div>`;
        }).join('');
        const activeTab = document.querySelector('.notif-tab.active')?.dataset.notifFilter || 'all';
        applyNotifFilter(activeTab);
      }
      const u=rows.filter(n=>n.unread).length;
      const b=document.getElementById('notificationBadge'); if(b) b.textContent=u;
    }catch(e){
      listBody.innerHTML='<div class="muted" style="padding:12px;">Notifications unavailable.</div>';
    }
  };
  document.getElementById('moveTopBtn').onclick=()=>window.scrollTo({top:0,behavior:'smooth'});

  // Profile initials/name.
  function initials(name){const p=String(name||'').trim().split(/\s+/).filter(Boolean);return p.length>1?(p[0][0]+p[p.length-1][0]).toUpperCase():((p[0]||'S').slice(0,2)).toUpperCase()}
  async function loadProfile(){
    try{
      const d=await A('/api/auth/me');
      const u=d.user||{};
      const name=u.full_name||u.username||'Santosh Madnani';
      const email=u.email||'santoshmadnani553@gmail.com';
      const adminEmails=['santoshmadnani553@gmail.com', 'santoshmadnani@catrader.site'];
      const isAdmin = u.is_admin || u.role === 'admin' || adminEmails.includes(String(email).toLowerCase());

      window.__CA_USER_ROLE = isAdmin ? 'admin' : 'user';
      window.__CA_USER_EMAIL = email;

      if($('userDisplayName')) $('userDisplayName').textContent=name.split(/\s+/)[0];
      if($('userAvatar')) $('userAvatar').textContent=initials(name);
      if($('profileMenuName')) $('profileMenuName').textContent=name;
      if($('profileMenuEmail')) $('profileMenuEmail').textContent=email;
      if($('profileMenuRole')) $('profileMenuRole').textContent=isAdmin ? 'Super Admin' : 'Trader';

      if($('profileModalName')) $('profileModalName').textContent=name;
      if($('profileModalEmail')) $('profileModalEmail').textContent=email;
      if($('profileModalRole')) $('profileModalRole').textContent=isAdmin ? 'Super Admin (Full Access)' : 'Standard Trader';
      if($('profileNameInput')) $('profileNameInput').value=name;

      const serverTab = document.querySelector('.navtab[data-tab="server"]');
      if(serverTab) serverTab.style.display = isAdmin ? 'inline-flex' : 'none';

      const adminWidget = $('adminFundTransferCard');
      if(adminWidget) adminWidget.style.display = isAdmin ? 'block' : 'none';

      const resetBtn = $('resetFundsBtn');
      if(resetBtn) resetBtn.style.display = isAdmin ? 'inline-block' : 'none';
      const fs = $('fitnessSwitchBtn');
      if(fs) fs.style.display = isAdmin ? 'flex' : 'none';
    }catch(_){}
  }

  // Admin Fund Allocation Submission Handler (Item 22)
  $('adminFundSubmitBtn')?.addEventListener('click', async () => {
    const email = $('adminFundTargetEmail')?.value?.trim();
    const amount = Number($('adminFundAmount')?.value);
    const wallet = $('adminFundWalletSelect')?.value || 'trading';
    if(!email || !amount || amount <= 0){
      alert('Please enter a valid Gmail address and positive credit amount.');
      return;
    }
    try {
      const res = await api('/api/admin/funds/add', {
        method: 'POST',
        body: JSON.stringify({ email, amount, wallet_type: wallet })
      });
      toast(`✓ Successfully credited ₹${fmt(amount)} to ${email}`);
      $('adminFundAmount').value = '';
      void loadFundsTab();
    } catch(err) {
      alert(`Fund allocation failed: ${err.message}`);
    }
  });
  document.getElementById('userChip').onclick=e=>{if(e.target.closest('.user-menu'))return;document.getElementById('userMenu').classList.toggle('open')};document.getElementById('profileDetailsBtn').onclick=()=>{document.getElementById('profileModal').classList.add('open');document.getElementById('profileModal').setAttribute('aria-hidden','false')};document.getElementById('fitnessSwitchBtn')?.addEventListener('click',async()=>{try{await A('/api/auth/select-terminal',{method:'POST',body:JSON.stringify({terminal:'fitness'})});location.href='/fitness'}catch(e){toast(e.message)}});document.getElementById('profileModalClose').onclick=()=>closeModal('profileModal');document.getElementById('profileSaveBtn').onclick=async()=>{const n=document.getElementById('profileNameInput').value.trim();if(!n)return;try{await A('/api/auth/profile',{method:'PATCH',body:JSON.stringify({full_name:n})});await loadProfile();closeModal('profileModal');document.getElementById('userMenu').classList.remove('open')}catch(e){toast(e.message)}};

  // Options panel: real Upstox option chain, expiry selection, Greeks and buyability.
  let optionState={expiry:null,chain:null};
  let optChainMode = 'oi'; // 'oi' or 'greeks'
  async function loadOptions(){
    if(!S) return;
    try{
      const isMcx = /CRUDE|GOLD|SILVER|NATURALGAS|COPPER|ZINC|LEAD|NICKEL|ALUMINIUM/.test(String(S).toUpperCase()) || F === 'mcx';
      const mcxBox = document.getElementById('mcxOptSelector');
      if(mcxBox){
        mcxBox.style.display = isMcx ? 'block' : 'none';
        const mcxSym = document.getElementById('mcxOptSymbol');
        if(mcxSym && isMcx) mcxSym.value = S;
      }
      const q = APP_CACHE.quote || await loadHeaderQuote();
      updateOptionHeader(q);
      if(document.getElementById('optionsProviderStatus')) document.getElementById('optionsProviderStatus').textContent='Loading live option chain…';
      let expiries = [];
      try{
        const ex = await A('/api/options/' + encodeURIComponent(S) + '/expiries', {timeoutMs:3500});
        expiries = ex.expiries || [];
      }catch(_){}
      if(!optionState.expiry) optionState.expiry = expiries[0] || 'current_week';

      // Render Zerodha-style expiry pills
      const pillBox = document.getElementById('optionsExpiryPills');
      if(pillBox){
        pillBox.innerHTML = expiries.slice(0, 8).map(exp => {
          const isAct = exp === optionState.expiry;
          return `<button type="button" class="chip-filter ${isAct ? 'active' : ''}" data-opt-expiry="${esc(exp)}" style="font-size:11px;padding:3px 10px;font-weight:600;white-space:nowrap;">${esc(exp)}</button>`;
        }).join('');
        pillBox.querySelectorAll('[data-opt-expiry]').forEach(btn => {
          btn.onclick = async () => {
            optionState.expiry = btn.dataset.optExpiry;
            pillBox.querySelectorAll('[data-opt-expiry]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            await fetchOptionChain();
          };
        });
      }

      // Wire OI vs Greeks toggle
      document.getElementById('btnOptViewOI')?.addEventListener('click', () => {
        optChainMode = 'oi';
        document.getElementById('btnOptViewOI')?.classList.add('active');
        document.getElementById('btnOptViewGreeks')?.classList.remove('active');
        void fetchOptionChain();
      });
      document.getElementById('btnOptViewGreeks')?.addEventListener('click', () => {
        optChainMode = 'greeks';
        document.getElementById('btnOptViewGreeks')?.classList.add('active');
        document.getElementById('btnOptViewOI')?.classList.remove('active');
        void fetchOptionChain();
      });
      document.getElementById('optionsRefreshBtn')?.addEventListener('click', () => fetchOptionChain());

      await fetchOptionChain();
    }catch(e){
      const host = document.getElementById('optionChainTable') || document.getElementById('zerodhaOptionChainContainer');
      if(host) host.innerHTML = `<div class="options-empty">${e.message}</div>`;
    }
  }

  async function fetchOptionChain(){
    const host = document.getElementById('zerodhaOptionChainContainer') || document.getElementById('optionChainTable');
    if(!host) return;
    try{
      const d = await A('/api/options/' + encodeURIComponent(S) + (optionState.expiry ? `?expiry=${encodeURIComponent(optionState.expiry)}` : ''), {timeoutMs:5000});
      APP_CACHE.options = d;
      optionState.chain = d;
      const spot = Number(d.spot || 0);
      const atm = Number(d.atm_strike || 0);
      const lot = S.includes("BANK") ? 15 : S.includes("NIFTY") ? 25 : S.includes("CRUDE") ? 100 : 1;
      const rows = d.strikes || [];

      // Update spot header
      if(document.getElementById('optionsSpotLtp')) document.getElementById('optionsSpotLtp').textContent = fmt(spot);
      if(document.getElementById('optionsSymbolTitle')) document.getElementById('optionsSymbolTitle').textContent = S;

      // Calculate max OI for depth visualization
      let maxCallOi = 1, maxPutOi = 1, totalCallOi = 0, totalPutOi = 0;
      rows.forEach(r => {
        const coi = Number(r.call?.oi || 0);
        const poi = Number(r.put?.oi || 0);
        if(coi > maxCallOi) maxCallOi = coi;
        if(poi > maxPutOi) maxPutOi = poi;
        totalCallOi += coi;
        totalPutOi += poi;
      });

      const pcr = totalCallOi > 0 ? (totalPutOi / totalCallOi).toFixed(2) : '1.00';
      if(document.getElementById('optFooterPcr')) document.getElementById('optFooterPcr').textContent = pcr;
      if(document.getElementById('optFooterMaxPain')) document.getElementById('optFooterMaxPain').textContent = fmt(atm);
      if(document.getElementById('optFooterLotSize')) document.getElementById('optFooterLotSize').textContent = `${lot} / lot`;

      // Find ATM IV
      const atmRow = rows.find(r => Number(r.strike) === atm) || rows[Math.floor(rows.length/2)];
      const atmIv = atmRow?.call?.iv || atmRow?.put?.iv || 14.5;
      if(document.getElementById('optFooterAtmIv')) document.getElementById('optFooterAtmIv').textContent = `${Number(atmIv).toFixed(1)}%`;

      const isGreeks = optChainMode === 'greeks';

      host.innerHTML = `
        <table style="width:100%;border-collapse:collapse;font-size:12px;">
          <thead>
            <tr style="background:var(--surface-2);border-bottom:1px solid var(--border);">
              <th colspan="${isGreeks ? 5 : 4}" style="text-align:center;color:var(--buy);font-weight:700;padding:6px;">CALLS</th>
              <th style="text-align:center;font-weight:800;color:var(--text);padding:6px;width:90px;">STRIKE</th>
              <th colspan="${isGreeks ? 5 : 4}" style="text-align:center;color:var(--sell);font-weight:700;padding:6px;">PUTS</th>
            </tr>
            <tr style="background:var(--surface);border-bottom:1px solid var(--border-soft);font-size:11px;color:var(--text-faint);">
              ${isGreeks ? `
                <th style="padding:4px 8px;">Delta</th>
                <th style="padding:4px 8px;">Gamma</th>
                <th style="padding:4px 8px;">Theta</th>
                <th style="padding:4px 8px;">IV</th>
                <th style="padding:4px 8px;text-align:right;">LTP</th>
              ` : `
                <th style="padding:4px 8px;">OI (Lakhs)</th>
                <th style="padding:4px 8px;">Vol</th>
                <th style="padding:4px 8px;">IV</th>
                <th style="padding:4px 8px;text-align:right;">LTP</th>
              `}
              <th style="text-align:center;padding:4px 8px;">Price</th>
              ${isGreeks ? `
                <th style="padding:4px 8px;text-align:left;">LTP</th>
                <th style="padding:4px 8px;">IV</th>
                <th style="padding:4px 8px;">Theta</th>
                <th style="padding:4px 8px;">Gamma</th>
                <th style="padding:4px 8px;">Delta</th>
              ` : `
                <th style="padding:4px 8px;text-align:left;">LTP</th>
                <th style="padding:4px 8px;">IV</th>
                <th style="padding:4px 8px;">Vol</th>
                <th style="padding:4px 8px;">OI (Lakhs)</th>
              `}
            </tr>
          </thead>
          <tbody>
            ${rows.map(r => {
              const c = r.call || {};
              const p = r.put || {};
              const strike = Number(r.strike || 0);
              const isAtm = strike === atm;
              const callSym = `${S} ${strike} CE`;
              const putSym = `${S} ${strike} PE`;
              const callOiL = (Number(c.oi || 0) / 100000).toFixed(2);
              const putOiL = (Number(p.oi || 0) / 100000).toFixed(2);
              const callPct = Math.min(100, Math.round((Number(c.oi || 0) / maxCallOi) * 100));
              const putPct = Math.min(100, Math.round((Number(p.oi || 0) / maxPutOi) * 100));

              return `
                <tr class="opt-chain-row" style="border-bottom:1px solid var(--border-soft);${isAtm ? 'background:rgba(59,130,246,0.06);' : ''}">
                  ${isGreeks ? `
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call Delta', ${c.delta||0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(c.delta)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call Gamma', ${c.gamma||0.001}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(c.gamma)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call Theta', ${c.theta||-10}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(c.theta)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call IV', ${c.iv||14}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(c.iv)}</td>
                    <td style="padding:5px 8px;text-align:right;position:relative;">
                      <div style="display:flex;align-items:center;justify-content:flex-end;gap:5px;">
                        <div class="opt-bs-group">
                          <button type="button" class="opt-bs-btn buy" data-opt-buy="${esc(callSym)}" data-opt-ltp="${c.ltp||0}" title="Buy ${callSym}">B</button>
                          <button type="button" class="opt-bs-btn sell" data-opt-sell="${esc(callSym)}" data-opt-ltp="${c.ltp||0}" title="Sell ${callSym}">S</button>
                          <button type="button" class="opt-bs-btn reco" data-opt-reco="${esc(callSym)}" data-opt-ltp="${c.ltp||0}" title="Recommend ${callSym}">R</button>
                        </div>
                        <b class="cell-up" style="font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call Greeks', ${c.delta||0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">₹${fmt(c.ltp)}</b>
                      </div>
                    </td>
                  ` : `
                    <td style="padding:5px 8px;font-family:var(--font-mono);position:relative;cursor:pointer;" onclick="openGreekModal('Call OI Analysis', ${c.delta||0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">
                      <div style="position:absolute;top:0;bottom:0;right:0;width:${callPct}%;background:rgba(38,217,166,0.12);pointer-events:none;"></div>
                      <span style="position:relative;z-index:1;">${callOiL}L</span>
                    </td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call Volume', ${c.delta||0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(c.volume)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call IV', ${c.iv||14}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(c.iv)}</td>
                    <td style="padding:5px 8px;text-align:right;position:relative;">
                      <div style="display:flex;align-items:center;justify-content:flex-end;gap:5px;">
                        <div class="opt-bs-group">
                          <button type="button" class="opt-bs-btn buy" data-opt-buy="${esc(callSym)}" data-opt-ltp="${c.ltp||0}" title="Buy ${callSym}">B</button>
                          <button type="button" class="opt-bs-btn sell" data-opt-sell="${esc(callSym)}" data-opt-ltp="${c.ltp||0}" title="Sell ${callSym}">S</button>
                          <button type="button" class="opt-bs-btn reco" data-opt-reco="${esc(callSym)}" data-opt-ltp="${c.ltp||0}" title="Recommend ${callSym}">R</button>
                        </div>
                        <b class="cell-up" style="font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Call Greeks', ${c.delta||0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">₹${fmt(c.ltp)}</b>
                      </div>
                    </td>
                  `}
                  
                  <td style="text-align:center;padding:5px 8px;font-family:var(--font-mono);font-weight:700;cursor:pointer;" onclick="openGreekModal('Strike ${strike}', ${c.delta||0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">
                    <span class="strike-pill ${isAtm ? 'atm' : ''}" style="display:inline-block;padding:2px 8px;border-radius:12px;background:${isAtm ? 'var(--gold)' : 'var(--surface-3)'};color:${isAtm ? '#000' : 'var(--text)'};font-size:11.5px;">${strike}${isAtm ? ' · ATM' : ''}</span>
                  </td>

                  ${isGreeks ? `
                    <td style="padding:5px 8px;text-align:left;position:relative;">
                      <div style="display:flex;align-items:center;justify-content:flex-start;gap:5px;">
                        <b class="cell-down" style="font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put Greeks', ${p.delta||-0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">₹${fmt(p.ltp)}</b>
                        <div class="opt-bs-group">
                          <button type="button" class="opt-bs-btn buy" data-opt-buy="${esc(putSym)}" data-opt-ltp="${p.ltp||0}" title="Buy ${putSym}">B</button>
                          <button type="button" class="opt-bs-btn sell" data-opt-sell="${esc(putSym)}" data-opt-ltp="${p.ltp||0}" title="Sell ${putSym}">S</button>
                          <button type="button" class="opt-bs-btn reco" data-opt-reco="${esc(putSym)}" data-opt-ltp="${p.ltp||0}" title="Recommend ${putSym}">R</button>
                        </div>
                      </div>
                    </td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put IV', ${p.iv||14}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(p.iv)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put Theta', ${p.theta||-10}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(p.theta)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put Gamma', ${p.gamma||0.001}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(p.gamma)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put Delta', ${p.delta||-0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(p.delta)}</td>
                  ` : `
                    <td style="padding:5px 8px;text-align:left;position:relative;">
                      <div style="display:flex;align-items:center;justify-content:flex-start;gap:5px;">
                        <b class="cell-down" style="font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put Greeks', ${p.delta||-0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">₹${fmt(p.ltp)}</b>
                        <div class="opt-bs-group">
                          <button type="button" class="opt-bs-btn buy" data-opt-buy="${esc(putSym)}" data-opt-ltp="${p.ltp||0}" title="Buy ${putSym}">B</button>
                          <button type="button" class="opt-bs-btn sell" data-opt-sell="${esc(putSym)}" data-opt-ltp="${p.ltp||0}" title="Sell ${putSym}">S</button>
                          <button type="button" class="opt-bs-btn reco" data-opt-reco="${esc(putSym)}" data-opt-ltp="${p.ltp||0}" title="Recommend ${putSym}">R</button>
                        </div>
                      </div>
                    </td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put IV', ${p.iv||14}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(p.iv)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);cursor:pointer;" onclick="openGreekModal('Put Volume', ${p.delta||-0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">${fmt(p.volume)}</td>
                    <td style="padding:5px 8px;font-family:var(--font-mono);position:relative;cursor:pointer;" onclick="openGreekModal('Put OI Analysis', ${p.delta||-0.5}, '${esc(S)}', ${strike}, ${c.delta||0.5}, ${p.delta||-0.5})">
                      <div style="position:absolute;top:0;bottom:0;left:0;width:${putPct}%;background:rgba(239,68,68,0.12);pointer-events:none;"></div>
                      <span style="position:relative;z-index:1;">${putOiL}L</span>
                    </td>
                  `}
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      `;

      // Wire B/S/R Buttons in Option Chain
      host.querySelectorAll('[data-opt-buy]').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const sym = btn.dataset.optBuy;
          const ltp = Number(btn.dataset.optLtp || 0);
          openQuickOrderModal({
            symbol: sym,
            display_symbol: sym,
            recommendation: 'BUY',
            entry: ltp,
            target: roundVal(ltp + 30),
            stop_loss: roundVal(Math.max(0.05, ltp - 15)),
            instrument: { symbol: sym, display: sym, kind: 'OPTION', lot_size: lot }
          });
        };
      });

      host.querySelectorAll('[data-opt-sell]').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const sym = btn.dataset.optSell;
          const ltp = Number(btn.dataset.optLtp || 0);
          openQuickOrderModal({
            symbol: sym,
            display_symbol: sym,
            recommendation: 'SELL',
            entry: ltp,
            target: roundVal(Math.max(0.05, ltp - 30)),
            stop_loss: roundVal(ltp + 15),
            instrument: { symbol: sym, display: sym, kind: 'OPTION', lot_size: lot }
          });
        };
      });

      host.querySelectorAll('[data-opt-reco]').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const sym = btn.dataset.optReco;
          const ltp = Number(btn.dataset.optLtp || 0);
          applyOptionRecommendation(sym, ltp, S, lot);
        };
      });

    }catch(e){
      host.innerHTML = `<div class="options-empty">${e.message}</div>`;
    }
  }

  function openGreekModal(greekName, greekVal, symbol, strike, callDelta, putDelta){
    const modal = document.getElementById('greekModal');
    if(!modal) return;
    const body = document.getElementById('greekModalBody');
    const sym = symbol || S || 'NIFTY';
    const val = Number(greekVal) || 0;
    const isCall = greekName.includes('Call') || !greekName.includes('Put');
    const delta = isCall ? (Number(callDelta) || 0.50) : (Number(putDelta) || -0.50);

    let title = '';
    let explanation = '';
    let formula = '';
    let realLifeExample = '';
    let simDefaultMove = sym.includes('BANK') ? 100 : sym.includes('NIFTY') ? 50 : 10;

    if(greekName.includes('Gamma')){
      title = `${greekName} (${val > 0 ? '+' : ''}${fmt(val)})`;
      explanation = `<b>Gamma (Γ)</b> measures the <b>rate of change of Delta</b> for every ₹1 move in the underlying stock or index (${sym}). It is the <b>acceleration</b> factor for your option premium.`;
      formula = `Δ(Delta) = Gamma × Underlying Move`;
      realLifeExample = `
        <div style="background:var(--surface-2);border-left:3px solid var(--gold);padding:10px 12px;border-radius:6px;font-size:11.5px;line-height:1.5;">
          <b>Movement Explanation with Current Value (${val}):</b><br>
          • Current Gamma is <b>${val}</b> and initial Delta is <b>${delta.toFixed(3)}</b>.<br>
          • If <b>${sym}</b> price moves up by <b>₹10.00</b>, your option's Delta will increase by <b>+${(10 * val).toFixed(3)}</b> (10 × ${val}), shifting Delta from ${delta.toFixed(3)} to <b>${(delta + 10 * val).toFixed(3)}</b>.<br>
          • Option Price Movement: Over this 10-point move in ${sym}, the option gains approximately <b>₹${(10 * delta + 0.5 * val * 100).toFixed(2)}</b>.<br>
          • <i>Key Insight:</i> Because of Gamma, as the stock moves further in your favor, the option gains value faster and faster!
        </div>
      `;
    } else if(greekName.includes('Delta')){
      title = `${greekName} (${val > 0 ? '+' : ''}${fmt(val)})`;
      explanation = `<b>Delta (Δ)</b> measures the <b>expected price change of the option</b> for every ₹1 change in the price of ${sym}.`;
      formula = `Option Move ≈ Delta × Underlying Move`;
      realLifeExample = `
        <div style="background:var(--surface-2);border-left:3px solid var(--buy);padding:10px 12px;border-radius:6px;font-size:11.5px;line-height:1.5;">
          <b>Movement Explanation with Current Value (${val}):</b><br>
          • If <b>${sym}</b> moves by <b>₹10.00</b>, this option's premium is expected to move by <b>₹${(10 * val).toFixed(2)}</b> (10 × ${val}).<br>
          • If <b>${sym}</b> moves by <b>₹50.00</b>, the option moves by <b>₹${(50 * val).toFixed(2)}</b>.<br>
          • Deep In-The-Money (ITM) options have Delta close to 1.0 (moving 1:1 with the stock), while Out-Of-The-Money (OTM) options have lower Delta.
        </div>
      `;
    } else if(greekName.includes('Theta')){
      title = `${greekName} (${fmt(val)})`;
      explanation = `<b>Theta (Θ)</b> represents <b>time decay</b>. It measures how much option premium erodes with each passing calendar day, assuming all other factors remain constant.`;
      formula = `Daily Decay = |Theta| per day`;
      realLifeExample = `
        <div style="background:var(--surface-2);border-left:3px solid var(--sell);padding:10px 12px;border-radius:6px;font-size:11.5px;line-height:1.5;">
          <b>Movement Explanation with Current Value (${val}):</b><br>
          • If <b>${sym}</b> remains completely unchanged over the next 24 hours, this option will lose approximately <b>₹${Math.abs(val).toFixed(2)}</b> in premium purely due to time erosion.<br>
          • Over a 3-day weekend holding period, time decay erodes approximately <b>₹${(Math.abs(val) * 3).toFixed(2)}</b>.<br>
          • Option buyers lose Theta each day; option sellers profit from Theta.
        </div>
      `;
    } else if(greekName.includes('Vega')){
      title = `${greekName} (${fmt(val)})`;
      explanation = `<b>Vega (ν)</b> measures the sensitivity of the option price to a <b>1% change in Implied Volatility (IV)</b>.`;
      formula = `Option Move = Vega × Change in IV (%)`;
      realLifeExample = `
        <div style="background:var(--surface-2);border-left:3px solid var(--gold-dim);padding:10px 12px;border-radius:6px;font-size:11.5px;line-height:1.5;">
          <b>Movement Explanation with Current Value (${val}):</b><br>
          • If Implied Volatility (IV) increases by <b>+1%</b> (e.g. before an earnings announcement or RBI policy), this option gains <b>+₹${Math.abs(val).toFixed(2)}</b> even if ${sym} price does not move at all.<br>
          • If IV crashes by <b>-5%</b> (post-event IV crush), the option loses approximately <b>-₹${(Math.abs(val) * 5).toFixed(2)}</b> in premium.
        </div>
      `;
    } else {
      title = `${greekName} (${fmt(val)}%)`;
      explanation = `<b>Implied Volatility (IV)</b> represents the market's expected future price fluctuation of ${sym} over the next year.`;
      formula = `High IV = Higher Option Premiums; Low IV = Cheaper Options`;
      realLifeExample = `
        <div style="background:var(--surface-2);border-left:3px solid var(--neutral);padding:10px 12px;border-radius:6px;font-size:11.5px;line-height:1.5;">
          <b>Movement Explanation with Current Value (${val}%):</b><br>
          • Current IV of <b>${val}%</b> reflects the market's expected volatility.<br>
          • Higher IV inflates both Call and Put premiums; lower IV makes option purchases cheaper.<br>
          • Ahead of high-impact news, IV rises; once results are out, IV collapses ("IV crush").
        </div>
      `;
    }

    document.getElementById('greekModalTitle').textContent = title;
    body.innerHTML = `
      <div style="font-size:12px;color:var(--text);line-height:1.45;">${explanation}</div>
      ${realLifeExample}
      <div class="card" style="padding:12px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
        <div style="font-weight:700;font-size:11.5px;margin-bottom:8px;display:flex;justify-content:space-between;">
          <span>Interactive Price Sensitivity Simulator</span>
          <span class="muted">${sym} Strike: ${strike || 'ATM'}</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          <label style="font-size:11px;min-width:110px;">Move in ${sym}:</label>
          <input type="range" id="greekSimSlider" min="-${simDefaultMove*2}" max="${simDefaultMove*2}" step="${Math.max(1, Math.round(simDefaultMove/10))}" value="${Math.round(simDefaultMove/2)}" style="flex:1;">
          <span id="greekSimMoveDisplay" style="font-family:var(--font-mono);font-weight:700;min-width:70px;text-align:right;">+₹${Math.round(simDefaultMove/2)}</span>
        </div>
        <div id="greekSimResult" style="margin-top:10px;padding:8px 10px;background:var(--surface);border-radius:6px;font-family:var(--font-mono);font-size:11px;color:var(--text);display:grid;grid-template-columns:1fr 1fr;gap:8px;">
        </div>
      </div>
    `;

    function updateSim(move){
      const res = document.getElementById('greekSimResult');
      if(!res) return;
      if(greekName.includes('Gamma')){
        const deltaChg = move * val;
        const newDelta = delta + deltaChg;
        const optGain = move * delta + 0.5 * val * move * move;
        res.innerHTML = `
          <div>Delta Change: <b style="color:${deltaChg>=0?'var(--buy)':'var(--sell)'}">${deltaChg>=0?'+':''}${deltaChg.toFixed(3)}</b></div>
          <div>New Delta: <b>${newDelta.toFixed(3)}</b></div>
          <div style="grid-column:span 2">Estimated Option Gain: <b style="color:${optGain>=0?'var(--buy)':'var(--sell)'}">${optGain>=0?'+':''}₹${optGain.toFixed(2)}</b></div>
        `;
      } else if(greekName.includes('Delta')){
        const optGain = move * val;
        res.innerHTML = `
          <div>Underlying Move: <b>${move>=0?'+':''}₹${move}</b></div>
          <div>Delta: <b>${val}</b></div>
          <div style="grid-column:span 2">Estimated Option Gain: <b style="color:${optGain>=0?'var(--buy)':'var(--sell)'}">${optGain>=0?'+':''}₹${optGain.toFixed(2)}</b></div>
        `;
      } else if(greekName.includes('Theta')){
        const days = Math.max(1, Math.round(Math.abs(move) / (simDefaultMove/4)));
        const decay = Math.abs(val) * days;
        res.innerHTML = `
          <div>Time Elapsed: <b>${days} day(s)</b></div>
          <div>Daily Theta: <b>${val}</b></div>
          <div style="grid-column:span 2">Cumulative Premium Decay: <b style="color:var(--sell)">-₹${decay.toFixed(2)}</b></div>
        `;
      } else {
        const ivMove = (move / 10).toFixed(1);
        const optChg = (Number(ivMove) * Math.abs(val)).toFixed(2);
        res.innerHTML = `
          <div>IV Shift: <b>${ivMove>=0?'+':''}${ivMove}%</b></div>
          <div>Vega / IV: <b>${val}</b></div>
          <div style="grid-column:span 2">Option Premium Shift: <b style="color:${optChg>=0?'var(--buy)':'var(--sell)'}">${optChg>=0?'+':''}₹${optChg}</b></div>
        `;
      }
    }

    const slider = document.getElementById('greekSimSlider');
    slider?.addEventListener('input', (e) => {
      const m = Number(e.target.value);
      document.getElementById('greekSimMoveDisplay').textContent = `${m>=0?'+':''}₹${m}`;
      updateSim(m);
    });
    updateSim(Math.round(simDefaultMove/2));

    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  }
  window.openGreekModal = openGreekModal;
  document.getElementById('greekModalClose')?.addEventListener('click', () => {
    const modal = document.getElementById('greekModal');
    if(modal){ modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
  });

  function showGreeks(r){
    const c=r?.call||{},p=r?.put||{};
    document.getElementById('greeksTitle').textContent=`Greeks — ${S} ${r?.strike||''} (Click card for meaning & price simulation)`;
    const items = [
      ['Call Delta', c.delta, c.delta, p.delta],
      ['Call Gamma', c.gamma, c.delta, p.delta],
      ['Call Theta', c.theta, c.delta, p.delta],
      ['Call Vega', c.vega, c.delta, p.delta],
      ['Call IV', c.iv, c.delta, p.delta],
      ['Put Delta', p.delta, c.delta, p.delta],
      ['Put Gamma', p.gamma, c.delta, p.delta],
      ['Put Theta', p.theta, c.delta, p.delta],
      ['Put Vega', p.vega, c.delta, p.delta],
      ['Put IV', p.iv, c.delta, p.delta]
    ];
    document.getElementById('greeksGrid').innerHTML = items.map(x=>`
      <div class="stat-card greek-clickable" style="border:1px solid var(--border-soft);border-radius:8px;padding:10px;cursor:pointer;" title="Click to understand ${x[0]} and simulate option movement" onclick="window.openGreekModal('${x[0]}', ${x[1] ?? 0}, '${S}', '${r?.strike || ''}', '${x[2] ?? 0}', '${x[3] ?? 0}')">
        <div class="label" style="display:flex;justify-content:space-between;align-items:center;">
          <span>${x[0]}</span>
          <span style="font-size:9.5px;color:var(--gold);opacity:0.8;">ⓘ Learn</span>
        </div>
        <div class="value" style="font-size:16px">${fmt(x[1])}</div>
      </div>
    `).join('');
  }
  window.showGreeks = showGreeks;
  document.getElementById('findBuyableBtn').onclick=null;

  document.getElementById('scanPatterns').onclick=scanPatterns;
  document.querySelectorAll('.navtab').forEach(t=>t.addEventListener('click',()=>{if(t.dataset.tab==='options')void loadOptions()}));

  document.querySelectorAll('.wl-filters .chip-filter').forEach(c=>c.addEventListener('click',()=>{document.querySelectorAll('.wl-filters .chip-filter').forEach(x=>x.classList.remove('active'));c.classList.add('active');F=c.dataset.filter;R()}));

  await loadProfile();connectWS();void initMarketState();setInterval(()=>{if(document.visibilityState==='visible')void initMarketState()},30000);await W0();if(S)void onSymbolChanged(S);void subscribeAllLive();renderApplied();draw();

  window.state = state;
  window.__CA_TRADER_STATE = state;
  window.draw = draw;
  window.loadChart = loadChart;
  window.ensureChartLayout = ensureChartLayout;
  window.selectedSymbol = () => S || document.querySelector('.wl-item.selected')?.dataset.symbol || window.CATraderSymbol || state.symbol || 'RELIANCE';

  // Public bridge for code in the other terminal IIFEs. Keeping one canonical
  // chart loader prevents cross-IIFE ReferenceErrors from stopping analysis.
  window.CATraderAnalysis = Object.assign(window.CATraderAnalysis || {}, {
    loadChart,
    loadChartBundle,
    loadChartMtf,
    renderIndicators,
    ensureChartLayout,
    draw
  });
  // Public live-market bridge: later IIFEs must use the same tick applier.
  // Without this bridge, the background snapshot loop can throw a ReferenceError
  // because applyLiveTick is private to this IIFE, which makes prices update only
  // when a watchlist/tab interaction calls the first IIFE again.
  window.CATraderLiveMarket = Object.assign(window.CATraderLiveMarket || {}, {
    applyLiveTick,
    applyMarketStreamState,
    subscribeAllLive,
    subscribeInstrument,
    getLiveTick: (symbol) => (window.__CA_WL_QUOTES || {})[String(symbol || '').toUpperCase()] || null
  });
})();
