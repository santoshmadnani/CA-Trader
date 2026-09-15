with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos_charts = text.find('id="panel-charts"')
pos_console = text.find('id="panel-console"')
print("Charts panel length:", pos_console - pos_charts)
print(text[pos_charts:pos_charts+500])
print("...")
print(text[pos_console-300:pos_console])

