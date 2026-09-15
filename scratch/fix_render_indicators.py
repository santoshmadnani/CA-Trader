# -*- coding: utf-8 -*-

with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

p_start = c.find('function renderIndicators(rows){')
p_end = c.find('function fallbackTechnicalRows()', p_start)

if p_start == -1 or p_end == -1:
    print("Error: bounds not found")
    sys.exit(1)

clean_block = """function renderIndicators(rows){
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
    const pane=document.getElementById('indicatorAppliedPane');
    if(pane){
      const selected=state.appliedIndicators||[];
      const wanted=selected.length?rows.filter(r=>selected.some(i=>i.name===r.name)):[];
      pane.innerHTML=wanted.length?wanted.map(r=>`<span class="indicator-live-chip"><b>${r.name}</b><span>${fmt(r.value)}</span><span class="tag ${r.signal==='BUY'?'buy':r.signal==='SELL'?'sell':'neutral'}">${r.signal}</span></span>`).join(''):(selected.length?selected.map(i=>`<span class="indicator-live-chip"><b>${esc(i.name)}</b><span>Applied · waiting for value</span></span>`).join(''):'');
    }
    const upd = document.getElementById('signalUpdated');
    if(upd) upd.textContent=`Updated ${new Date().toLocaleTimeString('en-IN',{hour12:false})}`;
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
  window.toggleChartIndicator = toggleChartIndicator;

  """

c = c[:p_start] + clean_block + c[p_end:]
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(c)
print("terminal.html: Fixed renderIndicators and toggleChartIndicator block cleanly.")

