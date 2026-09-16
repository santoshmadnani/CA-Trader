import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check position of #positionAdvisoryBanner
idx1 = text.find('id="positionAdvisoryBanner"')
print('idx1 positionAdvisoryBanner:', idx1)
end_banner = text.find('</div>\n\n      <!-- Positions Section', idx1)
print('end_banner:', end_banner)
print(text[end_banner-50:end_banner+100])

# Check position of toggleFloatingPositionsWidget
idx2 = text.find('window.toggleFloatingPositionsWidget = function')
print('idx2 toggleFloatingPositionsWidget:', idx2)

# Check position of renderPositionAdvisorData
idx3 = text.find('function renderPositionAdvisorData(adv)')
print('idx3 renderPositionAdvisorData:', idx3)

