with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()
import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup
import subprocess
import tempfile
import os

import re
scripts = list(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>', text, re.DOTALL))
print(f'Total script tags: {len(scripts)}')
with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

for idx, match in enumerate(scripts):
    s = match.group(1)
    start_pos = match.start()
    line_no = text[:start_pos].count('\n') + 1
    print(f'\n--- Script {idx} (starts around line {line_no}, len: {len(s)}) ---')
    # Check for basic JS syntax issues
    # Count braces, parens, brackets
    curly = s.count('{') - s.count('}')
    paren = s.count('(') - s.count(')')
    square = s.count('[') - s.count(']')
    print(f'Curly: {curly}, Paren: {paren}, Square: {square}')
soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')
print(f"Found {len(scripts)} <script> tags.")

# Check if node is available to test JS syntax
has_node = False
try:
    subprocess.run(['node', '-v'], capture_output=True, check=True)
    has_node = True
except Exception:
    pass

print(f"Node.js available: {has_node}")

if has_node:
    for idx, s in enumerate(scripts):
        code = s.string or ''
        if not code.strip():
            continue
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', encoding='utf-8', delete=False) as tf:
            tf.write(code)
            t_path = tf.name
        try:
            r = subprocess.run(['node', '--check', t_path], capture_output=True, text=True, encoding='utf-8')
            if r.returncode != 0:
                print(f"\n[!] Syntax Error in script #{idx+1}:")
                print(r.stderr)
            else:
                print(f"Script #{idx+1} syntax OK ({len(code):,} chars)")
        finally:
            if os.path.exists(t_path):
                os.remove(t_path)
