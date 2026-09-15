import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts_with_pos = []
for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL):
    scripts_with_pos.append((m.start(), m.end(), m.group(1)))

print(f"Total scripts: {len(scripts_with_pos)}")

for idx, (sp, ep, s) in enumerate(scripts_with_pos):
    line_num = html[:sp].count('\n') + 1
    ob = s.count('{')
    cb = s.count('}')
    op = s.count('(')
    cp = s.count(')')
    oq = s.count('[')
    cq = s.count(']')
    issues = []
    if ob != cb: issues.append(f"BRACE MISMATCH {ob}/{cb} diff={ob-cb}")
    if op != cp: issues.append(f"PAREN MISMATCH {op}/{cp} diff={op-cp}")
    if oq != cq: issues.append(f"BRACKET MISMATCH {oq}/{cq} diff={oq-cq}")
    has_wl = 'W0(' in s or 'loadWatchlist' in s
    print(f"Script {idx}: line={line_num}, len={len(s)}, watchlist={has_wl} {'*** '+str(issues)+' ***' if issues else 'OK'}")
    if issues:
        print(f"  START: {repr(s[:100])}")
        print(f"  END:   {repr(s[-100:])}")

