import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')

def show_at(keyword, before=5, after=60):
    idx = content.find(keyword)
    if idx < 0:
        print(f'NOT FOUND: {repr(keyword)}')
        return -1
    ln = content[:idx].count('\n')
    print(f'\n=== {repr(keyword)} at line {ln+1} ===')
    for i, l in enumerate(lines[max(0,ln-before):ln+after], max(0,ln-before)+1):
        print(f'{i}: {l[:250]}')
    return ln

# Find the reco option search box in HTML
show_at('recoOptionSearch', before=5, after=40)
show_at('option-search', before=5, after=40)
show_at('chartRecoOptSearch', before=5, after=40)
show_at('chartRecoAction', before=5, after=40)
show_at('renderChartRecoData', before=3, after=120)
