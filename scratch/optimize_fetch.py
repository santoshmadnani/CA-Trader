from pathlib import Path

def optimize_fetch():
    path = Path('app.py')
    code = path.read_text(encoding='utf-8')

    old_fetch_loop = '''    for ticker, name in symbols.items():
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
            pass'''

    new_fetch_loop = '''    from concurrent.futures import ThreadPoolExecutor
    def _fetch_one(t_info):
        ticker, name = t_info
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=2d"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=3.5, context=ctx) as resp:
                d = json.loads(resp.read().decode('utf-8'))
                meta = d['chart']['result'][0]['meta']
                price = float(meta.get('regularMarketPrice') or 0.0)
                prev = float(meta.get('previousClose') or meta.get('chartPreviousClose') or price)
                chg = price - prev if prev else 0.0
                pct = (chg / prev * 100.0) if prev else 0.0
                return ticker, {
                    "name": name,
                    "symbol": ticker,
                    "price": round(price, 2),
                    "prev_close": round(prev, 2),
                    "change": round(chg, 2),
                    "pct": round(pct, 2),
                    "status": "GREEN" if chg >= 0 else "RED"
                }
        except Exception:
            return ticker, None

    with ThreadPoolExecutor(max_workers=7) as executor:
        results = executor.map(_fetch_one, symbols.items())
        for ticker, q_data in results:
            if q_data:
                quotes[ticker] = q_data'''

    if old_fetch_loop in code:
        code = code.replace(old_fetch_loop, new_fetch_loop, 1)
        path.write_text(code, encoding='utf-8')
        print("Parallelized fetch_global_market_quotes successfully")
    else:
        print("WARN: old_fetch_loop not found")

if __name__ == '__main__':
    optimize_fetch()

