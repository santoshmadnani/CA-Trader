import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')
s10_code = scripts[9].string or ''

idx = 18942
print("Char 18942 region:")
print(s10_code[max(0, idx-200):min(len(s10_code), idx+200)])

# Let's count braces by line in s10
lines = s10_code.splitlines()
depth = 0
for i, line in enumerate(lines):
    opens = line.count('{')
    closes = line.count('}')
    depth += opens - closes
    if depth < 0 or i > len(lines) - 30:
        print(f"L{i+1:3d} (depth={depth:+2d}): {line}")

