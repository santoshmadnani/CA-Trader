import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("def _calc_reco_pnl(")
if idx != -1:
    print(text[idx:idx+1200])

