import urllib.request
import json

def check(url, label):
    try:
        r = urllib.request.urlopen(url, timeout=30)
        data = r.read().decode()[:3000]
        print(f'\n=== {label} ===')
        print(data)
    except Exception as e:
        print(f'\n=== {label} ERROR ===')
        print(str(e))

check('http://localhost:8000/api/instruments/search?q=NIFTY&limit=5', 'Search NIFTY')
check('http://localhost:8000/api/analysis/overall/NIFTY', 'Overall NIFTY')
check('http://localhost:8000/api/options/summary/CRUDEOIL', 'Options CRUDEOIL')
check('http://localhost:8000/api/analysis/rationale/NIFTY', 'Rationale NIFTY')
check('http://localhost:8000/api/market/other-factors', 'Other Factors')
