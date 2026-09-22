import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='replace') as f:
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

for fn in ['renderDualRecommendations', 'loadDualRecommendations', 'fetchDualRecommendations', 'loadRecommendations', 'renderRecommendations', 'updateRecommendationsUI']:
    matches = list(re.finditer(rf'function\s+{fn}|const\s+{fn}|window\.{fn}', text))
    print(f"{fn}: {len(matches)} matches")
    for m in matches:
        line_no = text[:m.start()].count('\n') + 1
        print(f"  Line {line_no}: {text[m.start():m.start()+80]}")
for m in re.finditer(r'(?:loadReco|recoTable|recoHistory|renderReco)[a-zA-Z0-9_]*', text):
    print(m.group(0))
