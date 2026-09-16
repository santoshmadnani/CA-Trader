import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("async def save_recommendation_to_history_api")
if idx != -1:
    print(text[idx:idx+1200])

