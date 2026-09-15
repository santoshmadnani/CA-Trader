import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
import sqlite3
con = sqlite3.connect('/app/data/ca_trader.sqlite3')
cur = con.cursor()

# Test app search function
import app
items = app.UPSTOX.search_instruments('NIFTY 23500', exchanges='NSE,BSE,MCX')
print('Search NIFTY 23500 count:', len(items.get('data', [])))
for x in items.get('data', [])[:5]:
    print(' ', x.get('trading_symbol') or x.get('symbol') or x.get('name'), '|', x.get('instrument_type'), '|', x.get('instrument_key'))

items2 = app.UPSTOX.search_instruments('CRUDEOIL 17 SEP', exchanges='MCX')
print('Search CRUDEOIL 17 SEP count:', len(items2.get('data', [])))
for x in items2.get('data', [])[:5]:
    print(' ', x.get('trading_symbol') or x.get('symbol') or x.get('name'), '|', x.get('instrument_type'), '|', x.get('instrument_key'))
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"docker exec ca-trader python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

