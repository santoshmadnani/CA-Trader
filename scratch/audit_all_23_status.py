# -*- coding: utf-8 -*-
from pathlib import Path

app_code = Path("app.py").read_text(encoding="utf-8")
term_code = Path("terminal.html").read_text(encoding="utf-8")

items = {}

# 1. Bell & profile dropdown z-index & overflow
items[1] = ("z-index: 2500" in term_code or "z-index: 2000" in term_code) and "overflow: visible" in term_code

# 2. Recommendation above chart levels & updates with watchlist
items[2] = "chartRecoEntry" in term_code and "chartRecoSl" in term_code and "chartRecoTgt" in term_code and "updateChartRecoBanner" in term_code

# 3. Pattern card click shows candle time & highlights on chart
items[3] = "state.highlightedPattern" in term_code and "formatPatternTimeRange" in term_code

# 4. Trend strictly 3 states with reasons
items[4] = "Sideways Market" in term_code and "Higher Highs & Higher Lows" in term_code

# 5. Backtesting timeframe and from/to datetime graceful defaults
items[5] = "btFromDateTime" in term_code and "btToDateTime" in term_code and "btTfSelect" in term_code

# 6. Tooltip/comment box indicator/diagram based
items[6] = "showDrawingTooltip" in term_code and "getIndicatorSignal" in term_code

# 7. Move drawings
items[7] = "moveDrawing" in term_code and "state.dragDrawing" in term_code and "drawingHit" in term_code

# 8. Trend line dotted moving with cursor + infinite
items[8] = "trend_ray" in term_code and "state.cursorPoint" in term_code

# 9. Applied indicators hover highlight & click modal
items[9] = "state.highlightIndicatorIdx" in term_code and "isHighlighted" in term_code

# 10. Audit indicators calculations
items[10] = "supertrendSeries" in term_code and "keltnerSeries" in term_code and "atrSeries" in term_code

# 11. RSI isolated box with splitter
items[11] = "updateOscSplitterPosition" in term_code and "chartOscSplitter" in term_code

# 12. Expiry dropdown contrast
items[12] = "optionExpiry" in term_code and "color: var(--text)" in term_code

# 13. MCX option chain autocomplete
items[13] = "mcxSymbolSuggestions" in term_code and "setupMcxAutocomplete" in term_code

# 14. Recommendations options focus & stop duplicates
items[14] = "on-demand" in app_code and "last_ts" in app_code

# 15. Editable max profit / max loss inputs
items[15] = "recoMaxProfit" in term_code and "recoMaxLoss" in term_code

# 16. News MACRO vertical glitch fix & probability calibration
items[16] = "tag-meta" in term_code and "material" in app_code.lower()

# 17. News click headline vs card & CA AI discussion modal
items[17] = "newsDiscussionModal" in term_code and "/api/news/discuss" in app_code and "openNewsDiscussionModal" in term_code

# 18. Full-width Backtesting layout
items[18] = "btChartViewport" in term_code and "100%" in term_code

# 19. Fundamentals UI redesign
items[19] = "Executive Financial Assessment" in term_code and "shareholdingBars" in term_code

# 20. Remove fund balance card from Orders & Positions
items[20] = "fundCards" not in term_code[term_code.find('id="panel-orders"'):term_code.find('id="panel-orders"')+1000] if 'id="panel-orders"' in term_code else False

# 21. Segregate Today's vs Past Orders & Open vs Closed Positions
items[21] = "activeOrderSubTab" in term_code and "activePosSubTab" in term_code and "subTabOpenPositions" in term_code

# 22. Admin funds transfer & server console restriction
items[22] = "/api/admin/funds/add" in app_code and "adminFundTransferCard" in term_code and "adminFundSubmitBtn" in term_code

# 23. Profile details Name + Email + Admin check
items[23] = "profileModalEmail" in term_code and "santoshmadnani553@gmail.com" in app_code and "santoshmadnani@catrader.site" in app_code

for k in sorted(items.keys()):
    print(f"Item {k:2d}: {'[OK]' if items[k] else '[PENDING]'}")

