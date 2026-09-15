with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('async function loadOptions')
if pos != -1:
    print(text[pos:pos+3000])
else:
    print("loadOptions not found")
