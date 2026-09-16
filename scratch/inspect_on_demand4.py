import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('async def recommendation_on_demand')
if idx != -1:
    print(text[idx+1000:idx+3000])

