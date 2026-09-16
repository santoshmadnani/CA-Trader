import urllib.request, json, ssl

def fetch_symbol(sym):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=2d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            price = meta.get('regularMarketPrice')
            prev = meta.get('previousClose') or meta.get('chartPreviousClose')
            chg = (price - prev) if (price and prev) else 0.0
            pct = (chg / prev * 100) if prev else 0.0
            return {"symbol": sym, "price": round(price, 2) if price else None, "prev_close": round(prev, 2) if prev else None, "change": round(chg, 2), "pct": round(pct, 2)}
    except Exception as e:
        return {"symbol": sym, "error": str(e)}

def test_all():
    symbols = {
        "dow": "^DJI",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "dxy": "DX-Y.NYB",
        "us10y": "^TNX",
        "crude": "BZ=F",
        "nifty": "^NSEI"
    }
    for k, sym in symbols.items():
        res = fetch_symbol(sym)
        print(f"{k:8s} ({sym:10s}): {res}")

if __name__ == '__main__':
    test_all()

