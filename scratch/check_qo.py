with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="quickOrderModal"')
print(text[idx-50:idx+1500].encode('ascii', errors='replace').decode('ascii'))

