with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
scripts = list(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>', text, re.DOTALL))
s1 = scripts[1].group(1)
start_line = text[:scripts[1].start()].count('\n') + 1

# Let's use a real JS parser via node if possible, or python slimit / esprima if installed, or python tokenizing
# Let's see what python packages we have:
try:
    import esprima
    print('esprima available!')
except:
    print('esprima not available')

