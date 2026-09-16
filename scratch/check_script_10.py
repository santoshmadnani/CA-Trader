import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')

print(f"Total scripts: {len(scripts)}")
s10 = scripts[9] # 0-indexed for Script #10
s10_code = s10.string or ''

# Find where s10 is located in the HTML
s10_pos = html.find(s10_code[:60])
line_num = html[:s10_pos].count('\n') + 1
print(f"Script #10 starts at line {line_num}")
print("Head of Script #10:\n", s10_code[:300])
print("\nAround char 18942 of Script #10:")
print(s10_code[max(0, 18900):min(len(s10_code), 19100)])

