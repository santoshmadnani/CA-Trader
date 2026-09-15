with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx1 = text.find('@app.get("/api/orders")')
print('=== /api/orders in app.py ===')
print(text[idx1:idx1+1000])

idx2 = text.find('@app.get("/api/positions")')
print('=== /api/positions in app.py ===')
print(text[idx2:idx2+1000])

