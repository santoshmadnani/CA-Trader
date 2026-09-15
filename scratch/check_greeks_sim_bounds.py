import zipfile

with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    text = z.read('terminal.html').decode('utf-8', errors='ignore')

p_greeks = text.find('id="chartGreeksGrid"')
p_sim = text.find('id="chartPriceSensitivityCard"')
print("chartGreeksGrid:", p_greeks)
print("chartPriceSensitivityCard:", p_sim)

# What card wraps chartGreeksGrid and chartPriceSensitivityCard?
card_greeks = text.rfind('<div class="grid', 0, p_greeks)
card_sim = text.rfind('<div class="card"', 0, p_sim)
sim_end = text.find('<!-- Candlestick Pattern / Trend Highlight', p_sim)
print("card_greeks:", card_greeks)
print("card_sim:", card_sim)
print("sim_end:", sim_end)
print("After sim:", repr(text[sim_end:sim_end+80]))

