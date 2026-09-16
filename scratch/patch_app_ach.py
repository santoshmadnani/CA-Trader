with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_ach_block = """        if not ach.get("achievable"):
            ach["achievable"] = True
            ach["target"] = round(opt_entry + max(500.0 / lot, opt_entry * 0.20), 2)
            ach["stop_loss"] = round(max(0.05, opt_entry - max(250.0 / lot, opt_entry * 0.10)), 2)
            ach["risk_amount"] = round(abs(opt_entry - ach["stop_loss"]), 2)
            ach["reward_amount"] = round(abs(ach["target"] - opt_entry), 2)
            ach["risk_reward"] = round(ach["reward_amount"] / max(0.01, ach["risk_amount"]), 2)
            ach["realistic_profit"] = round(ach["reward_amount"] * lot, 2)
            ach["time_horizon"] = 375
            ach["greeks"] = ach.get("greeks") or {"delta": 0.5, "gamma": 0.001, "theta": -8.0, "vega": 12.0, "iv": 22.0}
        if False and not ach["achievable"]:"""

new_ach_block = """        if not ach.get("achievable"):
            inst_obj = {"kind": "OPTION", "symbol": symbol, "display": symbol, "entry": opt_entry, "instrument_key": key, "lot_size": lot, "option_type": opt_type}
            reason_msg = f"Setup does not qualify: {ach.get('reason') or 'Unfavorable mathematical move / high Theta friction'}"
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
                "greeks": ach.get("greeks") or bs_greeks(last_price, opt_strike, t_years=15.0/365.0, r=0.07, sigma=0.18, opt_type=opt_type),
                "rationale": reason_msg,
                "reason": reason_msg,
                "provider": "upstox+greeks_engine",
                "timestamp": now_iso(),
                **next_day_info
            }
            CACHE.set(cache_key, res_opt, 15)
            return res_opt
        if not ach.get("achievable"):"""

if old_ach_block in text:
    text = text.replace(old_ach_block, new_ach_block, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Successfully replaced unachievable option override with NO_TRADE guard")
else:
    print("Old ach block not found exactly, check diff")

