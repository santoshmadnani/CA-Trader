import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'@app\.get\(["\']/api/news', app):
    idx = m.start()
    print("Match at", idx, ":")
    print(app[idx:idx+1500])
    print("="*60)

for m in re.finditer(r'def (?:fetch_news|recommendation_news_evidence|get_news)', app):
    idx = m.start()
    print("Match at", idx, ":")
    print(app[idx:idx+1200])
    print("="*60)

