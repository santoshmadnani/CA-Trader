import zipfile, re

BASE = r'c:\Users\SantoshMadnani\Documents\CA_Trader\7'
ZIP42 = r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip'

with zipfile.ZipFile(ZIP42) as z:
    content = z.read('terminal.html').decode('utf-8', errors='ignore')

# Exact slice for panel-reco
p_reco = content.find('id="panel-reco"')
p_news = content.find('id="panel-news"')
print("Slice for panel-reco:", p_reco, "to", p_news)
panel_reco_chunk = content[content.rfind('<div class="panel"', 0, p_reco):content.rfind('<div class="panel"', 0, p_news)]
print("Starts with:", repr(panel_reco_chunk[:60]))
print("Ends with:", repr(panel_reco_chunk[-60:]))

# Exact slice for panel-auto
p_auto = content.find('id="panel-auto"')
p_rep = content.find('id="panel-reports"')
print("\nSlice for panel-auto:", p_auto, "to", p_rep)
panel_auto_chunk = content[content.rfind('<div class="panel"', 0, p_auto):content.rfind('<div class="panel"', 0, p_rep)]
print("Starts with:", repr(panel_auto_chunk[:60]))
print("Ends with:", repr(panel_auto_chunk[-60:]))

