with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Find all script tags
scripts = list(re.finditer(r'<script\b[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE))
print(f"Total script tags: {len(scripts)}")

targets = [
    'caAiOpen',
    'caAiOpenMobile',
    'caAiModal',
    'chartAiSuggestBtn',
    'btnOpenIndicatorsModal',
    'chartRecoRefreshBtn',
    'loadChartAiSuggestions',
    'openModal',
    'sendAiChat',
    'updateChartRecoBanner'
]

for s_idx, s in enumerate(scripts):
    s_content = s.group(1)
    s_start_line = text.count('\n', 0, s.start()) + 1
    s_end_line = text.count('\n', 0, s.end()) + 1
    found = [t for t in targets if t in s_content]
    if found:
        print(f"Script #{s_idx+1} (lines {s_start_line} - {s_end_line}): contains {found}")


