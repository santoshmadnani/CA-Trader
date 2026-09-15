with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = "button!==0"
idx = text.find(target)
if idx != -1:
    print(text[idx-50:idx+2500])

