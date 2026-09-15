import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')

def show_at(keyword, before=5, after=40):
    idx = content.find(keyword)
    if idx < 0:
        print(f'NOT FOUND: {repr(keyword)}')
        return -1
    ln = content[:idx].count('\n')
    print(f'\n=== {repr(keyword)} at line {ln+1} ===')
    for i, l in enumerate(lines[max(0,ln-before):ln+after], max(0,ln-before)+1):
        print(f'{i}: {l[:300]}')
    return ln

# Find the HTML element for chartRecoOptionSearch
show_at('chartRecoOptionSearch', before=8, after=20)
show_at('chartRecoOptionSuggestions', before=3, after=20)

# Also check what updateRecommendationRationale looks like at start
show_at('function updateRecommendationRationale', before=3, after=20)
