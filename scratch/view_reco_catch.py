import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('async function updateChartRecoBanner(')
p2 = c.find('catch(e) {', p)
print(c[p2:p2+2500])

