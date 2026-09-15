# -*- coding: utf-8 -*-
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("=== NAV TABS ===")
for m in re.finditer(r'<div[^>]+data-tab=[\'"][^\'"]+[\'"][^>]*>', text):
    print(m.group(0))

print("\n=== TIMEOUT / TURBO LOAD OCCURRENCES ===")
for m in re.finditer(r'turbo|timeout|Request timed out', text, re.IGNORECASE):
    line = text[:m.start()].count('\n') + 1
    snippet = text[max(0, m.start()-40):min(len(text), m.end()+60)].replace('\n', ' ')
    print(f"L{line}: {snippet}")

print("\n=== CA AI PANEL / MOBILE OCCURRENCES ===")
for m in re.finditer(r'chartAiPanel|chartAiSuggestBtn|chart-ai', text):
    line = text[:m.start()].count('\n') + 1
    print(f"L{line}: {text[m.start():m.start()+80].replace(chr(10), ' ')}")

print("\n=== PATTERN OCCURRENCES ===")
for m in re.finditer(r'scanPatterns|pattern-card|window\.__caPatterns', text):
    line = text[:m.start()].count('\n') + 1
    print(f"L{line}: {text[m.start():m.start()+80].replace(chr(10), ' ')}")
