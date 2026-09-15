with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = "panY"
pos = 0
while True:
    idx = text.find(target, pos)
    if idx == -1: break
    print(f"--- panY at {idx} ---")
    print(text[max(0, idx-30):min(len(text), idx+200)])
    pos = idx + len(target) + 10

