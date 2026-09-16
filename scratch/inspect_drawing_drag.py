import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("state.selectedDrawingIdx = (state.drawingsLocked ? -1 : hit);")
if idx != -1:
    print(text[idx-400:idx+800])

