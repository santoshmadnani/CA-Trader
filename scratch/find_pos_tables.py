with open('terminal.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'data-tab="positions"' in line or 'data-tab="orders"' in line or 'positionsTable' in line or 'ordersTable' in line:
            print(f"{idx}: {line.strip()[:80]}")

