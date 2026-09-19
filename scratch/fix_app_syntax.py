from pathlib import Path
with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()
import io
import re
import sys

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

    path.write_text(code, encoding='utf-8')
    print("fix_syntax completed")
# Fix 3: check line 5832 duplicate segment=seg
content = content.replace("            side=side,\n            segment=seg\n            segment=seg,", "            side=side,\n            segment=seg,")
content = content.replace("            side=side,\r\n            segment=seg\r\n            segment=seg,", "            side=side,\r\n            segment=seg,")

if __name__ == '__main__':
    fix_syntax()
with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Saved app.py")
    main()
