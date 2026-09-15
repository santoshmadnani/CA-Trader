import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('async function fetchOptionChain')
if pos != -1:
    print(text[pos:pos+4000])

