import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

def show_region(title, search_str, before=100, after=1200):
    idx = app.find(search_str)
    print(f"=== {title} (at {idx}) ===")
    if idx != -1:
        print(app[max(0, idx-before):min(len(app), idx+after)])
    else:
        print("NOT FOUND")
    print("="*60)

show_region("analysis_overall", 'async def analysis_overall(')
show_region("market_macro_factors", '@app.get("/api/market/macro-factors")')
show_region("recommendation_history scrap", "UPDATE recommendations SET status='SCRAPPED'")

