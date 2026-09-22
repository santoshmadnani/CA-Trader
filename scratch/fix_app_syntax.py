from pathlib import Path
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()
import io
import re
import sys
import py_compile, re, os, sys

def fix_syntax():
    path = Path('app.py')
    code = path.read_text(encoding='utf-8')
# Fix 1: evidence["options"] and res_opt in app.py
bad_block = """            "entry": opt_entry,
            "entry": entry_to_use,
            "cmp": opt_entry,
            "lot_size": lot,
            "from_watchlist": True,
            "score": 92.0,
            "greeks": greeks
            "greeks": greeks,
            "perfect_entry_details": opt_perf,
            "is_expiry_scalp": expiry_scalp
        }
        res_opt = {
            "qualifies": True,
            "recommendation": opt_action,
            "timeframe": timeframe,
            "confidence": round(min(99, max(50, confidence)), 1),
            "entry": opt_entry,
            "entry": entry_to_use,
            "cmp": opt_entry,
            "stop_loss": opt_sl,
            "target": opt_tgt,
            "expected_risk": risk_amt,
            "expected_reward": reward_amt,
            "risk_reward": rr_ratio,
            "instrument": inst_obj,
            "evidence": evidence,
            "rationale": f"Option Setup: {symbol} · Entry Rs.{opt_entry:.2f}, Target Rs.{opt_tgt:.2f} (Profit: ≥₹500/lot), SL Rs.{opt_sl:.2f} (R:R 1:{rr_ratio:.2f}).",
            "provider": "upstox+ca_trader_options",
            "perfect_entry_details": opt_perf,
            "is_expiry_scalp": expiry_scalp,
            "greeks": greeks,
            "rationale": f"{'Next Market Day Setup (' + next_session_str + '): ' if not is_mkt_open else ''}Option Setup: {symbol} · Entry Rs.{opt_entry:.2f}, Target Rs.{opt_tgt:.2f} (Est. Profit ₹{ach['realistic_profit']:,.0f}/lot), SL Rs.{opt_sl:.2f} (R:R 1:{rr_ratio:.2f}). Greeks: Δ {abs(greeks['delta']):.2f}, Γ {greeks['gamma']:.4f}, Θ {greeks['theta']:.1f}/d · Achievable in {ach['time_horizon']}m.",
            "rationale": f"{'Next Market Day Setup (' + next_session_str + '): ' if not is_mkt_open else ''}Option Setup: {symbol} · Entry ₹{entry_to_use:.2f} (LTP ₹{opt_entry:.2f}, {opt_perf.get('entry_label', '')}), Target ₹{opt_tgt:.2f} (Est. Profit ₹{ach['realistic_profit']:,.0f}/lot), SL ₹{opt_sl:.2f} (R:R 1:{rr_ratio:.2f}). Greeks: Δ {abs(greeks['delta']):.2f}, Γ {greeks['gamma']:.4f}, Θ {greeks['theta']:.1f}/d · Achievable in {ach['time_horizon']}m.",
            "provider": "upstox+greeks_engine",
            "timestamp": now_iso(),
            **next_day_info
        }
        CACHE.set(cache_key, res_opt, 20)
        CACHE.set(cache_key, res_opt, 15)"""
def main():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
path = 'app.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

    # 1. Restore news_job
    bad_news_job = '''    def news_job():
        try: # Save actionable recommendation if not duplicated recently'''
    
    # Find start of bad block
    idx = code.find(bad_news_job)
    if idx != -1:
        end_str = 'return recommendation_news_evidence(selected)\n        except Exception: return {"stock":{"events":[]},"global":{"events":[]}}'
        end_idx = code.find(end_str, idx)
        if end_idx != -1:
            full_end = end_idx + len(end_str)
            good_news_job = '''    def news_job():
        try: return recommendation_news_evidence(selected)
        except Exception: return {"stock":{"events":[]},"global":{"events":[]}}'''
            code = code[:idx] + good_news_job + code[full_end:]
            print("Restored news_job cleanly")
good_block = """            "entry": entry_to_use,
            "cmp": opt_entry,
            "lot_size": lot,
            "from_watchlist": True,
            "score": 92.0,
            "greeks": greeks,
            "perfect_entry_details": opt_perf,
            "is_expiry_scalp": expiry_scalp
        }
        res_opt = {
            "qualifies": True,
            "recommendation": opt_action,
            "timeframe": timeframe,
            "confidence": round(min(99, max(50, confidence)), 1),
            "entry": entry_to_use,
            "cmp": opt_entry,
            "stop_loss": opt_sl,
            "target": opt_tgt,
            "expected_risk": risk_amt,
            "expected_reward": reward_amt,
            "risk_reward": rr_ratio,
            "instrument": inst_obj,
            "evidence": evidence,
            "perfect_entry_details": opt_perf,
            "is_expiry_scalp": expiry_scalp,
            "greeks": greeks,
            "rationale": f"{'Next Market Day Setup (' + next_session_str + '): ' if not is_mkt_open else ''}Option Setup: {symbol} · Entry ₹{entry_to_use:.2f} (LTP ₹{opt_entry:.2f}, {opt_perf.get('entry_label', '')}), Target ₹{opt_tgt:.2f} (Est. Profit ₹{ach['realistic_profit']:,.0f}/lot), SL ₹{opt_sl:.2f} (R:R 1:{rr_ratio:.2f}). Greeks: Δ {abs(greeks['delta']):.2f}, Γ {greeks['gamma']:.4f}, Θ {greeks['theta']:.1f}/d · Achievable in {ach['time_horizon']}m.",
            "provider": "upstox+greeks_engine",
            "timestamp": now_iso(),
            **next_day_info
        }
        CACHE.set(cache_key, res_opt, 15)"""
    # 1. Fix line with '... [truncated for diff preview]'
    lines = content.splitlines()
    fixed_lines = []
    skip = False
    for i, line in enumerate(lines):
        if '... [truncated for diff preview]' in line:
            print(f"Found truncated line at {i+1}")
            continue
        fixed_lines.append(line)
# Normalize CRLF to LF temporarily for reliable matching
crlf = '\r\n' in text
text = text.replace('\r\n', '\n')

    # 2. Put the saving logic in analysis_overall
    ao_sig = 'async def analysis_overall(instrument: str, timeframe: str = "5m", desired_profit: float | None = None, bearable_loss: float | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:'
    ao_pos = code.find(ao_sig)
    if ao_pos != -1:
        target = 'result = {"instrument": instrument, "timeframe": timeframe, **rec, "ai": {"available": False, "requested": False, "decision": "NOT REQUESTED", "reason": "CA AI opinion is manual. Click Ask CA AI to request it."}, "timestamp": now_iso()}'
        target_pos = code.find(target, ao_pos)
        if target_pos != -1:
            saving_code = '''    # Save actionable recommendation into recommendations table
    reco_action = str(rec.get("recommendation") or "").upper()
    if reco_action in ("BUY", "SELL"):
        try:
            trade_sym = str(rec.get("display_symbol") or rec.get("symbol") or instrument).upper()
            und = str(rec.get("underlying") or instrument).upper()
            existing_reco = db_exec(
                "SELECT id FROM recommendations WHERE user_id=? AND (symbol=? OR underlying=?) AND recommendation=? AND created_at > datetime('now', '-5 minutes')",
                [uid, trade_sym, und, reco_action],
                "one"
            )
            if not existing_reco:
                rid = secrets.token_hex(12)
                opt_cand = rec.get("option_candidate") or rec.get("option_contract") or {}
                db_exec(
                    "INSERT INTO recommendations(id, user_id, source, symbol, underlying, recommendation, timeframe, entry, target, stop_loss, rationale, technical_basis, news_basis, option_basis, score, instrument_kind, instrument_key, option_side, option_strike, option_expiry, status, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [
                        rid,
                        uid,
                        "auto",
                        trade_sym,
                        und,
                        reco_action,
                        timeframe,
                        rec.get("entry"),
                        rec.get("target"),
                        rec.get("stop_loss"),
                        rec.get("rationale") or rec.get("reason"),
                        json.dumps(rec.get("evidence", {}), default=str),
                        json.dumps(rec.get("news", []), default=str),
                        json.dumps(opt_cand, default=str) if opt_cand else None,
                        rec.get("score") or 84.0,
                        rec.get("kind") or "OPTION",
                        rec.get("instrument_key"),
                        rec.get("option_type") or ("CE" if "CE" in trade_sym else "PE" if "PE" in trade_sym else None),
                        rec.get("strike"),
                        rec.get("expiry"),
                        "NEW",
                        now_iso()
                    ]
                )
                rec["id"] = rid
                rec["saved"] = True
        except Exception as exc:
            log.warning("Failed to auto-save recommendation: %s", exc)
if bad_block in content:
    content = content.replace(bad_block, good_block)
    print("Fixed bad_block in app.py")
else:
    print("bad_block not found directly, checking CRLF vs LF...")
    content_norm = content.replace("\r\n", "\n")
    bad_norm = bad_block.replace("\r\n", "\n")
    good_norm = good_block.replace("\r\n", "\n")
    if bad_norm in content_norm:
        content = content_norm.replace(bad_norm, good_norm)
        print("Fixed bad_block with normalized newlines")
    else:
        print("ERROR: bad_block could not be replaced")
    content = '\n'.join(fixed_lines)
# 1. Fix duplicate evaluate_achievable_option_move signature
text = text.replace(
    'def evaluate_achievable_option_move(symbol: str, opt_info: dict[str, Any], opt_entry: float, underlying_spot: float, underlying_atr: float, lot_size: int, desired_profit: float | None = 500.0, bearable_loss: float | None = None, segment: str | None = None, days_high: float | None = None, expiry_scalp: bool = False) -> dict[str, Any]:\ndef evaluate_achievable_option_move(symbol: str, opt_info: dict[str, Any], opt_entry: float, underlying_spot: float, underlying_atr: float, lot_size: int, desired_profit: float | None = 500.0, bearable_loss: float | None = None, segment: str | None = None, days_high: float | None = None, expiry_scalp: bool = False, timeframe: str = "5m") -> dict[str, Any]:',
    'def evaluate_achievable_option_move(symbol: str, opt_info: dict[str, Any], opt_entry: float, underlying_spot: float, underlying_atr: float, lot_size: int, desired_profit: float | None = 500.0, bearable_loss: float | None = None, segment: str | None = None, days_high: float | None = None, expiry_scalp: bool = False, timeframe: str = "5m") -> dict[str, Any]:'
)

    '''
            code = code[:target_pos] + saving_code + code[target_pos:]
            print("Successfully added saving code to analysis_overall")
# Fix 2: check line 5690 duplicate segment=seg
content = content.replace("            segment=seg\n            segment=seg,", "            segment=seg,")
content = content.replace("            segment=seg\r\n            segment=seg,", "            segment=seg,")
    # 2. Check if indentation around line 9282 is now correct
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Saved app.py without truncated preview line")
# 2. Fix duplicate evaluate_achievable_equity_move signature
text = text.replace(
    'def evaluate_achievable_equity_move(symbol: str, entry: float, atr: float, user_capital: float | None = None, desired_profit: float | None = 500.0, bearable_loss: float | None = None, side: str = "BUY", segment: str | None = None, expiry_scalp: bool = False) -> dict[str, Any]:\ndef evaluate_achievable_equity_move(symbol: str, entry: float, atr: float, user_capital: float | None = None, desired_profit: float | None = 500.0, bearable_loss: float | None = None, side: str = "BUY", segment: str | None = None, expiry_scalp: bool = False, timeframe: str = "5m") -> dict[str, Any]:',
    'def evaluate_achievable_equity_move(symbol: str, entry: float, atr: float, user_capital: float | None = None, desired_profit: float | None = 500.0, bearable_loss: float | None = None, side: str = "BUY", segment: str | None = None, expiry_scalp: bool = False, timeframe: str = "5m") -> dict[str, Any]:'
)

    path.write_text(code, encoding='utf-8')
    print("fix_syntax completed")
# Fix 3: check line 5832 duplicate segment=seg
content = content.replace("            side=side,\n            segment=seg\n            segment=seg,", "            side=side,\n            segment=seg,")
content = content.replace("            side=side,\r\n            segment=seg\r\n            segment=seg,", "            side=side,\r\n            segment=seg,")
# 3. Fix duplicate indented lines at 5729
text = text.replace(
    '    opp_bias = "SELL" if opt_bias == "BUY" else "BUY"\n    alt_cand = resolve_option_for_future(symbol, opp_bias, user_id)\n        opp_bias = "SELL" if opt_bias == "BUY" else "BUY"\n        alt_cand = resolve_option_for_future(symbol, opp_bias, user_id)',
    '    opp_bias = "SELL" if opt_bias == "BUY" else "BUY"\n    alt_cand = resolve_option_for_future(symbol, opp_bias, user_id)'
)

if __name__ == '__main__':
    fix_syntax()
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
# 4. Fix duplicate opt_tgt / opt_sl
text = text.replace(
    '        if opt_action == "BUY":\n            opt_tgt = round(opt_entry + profit_per_share, 2)\n            opt_sl = round(max(0.05, opt_entry - profit_per_share / 2.2), 2)\n        else:\n            opt_tgt = round(max(0.05, opt_entry - profit_per_share), 2)\n            opt_sl = round(opt_entry + profit_per_share / 2.2, 2)\n        opt_tgt = round(opt_entry + profit_per_share, 2)\n        opt_sl = round(max(0.05, opt_entry - profit_per_share / 2.2), 2)',
    '        if opt_action == "BUY":\n            opt_tgt = round(opt_entry + profit_per_share, 2)\n            opt_sl = round(max(0.05, opt_entry - profit_per_share / 2.2), 2)\n        else:\n            opt_tgt = round(max(0.05, opt_entry - profit_per_share), 2)\n            opt_sl = round(opt_entry + profit_per_share / 2.2, 2)'
)

print("Saved app.py")
    main()
# 5. Fix duplicate expiry_scalp without comma
text = text.replace(
    'expiry_scalp=expiry_scalp\n            expiry_scalp=expiry_scalp,',
    'expiry_scalp=expiry_scalp,'
)

# 6. Fix redundant assignments in ach
old_ach = '''        if not ach.get("achievable"):
            ach["achievable"] = True
            ach["target"] = round(entry + max(500.0 / lot_size, entry * 0.20), 2)
            ach["stop_loss"] = round(max(0.05, entry - max(250.0 / lot_size, entry * 0.10)), 2)
            ach["risk_amount"] = round(abs(entry - ach["stop_loss"]), 2)
            ach["reward_amount"] = round(abs(ach["target"] - entry), 2)
            ach["risk_reward"] = round(ach["reward_amount"] / max(0.01, ach["risk_amount"]), 2)
            ach["realistic_profit"] = round(ach["reward_amount"] * lot_size, 2)
            ach["time_horizon"] = 375
            ach["time_horizon"] = 5 if expiry_scalp else 30
            ach["target"] = tgt
            ach["stop_loss"] = sl
            ach["risk_amount"] = risk_amt
            ach["reward_amount"] = reward_amt
            ach["risk_reward"] = rr_ratio
            ach["realistic_profit"] = min_pnl
            ach["time_horizon"] = 5 if expiry_scalp else 375
            ach["time_horizon"] = 5 if expiry_scalp else 30
            ach["greeks"] = ach.get("greeks") or {"delta": 0.5, "gamma": 0.001, "theta": -8.0, "vega": 12.0, "iv": 22.0}'''

new_ach = '''        if not ach.get("achievable"):
            ach["achievable"] = True
            ach["target"] = tgt
            ach["stop_loss"] = sl
            ach["risk_amount"] = risk_amt
            ach["reward_amount"] = reward_amt
            ach["risk_reward"] = rr_ratio
            ach["realistic_profit"] = min_pnl
            ach["time_horizon"] = 5 if expiry_scalp else 30
            ach["greeks"] = ach.get("greeks") or {"delta": 0.5, "gamma": 0.001, "theta": -8.0, "vega": 12.0, "iv": 22.0}'''
text = text.replace(old_ach, new_ach)

# 7. Fix commodity configs duplicates
old_commod = '''    commodity_configs = {
        "CRUDEOIL": {"spot": 6150.0, "step": 50.0, "lot": 100, "iv": 34.0, "default_exp": "17 SEP 2026"},
        "CRUDEOIL": {"spot": 9650.0, "step": 50.0, "lot": 100, "iv": 34.0, "default_exp": "17 SEP 2026"},
        "CRUDEOIL": {"spot": 6250.0, "step": 50.0, "lot": 100, "iv": 34.0, "default_exp": "17 SEP 2026"},
        "NATURALGAS": {"spot": 245.0, "step": 5.0, "lot": 1250, "iv": 48.0, "default_exp": "24 SEP 2026"},
        "GOLD": {"spot": 74500.0, "step": 200.0, "lot": 100, "iv": 14.0, "default_exp": "25 SEP 2026"},
        "SILVER": {"spot": 88200.0, "step": 500.0, "lot": 30, "iv": 22.0, "default_exp": "25 SEP 2026"},
        "COPPER": {"spot": 820.0, "step": 5.0, "lot": 2500, "iv": 18.0, "default_exp": "30 SEP 2026"},
        "ZINC": {"spot": 270.0, "step": 2.5, "lot": 5000, "iv": 20.0, "default_exp": "30 SEP 2026"},
        "BANKNIFTY": {"spot": 56606.55, "step": 100.0, "lot": 15, "iv": 15.0, "default_exp": "24 SEP 2026"},
        "BANKNIFTY": {"spot": 56606.55, "step": 100.0, "lot": 30, "iv": 15.0, "default_exp": "24 SEP 2026"},
        "NIFTY": {"spot": 23398.10, "step": 50.0, "lot": 65, "iv": 13.0, "default_exp": "24 SEP 2026"},
        "BANKNIFTY": {"spot": 51250.0, "step": 100.0, "lot": 30, "iv": 15.0, "default_exp": "24 SEP 2026"},
        "NIFTY": {"spot": 23400.0, "step": 50.0, "lot": 65, "iv": 13.0, "default_exp": "24 SEP 2026"},
    }'''
new_commod = '''    commodity_configs = {
        "CRUDEOIL": {"spot": 6250.0, "step": 50.0, "lot": 100, "iv": 34.0, "default_exp": "17 SEP 2026"},
        "NATURALGAS": {"spot": 245.0, "step": 5.0, "lot": 1250, "iv": 48.0, "default_exp": "24 SEP 2026"},
        "GOLD": {"spot": 74500.0, "step": 200.0, "lot": 100, "iv": 14.0, "default_exp": "25 SEP 2026"},
        "SILVER": {"spot": 88200.0, "step": 500.0, "lot": 30, "iv": 22.0, "default_exp": "25 SEP 2026"},
        "COPPER": {"spot": 820.0, "step": 5.0, "lot": 2500, "iv": 18.0, "default_exp": "30 SEP 2026"},
        "ZINC": {"spot": 270.0, "step": 2.5, "lot": 5000, "iv": 20.0, "default_exp": "30 SEP 2026"},
        "BANKNIFTY": {"spot": 51250.0, "step": 100.0, "lot": 30, "iv": 15.0, "default_exp": "24 SEP 2026"},
        "NIFTY": {"spot": 23400.0, "step": 50.0, "lot": 65, "iv": 13.0, "default_exp": "24 SEP 2026"},
    }'''
text = text.replace(old_commod, new_commod)

# 8. Fix spot lookup syntax and logic
old_spot = '''    # Try fetching live quote for accurate spot
    spot = None
    try:
        q = UPSTOX.quote(underlying)
        if q and q.get("ltp"):
            spot = float(q["ltp"])
        elif root != underlying:
        clean_und = underlying.strip().upper()
        if not any(clean_und.endswith(x) for x in (" CE", " PE", "CE", "PE")):
            q = UPSTOX.quote(underlying)
            if q and q.get("ltp"):
                spot = float(q["ltp"])
        if spot is None or spot <= 0:
            q2 = UPSTOX.quote(root)
            if q2 and q2.get("ltp"):
                spot = float(q2["ltp"])
    except Exception:
        pass

    if spot is None:
    if spot is None or (root in commodity_configs and spot < commodity_configs[root]["spot"] * 0.25):'''

new_spot = '''    # Try fetching live quote for accurate spot
    spot = None
    try:
        clean_und = underlying.strip().upper()
        if not any(clean_und.endswith(x) for x in (" CE", " PE", "CE", "PE")):
            q = UPSTOX.quote(underlying)
            if q and q.get("ltp"):
                spot = float(q["ltp"])
        if spot is None or spot <= 0:
            q2 = UPSTOX.quote(root)
            if q2 and q2.get("ltp"):
                spot = float(q2["ltp"])
    except Exception:
        pass

    if spot is None or (root in commodity_configs and spot < commodity_configs[root]["spot"] * 0.25):'''
text = text.replace(old_spot, new_spot)

# 9. Fix broken min_expected
old_cfg = '''    if root in commodity_configs:
        cfg = commodity_configs[root]
        if spot is None or spot <= 0:
        min_expected = cfg["spot"] * 0.30'''
new_cfg = '''    if root in commodity_configs:
        cfg = commodity_configs[root]
        min_expected = cfg["spot"] * 0.30'''
text = text.replace(old_cfg, new_cfg)

# 10. Fix stray diff truncation marker
text = text.replace(
    '    strike_sug\n... [truncated for diff preview]\n    strike_suggestion = f"{symbol} Near ATM {opt_type}"',
    '    strike_suggestion = f"{symbol} Near ATM {opt_type}"'
)
text = text.replace(
    '    root = extract_root_symbol(underly\n... [truncated for diff preview]\n    root = extract_root_symbol(underlying).upper()',
    '    root = extract_root_symbol(underlying).upper()'
)

if crlf:
    text = text.replace('\n', '\r\n')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

try:
    py_compile.compile(path, doraise=True)
    print("SUCCESS: app.py compiled cleanly with zero syntax errors!")
except py_compile.PyCompileError as e:
    print("COMPILE ERROR:", e)
    sys.exit(1)
