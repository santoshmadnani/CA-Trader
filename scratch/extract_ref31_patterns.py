import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'scratch\ref31\terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

def show_around(keyword, before=5, after=120):
    idx = content.find(keyword)
    if idx < 0:
        print(f'NOT FOUND: {keyword}')
        return
    ln = content[:idx].count('\n')
    start = max(0, ln - before)
    end = min(len(lines), ln + after)
    print(f'\n=== {keyword!r} at line {ln+1} ===')
    for i, l in enumerate(lines[start:end], start+1):
        print(f'{i}: {l}')

show_around('id="patternList"', before=3, after=100)
show_around('candlestickPatternList', before=3, after=60)
show_around('chartPatternList', before=3, after=30)
show_around('structureBox', before=3, after=30)
show_around('formatPatternTimeRange', before=2, after=20)
show_around('bindPatternClicks', before=2, after=30)
