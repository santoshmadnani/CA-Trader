# apply_fixes_phase1.py
import re
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=== Patching terminal.html and app.py ===")

# -------------------------------------------------------------
# 1. Patch terminal.html
# -------------------------------------------------------------
with open('terminal.html', 'r', encoding='utf-8') as f:
    t_html = f.read()

# A. Update getSymbolLotSize
old_get_lot = """  function getSymbolLotSize(sym){
    const s = String(sym || window.__caOrderInstrumentKey || selectedSymbol() || '').toUpperCase();
    if(s.includes('BANKNIFTY')) return 15;
    if(s.includes('FINNIFTY')) return 25;
    if(s.includes('MIDCPNIFTY')) return 50;
    if(s.includes('NIFTY')) return 25;
    if(s.includes('CRUDEOIL')) return 100;
    if(s.includes('NATURALGAS')) return 1250;
    if(s.includes('GOLDM')) return 10;
    if(s.includes('GOLD')) return 100;
    if(s.includes('SILVERM')) return 5;
    if(s.includes('SILVER')) return 30;
    if(s.includes('COPPER')) return 2500;
    if(s.includes('ZINC')) return 5000;
    return window.__caOrderLotSize || 1;
  }"""

new_get_lot = """  function getSymbolLotSize(sym){
    const s = String(sym || window.__caOrderInstrumentKey || selectedSymbol() || '').toUpperCase();
    if(s.includes('BANKNIFTY')) return 15;
    if(s.includes('FINNIFTY')) return 25;
    if(s.includes('MIDCPNIFTY')) return 50;
    if(s.includes('NIFTY')) return 65;
    if(s.includes('CRUDEOIL')) return 100;
    if(s.includes('NATURALGAS')) return 1250;
    if(s.includes('GOLDM')) return 10;
    if(s.includes('GOLD')) return 100;
    if(s.includes('SILVERM')) return 5;
    if(s.includes('SILVER')) return 30;
    if(s.includes('COPPER')) return 2500;
    if(s.includes('ZINC')) return 5000;
    return window.__caOrderLotSize || 1;
  }"""

if old_get_lot in t_html:
    t_html = t_html.replace(old_get_lot, new_get_lot)
    print("✓ Updated getSymbolLotSize with NIFTY=65 in terminal.html")
else:
    print("! old_get_lot not matched")

# B. Update openOrder and orderQty input listener
old_open_order = """  function openOrder(side,instrument=null,lotSize=1,display=null){
    orderSide=side;
    window.__caOrderInstrumentKey=instrument;
    window.__caOrderLotSize=Number(lotSize)||1;
    window.__caOrderDisplay=display;
    $('orderModalTitle').textContent=`${side} ${display||instrument||selectedSymbol()}`;
    $('orderQtyLabel').textContent=instrument?'Lots':'Quantity / Lots';
    $('orderQty').value=1;
    const currentLot = getSymbolLotSize(instrument || display || selectedSymbol());
    $('orderReferenceShares').textContent = `1 Lot = ${currentLot} Qty (Total: ${currentLot * (Number($('orderQty').value)||1)} Qty)`;
    if($('orderTrailingSl')) $('orderTrailingSl').value = '';
    $('orderSubmit').textContent=`Place ${side}`;
    $('orderSubmit').className='btn '+(side==='BUY'?'gold':'ghost');
    openModal('orderModal');
    refreshOrderQuote();
  }"""

new_open_order = """  function openOrder(side,instrument=null,lotSize=null,display=null){
    orderSide=side;
    window.__caOrderInstrumentKey=instrument;
    const symName = instrument || display || selectedSymbol() || 'NIFTY';
    const currentLot = Number(lotSize) || getSymbolLotSize(symName);
    window.__caOrderLotSize = currentLot;
    window.__caOrderDisplay = display;
    $('orderModalTitle').textContent=`${side} ${display||instrument||selectedSymbol()}`;
    const isDerivative = currentLot > 1 || String(symName).toUpperCase().includes('NIFTY') || String(symName).toUpperCase().includes('CRUDE');
    $('orderQtyLabel').textContent = isDerivative ? `Quantity (1 Lot = ${currentLot} Contracts)` : 'Quantity';
    $('orderQty').value = currentLot;
    $('orderReferenceShares').textContent = `1 Lot = ${currentLot} Contracts (Type 1 or ${currentLot} for 1 Lot, 2 or ${currentLot * 2} for 2 Lots)`;
    if($('orderTrailingSl')) $('orderTrailingSl').value = '';
    $('orderSubmit').textContent=`Place ${side}`;
    $('orderSubmit').className='btn '+(side==='BUY'?'gold':'ghost');
    openModal('orderModal');
    refreshOrderQuote();
  }"""

if old_open_order in t_html:
    t_html = t_html.replace(old_open_order, new_open_order)
    print("✓ Updated openOrder in terminal.html")
else:
    print("! old_open_order not matched")

old_order_qty_listener = """  $('orderQty')?.addEventListener('input',()=>{
    const currentLot = getSymbolLotSize(window.__caOrderInstrumentKey || selectedSymbol());
    const lots = Number($('orderQty').value) || 1;
    if($('orderReferenceShares')) $('orderReferenceShares').textContent = `1 Lot = ${currentLot} Qty (Total: ${currentLot * lots} Qty)`;
  });"""

new_order_qty_listener = """  $('orderQty')?.addEventListener('input',()=>{
    const currentLot = window.__caOrderLotSize || getSymbolLotSize(window.__caOrderInstrumentKey || selectedSymbol());
    const val = Number($('orderQty').value) || 0;
    const effectiveQty = (currentLot > 1 && val > 0 && val < currentLot) ? (val * currentLot) : val;
    if($('orderReferenceShares')) $('orderReferenceShares').textContent = `1 Lot = ${currentLot} Contracts (Total: ${effectiveQty} Contracts)`;
  });"""

if old_order_qty_listener in t_html:
    t_html = t_html.replace(old_order_qty_listener, new_order_qty_listener)
    print("✓ Updated orderQty input listener")
else:
    print("! old_order_qty_listener not matched")

# C. Update orderSubmit quantity calculation
old_order_submit_qty = """      const lots=Number($('orderQty').value)||1;
      const body={
        symbol:window.__caOrderInstrumentKey||window.__caOrderDisplay||selectedSymbol(),
        side:orderSide,
        quantity:Math.max(1,Math.round(lots*(window.__caOrderInstrumentKey?window.__caOrderLotSize:1))),"""

new_order_submit_qty = """      const currentLot = window.__caOrderLotSize || getSymbolLotSize(window.__caOrderInstrumentKey || window.__caOrderDisplay || selectedSymbol());
      const rawQty = Number($('orderQty').value) || currentLot;
      let finalQty = rawQty;
      if (currentLot > 1) {
        if (rawQty < currentLot) {
          finalQty = Math.max(1, Math.round(rawQty)) * currentLot;
        } else {
          finalQty = Math.max(currentLot, Math.round(rawQty / currentLot) * currentLot);
        }
      }
      const body={
        symbol:window.__caOrderInstrumentKey||window.__caOrderDisplay||selectedSymbol(),
        side:orderSide,
        quantity:finalQty,"""

if old_order_submit_qty in t_html:
    t_html = t_html.replace(old_order_submit_qty, new_order_submit_qty)
    print("✓ Updated orderSubmit quantity calculation")
else:
    print("! old_order_submit_qty not matched")

# D. Update openQuickOrderModal
old_qo_lot = """    const lotSize = Number(inst.lot_size || window.__caOrderLotSize || 1);
    const tslPts = (entry && sl) ? Math.max(1, Math.round(Math.abs(entry - sl) * 0.5 * 10) / 10) : 0;

    $('quickOrderSideBadge').textContent = orderSideText;
    $('quickOrderSideBadge').className = `tag ${isBuy ? 'buy' : 'sell'}`;
    $('quickOrderModalTitle').textContent = `Quick 1-Click Order · ${orderSideText}`;
    $('quickOrderSymbol').textContent = dispSym;
    $('quickOrderSymbol').dataset.symbolKey = inst.symbol || sym;
    $('quickOrderSymbol').dataset.lotSize = lotSize;
    $('quickOrderSymbol').dataset.side = orderSideText;
    $('quickOrderLtp').textContent = entry ? `₹${fmt(entry)}` : 'Market Price';

    $('quickOrderQty').value = 1;
    $('quickOrderQtyLabel').textContent = isOption ? 'Lots' : 'Quantity / Lots';
    $('quickOrderSharesHint').textContent = isOption ? `1 lot = ${lotSize} contracts` : `1 unit`;"""

new_qo_lot = """    const currentLot = Number(inst.lot_size) || getSymbolLotSize(dispSym || sym);
    const lotSize = currentLot;
    const tslPts = (entry && sl) ? Math.max(1, Math.round(Math.abs(entry - sl) * 0.5 * 10) / 10) : 0;

    $('quickOrderSideBadge').textContent = orderSideText;
    $('quickOrderSideBadge').className = `tag ${isBuy ? 'buy' : 'sell'}`;
    $('quickOrderModalTitle').textContent = `Quick 1-Click Order · ${orderSideText}`;
    $('quickOrderSymbol').textContent = dispSym;
    $('quickOrderSymbol').dataset.symbolKey = inst.symbol || sym;
    $('quickOrderSymbol').dataset.lotSize = lotSize;
    $('quickOrderSymbol').dataset.side = orderSideText;
    $('quickOrderLtp').textContent = entry ? `₹${fmt(entry)}` : 'Market Price';

    $('quickOrderQty').value = lotSize;
    $('quickOrderQtyLabel').textContent = isOption ? `Quantity (1 Lot = ${lotSize} Contracts)` : 'Quantity';
    $('quickOrderSharesHint').textContent = isOption ? `1 Lot = ${lotSize} Contracts (Type 1 or ${lotSize} for 1 Lot, ${lotSize*2} for 2 Lots)` : `1 unit`;"""

if old_qo_lot in t_html:
    t_html = t_html.replace(old_qo_lot, new_qo_lot)
    print("✓ Updated openQuickOrderModal lot display and default")
else:
    print("! old_qo_lot not matched")

# E. Update quickOrderSubmit
old_qo_submit = """      const lots = Number($('quickOrderQty').value) || 1;
      const totalQty = Math.max(1, Math.round(lots * lotSize));"""

new_qo_submit = """      const rawLots = Number($('quickOrderQty').value) || lotSize;
      let totalQty = rawLots;
      if (lotSize > 1) {
        if (rawLots < lotSize) {
          totalQty = Math.max(1, Math.round(rawLots)) * lotSize;
        } else {
          totalQty = Math.max(lotSize, Math.round(rawLots / lotSize) * lotSize);
        }
      }"""

if old_qo_submit in t_html:
    t_html = t_html.replace(old_qo_submit, new_qo_submit)
    print("✓ Updated quickOrderSubmit quantity calculation")
else:
    print("! old_qo_submit not matched")

# F. Fix applyLiveTick for positions (line 5354)
old_live_pos = """    document.querySelectorAll('[data-pos-symbol]').forEach(row=>{
      if(String(row.dataset.posSymbol||'').toUpperCase()!==key)return;
      const l=row.querySelector('.pos-ltp');if(l)l.textContent=fmt(ltp);
      const avg=Number(row.dataset.avg||0),qty=Number(row.dataset.qty||0),side=String(row.dataset.side||'BUY').toUpperCase();
      const pnl=(side==='BUY'?(ltp-avg):(avg-ltp))*qty;const pe=row.querySelector('.pos-pnl');if(pe){pe.textContent=fmtMoney(pnl);pe.className='pos-pnl '+(pnl>=0?'cell-up':'cell-down')}
    });"""

new_live_pos = """    document.querySelectorAll('[data-pos-symbol]').forEach(row=>{
      if(String(row.dataset.posSymbol||'').toUpperCase()!==key)return;
      const l=row.querySelector('.pos-ltp');if(l)l.textContent=fmt(ltp);
      // Closed positions have already settled and must not be overwritten by live ticks
      if(row.dataset.isOpen !== 'true') return;
      const avg=Number(row.dataset.avg||0),qty=Number(row.dataset.qty||0),side=String(row.dataset.side||'BUY').toUpperCase();
      if(qty > 0 && avg > 0){
        const pnl=(side==='BUY'?(ltp-avg):(avg-ltp))*qty;
        const pe=row.querySelector('.pos-pnl');
        if(pe){
          pe.textContent=fmtMoney(pnl);
          pe.className='pos-pnl '+(pnl>=0?'cell-up':'cell-down');
        }
      }
    });"""

if old_live_pos in t_html:
    t_html = t_html.replace(old_live_pos, new_live_pos)
    print("✓ Updated applyLiveTick for positions")
else:
    print("! old_live_pos not matched")

# G. Fix position table row rendering in loadPositions (around line 10708)
old_pos_tr = """                return `
                  <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}">"""

new_pos_tr = """                return `
                  <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}" data-avg="${avgPrice}" data-qty="${finalDispQty}" data-side="${esc(x.side||'BUY')}" data-is-open="${isOpen ? 'true' : 'false'}">"""

if old_pos_tr in t_html:
    t_html = t_html.replace(old_pos_tr, new_pos_tr)
    print("✓ Updated position table tr with data-avg, data-qty, data-side, data-is-open")
else:
    print("! old_pos_tr not matched")

# Also ensure closed positions show '—' for Live P&L or don't confuse user with ₹0.00
old_pos_pnl_td = """                    <td class="pos-pnl ${livePnl >= 0 ? 'cell-up' : 'cell-down'}" style="font-weight:700;font-family:var(--font-mono);">
                      ${fmtMoney(livePnl)}
                    </td>"""

new_pos_pnl_td = """                    <td class="pos-pnl ${isOpen ? (livePnl >= 0 ? 'cell-up' : 'cell-down') : 'cell-num'}" style="font-weight:700;font-family:var(--font-mono);">
                      ${isOpen ? fmtMoney(livePnl) : '<span style="color:var(--text-faint);font-size:10px;">Settled</span>'}
                    </td>"""

if old_pos_pnl_td in t_html:
    t_html = t_html.replace(old_pos_pnl_td, new_pos_pnl_td)
    print("✓ Updated pos-pnl td for open vs closed positions")
else:
    print("! old_pos_pnl_td not matched")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(t_html)
print("terminal.html patch completed.")

# -------------------------------------------------------------
# 2. Patch app.py
# -------------------------------------------------------------
with open('app.py', 'r', encoding='utf-8') as f:
    a_py = f.read()

# Update lot sizes in app.py
a_py = a_py.replace('"NIFTY": {"spot": 23398.10, "step": 50.0, "lot": 25, "iv": 13.0, "default_exp": "24 SEP 2026"}',
                    '"NIFTY": {"spot": 23398.10, "step": 50.0, "lot": 65, "iv": 13.0, "default_exp": "24 SEP 2026"}')
a_py = a_py.replace('lot = 25 if "NIFTY" in sym else 15 if "BANK" in sym else 100 if "CRUDE" in sym else 10',
                    'lot = 65 if "NIFTY" in sym else 15 if "BANK" in sym else 100 if "CRUDE" in sym else 10')
a_py = a_py.replace('lot_size = 15 if s == "BANKNIFTY" else 25',
                    'lot_size = 15 if s == "BANKNIFTY" else 65')
a_py = a_py.replace('lot = int(meta.get("lot_size") or (30 if "BANK" in symbol.upper() else 25 if "NIFTY" in symbol.upper() else 1))',
                    'lot = int(meta.get("lot_size") or (15 if "BANK" in symbol.upper() else 65 if "NIFTY" in symbol.upper() else 1))')

# Anti-Counter-Trend & Confluence Guard in overall_recommendation
# Locate where opt_info is evaluated:
old_opt_block = """        if opt_type == "PE":
            opt_action = "BUY" if side in ("SELL", "NO_TRADE") else "SELL"
        else:
            opt_action = "BUY" if side in ("BUY", "NO_TRADE") else "SELL"

        # Option recommendations are strictly BUY only: Call Buying (BUY CE) or Put Buying (BUY PE)
        opt_action = "BUY"
        profit_per_share = max(500.0 / lot, opt_entry * 0.25)"""

new_opt_block = """        # Multi-Factor Trend Alignment Guard:
        # Never recommend counter-trend option buying against the underlying trend.
        is_underlying_bullish = side == "BUY" or (last_price >= ema20 and rsi_val >= 50.0)
        is_underlying_bearish = side == "SELL" or (last_price <= ema20 and rsi_val <= 50.0)
        
        if opt_type == "PE" and is_underlying_bullish:
            inst_obj = {"kind": "OPTION", "symbol": symbol, "display": symbol, "entry": opt_entry, "instrument_key": key, "lot_size": lot, "option_type": opt_type}
            reason_msg = f"Counter-Trend Guard: Underlying {underlying} is Bullish (above 20 EMA, RSI {rsi_val:.1f}). Put buying (PE) into an advancing market carries high directional friction and severe Theta erosion."
            res_opt = {
                "qualifies": False,
                "recommendation": "NO_TRADE",
                "timeframe": timeframe,
                "confidence": 35.0,
                "entry": None,
                "stop_loss": None,
                "target": None,
                "expected_risk": None,
                "expected_reward": None,
                "risk_reward": None,
                "instrument": inst_obj,
                "evidence": evidence,
                "greeks": bs_greeks(last_price, opt_strike, t_years=15.0/365.0, r=0.07, sigma=0.18, opt_type="PE"),
                "rationale": reason_msg,
                "reason": reason_msg,
                "provider": "upstox+greeks_engine",
                "timestamp": now_iso(),
                **next_day_info
            }
            CACHE.set(cache_key, res_opt, 15)
            return res_opt
            
        if opt_type == "CE" and is_underlying_bearish:
            inst_obj = {"kind": "OPTION", "symbol": symbol, "display": symbol, "entry": opt_entry, "instrument_key": key, "lot_size": lot, "option_type": opt_type}
            reason_msg = f"Counter-Trend Guard: Underlying {underlying} is Bearish (below 20 EMA, RSI {rsi_val:.1f}). Call buying (CE) into a falling market carries high directional friction and severe Theta erosion."
            res_opt = {
                "qualifies": False,
                "recommendation": "NO_TRADE",
                "timeframe": timeframe,
                "confidence": 35.0,
                "entry": None,
                "stop_loss": None,
                "target": None,
                "expected_risk": None,
                "expected_reward": None,
                "risk_reward": None,
                "instrument": inst_obj,
                "evidence": evidence,
                "greeks": bs_greeks(last_price, opt_strike, t_years=15.0/365.0, r=0.07, sigma=0.18, opt_type="CE"),
                "rationale": reason_msg,
                "reason": reason_msg,
                "provider": "upstox+greeks_engine",
                "timestamp": now_iso(),
                **next_day_info
            }
            CACHE.set(cache_key, res_opt, 15)
            return res_opt

        opt_action = "BUY"
        profit_per_share = max(500.0 / lot, opt_entry * 0.20)"""

if old_opt_block in a_py:
    a_py = a_py.replace(old_opt_block, new_opt_block)
    print("✓ Enforced Anti-Counter-Trend Guard in overall_recommendation in app.py")
else:
    print("! old_opt_block not matched")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(a_py)
print("app.py patch completed.")
