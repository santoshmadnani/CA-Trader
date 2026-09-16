with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("Length of terminal.html:", len(text))

# Check navtabs
idx_nav = text.find('id="navtabs"')
print("navtabs found at:", idx_nav)

# Check panel-dashboard
idx_dash = text.find('id="panel-dashboard"')
print("panel-dashboard found at:", idx_dash)

# Check panel-reco
idx_reco = text.find('id="panel-reco"')
print("panel-reco found at:", idx_reco)

# Check where panels end
idx_end_panels = text.find('<!-- Floating / Modals')
print("Modals start at:", idx_end_panels)

