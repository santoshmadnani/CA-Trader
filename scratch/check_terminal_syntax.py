import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check script tags matching
opens = len(re.findall(r'<script\b', text, re.I))
closes = len(re.findall(r'</script>', text, re.I))
print(f"Scripts: open={opens}, close={closes}")

# Check div tags matching
div_opens = len(re.findall(r'<div\b', text, re.I))
div_closes = len(re.findall(r'</div>', text, re.I))
print(f"Divs: open={div_opens}, close={div_closes}")

# Check notes panel
print("panel-notes present:", 'id="panel-notes"' in text)
# Check notes navtab
print("data-tab='notes' present:", 'data-tab="notes"' in text)
# Check Trade Sentinel modal
print("tradeSentinelModal present:", 'id="tradeSentinelModal"' in text)
# Check zoom buttons
print("btnChartZoomIn present:", 'id="btnChartZoomIn"' in text)
# Check chartFullscreenToolbarBtn
print("chartFullscreenToolbarBtn present:", 'id="chartFullscreenToolbarBtn"' in text)
# Check Save to History button
print("chartRecoSaveHistBtn present:", 'id="chartRecoSaveHistBtn"' in text)
# Check autoRecoTimerBadge
print("autoRecoTimerBadge present:", 'id="autoRecoTimerBadge"' in text)

