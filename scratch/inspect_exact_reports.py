import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('data-tab="reports"')
if idx != -1:
    tag_start = text.rfind('<div class="navtab"', 0, idx)
    tag_end = text.find('</div>', idx) + 6
    print("Exact reports navtab snippet:")
    print(repr(text[tag_start:tag_end]))

