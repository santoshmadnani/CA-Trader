import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
    content = f.read()

# ==============================================================================
# 1. Update loadPortfolioSnapshot with resilient fallback and separated renderers
# ==============================================================================

old_portfolio_code = """  // Authoritative Portfolio Snapshot & Classic Broker Positions Table (Item 7)
  async function loadPortfolioSnapshot(force=true){
    try{
      const d=await api('/api/portfolio/snapshot?_='+Date.now(),{timeoutMs:3500,cache:'no-store'});"""

new_portfolio_code = """  // Reusable Broker Positions Table Renderer
  function renderPositionsTable(allPositions, advisories=[]){
    const openPositions = allPositions.filter(x => String(x.status||'OPEN').toUpperCase() === 'OPEN' && Number(x.quantity||0) > 0);
    const closedPositions = allPositions.filter(x => String(x.status||'OPEN').toUpperCase() === 'CLOSED' || Number(x.quantity||0) === 0);
    const targetPositions = activePosSubTab === 'open' ? openPositions : closedPositions;

    if($('positionsTable')){
      const prevWrap = $('positionsTable').querySelector('.table-wrap');
      const prevScrollLeft = prevWrap ? prevWrap.scrollLeft : 0;
      const prevScrollTop = prevWrap ? prevWrap.scrollTop : 0;
      const isOpen = activePosSubTab === 'open';
      $('positionsTable').innerHTML = `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Entry Time</th>
                ${!isOpen ? '<th>Exit Time</th>' : ''}
                <th>Avg Price</th>
                ${!isOpen ? '<th>Exit Price</th>' : ''}
                <th>LTP</th>
                <th>Live P&amp;L</th>
                ${!isOpen ? '<th>Final P&amp;L</th>' : ''}
                ${isOpen ? '<th>Stop Loss</th><th>Target</th><th>TSL</th>' : ''}
                <th>Action &amp; Analysis</th>
              </tr>
            </thead>
            <tbody>
              ${targetPositions.length ? targetPositions.map(x => {
                const symUpper = String(x.symbol || '').toUpperCase();
                const liveQuote = (window.__CA_WL_QUOTES || {})[symUpper] || (window.__CA_WL_QUOTES || {})[x.symbol] || {};
                const avgPrice = Number(x.avg_price || x.entry || 0);
                const qty = Number(x.quantity || 1);
                const isBuy = String(x.side || 'BUY').toUpperCase() === 'BUY';
                
                let ltpVal = (x.ltp != null && Number(x.ltp) > 0) ? Number(x.ltp) :
                             (liveQuote.ltp != null && Number(liveQuote.ltp) > 0) ? Number(liveQuote.ltp) :
                             (liveQuote.close != null && Number(liveQuote.close) > 0) ? Number(liveQuote.close) :
                             (x.mark != null && Number(x.mark) > 0) ? Number(x.mark) :
                             (x.current_price != null && Number(x.current_price) > 0) ? Number(x.current_price) : avgPrice;

                let livePnl = 0;
                if (ltpVal > 0 && avgPrice > 0) {
                  livePnl = isBuy ? (ltpVal - avgPrice) * qty : (avgPrice - ltpVal) * qty;
                } else if (x.live_pnl != null) {
                  livePnl = Number(x.live_pnl);
                } else if (x.unrealized_pnl != null) {
                  livePnl = Number(x.unrealized_pnl);
                }

                const finalPnl = Number(x.final_pnl != null ? x.final_pnl : (x.realized_pnl != null ? x.realized_pnl : 0));
                const entryTimeStr = x.created_at || x.opened_at || x.entry_time || '';
                const exitTimeStr = x.closed_at || x.updated_at || x.exit_time || '';

                const dispQty = Number(x.display_quantity || x.closed_quantity || (x.quantity > 0 ? x.quantity : 1));
                const finalDispQty = (symUpper.includes('CRUDEOIL') && dispQty === 1) ? 100 : dispQty;
                return `
                  <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}">
                    <td><b>${esc(x.symbol)}</b></td>
                    <td><span class="tag ${signalClass(x.side)}">${esc(x.side||'BUY')}</span></td>
                    <td><b>${fmt(finalDispQty)}</b></td>
                    <td style="font-size:11px;color:var(--text-faint);">${esc(formatTime(entryTimeStr))}</td>
                    ${!isOpen ? `<td style="font-size:11px;color:var(--text-faint);">${esc(formatTime(exitTimeStr))}</td>` : ''}
                    <td>₹${fmt(avgPrice)}</td>
                    ${!isOpen ? `<td>${x.exit_price ? '₹'+fmt(x.exit_price) : '—'}</td>` : ''}
                    <td class="pos-ltp">₹${fmt(ltpVal)}</td>
                    <td class="pos-pnl ${livePnl >= 0 ? 'cell-up' : 'cell-down'}" style="font-weight:700;font-family:var(--font-mono);">
                      ${fmtMoney(livePnl)}
                    </td>
                    ${!isOpen ? `
                      <td class="pos-final-pnl ${finalPnl >= 0 ? 'cell-up' : 'cell-down'}" style="font-weight:700;font-family:var(--font-mono);">
                        ${fmtMoney(finalPnl)}
                      </td>
                    ` : ''}
                    ${isOpen ? `
                      <td>₹${fmt(x.stop_loss)}</td>
                      <td>₹${fmt(x.target)}</td>
                      <td>${x.trailing_sl ? fmt(x.trailing_sl)+' pts' : '—'}</td>
                    ` : ''}
                    <td>
                      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
                        ${isOpen ? `<button class="btn ghost small position-squareoff" data-position-id="${esc(x.id)}" style="padding:2px 8px;font-size:10.5px;">Square off</button>` : ''}
                        <button class="btn gold small pos-analysis-btn" onclick="openPosAnalysisModal('${esc(x.id)}')" style="padding:2px 8px;font-size:10.5px;" title="View Entry Thesis & CA AI Loss Analysis"> AI Analysis</button>
                      </div>
                    </td>
                  </tr>
                `;
              }).join('') : `<tr><td colspan="11" class="data-empty" style="text-align:center;padding:20px;">No ${activePosSubTab} positions.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;
      const curWrap = $('positionsTable')?.querySelector('.table-wrap');
      if(curWrap && (prevScrollLeft || prevScrollTop)){
        curWrap.scrollLeft = prevScrollLeft;
        curWrap.scrollTop = prevScrollTop;
      }
    }

    // Square-off button delegation
    document.querySelectorAll('.position-squareoff').forEach(btn => {
      btn.onclick = async () => {
        if(!confirm('Square off this position at the latest live price?')) return;
        try{
          const r = await api('/api/positions/' + encodeURIComponent(btn.dataset.positionId) + '/square-off', {method: 'POST'});
          toast(`Squared off · Final P&L ${fmtMoney(r.final_pnl)}`);
          await loadPortfolioSnapshot(true);
          if(typeof refreshNotificationBadge === 'function') void refreshNotificationBadge();
        }catch(e){toast(e.message)}
      };
    });
  }
  window.renderPositionsTable = renderPositionsTable;

  // Reusable Orders Table Renderer
  function renderOrdersTable(allOrders){
    const todayStr = new Date().toISOString().slice(0, 10);
    const todayOrders = allOrders.filter(x => (x.created_at || '').startsWith(todayStr));
    const pastOrders = allOrders.filter(x => !(x.created_at || '').startsWith(todayStr));
    const targetOrders = activeOrderSubTab === 'today' ? todayOrders : pastOrders;

    if($('ordersTable')){
      const prevOrderWrap = $('ordersTable').querySelector('.table-wrap');
      const prevOrderScrollLeft = prevOrderWrap ? prevOrderWrap.scrollLeft : 0;
      const prevOrderScrollTop = prevOrderWrap ? prevOrderWrap.scrollTop : 0;

      $('ordersTable').innerHTML = `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Type</th>
                <th>Price</th>
                <th>TSL</th>
                <th>Status</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              ${targetOrders.length ? targetOrders.map(x => `
                <tr data-order-symbol="${esc(x.symbol)}">
                  <td><b>${esc(x.symbol)}</b></td>
                  <td><span class="tag ${signalClass(x.side)}">${esc(x.side)}</span></td>
                  <td>${fmt(x.quantity)}</td>
                  <td>${esc(x.order_type || 'MARKET')}</td>
                  <td>₹${fmt(x.price || x.ltp)}</td>
                  <td>${x.trailing_sl ? fmt(x.trailing_sl)+' pts' : '—'}</td>
                  <td><span class="tag ${signalClass(x.status_display || x.status)}">${esc(x.status_display || x.status || 'SUBMITTED')}</span></td>
                  <td style="font-size:11px;color:var(--text-faint);">${esc(formatTime(x.created_at || ''))}</td>
                </tr>
              `).join('') : `<tr><td colspan="8" class="data-empty" style="text-align:center;padding:20px;">No ${activeOrderSubTab === 'today' ? "today's" : "past"} orders.</td></tr>`}
            </tbody>
          </table>
        </div>
      `;

      const curOrderWrap = $('ordersTable')?.querySelector('.table-wrap');
      if(curOrderWrap && (prevOrderScrollLeft || prevOrderScrollTop)){
        curOrderWrap.scrollLeft = prevOrderScrollLeft;
        curOrderWrap.scrollTop = prevOrderScrollTop;
      }
    }
  }
  window.renderOrdersTable = renderOrdersTable;

  // Authoritative Portfolio Snapshot with Resilient Direct DB Fallback (Item 7 & Release 36)
  async function loadPortfolioSnapshot(force=true){
    try{
      const d=await api('/api/portfolio/snapshot?_='+Date.now(),{timeoutMs:10000,cache:'no-store'});
      const b=d.funds||{};
      if($('fundCards')){
        $('fundCards').innerHTML=[['Trading Funds',b.trading_funds],['Testing Funds',b.testing_funds],['Auto Trade Funds',b.auto_trade_funds],['Role',window.__CA_USER_ROLE==='admin'?'Admin':'User']].map(x=>`<div class="card stat-card"><div class="label">${x[0]}</div><div class="value">${x[0]==='Role'?esc(x[1]):fmtMoney(x[1]||0)}</div></div>`).join('');
      }

      // Check for Position Risk Advisories (Item 12)
      const advisories = d.advisories || [];
      const advBanner = $('positionAdvisoryBanner');
      const advText = $('positionAdvisoryText');
      if(advBanner && advText){
        if(advisories.length > 0){
          advBanner.style.display = 'block';
          advText.innerHTML = advisories.map(a => `• <b>${esc(a.symbol)}:</b> ${esc(a.message || a.warning || 'Adverse trend reversal detected against your open position.')}`).join('<br>');
        } else {
          advBanner.style.display = 'none';
        }
      }

      renderPositionsTable(d.positions || [], advisories);
      renderOrdersTable(d.orders || []);

      window.__CA_PORTFOLIO_SNAPSHOT = d;
      return d;
    }catch(e){
      console.warn('Portfolio snapshot request delayed or timed out, activating direct DB fallback:', e.message);
      // Fast fallback to local DB endpoints so Orders and Positions NEVER show "Request timed out"
      try {
        const [oRes, pRes] = await Promise.all([
          api('/api/orders?_='+Date.now(), {timeoutMs: 4000, cache: 'no-store'}).catch(()=>null),
          api('/api/positions?_='+Date.now(), {timeoutMs: 4000, cache: 'no-store'}).catch(()=>null)
        ]);
        if(pRes && Array.isArray(pRes.items)){
          renderPositionsTable(pRes.items, []);
        } else if(window.__CA_PORTFOLIO_SNAPSHOT?.positions){
          renderPositionsTable(window.__CA_PORTFOLIO_SNAPSHOT.positions, []);
        } else if($('positionsTable')){
          $('positionsTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;
        }

        if(oRes && Array.isArray(oRes.items)){
          renderOrdersTable(oRes.items);
        } else if(window.__CA_PORTFOLIO_SNAPSHOT?.orders){
          renderOrdersTable(window.__CA_PORTFOLIO_SNAPSHOT.orders);
        } else if($('ordersTable')){
          $('ordersTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;
        }
      } catch(err) {
        if($('positionsTable')) $('positionsTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;
        if($('ordersTable')) $('ordersTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;
      }
      return null;
    }
  }"""

# Find and replace the whole loadPortfolioSnapshot block
# From `// Authoritative Portfolio Snapshot` to `window.__CA_PORTFOLIO_SNAPSHOT = d;\n      return d;\n    }catch(e){\n      if($('positionsTable')) $('positionsTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;\n      if($('ordersTable')) $('ordersTable').innerHTML = `<div class="data-empty">${esc(e.message)}</div>`;\n      return null;\n    }\n  }`

pattern_snapshot = re.compile(
    r"// Authoritative Portfolio Snapshot & Classic Broker Positions Table \(Item 7\)\s*async function loadPortfolioSnapshot\(force=true\)\{.*?return null;\s*\}\s*\}",
    re.DOTALL
)

if pattern_snapshot.search(content):
    content = pattern_snapshot.sub(new_portfolio_code, content, count=1)
    print("Replaced loadPortfolioSnapshot successfully!")
else:
    print("Could not find loadPortfolioSnapshot block with regex!")

with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Finished applying portfolio patch.")

