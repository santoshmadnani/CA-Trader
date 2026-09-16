import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect where chartRecoBanner starts
start_banner = text.find('<div class="card" id="chartRecoBanner"')
if start_banner == -1:
    print("chartRecoBanner not found")
    sys.exit(1)

# Find where dashRationaleCard starts
start_rationale = text.find('<div class="card" id="dashRationaleCard"')
if start_rationale == -1:
    print("dashRationaleCard not found")
    sys.exit(1)

print("Current text between chartRecoBanner and dashRationaleCard:")
print(repr(text[start_banner:start_rationale]))

banner_replacement = '''<div class="card" id="chartRecoBanner" style="margin-bottom:12px;padding:12px 16px;background:var(--surface);border:1px solid rgba(38,217,166,0.3);box-shadow:0 6px 20px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;overflow:visible !important;position:relative;z-index:1000;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;background:var(--buy-bg);color:var(--buy);font-size:14px;font-weight:700;">✦</span>
          <div>
            <div style="display:flex;align-items:center;gap:8px;position:relative;flex-wrap:wrap;">
              <span class="tag neutral" id="chartRecoAction" style="font-size:11.5px;font-weight:700;padding:2px 8px;">SIGNAL</span>
              <span style="font-weight:700;font-size:13.5px;color:var(--text);" id="chartRecoSymbol">—</span>
              <select id="chartRecoOptionSelect" style="display:inline-block;height:26px;font-size:11px;padding:2px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface-2);color:var(--text);font-family:var(--font-mono);max-width:210px;cursor:pointer;">
                <option value="">Auto (Best Option)</option>
              </select>
              <span class="muted" style="font-size:11px;" id="chartRecoConfidence">Live Consensus</span>
              <span class="tag neutral" id="chartRecoLotSize" style="font-size:10px;font-family:var(--font-mono);" title="Lot size for this contract">Lot: —</span>
            </div>
            <div class="muted" id="chartRecoRationale" style="display:none;"></div>
          </div>
        </div>

        <!-- Entry / SL / Target / R:R pills + Actions -->
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0;box-sizing:border-box;">
          <div class="stat-pill clickable-calc" id="chartRecoEntryPill" title="Click to inspect Entry calculation proof" style="cursor:pointer;background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">Entry ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--text);" id="chartRecoEntry">₹--</div>
          </div>
          <div class="stat-pill clickable-calc" id="chartRecoSlPill" title="Click to inspect Stop Loss calculation proof" style="cursor:pointer;background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">Stop Loss ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--sell);" id="chartRecoSl">₹--</div>
          </div>
          <div class="stat-pill clickable-calc" id="chartRecoTgtPill" title="Click to inspect Target calculation proof" style="cursor:pointer;background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">Target ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--buy);" id="chartRecoTgt">₹--</div>
          </div>
          <div class="stat-pill" style="background:var(--surface-2);border:1px solid var(--border-soft);padding:4px 10px;border-radius:6px;text-align:center;min-width:0;">
            <div style="font-size:9px;color:var(--text-faint);text-transform:uppercase;">R : R</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--gold);" id="chartRecoRr">1 : 2.0</div>
          </div>
          <button type="button" class="btn ghost small" id="chartRecoAddWlBtn" style="height:30px;display:none;font-size:11px;padding:0 8px;border-color:var(--primary);color:var(--primary);" title="Add recommended option to watchlist">+ Watchlist</button>
          <button type="button" class="btn ghost small" id="chartRecoRefreshBtn" title="Refresh Live Recommendation" style="height:30px;display:inline-flex;align-items:center;gap:5px;padding:0 8px;border-color:var(--border);background:var(--surface-2);cursor:pointer;">
            <span>↻ Refresh</span>
          </button>
          <button type="button" class="btn gold small" id="chartRecoQuickOrderBtn" title="Place 1-Click Quick Order" style="height:30px;display:inline-flex;align-items:center;gap:5px;padding:0 12px;font-weight:700;cursor:pointer;">
            <span>Quick Order</span>
          </button>
        </div>
      </div>

      <!-- Confluence Rationale Table -->
      '''

new_text = text[:start_banner] + banner_replacement + text[start_rationale:]
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Updated terminal.html successfully.")

