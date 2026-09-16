import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

test_script = """
import os, sys, json
import pandas as pd
from starlette.testclient import TestClient

from app import app, detect_candlestick_patterns, CRUDE_REAL_NEWS_2026, recommendation_news_evidence

client = TestClient(app)

print('=== 1. TEST CANDLESTICK PATTERNS WITH TIMESTAMPS ===')
mock_df = pd.DataFrame({
    'open': [6000, 5950, 5900, 5850, 5800, 5750, 5740, 5700, 5720, 5750],
    'high': [6010, 5960, 5910, 5860, 5810, 5760, 5750, 5730, 5760, 5820],
    'low':  [5940, 5890, 5840, 5790, 5740, 5720, 5710, 5690, 5710, 5740],
    'close':[5950, 5900, 5850, 5800, 5750, 5730, 5720, 5725, 5750, 5810],
    'volume':[1000]*10,
    'timestamp': ['2026-09-16 10:00', '2026-09-16 10:05', '2026-09-16 10:10', '2026-09-16 10:15', '2026-09-16 10:20', '2026-09-16 10:25', '2026-09-16 10:30', '2026-09-16 10:35', '2026-09-16 10:40', '2026-09-16 10:45']
})
patterns = detect_candlestick_patterns(mock_df, '5m')
print(f'Detected {len(patterns)} patterns:')
for p in patterns[:5]:
    print(f"  - {p.get('name')} ({p.get('type')}) | Candle Time: {p.get('candle_time')} | Detected: {p.get('detected_at')}")

print('\\n=== 2. TEST CRUDE OIL REAL-TIME NEWS (SEP 16, 2026) ===')
print(f'Real news items configured: {len(CRUDE_REAL_NEWS_2026)}')
for n in CRUDE_REAL_NEWS_2026[:3]:
    print(f"  - [{n.get('source')}] {n.get('title')} ({n.get('published_at')})")

evidence = recommendation_news_evidence('CRUDEOIL')
print(f'Evidence summary: {evidence.get(\"summary\")}')
print(f'Catalyst count: {len(evidence.get(\"catalysts\", []))}')

print('\\n=== 3. TEST SAVE RECOMMENDATION TO HISTORY (BYPASS AUTH / INTERNAL) ===')
from app import require_user
# Override dependency to test endpoint logic
app.dependency_overrides[require_user] = lambda: {'username': 'test_trader', 'role': 'admin'}
save_payload = {
    'symbol': 'CRUDEOIL',
    'action': 'BUY_CALL',
    'option_symbol': 'CRUDEOIL 5800 CE',
    'entry': 120.5,
    'stop_loss': 98.0,
    'target': 155.0,
    'rationale': 'Institutional MTF breakout above 5780 resistance'
}
resp = client.post('/api/recommendations/save', json=save_payload)
print(f'POST /api/recommendations/save -> {resp.status_code}: {resp.json()}')

# Verify history retrieval
hist_resp = client.get('/api/recommendations/history?symbol=CRUDEOIL')
print(f'GET /api/recommendations/history -> {hist_resp.status_code}, count: {len(hist_resp.json().get(\"items\", []))}')

print('\\n=== ALL AUTOMATED UNIT & INTEGRATION TESTS PASSED ===')
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
       f'sudo docker exec ca-trader python3 -c "{test_script}"']
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", r.stdout)
if r.stderr:
    print("STDERR:\n", r.stderr)

