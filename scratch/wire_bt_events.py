# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

target = "$('btStepBtn')?.addEventListener('click', stepBacktestForward);"
replacement = target + """
    $('btStepBackBtn')?.addEventListener('click', () => {
      if(btState.currentIndex > 0){
        btState.currentIndex--;
        renderBacktestStep(false);
      }
    });
    $('btOptionContractSelect')?.addEventListener('change', (e) => {
      const parts = (e.target.value || '').split('|');
      btSelectedOptionStrike = Number(parts[0]);
      btSelectedOptionType = parts[1] || 'CE';
      updateBacktestOptionHeader();
      drawBacktestOptionCanvas();
    });"""

if target in c and "btStepBackBtn" not in c.split(target)[1][:300]:
    c = c.replace(target, replacement, 1)
    with open('terminal.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Wired btStepBackBtn and btOptionContractSelect successfully!")
else:
    print("Already wired or target not found")

