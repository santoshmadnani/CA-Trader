import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')

def show_at(keyword, before=3, after=80):
    idx = content.find(keyword)
    if idx < 0:
        print(f'NOT FOUND: {repr(keyword)}')
        return -1
    ln = content[:idx].count('\n')
    print(f'\n=== {repr(keyword)} at line {ln+1} ===')
    for i, l in enumerate(lines[max(0,ln-before):ln+after], max(0,ln-before)+1):
        print(f'{i}: {l[:300]}')
    return ln

# Find executeOptionSearch
show_at('function executeOptionSearch', before=2, after=80)

# Find renderChartRecoData  
show_at('function renderChartRecoData', before=2, after=80)

# Find updateRecommendationRationale function definition
show_at('function updateRecommendationRationale', before=2, after=120)

# find fetchOptionChain
show_at('async function fetchOptionChain', before=2, after=60)
