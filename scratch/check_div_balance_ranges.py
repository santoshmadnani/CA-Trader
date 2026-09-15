import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def check_range(start_line, end_line, name):
    depth = 0
    for idx in range(start_line - 1, end_line - 1):
        line = lines[idx]
        # Remove HTML comments to avoid false div counts
        cleaned = re.sub(r'<!--.*?-->', '', line)
        opens = len(re.findall(r'<div\b[^>]*>', cleaned, re.IGNORECASE))
        closes = len(re.findall(r'</div>', cleaned, re.IGNORECASE))
        depth += (opens - closes)
    print(f"[{name}] Lines {start_line}..{end_line}: net depth = {depth}")

check_range(1962, 2116, "panel-dashboard")
check_range(2117, 2299, "panel-charts")
check_range(2300, 2305, "panel-console")
check_range(2306, 2348, "panel-options")

