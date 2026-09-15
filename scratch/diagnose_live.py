"""
Diagnose catrader.site live — collect console errors, UI state, and check key elements.
"""
import subprocess, json, time, sys, os
sys.stdout.reconfigure(encoding='utf-8')

SITE = 'https://catrader.site'
KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

# Check the live site via SSH - get container logs
print('=== Container logs (last 60 lines) ===')
r = subprocess.run([
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    'docker logs ca-trader --tail 60 2>&1'
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print(r.stdout)
print(r.stderr)

print('\n=== Check /api/analysis/overall/NIFTY ===')
r2 = subprocess.run([
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    'curl -s "http://localhost:8000/api/analysis/overall/NIFTY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k:d[k] for k in list(d.keys())[:15]}, indent=2))" 2>&1'
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print(r2.stdout or r2.stderr)

print('\n=== Check /api/instruments/search?q=NIFTY ===')
r3 = subprocess.run([
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    'curl -s "http://localhost:8000/api/instruments/search?q=NIFTY&limit=5" 2>&1'
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print(r3.stdout[:2000] or r3.stderr)

print('\n=== Check /api/options/summary/CRUDEOIL ===')
r4 = subprocess.run([
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    'curl -s "http://localhost:8000/api/options/summary/CRUDEOIL" | python3 -c "import sys,json; d=json.load(sys.stdin); st=d.get(\'strikes\',[])[:3]; print(\'strikes:\',len(d.get(\'strikes\',[])),\'atm:\',d.get(\'atm_strike\')); [print(s) for s in st]" 2>&1'
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
print(r4.stdout or r4.stderr)

print('\n=== Check /api/analysis/rationale/NIFTY ===')
r5 = subprocess.run([
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    'curl -s "http://localhost:8000/api/analysis/rationale/NIFTY" 2>&1 | python3 -c "import sys; d=sys.stdin.read(); print(d[:3000])" 2>&1'
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
print(r5.stdout[:3000] or r5.stderr)
