import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

target_tick = """        if(pe){
          pe.textContent=fmtMoney(pnl);
          pe.className='pos-pnl '+(pnl>=0?'cell-up':'cell-down');
        }
      }
    });"""

replacement_tick = """        if(pe){
          pe.textContent=fmtMoney(pnl);
          pe.className='pos-pnl '+(pnl>=0?'cell-up':'cell-down');
        }
        // Real-time tick update for CA AI Advisor (Release 51)
        if(window.activeAdvisorPosition && String(window.activeAdvisorPosition.symbol||'').toUpperCase() === key){
          window.activeAdvisorPosition.ltp = ltp;
          window.activeAdvisorPosition.unrealized_pnl = pnl;
          const cpTag1 = document.getElementById('fpCurrentPnlTag');
          if(cpTag1){
            cpTag1.textContent = 'Now: ' + (pnl >= 0 ? '+' : '') + fmtMoney(pnl);
            cpTag1.className = 'tag ' + (pnl >= 0 ? 'buy' : 'sell');
          }
          const cpTag2 = document.getElementById('ordersCurrentPnlTag');
          if(cpTag2){
            cpTag2.textContent = 'Now: ' + (pnl >= 0 ? '+' : '') + fmtMoney(pnl);
            cpTag2.className = 'tag ' + (pnl >= 0 ? 'buy' : 'sell');
          }
          const entryLtpEl = document.getElementById('ordersTradeEntryLtp');
          if(entryLtpEl){
            entryLtpEl.textContent = `₹${fmt(avg)} / ₹${fmt(ltp)}`;
          }
        }
      }
    });"""

if target_tick in text:
    text = text.replace(target_tick, replacement_tick, 1)
    print('[OK] Added live tick hook to activeAdvisorPosition')
    with open('terminal.html', 'w', encoding='utf-8') as f:
        f.write(text)
else:
    print('[FAIL] target_tick not found')

print('Done')

