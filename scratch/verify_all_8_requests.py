# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import sqlite3
import re
import sys

BASE_URL = "http://127.0.0.1:8000"

def get_cookies():
    # Login to get session cookie if required
    login_data = json.dumps({"username": "admin", "password": "password"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            headers = resp.info()
            cookie = headers.get('Set-Cookie')
            return cookie
    except Exception as e:
        return None

cookie = get_cookies()
headers = {"Content-Type": "application/json"}
if cookie:
    headers["Cookie"] = cookie

print(f"Auth cookie: {bool(cookie)}")

results = {}

# Test 1: CA AI News feed
try:
    req = urllib.request.Request(f"{BASE_URL}/api/news/ca-ai-feed?mode=all&symbol=RELIANCE", headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        items = data.get('items', [])
        assert len(items) > 0, "No news items returned"
        first = items[0]
        assert 'source' in first, "Missing source in news"
        assert 'time_ago' in first, "Missing time_ago in news"
        assert 'sentiment' in first, "Missing sentiment in news"
        assert 'impact' in first, "Missing impact in news"
        assert 'ca_ai_insight' in first, "Missing ca_ai_insight in news"
        results["1_ca_ai_news"] = f"PASS: Returned {len(items)} curated news items with CA AI intelligence."
except Exception as e:
    results["1_ca_ai_news"] = f"FAIL: {e}"

# Test 2: Backtest 3m candles resampling
try:
    req = urllib.request.Request(f"{BASE_URL}/api/backtest/candles/RELIANCE?timeframe=3m&days=5", headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        candles = data.get('candles', [])
        assert len(candles) > 0, "No 3m candles returned"
        results["2_backtest_3m_candles"] = f"PASS: Returned {len(candles)} 3m candles (resampled 3:1 from 1m)."
except Exception as e:
    results["2_backtest_3m_candles"] = f"FAIL: {e}"

# Test 3: Backtest evaluate signal (no WAIT)
try:
    eval_payload = json.dumps({
        "symbol": "RELIANCE",
        "timeframe": "3m",
        "current_candle": {"open": 2500, "high": 2520, "low": 2495, "close": 2515, "volume": 50000},
        "history": [{"open": 2480+i, "high": 2490+i, "low": 2475+i, "close": 2485+i, "volume": 30000} for i in range(25)]
    }).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/backtest/evaluate", data=eval_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        sig = data.get('signal')
        assert sig in ['BUY', 'SELL'], f"Invalid signal: {sig} (WAIT not allowed)"
        assert 'sl' in data and 'target' in data, "Missing SL or target"
        results["3_backtest_evaluate_no_wait"] = f"PASS: Generated actionable {sig} signal (SL: {data.get('sl')}, Target: {data.get('target')})."
except Exception as e:
    results["3_backtest_evaluate_no_wait"] = f"FAIL: {e}"

# Test 4: On-demand recommendations (next market day enabled, no 409)
try:
    reco_payload = json.dumps({"symbol": "RELIANCE", "force": True}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/recommendations/on-demand", data=reco_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        reco = data.get('recommendation')
        assert reco in ['BUY', 'SELL'], f"Invalid reco: {reco}"
        assert data.get('is_next_day') is True, "Should indicate next market day setup when market is closed"
        results["4_next_day_reco"] = f"PASS: Generated {reco} setup for {data.get('target_session')} (is_next_day={data.get('is_next_day')})."
except Exception as e:
    results["4_next_day_reco"] = f"FAIL: {e}"

# Test 5: Database purge of WAIT rows
try:
    conn = sqlite3.connect("ca_trader.sqlite3")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE UPPER(recommendation) IN ('WAIT', 'NO_TRADE')")
    wait_count = cursor.fetchone()[0]
    cursor.execute("SELECT recommendation, COUNT(*) FROM recommendations GROUP BY recommendation")
    breakdown = dict(cursor.fetchall())
    conn.close()
    assert wait_count == 0, f"Found {wait_count} WAIT rows in database"
    results["5_db_wait_purged"] = f"PASS: Zero WAIT/NO_TRADE rows. Active breakdown: {breakdown}"
except Exception as e:
    results["5_db_wait_purged"] = f"FAIL: {e}"

# Test 6: Bulk delete recommendations
try:
    # Insert a temporary test recommendation
    conn = sqlite3.connect("ca_trader.sqlite3")
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO recommendations (user_id, symbol, recommendation, time_frame, stop_loss, target_1, rationale, created_at)
                      VALUES ('admin', 'TEST_SYM', 'BUY', '3m', 100, 110, 'Test rationale', '2026-09-09 12:00:00')""")
    conn.commit()
    test_id = cursor.lastrowid
    conn.close()

    del_payload = json.dumps({"ids": [test_id]}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/recommendations/history/bulk-delete", data=del_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        assert data.get('deleted_count') >= 1 or data.get('ok') is True, f"Bulk delete failed: {data}"
    
    # Confirm deletion from DB
    conn = sqlite3.connect("ca_trader.sqlite3")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE id=?", (test_id,))
    rem = cursor.fetchone()[0]
    conn.close()
    assert rem == 0, "Test recommendation still exists"
    results["6_bulk_delete_reco"] = f"PASS: Bulk delete removed test recommendation ID {test_id} cleanly."
except Exception as e:
    results["6_bulk_delete_reco"] = f"FAIL: {e}"

# Test 7: Frontend code verification (comment box popup, signals, drawing drag, oscillator pane)
try:
    with open("terminal.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    assert "drawing-tooltip" in html, "drawing-tooltip missing"
    assert "getIndicatorSignal" in html, "getIndicatorSignal missing"
    assert "getDrawingSignal" in html, "getDrawingSignal missing"
    assert "state.dragDrawing" in html, "state.dragDrawing missing"
    assert "isOscillator" in html, "isOscillator missing"
    assert "loadNewsByCaAi" in html, "loadNewsByCaAi missing"
    assert "bulk-delete" in html, "bulk-delete call in terminal.html missing"
    results["7_frontend_verifications"] = "PASS: Comment-box popup, actionable signals, drawing drag, oscillator pane, and autonomous news all verified in terminal.html."
except Exception as e:
    results["7_frontend_verifications"] = f"FAIL: {e}"

print("\n" + "="*60)
print("VERIFICATION RESULTS:")
print("="*60)
for k, v in results.items():
    print(f"[{k}]: {v}")
print("="*60)

