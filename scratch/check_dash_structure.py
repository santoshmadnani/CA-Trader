import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

start = html.find('id="panel-dashboard"')
end = html.find('id="panel-charts"')
dashboard_html = html[start:end]

# Find all cards inside panel-dashboard
for m in re.finditer(r'<div[^>]+id=["\']([^"\']+)["\'][^>]*>', dashboard_html):
    print("Element id:", m.group(1))

# Also search for tab navigation in sidebar or topbar that switches to history or reco
for m in re.finditer(r'data-tab=["\']([^"\']+)["\']', html):
    print("Nav item data-tab:", m.group(1))

