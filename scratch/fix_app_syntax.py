from pathlib import Path

def fix_syntax():
    path = Path('app.py')
    code = path.read_text(encoding='utf-8')

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

    '''
            code = code[:target_pos] + saving_code + code[target_pos:]
            print("Successfully added saving code to analysis_overall")

    path.write_text(code, encoding='utf-8')
    print("fix_syntax completed")

if __name__ == '__main__':
    fix_syntax()

