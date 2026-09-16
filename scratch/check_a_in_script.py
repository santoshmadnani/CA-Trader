import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

idx = html.find('async function loadChartAiSuggestions')
script_start = html.rfind('<script', 0, idx)
print(html[script_start:script_start+500])

# Check if 'const A =' or 'function A(' exists in this script
script_end = html.find('</script>', idx)
script_text = html[script_start:script_end]
print("Is 'function A' in script?", 'function A' in script_text or 'const A' in script_text or 'let A' in script_text or 'var A' in script_text)
print("Is 'function api' in script?", 'function api' in script_text or 'const api' in script_text or 'let api' in script_text)

