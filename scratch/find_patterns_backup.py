import sys

sys.stdout.reconfigure(encoding='utf-8')

for fname in ['terminal.html.bak', 'terminal_backup.html']:
    try:
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
        print(f"=== {fname} ===")
        import re
        for m in re.finditer(r'(candlestick|chart-pattern|pattern-card|patternList)', c, re.I):
            idx = m.start()
            print(f"Match {m.group(0)} at {idx}:")
            print(c[max(0, idx-100):min(len(c), idx+300)])
            print("-" * 40)
            if idx > 300000:
                break
    except Exception as e:
        print(fname, e)

