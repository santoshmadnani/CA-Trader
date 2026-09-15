# -*- coding: utf-8 -*-
"""
Inject external links, in-app navigation links, and explicit formulas into all 8 cards
of the Other Factors & Quantitative Intelligence Suite in terminal.html.
"""

with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

p1 = c.find('id="panel-other-factors"')
p2 = c.find('<!-- 1. Global & Macro Market Drivers -->', p1)
p_end = c.find('<!-- 8. Market Microstructure & Order Flow Imbalance -->', p2)
p_end2 = c.find('</div>\n    </div>', p_end)
if p_end2 == -1:
    p_end2 = c.find('</div>\n  </div>', p_end)

new_cards_html = """      <!-- 1. Global & Macro Market Drivers -->
      <div class="card" id="globalMacroSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(232,184,75,0.15);color:var(--gold);font-size:12px;font-weight:700;">M</span>
            <div>
              <div class="card-title">1. Global &amp; Macro Market Drivers</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">GIFT Nifty · India VIX · US Markets · Brent Crude &amp; Dollar Index</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag buy" id="macroNetBiasTag" style="font-size:10.5px;font-weight:700;">NET BIAS: BULLISH (76%)</span>
            <span class="tag neutral" id="macroDataStateTag" style="font-size:9.5px;">LIVE FEED</span>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px;" id="macroGridCards">
          <!-- GIFT Nifty -->
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <span style="font-size:11px;font-weight:700;color:var(--text-faint);">GIFT NIFTY</span>
              <span class="tag buy" id="giftNiftyTag" style="font-size:9px;padding:1px 5px;">+0.29% GAP UP</span>
            </div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--buy);" id="giftNiftyLevel">23,465.00</div>
            <div class="muted" style="font-size:10px;margin-top:3px;" id="giftNiftySignal">Gap-up opening momentum for domestic market</div>
            <div style="margin-top:6px;font-size:9.5px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border-soft);padding-top:4px;">
              <a href="https://www.nseindia.com" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;font-weight:600;">Source: NSE IFSC / SGX &gt;</a>
              <span class="muted">Gap % = (GIFT - PrevClose)/PrevClose</span>
            </div>
          </div>
          <!-- India VIX -->
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <span style="font-size:11px;font-weight:700;color:var(--text-faint);">INDIA VIX</span>
              <span class="tag buy" id="indiaVixTag" style="font-size:9px;padding:1px 5px;">13.25 (-3.98%)</span>
            </div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--text);" id="indiaVixRegime">LOW VOLATILITY</div>
            <div class="muted" style="font-size:10px;margin-top:3px;" id="indiaVixSignal">Subdued volatility; favorable for call buyers on dips</div>
            <div style="margin-top:6px;font-size:9.5px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border-soft);padding-top:4px;">
              <a href="https://www.nseindia.com/market-data/live-equity-market?symbol=INDIA%20VIX" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;font-weight:600;">Source: NSE India &gt;</a>
              <span class="muted">Regime: VIX &lt; 14 Low, &gt; 18 High</span>
            </div>
          </div>
          <!-- US Markets Closes -->
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <span style="font-size:11px;font-weight:700;color:var(--text-faint);">US MARKETS</span>
              <span class="tag buy" id="usMarketsTag" style="font-size:9px;padding:1px 5px;">GREEN</span>
            </div>
            <div style="font-size:12px;font-family:var(--font-mono);color:var(--text);display:flex;flex-direction:column;gap:2px;" id="usIndicesList">
              <div>S&amp;P 500: <b style="color:var(--buy);">5,626.02 (+0.54%)</b></div>
              <div>Nasdaq: <b style="color:var(--buy);">17,688.35 (+0.65%)</b></div>
              <div>Dow: <b style="color:var(--buy);">40,345.20 (+0.31%)</b></div>
            </div>
            <div style="margin-top:6px;font-size:9.5px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border-soft);padding-top:4px;">
              <a href="https://www.marketwatch.com" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;font-weight:600;">Source: US Exchanges &gt;</a>
              <span class="muted">Overnight Close Momentum</span>
            </div>
          </div>
          <!-- Macro Drivers: Crude & DXY -->
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <span style="font-size:11px;font-weight:700;color:var(--text-faint);">COMMODITY &amp; YIELDS</span>
              <span class="tag neutral" style="font-size:9px;padding:1px 5px;">FAVORABLE</span>
            </div>
            <div style="font-size:12px;font-family:var(--font-mono);color:var(--text);display:flex;flex-direction:column;gap:2px;" id="macroDriversList">
              <div>Brent Crude: <b>$72.40 (-1.12%)</b></div>
              <div>Dollar Index: <b>101.15 (-0.24%)</b></div>
              <div>US 10Y Yield: <b>3.64% (-4 bps)</b></div>
            </div>
            <div style="margin-top:6px;font-size:9.5px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--border-soft);padding-top:4px;">
              <a href="https://fred.stlouisfed.org" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;font-weight:600;">Source: FRED / ICE &gt;</a>
              <span class="muted">Inverse Correlation to NIFTY</span>
            </div>
          </div>
        </div>
        <div class="muted" style="margin-top:8px;font-size:10.5px;" id="macroSummaryText">
          Positive global handover with green US indices, soft crude oil, and complacent India VIX supporting bullish continuation.
        </div>
      </div>

      <!-- 2. Market Breadth Engine -->
      <div class="card" id="marketBreadthSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(38,217,166,0.15);color:var(--buy);font-size:12px;font-weight:700;">B</span>
            <div>
              <div class="card-title">2. Market Breadth Engine</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Advance/Decline Ratio · Moving Average Breadth · Volume Breadth Thrust</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag buy" id="breadthStatusTag" style="font-size:10.5px;font-weight:700;">STRONG ACCUMULATION BREADTH</span>
            <button class="btn ghost small" onclick="showTab('movers')" style="font-size:10px;padding:2px 8px;">View in Market Movers &gt;</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:10px;" id="breadthGridCards">
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Advances / Declines</div>
            <div style="font-size:15px;font-weight:700;font-family:var(--font-mono);margin-top:2px;" id="breadthAdRatio">36 Adv / 14 Dec (2.57x)</div>
            <div class="muted" style="font-size:10px;margin-top:2px;" id="breadthAdDesc">72% of index components trading positive</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>AD Ratio = Advances / Declines</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">% Above 20 &amp; 50 EMA</div>
            <div style="font-size:15px;font-weight:700;font-family:var(--font-mono);color:var(--buy);margin-top:2px;" id="breadthEmaPct">72.0% &gt; 20 EMA | 68.0% &gt; 50 EMA</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">Broad-based structural participation</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Count(Price &gt; EMA) / Total Constituents * 100</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Volume Breadth Thrust</div>
            <div style="font-size:15px;font-weight:700;font-family:var(--font-mono);color:var(--buy);margin-top:2px;" id="breadthThrust">76.5% Up-Volume</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">Aggressive institutional cash accumulation</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Up-Volume / (Up-Vol + Down-Vol) * 100</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">52-Week Highs vs Lows</div>
            <div style="font-size:15px;font-weight:700;font-family:var(--font-mono);margin-top:2px;" id="breadthHighsLows">28 Highs / 2 Lows</div>
            <div class="muted" style="font-size:10px;margin-top:2px;">Dominant expansion in multi-month leaders</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Source: <a href="javascript:void(0)" onclick="showTab('movers')" style="color:var(--primary);text-decoration:none;">In-App Market Movers Tab &gt;</a>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Sector Rotation & Relative Strength Matrix -->
      <div class="card" id="sectorRotationSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(24,144,255,0.15);color:var(--primary);font-size:12px;font-weight:700;">S</span>
            <div>
              <div class="card-title">3. Sector Rotation &amp; Relative Strength Matrix</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">8 Major NSE Sectors · Cycle Quadrants (Leading, Improving, Weakening, Lagging) · RS vs NIFTY</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag gold" id="sectorLeaderTag" style="font-size:10.5px;font-weight:700;">Leader: NIFTY BANK (+1.14%)</span>
            <span class="muted" style="font-size:10px;">Click any sector to chart</span>
          </div>
        </div>
        <div style="margin-top:6px;font-size:10.5px;padding:5px 8px;background:var(--surface-2);border-radius:6px;color:var(--text-faint);">
          Formula: <code>Relative Strength (RS) = ((Sector 20D % - Benchmark 20D %) / Benchmark 20D %) * 100</code> · Quadrants: Leading (RS &gt; 0, 1D &gt; 0), Improving (RS &lt; 0, 1D &gt; 0), Weakening (RS &gt; 0, 1D &lt; 0), Lagging (RS &lt; 0, 1D &lt; 0)
        </div>
        <div class="table-wrap" style="margin-top:10px;">
          <table style="width:100%;font-size:11px;">
            <thead>
              <tr style="border-bottom:1px solid var(--border-soft);text-align:left;">
                <th style="padding:6px 8px;">Sector</th>
                <th style="padding:6px 8px;">Weight</th>
                <th style="padding:6px 8px;">1D Return</th>
                <th style="padding:6px 8px;">5D Return</th>
                <th style="padding:6px 8px;">20D Return</th>
                <th style="padding:6px 8px;">RS vs NIFTY</th>
                <th style="padding:6px 8px;">Cycle Quadrant</th>
                <th style="padding:6px 8px;">Bias</th>
              </tr>
            </thead>
            <tbody id="sectorRotationRows">
              <!-- Dynamically populated -->
            </tbody>
          </table>
        </div>
      </div>

      <!-- 4. Quantitative Market Regime Classifier -->
      <div class="card" id="regimeClassifierSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(16,185,129,0.15);color:#10b981;font-size:12px;font-weight:700;">R</span>
            <div>
              <div class="card-title">4. Quantitative Market Regime Classifier</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Multi-factor Regime State · Calibrated Probabilities · Recommended Strategy Archetype</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag buy" id="regimeNameTag" style="font-size:10.5px;font-weight:700;">BULL_TREND REGIME</span>
            <button class="btn ghost small" onclick="showTab('charts')" style="font-size:10px;padding:2px 8px;">View in Chart &amp; Technicals &gt;</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:10px;">
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Regime Probabilities</div>
            <div style="font-size:13px;font-family:var(--font-mono);margin-top:4px;display:flex;flex-direction:column;gap:3px;">
              <div>P(Bullish Continuation): <b style="color:var(--buy);" id="pBullish">74%</b></div>
              <div>P(Bearish Breakdown): <b style="color:var(--sell);" id="pBearish">16%</b></div>
              <div>P(Rangebound Consolidation): <b style="color:var(--gold);" id="pRange">10%</b></div>
            </div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Bayesian Posterior P(Regime|EMA, Supertrend, ADX, VIX)</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Strategy Archetype</div>
            <div style="font-size:14px;font-weight:700;color:var(--text);margin-top:2px;" id="regimeStrategyArchetype">Momentum Long Call Buying on Pullbacks</div>
            <div class="muted" style="font-size:10.5px;margin-top:2px;" id="regimeRationale">Higher-high market structure, positive breadth, and low India VIX confirm expansion phase.</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              App Action: Long ATM Options when Price re-tests 20 EMA
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Volatility &amp; Momentum States</div>
            <div style="font-size:12.5px;font-family:var(--font-mono);margin-top:3px;" id="regimeVolState">Low Volatility Expansion (Normal VIX)</div>
            <div style="font-size:12.5px;font-family:var(--font-mono);margin-top:2px;" id="regimeAdxState">Strong Trending Momentum (ADX 28.5)</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Wilder ATR(14) + Wilder ADX(14) with VIX Baseline</code>
            </div>
          </div>
        </div>
      </div>

      <!-- 5. Volatility Surface & IV Skew -->
      <div class="card" id="volatilitySurfaceSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(234,179,8,0.15);color:var(--gold);font-size:12px;font-weight:700;">V</span>
            <div>
              <div class="card-title">5. Options Volatility Surface &amp; IV Skew</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">ATM IV · 25-Delta Put/Call Skew · IV Rank (IVR) · IV Percentile (IVP) · HV vs IV Spread</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag gold" id="volPricingVerdict" style="font-size:10.5px;font-weight:700;">FAIR / BUYER FRIENDLY</span>
            <button class="btn ghost small" onclick="showTab('options')" style="font-size:10px;padding:2px 8px;">View in Option Chain &gt;</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:10px;">
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">ATM Implied Volatility (IV)</div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);margin-top:2px;" id="volAtmIv">13.4%</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Contract-specific implied vol</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Black-Scholes Inversion of ATM Option Price</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">25-Delta Put/Call Skew</div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--buy);margin-top:2px;" id="volSkew">+2.2% (Normal)</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">25D Put IV (14.8%) vs 25D Call IV (12.6%)</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Skew = IV(25-Delta Put) - IV(25-Delta Call)</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">IV Rank &amp; IV Percentile</div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);margin-top:2px;" id="volIvrIvp">IVR 32.5 | IVP 38.0%</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Over 252-session lookback band</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>IVR = ((IV - 52W_Min)/(52W_Max - 52W_Min))*100</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">HV (20D) vs IV Spread</div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);margin-top:2px;" id="volHvIv">HV 11.8% vs IV 13.4% (-1.6%)</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Fair option premium pricing</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>HV = StdDev(ln(C_t/C_{t-1})) * sqrt(252)</code>
            </div>
          </div>
        </div>
      </div>

      <!-- 6. Open Interest Buildup Matrix & Gamma Flip -->
      <div class="card" id="oiMatrixSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(168,85,247,0.15);color:#a855f7;font-size:12px;font-weight:700;">O</span>
            <div>
              <div class="card-title">6. Open Interest Matrix &amp; Dealer Gamma Flip</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Live PCR (OI &amp; Volume) · Max Pain Strike · Dealer Gamma Flip Level · Strike Buildup Classification</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag buy" id="gammaFlipTag" style="font-size:10.5px;font-weight:700;">POSITIVE DEALER GAMMA</span>
            <button class="btn ghost small" onclick="showTab('options')" style="font-size:10px;padding:2px 8px;">View in Option Chain &gt;</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:10px;">
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Full Chain PCR (OI &amp; Volume)</div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--buy);margin-top:2px;" id="oiPcrValues">PCR OI 1.24 | Vol PCR 1.18</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Put writing exceeds call writing (Bullish floor)</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>PCR = Total Put OI / Total Call OI</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Max Pain &amp; Gamma Flip</div>
            <div style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--gold);margin-top:2px;" id="oiMaxPainGamma">Max Pain: 23,400 | Flip: 23,350</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Above 23,350: Dealer short-covering volatility dampening</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Max Pain = argmin(Total Option Buyer Losses)</code>
            </div>
          </div>
        </div>
        <div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;" id="oiBuildupPills">
          <!-- Populated with strike buildup highlights -->
        </div>
      </div>

      <!-- 7. Portfolio Risk, Position Sizing & Capital Protection -->
      <div class="card" id="portfolioRiskSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(239,68,68,0.15);color:var(--sell);font-size:12px;font-weight:700;">P</span>
            <div>
              <div class="card-title">7. Portfolio Risk, Position Sizing &amp; Safety Guardrails</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Capital-At-Risk Budgeting · Mathematical Expectancy (EV) · 1-Day VaR (95%) · Automated Kill Switch</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag buy" id="killSwitchTag" style="font-size:10.5px;font-weight:700;">KILL SWITCH: ARMED &amp; PROTECTED</span>
            <button class="btn ghost small" onclick="showTab('funds')" style="font-size:10px;padding:2px 8px;">View in Funds &gt;</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:10px;">
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Recommended Position Sizing</div>
            <div style="font-size:14px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:2px;" id="riskSizing">1 to 2 Lots (Risk capped at 1.5% capital)</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Max risk budgeted: ₹2,500 per setup</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Lots = floor((Capital * 1.5%) / (Entry - SL) * LotSize)</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Mathematical Expectancy (EV)</div>
            <div style="font-size:14px;font-weight:700;font-family:var(--font-mono);color:var(--buy);margin-top:2px;" id="riskExpectancy">+₹645 per trade net of costs</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">EV = P(Win)*AvgWin - P(Loss)*AvgLoss - Costs</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>EV = (P_win * Win_R) - (P_loss * Loss_R) - Slippage - Fees</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Value-at-Risk (VaR 95% 1-Day)</div>
            <div style="font-size:14px;font-weight:700;font-family:var(--font-mono);color:var(--text);margin-top:2px;" id="riskVar">₹1,850 (95% Confidence)</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Maximum expected loss at 95% threshold</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>VaR_95 = Capital * Portfolio_Vol * 1.645</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Automated Kill Switch Limits</div>
            <div style="font-size:12px;font-family:var(--font-mono);color:var(--text);margin-top:2px;" id="riskKillLimits">Daily Loss: -3.0% | Max DD: -6.0%</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Stale feed guard: Active (Spread &lt; 1.5%)</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Action: Auto-Locks Terminal Execution upon breach
            </div>
          </div>
        </div>
      </div>

      <!-- 8. Market Microstructure & Order Flow Imbalance -->
      <div class="card" id="microstructureSection" style="margin-bottom:14px;">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(59,130,246,0.15);color:var(--primary);font-size:12px;font-weight:700;">U</span>
            <div>
              <div class="card-title">8. Market Microstructure &amp; Order Flow Imbalance</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Bid/Ask Queue Imbalance · Effective Spread % · Estimated Slippage Penalty · Institutional Buying Velocity</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag buy" id="microstructureStatusTag" style="font-size:10.5px;font-weight:700;">HIGH BUYING PRESSURE</span>
            <button class="btn ghost small" onclick="showTab('charts')" style="font-size:10px;padding:2px 8px;">View Depth in Charts &gt;</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:10px;">
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Bid / Ask Quantity Imbalance</div>
            <div style="font-size:15px;font-weight:700;font-family:var(--font-mono);color:var(--buy);margin-top:2px;" id="microImbalance">63.4% Bids vs 36.6% Asks (1.73x)</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Buyer queue depth exceeds resting ask supply</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Imbalance = (Total Bids - Total Asks) / (Total Bids + Total Asks)</code>
            </div>
          </div>
          <div style="background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:10px;">
            <div class="muted" style="font-size:10px;text-transform:uppercase;">Effective Bid/Ask Spread &amp; Slippage</div>
            <div style="font-size:15px;font-weight:700;font-family:var(--font-mono);margin-top:2px;" id="microSpread">Spread 0.04% · Slippage ₹0.20/lot</div>
            <div class="muted" style="font-size:9.5px;margin-top:1px;">Tight institutional liquidity spreads</div>
            <div style="margin-top:6px;font-size:9.5px;color:var(--text-faint);border-top:1px solid var(--border-soft);padding-top:4px;">
              Formula: <code>Effective Spread = 2 * |Trade Price - Midpoint| / Midpoint * 100</code>
            </div>
          </div>
        </div>
        <div class="muted" style="margin-top:8px;font-size:10.5px;" id="microSummaryText">
          Aggressive market buy orders absorbing resting limit ask liquidity at dynamic VWAP.
        </div>
      </div>
"""

c = c[:p2] + new_cards_html + c[p_end2:]
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(c)

print("terminal.html: Added external source links, in-app quick links, and formulas to Other Factors suite.")

