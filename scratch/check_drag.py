with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = "state.drag"
pos = 0
while True:
    idx = text.find(target, pos)
    if idx == -1: break
    print(f"--- match at {idx} ---")
    print(text[max(0, idx-30):min(len(text), idx+300)])
    pos = idx + len(target) + 200

