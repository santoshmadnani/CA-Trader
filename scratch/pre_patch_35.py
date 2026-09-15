import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')

def show_at(keyword, before=3, after=50, label=None):
    idx = content.find(keyword)
    if idx < 0:
        print(f'NOT FOUND: {keyword}')
        return -1
    ln = content[:idx].count('\n')
    print(f'\n=== {label or keyword} at line {ln+1} ===')
    for i, l in enumerate(lines[max(0,ln-before):ln+after], max(0,ln-before)+1):
        print(f'{i}: {l[:220]}')
    return ln

show_at("$('patternList').innerHTML", before=5, after=80, label='patternList render')
show_at('async function loadChartBundle', before=2, after=60, label='loadChartBundle')
show_at('executeOptionSearch', before=5, after=100, label='executeOptionSearch')
show_at('updateRecommendationRationale', before=3, after=150, label='updateRecommendationRationale fn def')
