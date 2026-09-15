import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('host.innerHTML = `\n        <table')
if pos == -1:
    pos = text.find('host.innerHTML = `')
print(text[pos:pos+1500])
