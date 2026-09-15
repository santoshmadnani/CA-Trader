with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

for route in ['/force-login', '/api/auth/login']:
    idx = text.find(f'"{route}"')
    if idx == -1: idx = text.find(f"'{route}'")
    if idx != -1:
        print('=== ROUTE', route, '===')
        print(text[idx-20:idx+600])

