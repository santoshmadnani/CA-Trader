import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("--- 1. Crosshair & pointermove ---")
idx = text.find("vp.addEventListener('pointermove'")
if idx != -1:
    print(text[idx:idx+800])

print("\n--- 2. Lock Drawings implementation ---")
idx = text.find("btnLockDrawings")
while idx != -1:
    print("Found btnLockDrawings at", idx)
    print(text[max(0, idx-50):min(len(text), idx+400)])
    idx = text.find("btnLockDrawings", idx+1)

print("\n--- 3. Watchlist font style ---")
matches = [m.start() for m in re.finditer(r'\.wl-[a-z0-9_-]+\s*\{[^}]+\}', text)]
for m in matches[:10]:
    print(text[m:m+150])

print("\n--- 4. Quick order modal CSS ---")
idx = text.find("id=\"quickOrderModal\"")
if idx == -1: idx = text.find("quickOrderModal")
if idx != -1:
    print(text[idx:idx+600])

print("\n--- 5. Floating positions widget & movability ---")
idx = text.find("floatingPositionWidget")
if idx != -1:
    print(text[idx:idx+600])

