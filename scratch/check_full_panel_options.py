import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

start = text.find('id="panel-options"')
end = text.find('<!-- ============', start + 20)
if end == -1:
    end = text.find('id="panel-', start + 20)
print(text[start:end])

