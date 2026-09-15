import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find("ca_card_layouts")
while pos != -1:
    print(text[pos-200:pos+400])
    print("="*40)
    pos = text.find("ca_card_layouts", pos+1)

