import subprocess

key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
host = "ubuntu@15.252.81.122"

remote_code = """
import app, asyncio, json

async def test():
    print("=== LIVE INTERNAL VERIFICATION ===")
    
    # 1. Macro Factors
    res = await app.market_macro_factors({'id': 1, 'role': 'admin'})
    print("Macro Factors Result:")
    print("  Data state:", res.get('data_state'))
    print("  Gift Nifty:", res.get('gift_nifty'))
    print("  Dow Jones:", res.get('us_markets', {}).get('dow'))
    print("  S&P 500:", res.get('us_markets', {}).get('sp500'))
    for m in res.get('macro_drivers', []):
        print(f"  Driver: {m.get('factor')} -> Level: {m.get('level')} Prev: {m.get('prev_close')} Chg: {m.get('change')}")

    # 2. Recommendations Save
    rec = await app.analysis_overall('NIFTY', '5m', user={'id': 1, 'role': 'admin'})
    print("\\nOverall Reco Result:")
    print("  Signal:", rec.get('recommendation'))
    print("  Entry:", rec.get('entry'), "Target:", rec.get('target'), "SL:", rec.get('stop_loss'))
    print("  Saved in DB:", rec.get('saved'), "ID:", rec.get('id'))

    # 3. Recommendations History
    hist = await app.recommendation_history(None, user={'id': 1, 'role': 'admin'})
    print(f"\\nHistory Items count: {len(hist.get('items', []))}")

    # 4. News Unified
    news = await app.news_unified('NIFTY', 50, user={'id': 1, 'role': 'admin'})
    print(f"\\nNews Unified for NIFTY count: {len(news.get('events', []))}")

asyncio.run(test())
"""

# Run on remote
cmd = [
    "ssh", "-i", key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    host,
    f"sudo docker exec -i ca-trader python3 << 'EOF'\n{remote_code}\nEOF"
]

r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8')
print("STDOUT:\n", r.stdout)
if r.stderr:
    print("STDERR:\n", r.stderr)

