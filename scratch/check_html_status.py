with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

checks = {
    'userDisplayName Santosh': 'Santosh</div>' in text,
    'chartRecoAdvisoryBox present': 'id="chartRecoAdvisoryBox"' in text,
    'dashAutoRecoStrip': 'id="dashAutoRecoStrip"' in text,
    'dashRationaleThreeCards': 'id="dashRationaleThreeCards"' in text,
    'chartPriceSensitivityCard': 'id="chartPriceSensitivityCard"' in text,
    'chartSimSlider 0 to 100': 'id="chartSimSlider" min="0" max="100"' in text,
    'compact-date-input': 'compact-date-input' in text,
    'historicalRationaleModal': 'id="historicalRationaleModal"' in text,
    'walletAutoBalance present': 'id="walletAutoBalance"' in text,
    'btnRepSubUserTrades': 'id="btnRepSubUserTrades"' in text,
    'wl-r-btn in html/css': 'wl-r-btn' in text,
    'Show Rationale button': 'Show Rationale' in text,
    '52,051 in text': '52,051' in text,
    '40,920 in text': '40,920' in text,
}
for k, v in checks.items():
    print(f'{k:30}: {v}')

