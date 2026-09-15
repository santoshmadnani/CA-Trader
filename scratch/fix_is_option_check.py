# -*- coding: utf-8 -*-

with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

p_find = c.find('const isAlreadyOption =')
p_end = c.find('if (!isAlreadyOption) {', p_find)

new_code = """function isOptionSymbol(s){
      if(!s) return false;
      const str = String(s).toUpperCase().trim();
      return str.endsWith(' CE') || str.endsWith(' PE') || str.endsWith('CE') || str.endsWith('PE') || str.includes(' CE ') || str.includes(' PE ');
    }
    const isAlreadyOption = (rec?.instrument?.kind === 'OPTION') ||
                            isOptionSymbol(rec?.display_symbol) ||
                            isOptionSymbol(rec?.symbol) ||
                            isOptionSymbol(sym);

    """

c = c[:p_find] + new_code + c[p_end:]

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("terminal.html: Fixed isOptionSymbol and isAlreadyOption.")

