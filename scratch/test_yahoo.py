import urllib.request, json, ssl

def test_fetch():
    symbols = ["^DJI", "^GSPC", "^IXIC", "^NSEI", "DX-Y.NYB", "^TNX", "BZ=F"]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    url = "https://query1.finance.yahoo.com/v8/finance/chart/^DJI?interval=1d&range=2d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            print("Dow Jones meta:")
            print("Symbol:", meta.get('symbol'))
            print("Regular market price:", meta.get('regularMarketPrice'))
            print("Previous close:", meta.get('previousClose') or meta.get('chartPreviousClose'))
    except Exception as e:
        print("Yahoo chart query error:", e)

    # Also test multi-quote query
    quote_url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=^DJI,^GSPC,^IXIC,^TNX,DX-Y.NYB,BZ=F"
    req2 = urllib.request.Request(quote_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req2, timeout=5, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('quoteResponse', {}).get('result', [])
            print("\nMulti-quote results count:", len(results))
            for item in results:
                print(f"{item.get('symbol')}: Price={item.get('regularMarketPrice')} PrevClose={item.get('regularMarketPreviousClose')} Chg={item.get('regularMarketChangePercent')}%")
    except Exception as e:
        print("Yahoo multi-quote query error:", e)

if __name__ == '__main__':
    test_fetch()

