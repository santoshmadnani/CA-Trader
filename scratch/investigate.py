import sys, re
sys.stdout.reconfigure(encoding='utf-8')

def investigate():
    with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()
    with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
        app = f.read()

    print("=== terminal.html tabs check ===")
    for m in re.finditer(r'data-tab=["\']([^"\']+)["\']', html):
        print("Tab:", m.group(1))

    print("\n=== Recommendation History in terminal.html ===")
    for m in re.finditer(r'def loadRecommendationHistory|async function loadRecommendationHistory|function loadRecommendationHistory', html):
        idx = m.start()
        print(html[idx:idx+1200])
        print("="*40)

    print("\n=== Recommendation endpoints in app.py ===")
    for m in re.finditer(r'@app\.(?:get|post|route)\([^\)]*recommendation[^\)]*\)', app):
        idx = m.start()
        print(app[idx:idx+600])
        print("="*40)

    print("\n=== Search for recommendations table in app.py ===")
    for m in re.finditer(r'CREATE TABLE IF NOT EXISTS recommendations|INSERT INTO recommendations|FROM recommendations', app):
        idx = m.start()
        print(app[max(0, idx-50):min(len(app), idx+300)])
        print("="*40)

    print("\n=== Check what #history contains in terminal.html ===")
    # Look for tab panel id="history" or id="reco"
    for m in re.finditer(r'<div[^>]+id=["\'](?:history|reco)["\'][^>]*>', html):
        idx = m.start()
        print(html[idx:idx+800])
        print("="*40)

if __name__ == '__main__':
    investigate()

