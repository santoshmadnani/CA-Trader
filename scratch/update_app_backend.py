import re
import py_compile
import sys

app_path = r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\app.py"
def update_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

with open(app_path, "r", encoding="utf-8") as f:
    content = f.read()
    # Locate get_admin_api_passbook
    target_start = '@app.get("/api/admin/api-passbook")'
    if target_start not in content:
        print("Error: could not find get_admin_api_passbook")
        return

# 1. Fix duplicate fallback_recommendation_quick
old_def = 'def fallback_recommendation_quick(instrument: str, user_id: int | None = None, desired_profit: float | None = None) -> dict[str, Any]:\ndef fallback_recommendation_quick(instrument: str, user_id: int | None = None, desired_profit: float | None = None, expiry_scalp: bool = False) -> dict[str, Any]:'
new_def = 'def fallback_recommendation_quick(instrument: str, user_id: int | None = None, desired_profit: float | None = None, expiry_scalp: bool = False) -> dict[str, Any]:'
if old_def in content:
    content = content.replace(old_def, new_def)
    print("Fixed duplicate fallback_recommendation_quick")
    # Extract orphaned ledger block
    orphaned_match = re.search(r'(\n\s+ledger = \[\][\s\S]+?return \{\s+"ok": True,\s+"upstox":[\s\S]+?"statement": ledger\[:50\]\s+\})', content)
    if not orphaned_match:
        print("Error: could not find orphaned ledger block")
        return
    orphaned_code = orphaned_match.group(1)

# 2. Add source column to positions in init_db
old_mig = 'conn.execute("ALTER TABLE positions ADD COLUMN peak_pnl REAL DEFAULT 0")'
new_mig = '''conn.execute("ALTER TABLE positions ADD COLUMN peak_pnl REAL DEFAULT 0")
            with contextlib.suppress(Exception):
                conn.execute("ALTER TABLE positions ADD COLUMN source TEXT DEFAULT 'CA_TRADER'")'''
if old_mig in content and "ALTER TABLE positions ADD COLUMN source" not in content:
    content = content.replace(old_mig, new_mig)
    print("Added source migration to positions")
    # Cut orphaned block from end
    content = content.replace(orphaned_code, '')

# 3. Update resolve_option_for_future
resolve_pattern = re.compile(
    r'def resolve_option_for_future\(future_sym: str, opt_bias: str = "BUY", user_id: int \| None = None\) -> dict\[str, Any\] \| None:.*?(?=\ndef fallback_recommendation_quick)',
    re.DOTALL
)
    # Insert into get_admin_api_passbook right after current_gemini_tpm = sum(...)
    admin_head = 'current_gemini_tpm = sum(t[1] for t in GEMINI_USAGE_LOG["minute_tokens"])'
    if admin_head not in content:
        print("Error: could not find admin_head")
        return

new_resolve = '''def resolve_option_for_future(future_sym: str, opt_bias: str = "BUY", user_id: int | None = None) -> dict[str, Any] | None:
    """Find the optimal option contract for a futures symbol with STRICT directional consensus.
    Priority 1: Live Option Chain Engine (calculating true ATM/near-OTM strike and live Upstox LTP).
    Priority 2: User watchlist or database watchlist members (only if option chain is unavailable).
    """
    root = extract_root_symbol(future_sym).upper()
    is_bull = str(opt_bias).upper() in {"BUY", "LONG", "ACCUMULATE", "BULLISH"}
    bias_tag = "CE" if is_bull else "PE"
    content = content.replace(admin_head, admin_head + '\n' + orphaned_code)

    # Step 1: Query live option chain engine FIRST for best ATM/near-OTM option
    try:
        chain = generate_option_chain_engine(root)
        spot = float(chain.get("spot") or 0.0)
        step = float(chain.get("step") or 50.0)
        strikes = chain.get("strikes") or []
        if spot > 0 and strikes:
            atm_strike = round(spot / step) * step
            # Target near-ATM strike: exactly ATM or 1 strike near-OTM for maximum institutional leverage
            target_strike = atm_strike + (step if is_bull else -step)
            best_row = min(strikes, key=lambda r: abs(float(r.get("strike") or 0) - target_strike))
            if best_row:
                opt_node = best_row.get("call" if is_bull else "put") or {}
                exp = str(chain.get("expiry") or "").replace(" 2026", "").strip()
                stk_int = int(best_row["strike"])
                
                real_sym = opt_node.get("trading_symbol")
                opt_key = opt_node.get("instrument_key")
                opt_sym = real_sym or (f"{root} {exp} {stk_int} {bias_tag}".strip() if exp else f"{root} {stk_int} {bias_tag}".strip())
                
                live_ltp = float(opt_node.get("ltp") or 0.0)
                if live_ltp <= 0 or opt_key:
                    try:
                        q = UPSTOX.quote(opt_key or opt_sym)
                        if q and q.get("ltp"):
                            live_ltp = float(q["ltp"])
                    except Exception:
                        pass
                
                if live_ltp <= 0:
                    live_ltp = bs_price(spot, float(best_row["strike"]), opt_type=bias_tag)
    # Now replace the Release 56 block with the enhanced implementation
    release56_head = '# Release 56: Persistent Saved Views, Funds Passbook & Notification Endpoints'
    r56_idx = content.find(release56_head)
    if r56_idx == -1:
        print("Error: could not find release56_head")
        return

                return {
                    "symbol": opt_sym,
                    "display_name": opt_sym,
                    "display": opt_sym,
                    "instrument_key": opt_key or opt_sym,
                    "entry": round(float(live_ltp or 120.0), 2),
                    "strike": float(best_row["strike"]),
                    "option_type": bias_tag,
                    "side": bias_tag,
                    "expiry": exp,
                    "lot_size": 100 if "CRUDE" in root else (30 if "BANK" in root else (65 if "NIFTY" in root else 1))
                }
    except Exception as e:
        log.warning("Option chain strike selection fallback: %s", safe_text(e))
    # Everything from release56_head to end of file will be replaced by the complete, cleanly structured module
    new_release56_block = '''# Release 56 & 57: Persistent Saved Views, Funds Passbook, Real Trades & Notification Management
# ===========================================================================

    # Step 2: Fallback to database or watchlist ONLY if option chain engine had no strikes
    try:
        rows = db_exec(
            "SELECT symbol, instrument_key, display_name, ltp FROM watchlist_members "
            "WHERE (UPPER(symbol) LIKE ? OR UPPER(display_name) LIKE ?) AND (UPPER(symbol) LIKE ? OR UPPER(display_name) LIKE ?) "
            "ORDER BY id DESC",
            [f"%{root}%", f"%{root}%", f"%{bias_tag}%", f"%{bias_tag}%"],
            "all"
        )
        for r in rows:
            sym = str(r.get("symbol") or "").upper()
            disp = str(r.get("display_name") or sym).upper()
            if bias_tag in sym or bias_tag in disp:
                item = dict(r)
@app.get("/api/chart/views")
async def get_chart_views(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    rows = db_exec("SELECT id, name, view_data, created_at FROM saved_chart_views WHERE user_id=? ORDER BY id DESC", [uid], "all")
    views = []
    for r in rows:
        try:
            vd = json.loads(r["view_data"])
            views.append({"id": r["id"], "name": r["name"], **vd, "created_at": r["created_at"]})
        except Exception:
            views.append({"id": r["id"], "name": r["name"], "created_at": r["created_at"]})
    return {"ok": True, "views": views}

@app.post("/api/chart/views")
async def save_chart_view(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    body = await request.json()
    name = str(body.get("name") or "Custom View").strip()
    view_data = json.dumps(body)
    now_str = now_iso()
    db_exec("INSERT INTO saved_chart_views (user_id, name, view_data, created_at) VALUES (?, ?, ?, ?)", [uid, name, view_data, now_str])
    new_id = db_exec("SELECT last_insert_rowid() as id", [], "one")
    return {"ok": True, "id": new_id["id"] if new_id else 1, "name": name}

@app.delete("/api/chart/views/{view_id}")
async def delete_chart_view(view_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    db_exec("DELETE FROM saved_chart_views WHERE id=? AND user_id=?", [view_id, uid])
    return {"ok": True}

@app.post("/api/funds/passbook/upload")
async def upload_passbook(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    content_type = request.headers.get("content-type", "")
    csv_text = ""
    starting_balance = 100000.0
    trades = []
    
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        starting_balance = float(form.get("starting_balance") or 100000.0)
        upload_file = form.get("file")
        if upload_file is not None and hasattr(upload_file, "filename"):
            filename = str(upload_file.filename or "").lower()
            file_bytes = await upload_file.read()
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                try:
                    q = UPSTOX.quote(item.get("symbol") or item.get("instrument_key"))
                    if q and q.get("ltp"):
                        item["entry"] = float(q["ltp"])
                    import pandas as pd
                    import io
                    df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None)
                    header_idx = None
                    for i in range(min(25, len(df_raw))):
                        row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].dropna().tolist()]
                        if any("symbol" in x for x in row_vals) and any("trade" in x or "type" in x or "price" in x for x in row_vals):
                            header_idx = i
                            break
                    if header_idx is not None:
                        cols = [str(x).strip().lower().replace(" ", "_") for x in df_raw.iloc[header_idx]]
                        df = df_raw.iloc[header_idx+1:].copy()
                        df.columns = cols
                        for _, row in df.iterrows():
                            sym = str(row.get("symbol") or "").strip().upper()
                            if not sym or sym == "NAN":
                                continue
                            ttype = str(row.get("trade_type") or "BUY").strip().upper()
                            try:
                                qty = float(row.get("quantity") or 0)
                                price = float(row.get("price") or 0)
                            except Exception:
                                continue
                            if qty <= 0 or price <= 0:
                                continue
                            t_val = qty * price
                            t_time = str(row.get("order_execution_time") or row.get("trade_date") or now_iso())
                            trades.append({
                                "symbol": sym,
                                "trade_type": ttype,
                                "quantity": qty,
                                "price": price,
                                "amount": t_val,
                                "time": t_time
                            })
                except Exception as exc:
                    record_error("passbook_excel_parse", safe_text(exc), user_id=uid)
            else:
                csv_text = file_bytes.decode("utf-8", errors="ignore")
    else:
        try:
            body = await request.json()
            csv_text = body.get("csv_text") or ""
            starting_balance = float(body.get("starting_balance") or 100000.0)
        except Exception:
            pass

    if csv_text and not trades:
        lines = [line.strip() for line in csv_text.strip().split("\n") if line.strip()]
        if lines:
            header_idx = 0
            for i, l in enumerate(lines[:20]):
                if "symbol" in l.lower():
                    header_idx = i
                    break
            header = [h.strip().lower().replace(" ", "_") for h in lines[header_idx].split(",")]
            for row_str in lines[header_idx+1:]:
                parts = [p.strip().strip('"') for p in row_str.split(",")]
                if len(parts) < 4:
                    continue
                row = dict(zip(header, parts))
                sym = str(row.get("symbol") or "").strip().upper()
                if not sym:
                    continue
                ttype = str(row.get("trade_type") or "BUY").strip().upper()
                try:
                    qty = float(row.get("quantity") or 0)
                    price = float(row.get("price") or 0)
                except Exception:
                    pass
                return item
    except Exception:
        pass
                    continue
                if qty <= 0 or price <= 0:
                    continue
                t_val = qty * price
                t_time = str(row.get("order_execution_time") or row.get("trade_date") or now_iso())
                trades.append({
                    "symbol": sym,
                    "trade_type": ttype,
                    "quantity": qty,
                    "price": price,
                    "amount": t_val,
                    "time": t_time
                })

    return None
'''
    net_realized_cashflow = 0.0
    total_buy_val = 0.0
    total_sell_val = 0.0
    for t in trades:
        if t["trade_type"] == "BUY":
            net_realized_cashflow -= t["amount"]
            total_buy_val += t["amount"]
        elif t["trade_type"] == "SELL":
            net_realized_cashflow += t["amount"]
            total_sell_val += t["amount"]

if resolve_pattern.search(content):
    content = resolve_pattern.sub(new_resolve, content)
    print("Updated resolve_option_for_future")
else:
    print("WARNING: resolve_option_for_future regex not matched")
    current_balance = starting_balance + net_realized_cashflow
    db_exec("""
        INSERT OR REPLACE INTO user_passbooks (user_id, starting_balance, current_balance, total_buy, total_sell, trade_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [uid, starting_balance, current_balance, total_buy_val, total_sell_val, len(trades), now_iso()])

# 4. In generate_option_chain_engine, fix spot query so it NEVER selects an option contract
old_spot_query = '''        try:
            row = db_exec(
                "SELECT ltp FROM watchlist_members WHERE (UPPER(symbol) LIKE ? OR UPPER(display_name) LIKE ?) AND ltp > 0 ORDER BY id DESC",
                [f"%{root}%", f"%{root}%"],
                "one"
            )
            if row and row.get("ltp"):
                spot = float(row["ltp"])
        except Exception:
            pass'''
    return {
        "ok": True,
        "starting_balance": starting_balance,
        "current_balance": round(current_balance, 2),
        "net_pnl": round(net_realized_cashflow, 2),
        "total_trades": len(trades),
        "trades_imported": len(trades),
        "trades": trades[:50]
    }

new_spot_query = '''        index_map = {
            "BANKNIFTY": "NSE_INDEX|Nifty Bank",
            "NIFTY": "NSE_INDEX|Nifty 50",
            "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
            "MIDCPNIFTY": "NSE_INDEX|NIFTY MID SELECT"
        }
@app.get("/api/funds/passbook")
async def get_passbook(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    p = db_exec("SELECT * FROM user_passbooks WHERE user_id=?", [uid], "one")
    if not p:
        return {"ok": True, "starting_balance": 100000.0, "current_balance": 100000.0, "net_pnl": 0.0, "total_trades": 0, "trades": []}
    return {
        "ok": True,
        "starting_balance": float(p.get("starting_balance") or 100000.0),
        "current_balance": float(p.get("current_balance") or 100000.0),
        "net_pnl": float((p.get("current_balance") or 100000.0) - (p.get("starting_balance") or 100000.0)),
        "total_trades": int(p.get("trade_count") or 0)
    }

@app.get("/api/portfolio/external-positions")
async def list_external_positions(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    rows = db_exec("SELECT * FROM positions WHERE user_id=? AND id LIKE 'pos_ext_%' AND COALESCE(status, 'OPEN')='OPEN' ORDER BY id DESC", [uid], "all")
    res = []
    for r in rows:
        sym = r.get("symbol", "")
        entry = float(r.get("avg_price") or 0)
        qty = int(r.get("quantity") or 1)
        side = str(r.get("side") or "BUY").upper()
        sl = float(r.get("stop_loss") or 0)
        tgt = float(r.get("target") or 0)
        
        ltp = entry
        try:
            # STRICTLY match UNDERLYING only, NEVER option contracts (which have CE/PE and low option prices like 93 or 532)!
            row = db_exec(
                "SELECT ltp FROM watchlist_members WHERE (UPPER(symbol) = ? OR UPPER(display_name) = ? OR UPPER(instrument_key) = ?) "
                "AND UPPER(symbol) NOT LIKE '%CE%' AND UPPER(symbol) NOT LIKE '%PE%' AND ltp > 1000 ORDER BY id DESC",
                [root, root, index_map.get(root, root)],
                "one"
            )
            if row and row.get("ltp"):
                spot = float(row["ltp"])
            q = UPSTOX.quote(sym)
            if q and q.get("ltp"):
                ltp = float(q["ltp"])
        except Exception:
            pass'''
            pass
            
        pnl = (ltp - entry) * qty if side == "BUY" else (entry - ltp) * qty
        pnl_pct = (pnl / (entry * qty)) * 100 if (entry * qty) > 0 else 0
        
        advice = "HOLD"
        advice_reason = "Position advancing within structural invalidation boundaries."
        if side == "BUY":
            if sl > 0 and ltp <= sl:
                advice = "EXIT / STOPPED OUT"
                advice_reason = f"LTP (₹{ltp:,.2f}) hit stop level (₹{sl:,.2f}). Invalidate trade to protect capital."
            elif tgt > 0 and ltp >= tgt:
                advice = "BOOK PROFIT"
                advice_reason = f"LTP (₹{ltp:,.2f}) attained profit target (₹{tgt:,.2f}). Harvest asymmetric gains."
            elif pnl_pct >= 20.0:
                advice = "TRAIL STOP"
                advice_reason = f"+{pnl_pct:.1f}% gain. Trail stop loss to breakeven (₹{entry:,.2f}) to lock in gains."
        else:
            if sl > 0 and ltp >= sl:
                advice = "EXIT / STOPPED OUT"
                advice_reason = f"LTP (₹{ltp:,.2f}) exceeded stop level (₹{sl:,.2f}). Protect capital."
            elif tgt > 0 and ltp <= tgt:
                advice = "BOOK PROFIT"
                advice_reason = f"LTP (₹{ltp:,.2f}) hit downside target (₹{tgt:,.2f}). Harvest short gains."
                
        res.append({
            **dict(r),
            "ltp": ltp,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "ca_ai_advice": advice,
            "advice_reason": advice_reason
        })
    return {"ok": True, "positions": res}

if old_spot_query in content:
    content = content.replace(old_spot_query, new_spot_query)
    print("Updated spot query in generate_option_chain_engine")
else:
    print("WARNING: old_spot_query not found in generate_option_chain_engine")

# 5. Add external position endpoint
if '/api/portfolio/external-position' not in content:
    ext_endpoint = '''
@app.post("/api/portfolio/external-position")
@app.post("/api/positions/external")
@app.post("/api/portfolio/external-positions")
async def add_external_position(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    body = await request.json()
    symbol = str(body.get("symbol") or "").strip().upper()
    if not symbol:
        raise HTTPException(422, "Symbol is required")
    sym = str(body.get("symbol") or "").strip().upper()
    side = str(body.get("side") or "BUY").strip().upper()
    qty = int(body.get("quantity") or body.get("qty") or 1)
    entry = float(body.get("price") or body.get("entry") or body.get("avg_price") or 0.0)
    sl = float(body.get("stop_loss") or body.get("sl") or 0.0)
    tgt = float(body.get("target") or body.get("tgt") or 0.0)
    broker = str(body.get("terminal") or body.get("broker") or "Zerodha").strip()
    qty = int(body.get("quantity") or 1)
    entry = float(body.get("avg_price") or 0.0)
    sl = float(body.get("stop_loss") or 0.0)
    tgt = float(body.get("target") or 0.0)
    if not sym or entry <= 0:
        raise HTTPException(status_code=400, detail="Invalid symbol or entry price")
    
    # Try fetching live LTP
    ltp = entry
    try:
        q = UPSTOX.quote(symbol)
        if q and q.get("ltp"):
            ltp = float(q["ltp"])
    except Exception:
        pass

    pos_id = f"pos_ext_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    now_str = now_iso()
    pos_id = f"pos_ext_{secrets.token_hex(5)}"
    db_exec(
        "INSERT INTO positions (id, user_id, symbol, instrument_key, side, quantity, avg_price, stop_loss, target, status, source, fund_bucket, opened_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, 'trading', ?, ?)",
        [pos_id, user["id"], symbol, symbol, side, qty, entry, sl, tgt, broker.upper(), now_str, now_str]
        """INSERT INTO positions (id, user_id, symbol, instrument_key, side, quantity, avg_price, stop_loss, target, realized_pnl, unrealized_pnl, opened_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?)""",
        [pos_id, uid, sym, sym, side, qty, entry, sl, tgt, now_str, now_str]
    )
    new_pos = db_exec("SELECT * FROM positions WHERE id=?", [pos_id], "one")
    await add_notification(user["id"], "position_opened", "info", 80, f"External Position ({broker}) Added", f"{side} {qty}x {symbol} @ ₹{entry:,.2f}", f"pos:{pos_id}")
    return {"ok": True, "position": new_pos}
'''
    # Insert before @app.post("/api/positions/{position_id}/square-off")
    sq_anchor = '@app.post("/api/positions/{position_id}/square-off")'
    if sq_anchor in content:
        content = content.replace(sq_anchor, ext_endpoint + "\n" + sq_anchor)
        print("Added external position endpoint")
    return {"ok": True, "position_id": pos_id}

# 6. In _format_opt_candidate, ensure wider SL and no duplicate entry overwrite
old_fmt_cand = '''            "entry": round(opt_entry, 2),
            "stop_loss": round(opt_entry * sl_mult, 2),
            "target": round(opt_entry * tgt_mult, 2),
            "entry": opt_entry_final,
            "cmp": round(opt_entry, 2),
            "stop_loss": opt_sl,
            "target": opt_target,'''
@app.delete("/api/portfolio/trades/{trade_id}")
async def delete_trade(trade_id: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    db_exec("DELETE FROM positions WHERE id=? AND user_id=?", [trade_id, uid])
    db_exec("DELETE FROM orders WHERE id=? AND user_id=?", [trade_id, uid])
    db_exec("DELETE FROM backtest_trades WHERE id=? AND user_id=?", [trade_id, uid])
    return {"ok": True, "trade_id": trade_id}

new_fmt_cand = '''            "entry": opt_entry_final,
            "cmp": round(opt_entry, 2),
            "stop_loss": opt_sl,
            "target": opt_target,'''
@app.delete("/api/portfolio/trades")
async def clear_all_trades(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    db_exec("DELETE FROM positions WHERE user_id=? AND status='CLOSED'", [uid])
    db_exec("DELETE FROM orders WHERE user_id=?", [uid])
    db_exec("DELETE FROM backtest_trades WHERE user_id=?", [uid])
    return {"ok": True}

if old_fmt_cand in content:
    content = content.replace(old_fmt_cand, new_fmt_cand)
    print("Fixed duplicate entry keys in _format_opt_candidate")
@app.delete("/api/notifications/{notif_id}")
async def delete_notification(notif_id: int, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    db_exec("DELETE FROM notifications WHERE id=? AND user_id=?", [notif_id, uid])
    return {"ok": True}

with open(app_path, "w", encoding="utf-8") as f:
    f.write(content)
@app.post("/api/notifications/delete-batch")
async def delete_notifications_batch(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    body = await request.json()
    ids = body.get("ids") or []
    if ids:
        placeholders = ",".join("?" * len(ids))
        db_exec(f"DELETE FROM notifications WHERE user_id=? AND id IN ({placeholders})", [uid, *ids])
    return {"ok": True}

print("Saved app.py. Validating syntax...")
py_compile.compile(app_path, doraise=True)
print("app.py syntax is 100% VALID!")
@app.delete("/api/notifications")
async def delete_all_notifications(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    db_exec("DELETE FROM notifications WHERE user_id=?", [uid])
    return {"ok": True}

@app.post("/api/notifications/mark-read")
async def mark_notifications_read(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    body = await request.json()
    ids = body.get("ids") or []
    if ids:
        placeholders = ",".join("?" * len(ids))
        db_exec(f"UPDATE notifications SET is_read=1 WHERE user_id=? AND id IN ({placeholders})", [uid, *ids])
    return {"ok": True}

@app.post("/api/notifications/mark-all-read")
async def mark_all_notifications_read(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    db_exec("UPDATE notifications SET is_read=1 WHERE user_id=?", [uid])
    return {"ok": True}

@app.post("/api/notifications/settings")
async def set_notification_settings(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    uid = user["id"]
    body = await request.json()
    prune_days = int(body.get("auto_prune_days") or 15)
    muted = json.dumps(body.get("muted_categories") or [])
    now_str = now_iso()
    db_exec("""
        INSERT OR REPLACE INTO user_notification_settings (user_id, auto_prune_days, muted_categories, updated_at)
        VALUES (?, ?, ?, ?)
    """, [uid, prune_days, muted, now_str])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=prune_days)).isoformat()
    db_exec("DELETE FROM notifications WHERE user_id=? AND created_at < ?", [uid, cutoff])
    return {"ok": True, "auto_prune_days": prune_days}
'''

    content = content[:r56_idx] + new_release56_block

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully updated app.py!")

if __name__ == '__main__':
    update_app()
