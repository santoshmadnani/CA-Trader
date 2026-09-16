import os, sys, json, asyncio
import pandas as pd

from app import app, detect_candlestick_patterns, CRUDE_REAL_NEWS_2026, recommendation_news_evidence, save_recommendation_to_history_api, recommendation_history

print('=== 1. TEST CANDLESTICK PATTERNS WITH TIMESTAMPS ===')
mock_df = pd.DataFrame({
    'open': [6000, 5950, 5900, 5850, 5800, 5750, 5740, 5700, 5720, 5750],
    'high': [6010, 5960, 5910, 5860, 5810, 5760, 5750, 5730, 5760, 5820],
    'low':  [5940, 5890, 5840, 5790, 5740, 5720, 5710, 5690, 5710, 5740],
    'close':[5950, 5900, 5850, 5800, 5750, 5730, 5720, 5725, 5750, 5810],
    'volume':[1000]*10,
    'timestamp': ['2026-09-16 10:00', '2026-09-16 10:05', '2026-09-16 10:10', '2026-09-16 10:15', '2026-09-16 10:20', '2026-09-16 10:25', '2026-09-16 10:30', '2026-09-16 10:35', '2026-09-16 10:40', '2026-09-16 10:45']
})
patterns = detect_candlestick_patterns(mock_df.to_dict(orient='records'), '5m')
print(f'Detected {len(patterns)} patterns:')
for p in patterns[:5]:
    print(f"  - {p.get('name')} | Candle Time: {p.get('candle_time')} | Detected: {p.get('detected_at')}")

print('\n=== 2. TEST CRUDE OIL REAL-TIME NEWS (SEP 16, 2026) ===')
print(f'Real news items configured: {len(CRUDE_REAL_NEWS_2026)}')
for n in CRUDE_REAL_NEWS_2026[:3]:
    print(f"  - [{n.get('source')}] {n.get('headline')} ({n.get('published_at')})")

evidence = recommendation_news_evidence('CRUDEOIL')
print(f'Stock signal: {evidence.get("stock", {}).get("sentiment")}')
print(f'Stock events count: {len(evidence.get("stock_events", []))}')
print(f'Global events count: {len(evidence.get("global_events", []))}')

print('\n=== 3. TEST SAVE RECOMMENDATION TO HISTORY ===')
async def test_save_and_history():
    from app import db_exec
    real_users = db_exec("SELECT id, username FROM users", fetch="all")
    if real_users:
        user = {'id': real_users[0]['id'], 'username': real_users[0]['username'], 'role': 'admin'}
    else:
        user = {'id': 1, 'username': 'admin', 'role': 'admin'}
    print('Testing with user:', user)
    save_payload = {
        'symbol': 'CRUDEOIL',
        'action': 'BUY_CALL',
        'option_symbol': 'CRUDEOIL 5800 CE',
        'entry': 120.5,
        'stop_loss': 98.0,
        'target': 155.0,
        'rationale': 'Institutional MTF breakout above 5780 resistance'
    }
    save_res = await save_recommendation_to_history_api(save_payload, user=user)
    print('save_recommendation_to_history_api response:', save_res)
    assert save_res.get('success') is True, 'Save failed'

    from starlette.requests import Request
    req = Request({'type': 'http', 'query_string': b'symbol=CRUDEOIL'})
    hist_res = await recommendation_history(request=req, user=user)
    items = hist_res.get('items', [])
    print(f'recommendation_history count: {len(items)}')
    assert len(items) > 0, 'No history items returned'
    print('Last saved item ID:', items[0].get('id'))
    print('Last saved item Symbol:', items[0].get('symbol'))
    print('Last saved item Action:', items[0].get('action'))

asyncio.run(test_save_and_history())

print('\n=== ALL AUTOMATED INTEGRATION TESTS COMPLETED SUCCESSFULLY ===')
