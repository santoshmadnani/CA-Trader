with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('function fetchOptionChain')
if pos != -1:
    print(text[pos:pos+2500])
else:
    pos2 = text.find('loadOptions')
    print("loadOptions at", pos2)
    print(text[pos2:pos2+2500])

