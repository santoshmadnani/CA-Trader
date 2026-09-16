with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('dashConfluenceTableBody')
print("dashConfluenceTableBody at:", idx)
if idx != -1:
    print(text[idx-600:idx+600].encode('ascii', errors='replace').decode('ascii'))

