import zipfile, sys
sys.stdout.reconfigure(encoding='utf-8')

with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    text = z.read('terminal.html').decode('utf-8', errors='ignore')

p_summary = text.find('id="masterSummaryCard"')
p_shell = text.find('id="chartShell"')
chunk1 = text[text.rfind('<div', 0, p_summary):text.rfind('<div', 0, p_shell)]

p_greeks = text.find('id="chartGreeksGrid"')
p_candlepats = text.find('id="candlePatternCardTitle"')
p_candlepats_card = text.rfind('<div class="card"', 0, p_candlepats)
chunk2 = text[text.rfind('<div class="grid', 0, p_greeks):p_candlepats_card]

print("Chunk 1 length:", len(chunk1))
print("Chunk 2 length:", len(chunk2))

# Test removing from panel-charts
modified = text.replace(chunk1, '').replace(chunk2, '')

# Check div balance of panel-charts in modified
start_charts = modified.find('id="panel-charts"')
end_charts = modified.find('id="panel-console"')
charts_html = modified[start_charts:end_charts]

import re
opens = len(re.findall(r'<div\b[^>]*>', charts_html, re.I))
closes = len(re.findall(r'</div>', charts_html, re.I))
print(f"Modified panel-charts: opens={opens}, closes={closes}, diff={opens-closes}")
