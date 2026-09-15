with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Fix 1: in Script 1, remove unclosed lines 3845-3848
bad_block_1 = """document.querySelectorAll('.navtab').forEach(t=>{
  t.addEventListener('click', (e)=>{
    const targetTab = t.dataset.tab || e.target.closest('.navtab')?.dataset.tab;
    if(targetTab) showTab(targetTab);
['click', 'pointerdown'].forEach(evtName => {"""

good_block_1 = """['click', 'pointerdown'].forEach(evtName => {"""

assert bad_block_1 in text, "bad_block_1 not found!"
text = text.replace(bad_block_1, good_block_1, 1)

# Fix 2: in Script 2, remove lines 8149-8150
bad_block_2 = """  window.CATraderAnalysis = Object
... [truncated for diff preview]
  window.CATraderAnalysis = Object.assign(window.CATraderAnalysis || {}, {"""

good_block_2 = """  window.CATraderAnalysis = Object.assign(window.CATraderAnalysis || {}, {"""

assert bad_block_2 in text, "bad_block_2 not found!"
text = text.replace(bad_block_2, good_block_2, 1)

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed syntax errors in terminal.html successfully!")

