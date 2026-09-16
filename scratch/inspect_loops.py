import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("async def _auto_trade_loop()")
if idx != -1:
    print(text[idx:idx+1500])

