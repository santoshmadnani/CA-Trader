with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("function yFromPrice")
if idx != -1:
    print(text[idx-50:idx+400])

