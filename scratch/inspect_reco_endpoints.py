import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("save_recommendation_to_history_api")
if idx != -1:
    print(text[idx-50:idx+800])
else:
    print("save_recommendation_to_history_api not found")

idx2 = text.find("async def on_demand_recommendation")
if idx2 != -1:
    print(text[idx2-50:idx2+800])

