import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'scratch\ref31\terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

def show_range(start_line, end_line):
    for i, l in enumerate(lines[start_line-1:end_line], start_line):
        print(f'{i}: {l}')

# candlestick pattern list HTML - around line 2340 based on earlier findings
print('=== CANDLESTICK PATTERN SECTION HTML (2320-2370) ===')
show_range(2320, 2370)

print('\n=== loadChartPatterns JS (9715-9725) ===')
show_range(9715, 9725)

# Find the full loadChartPatterns function
idx_fn = content.find('async function loadChartPatterns')
if idx_fn < 0:
    idx_fn = content.find('function loadChartPatterns')
if idx_fn >= 0:
    fn_ln = content[:idx_fn].count('\n') + 1
    print(f'\nloadChartPatterns at line {fn_ln}')
    show_range(fn_ln, fn_ln + 80)

# Find the full loadStructure function
idx_st = content.find('async function loadStructure')
if idx_st < 0:
    idx_st = content.find('function loadStructure')
if idx_st >= 0:
    st_ln = content[:idx_st].count('\n') + 1
    print(f'\nloadStructure at line {st_ln}')
    show_range(st_ln, st_ln + 60)

# Find the candlestickPatternList in loadChartBundle
idx_bund = content.find('candlestickPatternList')
if idx_bund >= 0:
    bund_ln = content[:idx_bund].count('\n') + 1
    print(f'\ncandlestickPatternList first use at line {bund_ln}')
    show_range(max(1, bund_ln - 10), bund_ln + 60)
