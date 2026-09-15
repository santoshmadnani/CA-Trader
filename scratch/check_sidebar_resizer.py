import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find("localStorage.getItem('ca_sidebar_width')")
print(text[pos-300:pos+500])

