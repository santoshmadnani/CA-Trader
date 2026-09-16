import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's find renderCandles or drawCandles or chart drawing function
print("--- Drawing functions ---")
for m in re.finditer(r'(function\s+(?:render|draw)[a-zA-Z0-9_]*Candles?\s*\([^)]*\))', text):
    print(m.group(1))

# Let's search for panX
print("\n--- panX usage ---")
for m in re.finditer(r'([^\n]*panX[^\n]*)', text):
    line_num = text[:m.start()].count('\n') + 1
    print(f"Line {line_num}: {m.group(1).strip()[:100]}")

# Let's search for right margin or right padding on chart
print("\n--- right gutter / margin ---")
for m in re.finditer(r'([^\n]*(?:rightPad|marginRight|priceAxisWidth|gutterRight|chartWidth|rightOffset)[^\n]*)', text, re.IGNORECASE):
    line_num = text[:m.start()].count('\n') + 1
    print(f"Line {line_num}: {m.group(1).strip()[:100]}")

