with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_charts = text.find('id="panel-charts"')
idx_options = text.find('id="panel-options"')
print("idx_charts:", idx_charts)
print("idx_options:", idx_options)

chunk = text[idx_charts:idx_options]
print(f"Length of chunk between panel-charts and panel-options: {len(chunk):,} characters")

# Count open vs close divs in this chunk!
open_divs = len([m for m in chunk.split('<div')]) - 1
close_divs = len([m for m in chunk.split('</div')]) - 1
print(f"open_divs in chunk: {open_divs}, close_divs in chunk: {close_divs}")
print(f"Net unclosed divs: {open_divs - close_divs}")

