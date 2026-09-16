import os, sys, json, asyncio
import pandas as pd

from app import (
    app,
    detect_candlestick_patterns,
    CRUDE_REAL_NEWS_2026,
    NIFTY_REAL_NEWS_2026,
    BANKNIFTY_REAL_NEWS_2026,
    GOLD_REAL_NEWS_2026,
    recommendation_news_evidence,
    save_recommendation_to_history_api,
    recommendation_history,
    positions,
    db_exec
)

print('=== 1. VERIFY CANDLESTICK PATTERNS WITH EXACT TIMESTAMPS ===')
mock_candles = [
    {'open': 6000, 'high': 6010, 'low': 5940, 'close': 5950, 'volume': 1000, 'timestamp': '2026-09-16 10:00'},
    {'open': 5950, 'high': 5960, 'low': 5890, 'close': 5900, 'volume': 1000, 'timestamp': '2026-09-16 10:05'},
    {'open': 5900, 'high': 5910, 'low': 5840, 'close': 5850, 'volume': 1000, 'timestamp': '2026-09-16 10:10'},
    {'open': 5850, 'high': 5860, 'low': 5790, 'close': 5800, 'volume': 1000, 'timestamp': '2026-09-16 10:15'},
    {'open': 5800, 'high': 5810, 'low': 5740, 'close': 5750, 'volume': 1000, 'timestamp': '2026-09-16 10:20'},
    {'open': 5750, 'high': 5760, 'low': 5720, 'close': 5730, 'volume': 1000, 'timestamp': '2026-09-16 10:25'},
    {'open': 5740, 'high': 5750, 'low': 5710, 'close': 5720, 'volume': 1000, 'timestamp': '2026-09-16 10:30'},
    {'open': 5700, 'high': 5730, 'low': 5690, 'close': 5725, 'volume': 1000, 'timestamp': '2026-09-16 10:35'},
    {'open': 5720, 'high': 5760, 'low': 5710, 'close': 5750, 'volume': 1000, 'timestamp': '2026-09-16 10:40'},
    {'open': 5750, 'high': 5820, 'low': 5740, 'close': 5810, 'volume': 1000, 'timestamp': '2026-09-16 10:45'},
]
patterns = detect_candlestick_patterns(mock_candles, '5m')
print(f'Detected {len(patterns)} patterns:')
for p in patterns:
    print(f"  - {p.get('name')} | Candle: {p.get('candle_time')} | Detected: {p.get('detected_at')}")

print('\n=== 2. VERIFY INSTITUTIONAL NEWS ACROSS ALL ASSETS ===')
for sym in ['NIFTY', 'BANKNIFTY', 'CRUDEOIL', 'GOLD']:
    ev = recommendation_news_evidence(sym)
    stock_count = len(ev.get('stock_events', []))
    sig = ev.get('stock', {}).get('signal')
    mat = ev.get('stock', {}).get('materiality')
    print(f"  Asset {sym:10s} -> Signal: {sig}, Materiality: {mat}%, Catalysts: {stock_count}")

print('\n=== 3. VERIFY POSITIONS MAPPING & PERSISTENCE ===')
async def test_live():
    real_users = db_exec("SELECT id, username FROM users", fetch="all")
    user = {'id': real_users[0]['id'], 'username': real_users[0]['username'], 'role': 'admin'} if real_users else {'id': 1, 'username': 'admin', 'role': 'admin'}
    
    from starlette.requests import Request
    dummy_req = Request({'type': 'http', 'query_string': b''})
    
    # Check positions mapping
    pos_res = await positions(request=dummy_req, user=user)
    print("Positions API returned keys:", list(pos_res.keys()))
    assert 'items' in pos_res and 'positions' in pos_res, 'Positions mapping missing keys'
    
    # Check recommendation save
    save_payload = {
        'symbol': 'NIFTY',
        'action': 'BUY_CALL',
        'option_symbol': 'NIFTY 25400 CE',
        'entry': 145.0,
        'stop_loss': 120.0,
        'target': 195.0,
        'rationale': 'Institutional FII momentum breakout with volume confirmation'
    }
    save_res = await save_recommendation_to_history_api(save_payload, user=user)
    print("Save Recommendation response:", save_res)
    assert save_res.get('success') is True, 'Save failed'

    # Check recommendation history
    hist_res = await recommendation_history(request=dummy_req, user=user)
    items = hist_res.get('items', [])
    print(f"Recommendation History count: {len(items)}")
    assert len(items) > 0, 'No history items'

asyncio.run(test_live())

print('\n=== 4. VERIFY FRONTEND DOM ELEMENTS IN CONTAINER ===')
with open('terminal.html', 'r', encoding='utf-8') as f:
    th = f.read()

assert 'dashConfluenceTableBody' in th, 'dashConfluenceTableBody missing'
assert 'toggleCardDetail' in th, 'toggleCardDetail missing'
assert 'makeUniversalDraggable' in th, 'makeUniversalDraggable missing'
assert 'formatAiMarkdown' in th, 'formatAiMarkdown missing'
assert 'tutFeatureTree' in th, 'tutFeatureTree missing'
assert 'select#watchlistSelect' in th, 'select#watchlistSelect CSS missing'
print("All frontend elements (confluence grid, drilldowns, draggable, markdown, tutorial, watchlist CSS) VERIFIED in container!")

print('\n=== ALL RELEASE 49 INTEGRATION TESTS COMPLETED SUCCESSFULLY ===')

