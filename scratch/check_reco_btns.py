with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_dash = text.find('id="panel-dashboard"')
print(text[idx_dash+5000:idx_dash+7000].encode('ascii', errors='replace').decode('ascii'))

