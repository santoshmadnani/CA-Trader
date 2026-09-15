with open('terminal.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if idx > 3600: break
        l = line.lower()
        if ('position' in l or 'order' in l) and ('id=' in l or 'table' in l):
            print(f"{idx}: {line.strip()[:100]}")

