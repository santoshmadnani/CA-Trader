import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target_tr = """                return `
                  <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}" data-avg="${avgPrice}" data-qty="${finalDispQty}" data-side="${esc(x.side||'BUY')}" data-is-open="${isOpen ? 'true' : 'false'}">"""

replacement_tr = """                return `
                  <tr data-pos-symbol="${esc(x.symbol)}" data-pos-id="${esc(x.id)}" data-avg="${avgPrice}" data-qty="${finalDispQty}" data-side="${esc(x.side||'BUY')}" data-is-open="${isOpen ? 'true' : 'false'}" style="cursor:pointer;" onclick="window.selectAdvisorPositionById && window.selectAdvisorPositionById('${esc(x.id)}')">"""

if target_tr in text:
    text = text.replace(target_tr, replacement_tr, 1)
    print('[OK] Injected onclick into renderPositionsTable tr')
else:
    print('[WARN] target_tr not matched exactly, checking...')

target_fn = "window.toggleOrdersAdvisorChat = function(){"
replacement_fn = """window.selectAdvisorPositionById = function(posId){
  if(!posId) return;
  const snapshot = window.__CA_PORTFOLIO_SNAPSHOT?.positions || [];
  const pos = snapshot.find(p => String(p.id) === String(posId));
  if(pos){
    activeAdvisorPosition = pos;
    refreshPositionAdvisor();
  }
};

window.toggleOrdersAdvisorChat = function(){"""

if target_fn in text:
    text = text.replace(target_fn, replacement_fn, 1)
    print('[OK] Added window.selectAdvisorPositionById')
else:
    print('[WARN] target_fn not found')

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Done')

