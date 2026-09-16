with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<div class="top-icon-wrap"><button class="icon-btn" id="notificationBtn"'
btn_html = '<button class="btn small gold" id="turboLoadBtn" title="⚡ Turbo Refresh (Immediate instant live reload of all data feeds)" style="display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:3px 8px;font-weight:600;margin-right:6px;">⚡ Turbo Refresh</button>\n    <div class="top-icon-wrap"><button class="icon-btn" id="notificationBtn"'

if 'id="turboLoadBtn"' not in text:
    if target in text:
        text = text.replace(target, btn_html, 1)
        print("Injected turboLoadBtn")
    else:
        print("target not found")
else:
    print("turboLoadBtn already present")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated terminal.html")

