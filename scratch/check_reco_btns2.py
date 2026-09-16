with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_dash = text.find('id="panel-dashboard"')
print(text[idx_dash+6300:idx_dash+7200].encode('ascii', errors='replace').decode('ascii'))

