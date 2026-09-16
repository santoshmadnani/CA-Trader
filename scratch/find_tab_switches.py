import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("News loaders:")
for m in re.finditer(r'(function\s+[a-zA-Z0-9_]*News[a-zA-Z0-9_]*\s*\([^)]*\))', text):
    print(" ", m.group(1))

print("\nTab switch locations:")
for m in re.finditer(r'(tab\s*===\s*[\'"][a-z\-]+[\'"]|name\s*===\s*[\'"][a-z\-]+[\'"])', text):
    start = max(0, m.start() - 20)
    end = min(len(text), m.end() + 100)
    print(" ", text[start:end].replace('\n', ' '))

