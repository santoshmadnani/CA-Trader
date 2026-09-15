with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 175097
print(text[idx-200:idx+400])

