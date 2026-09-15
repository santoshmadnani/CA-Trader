import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f'Total lines: {len(lines)}')

def find_and_show(keyword, before=3, after=40, label=None):
    idx = content.find(keyword)
    if idx < 0:
        print(f'\nNOT FOUND: {keyword!r}')
        return -1
    ln = content[:idx].count('\n')
    print(f'\n=== {label or keyword!r} at line {ln+1} ===')
    start = max(0, ln - before)
    end = min(len(lines), ln + after)
    for i, l in enumerate(lines[start:end], start+1):
        print(f'{i}: {l[:200]}')
    return ln

# Key sections to inspect
find_and_show('executeOptionSearch', label='executeOptionSearch fn', after=60)
find_and_show('isOptionSymbol', label='isOptionSymbol fn', after=20)
find_and_show('renderChartRecoData', label='renderChartRecoData start', after=50)
find_and_show('updateRecommendationRationale', label='updateReco fn', after=30)
find_and_show('candlestickPatternList', label='candlestickPatternList', before=5, after=60)
find_and_show('patternScanStatus', label='patternScanStatus', before=3, after=60)
find_and_show('loadChartPatterns', label='loadChartPatterns', after=20)
