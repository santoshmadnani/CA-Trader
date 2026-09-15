import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
import app
items = app.UPSTOX.search_instruments('CRUDEOIL 17 SEP', exchanges='MCX')
contracts = items.get('data', [])
keys = [c.get('instrument_key') for c in contracts[:10] if c.get('instrument_key')]
print('Testing quotes for keys:', keys)
q = app.UPSTOX.quotes(keys)
print('Quotes returned:', len(q))
for item in q[:5]:
    print(' ', item.get('symbol') or item.get('instrument_key'), 'ltp:', item.get('ltp'), 'oi:', item.get('oi'), 'close:', item.get('close'))
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"docker exec ca-trader python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

