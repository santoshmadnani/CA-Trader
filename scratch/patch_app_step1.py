import re
from pathlib import Path

def patch_app():
    path = Path('app.py')
    code = path.read_text(encoding='utf-8')

    # 1. Add fetch_global_market_quotes function
    if 'def fetch_global_market_quotes' not in code:
        fetch_func = '''
def fetch_global_market_quotes() -> dict[str, Any]:
    cache_key = "global_market_quotes_live"
    cached = CACHE.get(cache_key)
    if cached is not None:
        return cached

    symbols = {
        "^DJI": "Dow Jones",
        "^GSPC": "S&P 500",
        "^IXIC": "Nasdaq Composite",
        "DX-Y.NYB": "US Dollar Index",
        "^TNX": "US 10-Yr Yield",
        "BZ=F": "Brent Crude",
        "^NSEI": "NIFTY 50"
    }
    quotes = {}
    import urllib.request, json, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for ticker, name in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                d = json.loads(resp.read().decode('utf-8'))
                meta = d['chart']['result'][0]['meta']
                price = float(meta.get('regularMarketPrice') or 0.0)
                prev = float(meta.get('previousClose') or meta.get('chartPreviousClose') or price)
                chg = price - prev if prev else 0.0
                pct = (chg / prev * 100.0) if prev else 0.0
                quotes[ticker] = {
                    "name": name,
                    "symbol": ticker,
                    "price": round(price, 2),
                    "prev_close": round(prev, 2),
                    "change": round(chg, 2),
                    "pct": round(pct, 2),
                    "status": "GREEN" if chg >= 0 else "RED"
                }
        except Exception:
            pass

    if quotes:
        CACHE.set(cache_key, quotes, 30) # 30s live cache
    return quotes
'''
        # Insert before market_macro_factors
        target = '@app.get("/api/market/macro-factors")'
        if target in code:
            code = code.replace(target, fetch_func + '\n' + target, 1)
            print("Added fetch_global_market_quotes")
        else:
            print("ERROR: @app.get('/api/market/macro-factors') not found")

    path.write_text(code, encoding='utf-8')
    print("Patched app.py step 1")

if __name__ == '__main__':
    patch_app()

