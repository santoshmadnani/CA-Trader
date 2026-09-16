with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text_app = f.read()

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text_term = f.read()

import re
print("app.py failed trade matches:")
for m in re.finditer(r'(?:failed|loss|review|post.?trade|trade.?analysis)', text_app, re.I):
    start = max(0, m.start() - 60)
    end = min(len(text_app), m.end() + 60)
    snippet = text_app[start:end].replace('\n', ' ')
    if any(k in snippet.lower() for k in ('ai', 'reason', 'analysis', 'explain', 'why')):
        print(" APP:", snippet[:120])

print("terminal.html failed trade matches:")
for m in re.finditer(r'(?:failed|loss|review|post.?trade|audit)', text_term, re.I):
    start = max(0, m.start() - 60)
    end = min(len(text_term), m.end() + 60)
    snippet = text_term[start:end].replace('\n', ' ')
    if any(k in snippet.lower() for k in ('ai', 'reason', 'modal', 'explain')):
        print(" TERM:", snippet[:120])

