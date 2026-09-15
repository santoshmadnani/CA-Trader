import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html.bak', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('function formatPatternTimeRange')
print("formatPatternTimeRange in bak at", p)
print(c[p:p+1200])

# Check bindPatternClicks in bak
p2 = c.find('function bindPatternClicks')
print("\nbindPatternClicks in bak at", p2)
print(c[p2:p2+2500])

