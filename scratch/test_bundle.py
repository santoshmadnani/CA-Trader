import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
import urllib.request, json
try:
    r = urllib.request.urlopen('http://localhost:8000/api/analysis/chart-bundle/NIFTY?timeframe=5m&include_mtf=false', timeout=15)
    d = json.loads(r.read().decode())
    print('Keys:', list(d.keys()))
    print('Candlestick patterns count:', len(d.get('patterns', {}).get('patterns', [])))
    print('Sample candle pattern:', d.get('patterns', {}).get('patterns', [])[:1])
    print('Chart patterns count:', len(d.get('chart_patterns', {}).get('patterns', [])))
    print('Sample chart pattern:', d.get('chart_patterns', {}).get('patterns', [])[:1])
    print('Structure trend:', d.get('structure', {}).get('trend'))
except Exception as e:
    print('Error:', e)
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"docker exec ca-trader python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

