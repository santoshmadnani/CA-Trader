with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target1 = "if(fpThetaBurnEl){\n    fpThetaBurnEl.textContent = '-₹' + fmt(tb) + '/hr';\n  }"
repl1 = "if(fpThetaBurnEl){\n    fpThetaBurnEl.textContent = tb > 0 ? ('-₹' + fmt(tb) + '/hr') : (adv.has_position ? '₹0.00/hr' : '—');\n  }"

target2 = "if(ordThetaBurnEl){\n    ordThetaBurnEl.textContent = '-₹' + fmt(tb) + '/hr';\n  }"
repl2 = "if(ordThetaBurnEl){\n    ordThetaBurnEl.textContent = tb > 0 ? ('-₹' + fmt(tb) + '/hr') : (adv.has_position ? '₹0.00/hr' : '—');\n  }"

if target1 in text:
    text = text.replace(target1, repl1, 1)
    print("Patched target1")
else:
    print("target1 not found")

if target2 in text:
    text = text.replace(target2, repl2, 1)
    print("Patched target2")
else:
    print("target2 not found")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("terminal.html updated")

