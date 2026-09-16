with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = re.findall(r'(?:fail|loss|audit|why|posttrade|review|retrospective|post_trade)[a-zA-Z0-9_]*', text, re.I)
print("Unique words in terminal.html:", set(matches))

# search for modal or card showing trade analysis or why trade closed
for m in re.finditer(r'id=["\']([a-zA-Z0-9_-]*(?:trade|analysis|audit|modal)[a-zA-Z0-9_-]*)["\']', text, re.I):
    print("Found ID:", m.group(1))

