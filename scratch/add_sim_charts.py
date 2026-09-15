# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'id="indicatorRows"></tbody></table></div>\n      </div>'
replacement = target + '''

      <!-- Indicator Price Sensitivity Simulator (Charts & Technicals - Item 10) -->
      <div class="card" style="margin-bottom:14px;" id="chartPriceSensitivityCard">
        <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:rgba(232,184,75,0.15);color:var(--gold);font-size:12px;font-weight:700;">⚡</span>
            <div>
              <div class="card-title">Price Sensitivity Simulator</div>
              <div class="muted" style="font-size:10.5px;margin-top:1px;">Simulate underlying price shocks against key indicator levels, Greeks, and option prices</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="tag neutral" id="chartSimCmpBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">CMP: ₹--</span>
            <span class="tag buy" id="chartSimDiffBadge" style="font-family:var(--font-mono);font-size:11px;font-weight:700;">Diff: +₹0.00 (+0.00%)</span>
          </div>
        </div>
        <div style="margin-top:12px;">
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);margin-bottom:4px;">
            <span>-5.0% Bear Shock</span>
            <span style="font-weight:700;color:var(--gold);" id="chartSimSliderDisplay">Simulated Price: ₹-- (CMP)</span>
            <span>+5.0% Bull Surge</span>
          </div>
          <input type="range" id="chartSimSlider" min="-50" max="50" value="0" step="1" style="width:100%;cursor:pointer;">
        </div>
        <div class="grid grid-4" style="margin-top:14px;gap:10px;" id="chartSimGrid">
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Simulated Price</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--text);margin-top:2px;" id="chartSimPriceVal">--</div>
            <div style="font-size:10px;color:var(--buy);" id="chartSimPriceDiff">0.00% vs CMP</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">ATM Call Premium Impact</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--buy);margin-top:2px;" id="chartSimCallDelta">₹0.00</div>
            <div style="font-size:10px;color:var(--text-dim);" id="chartSimCallDetail">Δ ≈ 0.50 per ₹1</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">ATM Put Premium Impact</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--sell);margin-top:2px;" id="chartSimPutDelta">₹0.00</div>
            <div style="font-size:10px;color:var(--text-dim);" id="chartSimPutDetail">Δ ≈ -0.50 per ₹1</div>
          </div>
          <div style="background:var(--surface-2);padding:10px 12px;border-radius:8px;border:1px solid var(--border-soft);">
            <div class="muted" style="font-size:10px;">Technical Threshold Breach</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:12px;color:var(--gold);margin-top:2px;" id="chartSimThreshold">At CMP Level</div>
            <div style="font-size:10px;color:var(--text-dim);" id="chartSimThresholdDetail">Testing key support/resistance</div>
          </div>
        </div>
      </div>'''

if target in c and "chartPriceSensitivityCard" not in c:
    c = c.replace(target, replacement, 1)
    with open('terminal.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Successfully added Price Sensitivity Simulator to Charts tab!')
else:
    print('Target string not found or already added')

