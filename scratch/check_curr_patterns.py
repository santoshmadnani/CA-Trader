import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

for fn in ['formatPatternTimeRange', 'bindPatternClicks', 'highlightedPattern', 'patternList', 'chartPatternList']:
    idx = c.find(fn)
    print(f"{fn} in terminal.html: {idx}")

