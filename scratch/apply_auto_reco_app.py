import ast, sys

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

loop_code = '''
async def _auto_recommendation_recorder_loop() -> None:
    """Auto-saves high-conviction trade setups every 5 minutes during trading hours.
    NSE runs 09:15 - 15:30 IST. MCX commodity trading runs 09:00 - 23:30 IST.
    Guarantees recommendation history is continuously populated through 11:30 PM.
    """
    await asyncio.sleep(20)
    while True:
        try:
            now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
            weekday = now_ist.weekday()
            if weekday < 5:
                current_minutes = now_ist.hour * 60 + now_ist.minute
                nse_active = (9 * 60 + 15) <= current_minutes <= (15 * 60 + 30)
                mcx_active = (9 * 60) <= current_minutes <= (23 * 60 + 30)
                
                symbols_to_scan = []
                if mcx_active:
                    symbols_to_scan.append("CRUDEOIL")
                if nse_active:
                    symbols_to_scan.extend(["NIFTY", "BANKNIFTY"])
                
                try:
                    active_users = db_exec("SELECT id FROM users LIMIT 10", [], "all") or [{"id": 1}]
                except Exception:
                    active_users = [{"id": 1}]
                
                for u in active_users:
                    uid = int(u.get("id") or 1)
                    for sym in symbols_to_scan:
                        try:
                            rec = await asyncio.wait_for(
                                asyncio.to_thread(
                                    overall_recommendation,
                                    sym, "5m", 1500.0, 800.0,
                                    {"risk_profile": "moderate"},
                                    {"enabled": True}, False, uid
                                ),
                                timeout=8.0
                            )
                            act = str(rec.get("recommendation") or "").upper()
                            if act in ("BUY", "SELL"):
                                ti = rec.get("instrument") or {}
                                trade_sym = str(ti.get("display") or ti.get("symbol") or sym)
                                score = float(rec.get("confidence") or rec.get("score") or 78.0)
                                entry = float(rec.get("entry") or 0.0)
                                sl = float(rec.get("stop_loss") or 0.0)
                                tgt = float(rec.get("target") or 0.0)
                                
                                recent = db_exec(
                                    "SELECT id FROM recommendations WHERE user_id=? AND symbol=? AND recommendation=? AND created_at > datetime('now', '-5 minutes')",
                                    [uid, trade_sym, act],
                                    "one"
                                )
                                if not recent:
                                    rid = secrets.token_hex(8)
                                    db_exec(
                                        """INSERT INTO recommendations (
                                            id, user_id, source, symbol, underlying, recommendation,
                                            timeframe, entry, target, stop_loss, rationale,
                                            technical_basis, news_basis, option_basis, score,
                                            outcome, final_pnl, success, exit_reason, created_at, status
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'ACTIVE')""",
                                        [
                                            rid, uid, "auto", trade_sym, sym, act,
                                            "5m", entry, tgt, sl,
                                            str(rec.get("reason") or "Auto 5-min institutional setup"),
                                            safe_json(rec.get("evidence", {}).get("technicals")),
                                            safe_json(rec.get("evidence", {}).get("news")),
                                            safe_json(rec.get("evidence", {}).get("options")),
                                            score,
                                            "PENDING", 0.0, 0, ""
                                        ]
                                    )
                                    log.info(f"[AutoReco] Saved 5-min {act} setup for {trade_sym} (User {uid})")
                        except Exception as inner_exc:
                            log.debug(f"[AutoReco] Scan error for {sym}: {inner_exc}")
        except Exception as exc:
            log.warning(f"[AutoReco] Loop error: {exc}")
        
        await asyncio.sleep(300)
'''

target = "async def _auto_trade_loop() -> None:"
if "_auto_recommendation_recorder_loop" not in text:
    if target in text:
        text = text.replace(target, loop_code + "\n\n" + target, 1)
        print("[OK] Inserted _auto_recommendation_recorder_loop before _auto_trade_loop")
    else:
        print("[FAIL] target not found")
        sys.exit(1)

# Hook into lifespan
lifespan_target = "auto_task = asyncio.create_task(_auto_trade_loop())\n    risk_task = asyncio.create_task(_paper_risk_loop())"
lifespan_replacement = "auto_task = asyncio.create_task(_auto_trade_loop())\n    risk_task = asyncio.create_task(_paper_risk_loop())\n    reco_task = asyncio.create_task(_auto_recommendation_recorder_loop())"

cancel_target = "auto_task.cancel(); risk_task.cancel()"
cancel_replacement = "auto_task.cancel(); risk_task.cancel(); reco_task.cancel()"

if "reco_task" not in text:
    if lifespan_target in text:
        text = text.replace(lifespan_target, lifespan_replacement, 1)
        print("[OK] Hooked reco_task into lifespan startup")
    if cancel_target in text:
        text = text.replace(cancel_target, cancel_replacement, 1)
        print("[OK] Hooked reco_task into lifespan cancellation")

# Verify AST
try:
    ast.parse(text)
    print("[OK] AST verified cleanly")
except Exception as e:
    print(f"[FAIL] AST error: {e}")
    sys.exit(1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("app.py updated successfully")

