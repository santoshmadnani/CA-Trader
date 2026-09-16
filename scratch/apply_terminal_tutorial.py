#!/usr/bin/env python3
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

tree_start = text.find('<div class="tut-tree" id="tutFeatureTree">')
if tree_start == -1:
    print("Error: tutFeatureTree start not found")
    sys.exit(1)

tree_end_marker = '</div>\n    </div>\n\n    <!-- ============ ALERTS'
if tree_end_marker not in text:
    tree_end_marker = '</div>\n    </div>\n    <!-- ============ ALERTS'
tree_end = text.find(tree_end_marker, tree_start)
if tree_end == -1:
    print("Error: tutFeatureTree end not found")
    sys.exit(1)

EXPANDED_TUTORIAL = '''<div class="tut-tree" id="tutFeatureTree">
        <!-- 1. Candlestick Charts & Interaction -->
        <div class="tut-node open">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">1</span>
              <span>1. Professional High-Frequency Charting, Zooming &amp; Crosshair Dynamics</span>
            </div>
            <span class="tut-toggle-btn">[-]</span>
          </div>
          <div class="tut-body">
            CA Trader's vector-grade HTML5 Canvas charting engine delivers institutional-grade rendering with microsecond response times.
            <ul class="tut-sublist">
              <li><b>Precision Crosshair:</b> Engaging touch or hovering on PC instantly generates high-contrast dotted crosshair lines across the full canvas, anchoring live price tags on the Y-axis and exact bar timestamps (IST) on the X-axis.</li>
              <li><b>Zoom &amp; Pinch Controls:</b> Tapping the <b>[+]</b> button or pinching two fingers apart zooms IN into the candles; tapping the <b>[−]</b> button or pinching fingers inward zooms OUT for broad macro view.</li>
              <li><b>Freeform Pan Drag:</b> Click or touch anywhere to slide the viewport horizontally across trading days and vertically across price ranges.</li>
              <li><b>Drawing Tools &amp; Accidental Drag Lock:</b> Select trendlines, rays, horizontal levels, channels, or Fibonacci retracements from the floating toolbar. Click <b>[🔒 Lock]</b> in the top toolbar to freeze all drawings in place, preventing accidental repositioning while panning.</li>
            </ul>
          </div>
        </div>

        <!-- 2. Technical Indicators -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">2</span>
              <span>2. 110+ Institutional Technical Indicators &amp; Signal Confluence</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Direct access to over 110 quantitative indicators powered by pure algorithmic formulas.
            <ul class="tut-sublist">
              <li><b>Indicator Catalog:</b> RSI (14), MACD (12, 26, 9), Bollinger Bands (20, 2), Supertrend (10, 3), Exponential Moving Averages (20, 50, 200 EMA), Session VWAP, ATR (14), ADX Trend Strength, Stochastic %K/%D, CCI, and Williams %R.</li>
              <li><b>Instant Formula Proofs:</b> Hovering or tapping any applied indicator pill in the toolbar opens a compact criteria box displaying the underlying numerical value, moving average distance, and active algorithmic signal (BULLISH, BEARISH, or NEUTRAL).</li>
              <li><b>Dismiss Anywhere:</b> Simply tap or click anywhere outside the comment box to immediately dismiss the tooltip.</li>
            </ul>
          </div>
        </div>

        <!-- 3. Patterns Engine -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">3</span>
              <span>3. Multi-Candle Pattern Recognition with Exact Timestamp Audit</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Real-time pattern recognition scanner scanning every 1-minute to daily timeframe simultaneously.
            <ul class="tut-sublist">
              <li><b>Institutional Catalog:</b> Three White Soldiers, Three Black Crows, Morning Star, Evening Star, Bullish/Bearish Engulfing, Hammer, Inverted Hammer, Shooting Star, Piercing Line, Dark Cloud Cover, and 20 EMA Momentum Retests.</li>
              <li><b>Exact Timestamps:</b> Every detected pattern logs both the exact candle time (e.g. <i>Today 10:45 IST</i>) and the precise detection timestamp so you know whether a breakout is fresh or maturing.</li>
              <li><b>Chart Highlighting:</b> Clicking any detected pattern formation in the list highlights the corresponding bars directly on the chart canvas.</li>
            </ul>
          </div>
        </div>

        <!-- 4. Recommendation Rationale -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">4</span>
              <span>4. AI Recommendation Confluence Matrix &amp; [+] Collapsible Drilldowns</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            The heart of CA Trader's decision engine: 6 full-width institutional Smart-Art blocks synthesizing multiple quantitative pillars into a unified trading verdict.
            <ul class="tut-sublist">
              <li><b>Full-Width Responsive Layout:</b> Spans the entire width of the trading dashboard on desktop and mobile.</li>
              <li><b>Interactive [+] Drilldown Drawers:</b> Click <b>[+] Details</b> on any block to expand full underlying evidence:
                <br>• <i>Technical Momentum:</i> Full 24-indicator catalog with levels and signals.
                <br>• <i>Patterns Matrix:</i> List of all detected patterns with exact timestamps.
                <br>• <i>Option Greeks:</i> Volatility surface, PCR ratio, Max Pain, and OI build-up.
                <br>• <i>Ingested News:</i> Complete institutional briefings with source citations and materiality %.
                <br>• <i>Macro Drivers:</i> Global indices (Dow, S&P 500), US 10Y yields, and currency exchange.
                <br>• <i>Risk Matrix:</i> Exact mathematical proofs for noise-safe Stop Loss and 1:2 Risk/Reward target.</li>
            </ul>
          </div>
        </div>

        <!-- 5. Option Greeks -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">5</span>
              <span>5. Dynamic Option Chain, Pure Black-Scholes Greeks &amp; ATM Strike Selection</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            High-speed derivative analytics engine calculating analytical Black-Scholes Greeks in real time on every price tick.
            <ul class="tut-sublist">
              <li><b>Dynamic ATM Strike:</b> Automatically maps underlying spot prices (NIFTY, BANKNIFTY, CRUDEOIL, etc.) to the optimal ATM option contract without manual searching.</li>
              <li><b>Greeks Breakdown:</b> Real-time Delta (directional sensitivity), Gamma (acceleration rate), Theta (daily rupee decay per lot), Vega (volatility sensitivity), and Implied Volatility (IV).</li>
              <li><b>Option Chain View:</b> Toggle full strikes ladder with Call OI, Put OI, net build-up, and strike volume.</li>
            </ul>
          </div>
        </div>

        <!-- 6. Orders & Sizing -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">6</span>
              <span>6. 1-Click Quick Execution, Noise-Safe Stop Loss &amp; Trailing SL Engine</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Institutional order management built to prevent premature shakeouts and protect profits.
            <ul class="tut-sublist">
              <li><b>Quick Order Modal:</b> Beautiful, centered dialog on mobile and desktop displaying instrument lot size (e.g. 65 for Nifty, 15 for Bank Nifty, 100 for Crude), recommended entry, and instant 1-click buy/sell.</li>
              <li><b>Noise-Safe Stop Loss:</b> Stop loss buffers are dynamically calibrated to 15–22% of option premium or 1.5× ATR, eliminating premature stop-outs during temporary market wicks.</li>
              <li><b>Trailing Stop Loss (TSL):</b> Once your trade crosses 50% distance to target, the algorithmic trailing stop advances to breakeven + 2 pts to guarantee capital safety.</li>
            </ul>
          </div>
        </div>

        <!-- 7. Position Sentinel -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">7</span>
              <span>7. Permanent Floating Position Sentinel Widget &amp; Draggable Popups</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Never lose track of your live trading exposure while navigating across charts, news, or notes.
            <ul class="tut-sublist">
              <li><b>Floating Sentinel Widget:</b> Fixed at the screen corner showing total open positions, live color-coded P&L (green/red), entry price, current LTP, stop loss, and target.</li>
              <li><b>Universal Mobility:</b> Click and drag (or touch and drag on mobile) the header bar of the position widget or any popup dialog (Orders, CA AI Chat, Quick Order) to move it freely anywhere on your screen.</li>
              <li><b>Minimize / Expand:</b> Click the <b>[_]</b> / <b>[▢]</b> toggle in the widget header to collapse it into a minimal footprint whenever you need maximum charting area.</li>
            </ul>
          </div>
        </div>

        <!-- 8. Ask CA AI -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">8</span>
              <span>8. Ask CA AI: Natural Language Institutional Quantitative Analyst</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            A private hedge fund quantitative analyst in your pocket powered by Google Gemini.
            <ul class="tut-sublist">
              <li><b>Rich Markdown Formatting:</b> All AI responses are beautifully styled with bold headings, highlighted parameters, formatted bullet points, and clean paragraph breaks for effortless reading.</li>
              <li><b>Instant Setup Audits:</b> Ask questions like <i>"Is this setup safe?"</i>, <i>"What is the mathematical proof of this stop loss?"</i>, or <i>"Switch Call to Put option"</i> to immediately receive revised risk parameters.</li>
              <li><b>Prompt Chips:</b> Tap quick pre-built prompt chips along the bottom bar for instant technical and fundamental audits.</li>
            </ul>
          </div>
        </div>

        <!-- 9. Real-Time News -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">9</span>
              <span>9. Institutional Real-Time News Catalysts &amp; Materiality Indexing</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Curated high-conviction market news feeds with institutional relevance scoring.
            <ul class="tut-sublist">
              <li><b>Zero Vague Headlines:</b> Every feed item includes a professional headline, 3-sentence deep briefing, verified publisher (Bloomberg, Reuters, RBI, Platts, Financial Times), and exact timestamp.</li>
              <li><b>Materiality Scoring:</b> Each catalyst is rated on a 0–100% materiality scale, highlighting high-impact events like central bank rate actions, oil export rerouting, or FII flow inflection points.</li>
              <li><b>Multi-Asset Feeds:</b> Dedicated streams for NIFTY, BANKNIFTY, CRUDE OIL, GOLD, and Global Macro drivers.</li>
            </ul>
          </div>
        </div>

        <!-- 10. Multi-Timeframe Alignment -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">10</span>
              <span>10. Multi-Timeframe (MTF) Trend Alignment &amp; Momentum Proofs</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Eliminates counter-trend trades by synchronizing micro and macro perspectives.
            <ul class="tut-sublist">
              <li><b>Hierarchical Alignment:</b> Evaluates 5m, 15m, 1h, and Daily trends simultaneously. Recommendations are only issued when micro momentum aligns with higher-timeframe order flow.</li>
              <li><b>Clean Signal Header:</b> Reliable, error-free signals heading showing clear BUY/SELL bias without technical fallback error messages.</li>
            </ul>
          </div>
        </div>

        <!-- 11. Trader Notes -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">11</span>
              <span>11. Trader Notes, Categorized Folders &amp; Screen Space Maximizer</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Your personal quantitative trade journal stored safely in local-first encrypted SQLite storage.
            <ul class="tut-sublist">
              <li><b>Folder Management:</b> Organize notes across custom folders (Breakouts, Earnings, Post-Trade Analysis, Risk Journal).</li>
              <li><b>[◀ Collapse Folders] Button:</b> Click the toggle button in the notes toolbar to hide the folder list and expand the note writing editor to 100% full screen width.</li>
              <li><b>Chart Attachments:</b> One-click screenshot capture saves live chart setups directly into your trade notes.</li>
            </ul>
          </div>
        </div>

        <!-- 12. Fullscreen Landscape & Shortcuts -->
        <div class="tut-node">
          <div class="tut-header">
            <div class="tut-header-left">
              <span class="tut-icon-badge">12</span>
              <span>12. Fullscreen Landscape Mode &amp; Pro Trader Shortcuts</span>
            </div>
            <span class="tut-toggle-btn">[+]</span>
          </div>
          <div class="tut-body">
            Immersive edge-to-edge chart analysis across all devices.
            <ul class="tut-sublist">
              <li><b>Video-Style Fullscreen:</b> Tap the Fullscreen button in the chart toolbar to launch true edge-to-edge fullscreen with automatic landscape rotation on mobile, just like a video player.</li>
              <li><b>Keyboard Hotkeys (PC):</b>
                <br>• <b>+ / − :</b> Zoom in / Zoom out
                <br>• <b>Space / Arrow Keys:</b> Pan across historical candles
                <br>• <b>Del / Backspace:</b> Remove selected drawing or indicator
                <br>• <b>Esc:</b> Exit fullscreen or cancel pending drawing</li>
              <li><b>Saved Recommendation History:</b> Click <b>💾 Save to History</b> on any active setup to permanently log it for performance tracking and post-trade review.</li>
            </ul>
          </div>
        </div>
      </div>'''

text = text[:tree_start] + EXPANDED_TUTORIAL + text[tree_end:]

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print(f"Updated tutorial with 12 comprehensive modules! ({len(text):,} bytes)")

