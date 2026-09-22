import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()
    lines = f.readlines()

idx = text.find('id="notificationBtn"')
if idx != -1:
    print(text[idx-200:idx+400])

for i in range(3130, 3195):
    print(f"{i+1}: {lines[i]}", end='')
