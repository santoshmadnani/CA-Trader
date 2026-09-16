import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="notificationBadge"')
if idx != -1:
    print(repr(text[idx-250:idx+50]))

