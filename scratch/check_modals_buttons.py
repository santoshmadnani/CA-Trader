import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("=== 1. Inspect Ask CA AI buttons and modal ===")
for id_name in ['caAiOpen', 'caAiOpenMobile', 'caAiModal', 'aiChatInput', 'aiChatSend', 'caAiClose', 'openCaAiAction']:
    pos = [m.start() for m in re.finditer(r'\b' + id_name + r'\b', text)]
    print(f"{id_name}: {len(pos)} occurrences")
    for p in pos[:3]:
        line = text[:p].count('\n') + 1
        snippet = text[max(0, p-40):min(len(text), p+60)].replace('\n', ' ')
        print(f"  Line {line}: {snippet}")

print("\n=== 2. Inspect CA AI Indicators buttons and panels ===")
for id_name in ['chartAiSuggestBtn', 'chartAiPanel', 'chartAiApplyAllBtn', 'chartAiCloseBtn', 'loadChartAiSuggestions']:
    pos = [m.start() for m in re.finditer(r'\b' + id_name + r'\b', text)]
    print(f"{id_name}: {len(pos)} occurrences")
    for p in pos[:3]:
        line = text[:p].count('\n') + 1
        snippet = text[max(0, p-40):min(len(text), p+60)].replace('\n', ' ')
        print(f"  Line {line}: {snippet}")

print("\n=== 3. Inspect Refresh buttons ===")
for id_name in ['chartRecoRefreshBtn', 'recoSectionRefreshBtn', 'refreshOtherFactorsBtn', 'dashHistoryCard', 'recoClearAllBtn']:
    pos = [m.start() for m in re.finditer(r'\b' + id_name + r'\b', text)]
    print(f"{id_name}: {len(pos)} occurrences")
    for p in pos[:3]:
        line = text[:p].count('\n') + 1
        snippet = text[max(0, p-40):min(len(text), p+60)].replace('\n', ' ')
        print(f"  Line {line}: {snippet}")

print("\n=== 4. Inspect openModal / closeModal implementations ===")
for m in re.finditer(r'function\s+(?:openModal|closeModal)\s*\([^)]*\)\s*\{[^}]*\}', text):
    line = text[:m.start()].count('\n') + 1
    print(f"Line {line}: {m.group(0)}")

