import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
import app
p = app.UPSTOX.search_instruments('CRUDEOIL 10000 CE 17 SEP', exchanges='MCX')
rows = p.get('data', [])
print('Found:', len(rows))
if rows:
    print('Row 0 keys and values:')
    for k, v in rows[0].items():
        print(f'  {k}: {v}')

key, meta = app.UPSTOX.resolve_instrument('CRUDEOIL FUT 17 SEP 10000CE')
print('Resolved key:', key, 'meta:', meta.get('trading_symbol') or meta.get('symbol'))
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"docker exec ca-trader python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

