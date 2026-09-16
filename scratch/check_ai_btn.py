import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

# Find JS for chartAiSuggestBtn
for m in re.finditer(r'chartAiSuggestBtn', html):
    idx = m.start()
    print("JS for chartAiSuggestBtn at", idx)
    print(html[max(0, idx-50):min(len(html), idx+800)])
    print("="*60)

# Check CSS for .ca-chart-ai-panel
for m in re.finditer(r'\.ca-chart-ai-panel', html):
    idx = m.start()
    print("CSS for ca-chart-ai-panel at", idx)
    print(html[max(0, idx-50):min(len(html), idx+400)])
    print("="*60)

