with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('Loading live option chain')
while pos != -1:
    print("Found at", pos)
    print(text[max(0, pos-200):pos+400])
    pos = text.find('Loading live option chain', pos+1)
