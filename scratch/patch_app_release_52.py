import sys, re, shutil
sys.stdout.reconfigure(encoding='utf-8')

# Backup app.py
shutil.copyfile('app.py', 'app.py.bak')
print('Backup created: app.py.bak')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add peak_pnl column migration to positions
target_migration = 'ALTER TABLE positions ADD COLUMN entry_reco_json TEXT")'
replacement_migration = """ALTER TABLE positions ADD COLUMN entry_reco_json TEXT")
            with contextlib.suppress(Exception):
                conn.execute("ALTER TABLE positions ADD COLUMN peak_pnl REAL DEFAULT 0")"""

if target_migration in text:
    text = text.replace(target_migration, replacement_migration, 1)
    print('[OK] Injected peak_pnl column migration into positions')
else:
    print('[FAIL] target_migration not found')
    sys.exit(1)

# 2. Update unrealized_pnl calculation to record high-water mark peak_pnl
target_pnl_update = """            pnl=(ltp-avg)*qty if side=="BUY" else (avg-ltp)*qty
            total_unreal+=pnl
            db_exec("UPDATE positions SET unrealized_pnl=?,updated_at=? WHERE id=? AND user_id=?",[pnl,now_iso(),p["id"],user_id])"""

replacement_pnl_update = """            pnl=(ltp-avg)*qty if side=="BUY" else (avg-ltp)*qty
            total_unreal+=pnl
            prev_pk = float(p.get("peak_pnl") or 0.0)
            new_pk = max(prev_pk, pnl)
            db_exec("UPDATE positions SET unrealized_pnl=?, peak_pnl=?, updated_at=? WHERE id=? AND user_id=?", [pnl, new_pk, now_iso(), p["id"], user_id])"""

if target_pnl_update in text:
    text = text.replace(target_pnl_update, replacement_pnl_update, 1)
    print('[OK] Updated positions table peak_pnl tracking')
else:
    print('[FAIL] target_pnl_update not found')
    sys.exit(1)

# 3. Calibrate CRUDEOIL in generate_option_chain_engine (realistic spot ~6150, step 50, realistic OI)
target_crude_cfg = '"CRUDEOIL": {"spot": 9532.0, "step": 50.0, "lot": 100, "iv": 32.0, "default_exp": "17 SEP 2026"},'
replacement_crude_cfg = '"CRUDEOIL": {"spot": 6150.0, "step": 50.0, "lot": 100, "iv": 34.0, "default_exp": "17 SEP 2026"},'

if target_crude_cfg in text:
    text = text.replace(target_crude_cfg, replacement_crude_cfg, 1)
    print('[OK] Calibrated CRUDEOIL spot configuration')
else:
    print('[FAIL] target_crude_cfg not found')
    sys.exit(1)

# 4. Calibrate OI in generate_option_chain_engine for commodities vs equities
target_oi_calc = """        dist = abs(stk - spot)
        oi_base = max(1200, int(45000 - dist * 15))
        vol_base = max(450, int(22000 - dist * 8))"""

replacement_oi_calc = """        dist = abs(stk - spot)
        if is_mcx:
            # Calibrate realistic MCX Commodity contracts (Crude Oil, Natural Gas, Gold, Silver)
            oi_base = max(450, int(12500 - dist * 4))
            vol_base = max(200, int(8500 - dist * 3))
        else:
            oi_base = max(1200, int(45000 - dist * 15))
            vol_base = max(450, int(22000 - dist * 8))"""

if target_oi_calc in text:
    text = text.replace(target_oi_calc, replacement_oi_calc, 1)
    print('[OK] Calibrated commodity OI and volume in option chain engine')
else:
    print('[FAIL] target_oi_calc not found')
    sys.exit(1)

# 5. Fix news_ca_ai_feed 2:00 PM cutoff to 48 hours
target_news_cutoff = """        ist_dt = p_dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        # Strictly purge older news prior to last market day 2:00 PM IST
        if ist_dt < cutoff_dt:
            continue"""

replacement_news_cutoff = """        ist_dt = p_dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        # Keep fresh actionable market news from the last 48 hours
        if (now_ist - ist_dt).total_seconds() > 48 * 3600:
            continue"""

if target_news_cutoff in text:
    text = text.replace(target_news_cutoff, replacement_news_cutoff, 1)
    print('[OK] Relaxed news cutoff to 48 hours for rich institutional news feed')
else:
    print('[FAIL] target_news_cutoff not found')
    sys.exit(1)

# 6. Strict Directional Consensus in resolve_option_for_future
target_resolve_opt = """def resolve_option_for_future(future_sym: str, opt_bias: str = "BUY", user_id: int | None = None) -> dict[str, Any] | None:
    \"\"\"Find a corresponding option contract for a futures symbol using root initials (e.g. CRUDEOIL).
    Matches root initials regardless of differences in expiration dates between future and option.
    \"\"\"
    root = extract_root_symbol(future_sym)
    # 1. First check user's watchlist with full symbol and root initials
    if user_id:
        wl = user_watchlist_option_contracts(user_id, future_sym, opt_bias)
        if not wl:
            wl = user_watchlist_option_contracts(user_id, root, opt_bias)
        if wl:
            return wl[0]

    # 2. Check all watchlist_members across database by matching root and bias (CE / PE)
    bias_tag = "CE" if str(opt_bias).upper() in {"BUY", "LONG", "ACCUMULATE"} else "PE"
    try:
        rows = db_exec(
            "SELECT symbol, instrument_key, display_name FROM watchlist_members "
            "WHERE (UPPER(symbol) LIKE ? OR UPPER(display_name) LIKE ?) "
            "ORDER BY id DESC",
            [f"%{root}%{bias_tag}%", f"%{root}%{bias_tag}%"],
            "all"
        )
        for r in rows:
            sym = str(r.get("symbol") or "").upper()
            disp = str(r.get("display_name") or sym).upper()
            if bias_tag in sym or bias_tag in disp:
                return r

        # Fallback to any option with root initials
        fallback_rows = db_exec(
            "SELECT symbol, instrument_key, display_name FROM watchlist_members "
            "WHERE (UPPER(symbol) LIKE ? OR UPPER(display_name) LIKE ?) "
            "ORDER BY id DESC",
            [f"%{root}%", f"%{root}%"],
            "all"
        )
        for r in fallback_rows:
            sym = str(r.get("symbol") or "").upper()
            disp = str(r.get("display_name") or sym).upper()
            if "CE" in sym or "PE" in sym or "CE" in disp or "PE" in disp:
                return r
    except Exception:
        pass
    return None"""

replacement_resolve_opt = """def resolve_option_for_future(future_sym: str, opt_bias: str = "BUY", user_id: int | None = None) -> dict[str, Any] | None:
    \"\"\"Find the optimal option contract for a futures symbol with STRICT directional consensus.
    If Bullish (BUY), strictly selects Call (CE). If Bearish (SELL), strictly selects Put (PE).
    Selects the best near-ATM strike with high liquidity from the real option chain.
    \"\"\"
    root = extract_root_symbol(future_sym).upper()
    is_bull = str(opt_bias).upper() in {"BUY", "LONG", "ACCUMULATE", "BULLISH"}
    bias_tag = "CE" if is_bull else "PE"

    # Step 1: Select optimal contract from the live option chain engine
    try:
        chain = generate_option_chain_engine(root)
        spot = float(chain.get("spot") or 6000.0)
        step = float(chain.get("step") or 50.0)
        strikes = chain.get("strikes") or []
        if strikes:
            # Target near-ATM strike: exactly ATM or 1 strike near-OTM for max leverage
            atm_strike = round(spot / step) * step
            target_strike = atm_strike + (step if is_bull else -step)
            # Find matching strike row
            best_row = None
            min_dist = 999999
            for r in strikes:
                stk = float(r.get("strike") or 0)
                dist = abs(stk - target_strike)
                if dist < min_dist:
                    min_dist = dist
                    best_row = r
            if best_row:
                opt_node = best_row.get("call" if is_bull else "put") or {}
                exp = str(chain.get("expiry") or "17 SEP 2026").replace(" 2026", "").strip()
                opt_sym = f"{root} FUT {exp} {int(best_row['strike'])}{bias_tag}"
                return {
                    "symbol": opt_sym,
                    "display_name": opt_sym,
                    "instrument_key": opt_node.get("instrument_key") or opt_sym,
                    "entry": float(opt_node.get("ltp") or 120.0),
                    "strike": float(best_row["strike"]),
                    "option_type": bias_tag,
                    "expiry": exp,
                    "lot_size": 100 if "CRUDE" in root else 1
                }
    except Exception as e:
        log.warning("Option chain strike selection fallback: %s", safe_text(e))

    # Step 2: Check user's watchlist with strict bias matching (NEVER return opposite option!)
    if user_id:
        wl = user_watchlist_option_contracts(user_id, future_sym, opt_bias)
        if not wl:
            wl = user_watchlist_option_contracts(user_id, root, opt_bias)
        if wl:
            for item in wl:
                s_u = str(item.get("symbol") or item.get("display_name") or "").upper()
                if bias_tag in s_u:
                    return item

    # Step 3: Check database watchlist_members strictly matching root AND bias_tag
    try:
        rows = db_exec(
            "SELECT symbol, instrument_key, display_name FROM watchlist_members "
            "WHERE (UPPER(symbol) LIKE ? OR UPPER(display_name) LIKE ?) "
            "ORDER BY id DESC",
            [f"%{root}%{bias_tag}%", f"%{root}%{bias_tag}%"],
            "all"
        )
        for r in rows:
            sym = str(r.get("symbol") or "").upper()
            disp = str(r.get("display_name") or sym).upper()
            if bias_tag in sym or bias_tag in disp:
                return r
    except Exception:
        pass
    return None"""

if target_resolve_opt in text:
    text = text.replace(target_resolve_opt, replacement_resolve_opt, 1)
    print('[OK] Updated resolve_option_for_future with strict directional consensus and option chain engine strike selection')
else:
    print('[FAIL] target_resolve_opt not found')
    sys.exit(1)

# Write updated app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('app.py patch applied successfully')

