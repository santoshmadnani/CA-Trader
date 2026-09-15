# -*- coding: utf-8 -*-
"""
Phase 1 & 5 UI Layout Fixes in terminal.html:
- Fix topbar & dropdowns z-index (Item 1)
- Expiry select contrast (Item 12)
- MCX options manual selector with autocomplete suggestions (Item 13)
- Max profit/loss inputs in recommendations (Item 15)
- Remove vertical MACRO glitch in news (Item 16)
- Add News Discussion Modal (Item 17)
- Full width backtesting layout (Item 18)
- Modernized fundamentals UI (Item 19)
- Remove fundCards from orders panel (Item 20)
- Divide orders & positions into Today vs Past / Open vs Closed (Item 21)
- Admin controls & profile modal Name + Email (Items 22, 23)
"""
from pathlib import Path
import re

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

# 1. CSS fixes for Topbar, Dropdowns, Select Options, and News
css_target = ".user-chip{cursor:pointer;position:relative}.user-menu{position:absolute;right:0;top:38px;width:250px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:0 18px 40px rgba(0,0,0,.3);padding:10px;display:none;z-index:90}.user-menu.open{display:block}.user-menu .profile-name{font-weight:700;font-size:12px}.user-menu .profile-role{font-size:10px;color:var(--text-faint);margin-top:2px}.notification-menu{position:absolute;right:0;top:38px;width:330px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:0 18px 40px rgba(0,0,0,.3);padding:10px;display:none;z-index:90}.notification-menu.open{display:block}.notification-row{padding:8px;border-bottom:1px solid var(--border-soft);font-size:10.5px}.notification-row:last-child{border-bottom:0}.top-icon-wrap{position:relative}"

css_replacement = """.user-chip{cursor:pointer;position:relative;display:flex;align-items:center;gap:8px;}
.user-menu{position:absolute;right:0;top:44px;width:260px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:0 20px 45px rgba(0,0,0,.5);padding:12px;display:none;z-index:2200;}
.user-menu.open{display:block;}
.user-menu .profile-name{font-weight:700;font-size:13px;color:var(--text);}
.user-menu .profile-email{font-size:11px;color:var(--text-dim);margin-top:2px;word-break:break-all;}
.user-menu .profile-role{font-size:10px;color:var(--gold);margin-top:4px;font-weight:600;}
.notification-menu{position:absolute;right:0;top:44px;width:340px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:0 20px 45px rgba(0,0,0,.5);padding:12px;display:none;z-index:2200;}
.notification-menu.open{display:block;}
.notification-row{padding:8px;border-bottom:1px solid var(--border-soft);font-size:11px;}
.notification-row:last-child{border-bottom:0;}
.top-icon-wrap{position:relative;}
.topbar{position:sticky;top:0;z-index:2000!important;}
#optionExpiry, .select-box select, #optionExpiry option, .select-box select option {
  background: var(--surface-2, #18202A) !important;
  color: var(--text, #E6EDF3) !important;
}
.tag-meta{font-size:10px;font-weight:600;padding:2px 7px;border-radius:5px;background:var(--surface-2);color:var(--text-dim);border:1px solid var(--border-soft);display:inline-block;}
.news-headline-link{color:var(--text);text-decoration:none;font-weight:600;display:block;}
.news-headline-link:hover{color:var(--gold);text-decoration:underline;}
.tab-sub-btn{padding:5px 12px;font-size:11px;font-weight:600;border-radius:6px;border:1px solid var(--border-soft);background:var(--surface-2);color:var(--text-dim);cursor:pointer;}
.tab-sub-btn.active{background:var(--gold);color:#0B2A1E;border-color:var(--gold);}
"""

assert css_target in content, "css_target not found"
content = content.replace(css_target, css_replacement, 1)

# 2. Update Profile Menu in HTML to include Email and Admin info
old_user_menu = '''      <div class="user-menu" id="userMenu">
        <div class="profile-name" id="profileMenuName">Profile</div>
        <div class="profile-role">Paper Trading</div>'''

new_user_menu = '''      <div class="user-menu" id="userMenu">
        <div class="profile-name" id="profileMenuName">Profile</div>
        <div class="profile-email" id="profileMenuEmail">—</div>
        <div class="profile-role" id="profileMenuRole">Paper Trading</div>'''

assert old_user_menu in content, "old_user_menu not found"
content = content.replace(old_user_menu, new_user_menu, 1)

# 3. Update Profile Modal to show both Name and Email ID (Item 23)
old_profile_modal = '''<div class="tool-modal" id="profileModal" aria-hidden="true">
  <div class="tool-modal-card">
    <div class="card-head"><div class="card-title">Profile details</div><button class="btn ghost small" id="profileModalClose">Cancel</button></div>
    <div class="field"><label>Name</label><input id="profileNameInput" class="tool-input" placeholder="First and last name"></div>
    <div class="tool-modal-actions"><button class="btn gold" id="profileSaveBtn">Save</button></div>
  </div>
</div>'''

new_profile_modal = '''<div class="tool-modal" id="profileModal" aria-hidden="true">
  <div class="tool-modal-card">
    <div class="card-head"><div class="card-title">Profile details</div><button class="btn ghost small" id="profileModalClose">Cancel</button></div>
    <div class="field"><label>Name</label><input id="profileNameInput" class="tool-input" placeholder="First and last name"></div>
    <div class="field"><label>Email ID</label><input id="profileEmailInput" class="tool-input" readonly style="opacity:0.85;cursor:not-allowed;background:var(--surface-3);"></div>
    <div class="field" style="margin-top:10px;"><label>Account Role</label><div id="profileRoleBadge" class="tag buy" style="display:inline-block;margin-top:4px;font-size:11px;">User</div></div>
    <div class="tool-modal-actions"><button class="btn gold" id="profileSaveBtn">Save</button></div>
  </div>
</div>'''

assert old_profile_modal in content, "old_profile_modal not found"
content = content.replace(old_profile_modal, new_profile_modal, 1)

# 4. Update MCX Option Selector with Autocomplete Search (Item 13)
old_mcx_selector = '''      <div id="mcxOptSelector" style="display:none;margin-bottom:10px;padding:10px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
        <div style="font-size:11px;font-weight:600;color:var(--text-dim);margin-bottom:8px;">MCX Option Chain — Manual Selector</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
          <div class="finder-field"><label>Commodity</label><input id="mcxOptSymbol" class="tool-input" style="width:140px;" placeholder="e.g. CRUDEOIL" value="CRUDEOIL"></div>
          <div class="finder-field"><label>Expiry Month</label><select id="mcxOptExpiry" class="tool-input" style="width:130px;"><option value="">Select expiry…</option></select></div>
          <div class="finder-field"><label>Year</label><select id="mcxOptYear" class="tool-input" style="width:90px;"></select></div>
          <button class="btn gold small" id="mcxOptLoadBtn" style="margin-top:18px;">Load Chain</button>
        </div>
        <div class="muted" style="font-size:10px;margin-top:5px;">MCX contracts use month+year naming (e.g. CRUDEOIL25SEPFUT). Select commodity and expiry to load the option chain.</div>
      </div>'''

new_mcx_selector = '''      <div id="mcxOptSelector" style="display:none;margin-bottom:10px;padding:10px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;position:relative;">
        <div style="font-size:11px;font-weight:600;color:var(--text-dim);margin-bottom:8px;">MCX Option Chain — Manual Selector</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
          <div class="finder-field" style="position:relative;">
            <label>Commodity</label>
            <input id="mcxOptSymbol" class="tool-input" style="width:150px;" placeholder="Search MCX commodity…" value="CRUDEOIL" autocomplete="off">
            <div id="mcxSymbolSuggestions" class="auto-suggestions-menu" style="display:none;position:absolute;top:calc(100% + 2px);left:0;width:200px;z-index:1500;background:var(--surface);border:1px solid var(--border);border-radius:7px;box-shadow:0 12px 30px rgba(0,0,0,.4);max-height:200px;overflow-y:auto;"></div>
          </div>
          <div class="finder-field"><label>Expiry Month</label><select id="mcxOptExpiry" class="tool-input" style="width:130px;"><option value="">Select expiry…</option></select></div>
          <div class="finder-field"><label>Year</label><select id="mcxOptYear" class="tool-input" style="width:90px;"></select></div>
          <button class="btn gold small" id="mcxOptLoadBtn" style="margin-top:18px;">Load Chain</button>
        </div>
        <div class="muted" style="font-size:10px;margin-top:5px;">Search MCX commodities (e.g. CRUDEOIL, NATURALGAS, GOLD, SILVER) to load option chain.</div>
      </div>'''

assert old_mcx_selector in content, "old_mcx_selector not found"
content = content.replace(old_mcx_selector, new_mcx_selector, 1)

# 5. Update Recommendations Header: replace buttons with Max Profit / Max Loss inputs (Item 15)
old_reco_buttons = '''        <div class="head-actions">
          <button class="btn ghost" id="onDemandRecommendationBtn">On-demand recommendation</button>
          <button class="btn ghost" id="maxProfitRecommendationBtn" style="border-color:var(--gold-dim);color:var(--gold);">✦ Max Profit</button>
          <button class="btn ghost" id="maxLossRecommendationBtn" style="border-color:rgba(255,92,114,0.4);color:var(--sell);">🛡️ Max Loss</button>
          <button class="btn gold" id="manualAiRecommendationBtn">＋ Ask CA AI</button>
        </div>'''

new_reco_buttons = '''        <div class="head-actions" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <button class="btn ghost" id="onDemandRecommendationBtn">On-demand recommendation</button>
          <div style="display:flex;align-items:center;gap:6px;background:var(--surface-2);padding:3px 8px;border-radius:7px;border:1px solid var(--border-soft);">
            <label style="font-size:10.5px;color:var(--buy);font-weight:600;">Target / Profit ₹</label>
            <input id="recoMaxProfit" type="number" min="0" step="100" class="tool-input" placeholder="e.g. 5000" style="width:95px;height:26px;font-size:11px;padding:2px 6px;">
          </div>
          <div style="display:flex;align-items:center;gap:6px;background:var(--surface-2);padding:3px 8px;border-radius:7px;border:1px solid var(--border-soft);">
            <label style="font-size:10.5px;color:var(--sell);font-weight:600;">Max Loss ₹</label>
            <input id="recoMaxLoss" type="number" min="0" step="100" class="tool-input" placeholder="e.g. 2000" style="width:95px;height:26px;font-size:11px;padding:2px 6px;">
          </div>
          <button class="btn gold" id="manualAiRecommendationBtn">＋ Ask CA AI</button>
        </div>'''

assert old_reco_buttons in content, "old_reco_buttons not found"
content = content.replace(old_reco_buttons, new_reco_buttons, 1)

# 6. Update Orders & Positions Panel (Item 20, 21)
old_orders_panel = '''    <div class="panel" id="panel-orders">
      <div class="page-head"><div><div class="page-title">Orders &amp; Positions</div><div class="page-sub">Live account state and user-isolated orders</div></div><div class="head-actions"><button class="btn gold" id="ordersNewBtn">＋ New Order</button></div></div>
      <div id="fundCards" class="grid grid-4" style="margin-bottom:14px"></div>
      <div class="card" style="margin-bottom:14px"><div class="card-head"><div class="card-title">Open Positions</div></div><div id="positionsTable"><div class="data-empty">Loading positions…</div></div></div>
      <div class="card"><div class="card-head"><div class="card-title">Orders</div></div><div id="ordersTable"><div class="data-empty">Loading orders…</div></div></div>
    </div>'''

new_orders_panel = '''    <div class="panel" id="panel-orders">
      <div class="page-head">
        <div>
          <div class="page-title">Orders &amp; Positions</div>
          <div class="page-sub">Paper executions with entry, SL, target, P&amp;L and CA AI rationale history</div>
        </div>
        <div class="head-actions">
          <button class="btn gold" id="ordersNewBtn">＋ New Order</button>
        </div>
      </div>

      <!-- Positions Section with Open vs Closed Sub-Tabs -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-head" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <div class="card-title" style="display:flex;align-items:center;gap:8px;">
            <span>💼 Positions</span>
            <span class="badge ghost" id="positionsCountBadge" style="font-size:10.5px;">0 open</span>
          </div>
          <div style="display:flex;gap:6px;">
            <button class="tab-sub-btn active" id="subTabOpenPositions">Open Positions</button>
            <button class="tab-sub-btn" id="subTabClosedPositions">Closed / Past Positions</button>
          </div>
        </div>
        <div id="positionsTable" class="table-wrap"><div class="data-empty">Loading positions…</div></div>
      </div>

      <!-- Orders Section with Today's vs Past Sub-Tabs -->
      <div class="card">
        <div class="card-head" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <div class="card-title" style="display:flex;align-items:center;gap:8px;">
            <span>⚡ Orders</span>
            <span class="badge ghost" id="ordersCountBadge" style="font-size:10.5px;">0 today</span>
          </div>
          <div style="display:flex;gap:6px;">
            <button class="tab-sub-btn active" id="subTabTodayOrders">Today's Orders</button>
            <button class="tab-sub-btn" id="subTabPastOrders">Past Orders</button>
          </div>
        </div>
        <div id="ordersTable" class="table-wrap"><div class="data-empty">Loading orders…</div></div>
      </div>
    </div>'''

assert old_orders_panel in content, "old_orders_panel not found"
content = content.replace(old_orders_panel, new_orders_panel, 1)

# 7. Add Admin Fund Allocation Widget in Funds Panel (Item 22)
old_funds_head = '''        <div class="head-actions" style="display:flex;gap:8px;align-items:center;">
          <button class="btn ghost small" id="fundsRefreshBtn" title="Refresh Wallet Balances">↻ Refresh</button>
          <button class="btn ghost small" id="fundsResetAllBtn" style="color:var(--sell);" title="Reset all 3 wallets to fresh ₹1,00,000">↺ Reset Wallets (₹1L Each)</button>
        </div>'''

new_funds_head = '''        <div class="head-actions" style="display:flex;gap:8px;align-items:center;">
          <button class="btn ghost small" id="fundsRefreshBtn" title="Refresh Wallet Balances">↻ Refresh</button>
          <button class="btn ghost small" id="fundsResetAllBtn" style="color:var(--sell);display:none;" title="Reset all 3 wallets to fresh ₹1,00,000">↺ Reset Wallets (₹1L Each)</button>
        </div>'''

assert old_funds_head in content, "old_funds_head not found"
content = content.replace(old_funds_head, new_funds_head, 1)

# Add Admin Fund Allocation Card right after 3 wallet cards
old_wallets_grid = '''        <div class="card stat-card" style="border-left:4px solid #60A5FA;padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="label" style="font-weight:700;color:var(--text);font-size:12px;">🤖 Auto-Trade Funds</span>
            <span class="tag" style="background:rgba(96,165,250,0.15);color:#60A5FA;font-size:9px;">Autonomous Bot</span>
          </div>
          <div class="value" id="walletAutoBalance" style="font-size:22px;font-weight:700;margin:6px 0;color:#60A5FA;">₹1,00,000.00</div>
          <div class="muted" id="walletAutoUsed" style="font-size:11px;">Used Margin: ₹0.00</div>
        </div>
      </div>'''

new_wallets_grid = '''        <div class="card stat-card" style="border-left:4px solid #60A5FA;padding:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="label" style="font-weight:700;color:var(--text);font-size:12px;">🤖 Auto-Trade Funds</span>
            <span class="tag" style="background:rgba(96,165,250,0.15);color:#60A5FA;font-size:9px;">Autonomous Bot</span>
          </div>
          <div class="value" id="walletAutoBalance" style="font-size:22px;font-weight:700;margin:6px 0;color:#60A5FA;">₹1,00,000.00</div>
          <div class="muted" id="walletAutoUsed" style="font-size:11px;">Used Margin: ₹0.00</div>
        </div>
      </div>

      <!-- Admin Cross-Account Fund Allocation Widget (Item 22) -->
      <div class="card" id="adminFundTransferCard" style="display:none;margin-bottom:16px;padding:14px 16px;border:1px solid var(--gold-dim);background:var(--surface);">
        <div class="card-head" style="margin-bottom:10px;">
          <div class="card-title" style="color:var(--gold);">👑 Admin Panel: Allocate Funds to User</div>
          <div class="muted" style="font-size:11px;">Credit paper capital to any registered user by their Gmail address</div>
        </div>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
          <div class="finder-field" style="flex:1;min-width:220px;">
            <label>Registered Gmail ID</label>
            <input id="adminFundTargetEmail" class="tool-input" placeholder="user@gmail.com">
          </div>
          <div class="finder-field" style="width:130px;">
            <label>Amount (₹)</label>
            <input id="adminFundAmount" type="number" step="10000" class="tool-input" value="100000">
          </div>
          <div class="finder-field" style="width:130px;">
            <label>Target Wallet</label>
            <select id="adminFundWallet" class="tool-input">
              <option value="all">All Wallets</option>
              <option value="trading">Trading Funds</option>
              <option value="testing">Testing Funds</option>
              <option value="auto_trade">Auto-Trade Funds</option>
            </select>
          </div>
          <button class="btn gold" id="adminFundSubmitBtn" style="margin-top:18px;height:38px;">Credit Funds</button>
        </div>
      </div>'''

assert old_wallets_grid in content, "old_wallets_grid not found"
content = content.replace(old_wallets_grid, new_wallets_grid, 1)

# 8. Full-Width Backtesting Layout (Item 18) & Date Range Inputs (Item 5)
old_bt_controls = '''            <label style="font-size:11px;color:var(--text-dim);font-weight:600;">
              Start Date &amp; Time
              <input type="datetime-local" id="btDateTime" class="input" style="padding:5px 10px;font-size:11px;margin-left:4px;border-radius:6px;background:var(--surface-2);color:var(--text);border:1px solid var(--border-soft);">
            </label>'''

new_bt_controls = '''            <label style="font-size:11px;color:var(--text-dim);font-weight:600;">
              From
              <input type="datetime-local" id="btFromDateTime" class="input" style="padding:5px 8px;font-size:11px;margin-left:3px;border-radius:6px;background:var(--surface-2);color:var(--text);border:1px solid var(--border-soft);">
            </label>
            <label style="font-size:11px;color:var(--text-dim);font-weight:600;">
              To
              <input type="datetime-local" id="btToDateTime" class="input" style="padding:5px 8px;font-size:11px;margin-left:3px;border-radius:6px;background:var(--surface-2);color:var(--text);border:1px solid var(--border-soft);">
            </label>'''

assert old_bt_controls in content, "old_bt_controls not found"
content = content.replace(old_bt_controls, new_bt_controls, 1)

# Replace the 2-column split grid with full-width stacked backtesting layout (Item 18)
old_bt_grid = '''      <!-- Main Replay Split Grid (Spacey & Modern) -->
      <div class="grid grid-2" style="gap:16px;margin-bottom:16px;align-items:start;">
        <!-- Left: Replay Candlestick Chart with Full Indicator & Oscillator Parity -->
        <div class="card" style="padding:14px;background:var(--surface);">
          <div class="card-head" style="margin-bottom:8px;flex-wrap:wrap;gap:8px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span class="card-title">Simulated Chart</span>
              <span class="tag buy" id="btTrendTag" style="font-size:10px;">NEUTRAL</span>
            </div>
            <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
              <button class="tf-btn active" id="btToggleEma" style="padding:2px 7px;font-size:10px;" title="Toggle 20-EMA">EMA 20</button>
              <button class="tf-btn active" id="btToggleBb" style="padding:2px 7px;font-size:10px;" title="Toggle Bollinger Bands">BB (20,2)</button>
              <button class="tf-btn active" id="btToggleSt" style="padding:2px 7px;font-size:10px;" title="Toggle Supertrend">Supertrend</button>
              <button class="tf-btn active" id="btToggleOsc" style="padding:2px 7px;font-size:10px;" title="Toggle RSI Sub-pane">RSI (14)</button>
            </div>
            <div style="display:flex;gap:10px;font-family:var(--font-mono);font-size:11px;flex-wrap:wrap;width:100%;padding-top:4px;" id="btOhlcBar">
              <span>O: <b id="btO">--</b></span>
              <span>H: <b id="btH">--</b></span>
              <span>L: <b id="btL">--</b></span>
              <span>C: <b id="btC">--</b></span>
              <span>RSI: <b id="btRsi">--</b></span>
            </div>
          </div>
          <div style="position:relative;height:420px;background:var(--surface-2);border-radius:8px;border:1px solid var(--border-soft);overflow:hidden;" id="btChartViewport">
            <canvas id="btCanvas" style="width:100%;height:100%;display:block;cursor:crosshair;"></canvas>
            <div id="btChartPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-faint);font-size:13px;pointer-events:none;">
              Select Start Date &amp; Time and click "Load Replay" to begin.
            </div>
          </div>
        </div>

        <!-- Right: CA AI Point-in-Time Signals & Trade Ticket -->
        <div style="display:flex;flex-direction:column;gap:14px;">
          <!-- CA AI Live Signal Card (Clickable Entry, SL, Target) -->
          <div class="card" style="padding:14px;background:var(--surface);border:1px solid rgba(38,217,166,0.25);">
            <div class="card-head" style="margin-bottom:8px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;background:var(--buy-bg);color:var(--buy);font-size:12px;font-weight:700;">✦</span>
                <span class="card-title">CA AI Point-in-Time Signal</span>
              </div>
              <span class="tag neutral" id="btSignalBadge" style="font-size:11px;font-weight:700;">WAIT</span>
            </div>
            <div id="btSignalContent" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px;">
              <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);text-align:center;cursor:pointer;" id="btSignalEntryBox" title="Click to view Entry formula & calculation proof">
                <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Entry ⓘ</div>
                <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--text);text-decoration:underline dashed;" id="btSignalEntry">--</div>
              </div>
              <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);text-align:center;cursor:pointer;" id="btSignalSlBox" title="Click to view Dynamic Stop Loss formula">
                <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Stop Loss ⓘ</div>
                <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--sell);text-decoration:underline dashed;" id="btSignalSl">--</div>
              </div>
              <div style="background:var(--surface-2);padding:8px 10px;border-radius:6px;border:1px solid var(--border-soft);text-align:center;cursor:pointer;" id="btSignalTgtBox" title="Click to view Target formula & calculation proof">
                <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Target ⓘ</div>
                <div style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--buy);text-decoration:underline dashed;" id="btSignalTgt">--</div>
              </div>
            </div>
            <div class="card-sub" id="btSignalRationale" style="font-size:11.5px;color:var(--text-dim);line-height:1.4;cursor:pointer;" title="Click to inspect mathematical proof">
              Replay engine calculates signals strictly on historical data available up to the current simulated minute. Zero future lookahead. Click Entry/SL/Target to inspect formulas.
            </div>
          </div>

          <!-- Trade Execution Ticket -->
          <div class="card" style="padding:14px;background:var(--surface);">
            <div class="card-head" style="margin-bottom:10px;">
              <span class="card-title">Place Simulated Trade</span>
              <span class="muted" style="font-size:11px;">Paper ledger execution</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px;">
              <div class="finder-field">
                <label>Qty / Lots</label>
                <input id="btOrderQty" type="number" min="1" value="10" class="input" style="padding:6px;border-radius:6px;font-size:12px;">
              </div>
              <div class="finder-field">
                <label>Custom SL (optional)</label>
                <input id="btCustomSl" type="number" step="0.1" placeholder="Auto" class="input" style="padding:6px;border-radius:6px;font-size:12px;">
              </div>
              <div class="finder-field">
                <label>Custom Target</label>
                <input id="btCustomTgt" type="number" step="0.1" placeholder="Auto" class="input" style="padding:6px;border-radius:6px;font-size:12px;">
              </div>
            </div>
            <div style="display:flex;gap:10px;">
              <button class="btn gold" id="btBuyBtn" style="flex:1;justify-content:center;padding:9px;font-weight:700;background:var(--buy);color:#0B2A1E;">⚡ Buy / Long</button>
              <button class="btn ghost" id="btSellBtn" style="flex:1;justify-content:center;padding:9px;font-weight:700;border-color:var(--sell);color:var(--sell);">⚡ Sell / Short</button>
            </div>
          </div>
        </div>
      </div>'''

new_bt_grid = '''      <!-- Full-Width Replay Chart Container (Item 18) -->
      <div class="card" style="padding:14px;background:var(--surface);margin-bottom:16px;width:100%;">
        <div class="card-head" style="margin-bottom:8px;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="card-title">Simulated Chart</span>
            <span class="tag buy" id="btTrendTag" style="font-size:10.5px;">Uptrend</span>
          </div>
          <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;">
            <button class="tf-btn active" id="btToggleEma" style="padding:3px 9px;font-size:10.5px;" title="Toggle 20-EMA">EMA 20</button>
            <button class="tf-btn active" id="btToggleBb" style="padding:3px 9px;font-size:10.5px;" title="Toggle Bollinger Bands">BB (20,2)</button>
            <button class="tf-btn active" id="btToggleSt" style="padding:3px 9px;font-size:10.5px;" title="Toggle Supertrend">Supertrend</button>
            <button class="tf-btn active" id="btToggleOsc" style="padding:3px 9px;font-size:10.5px;" title="Toggle RSI Sub-pane">RSI (14)</button>
          </div>
          <div style="display:flex;gap:12px;font-family:var(--font-mono);font-size:11.5px;flex-wrap:wrap;width:100%;padding-top:4px;" id="btOhlcBar">
            <span>O: <b id="btO">--</b></span>
            <span>H: <b id="btH">--</b></span>
            <span>L: <b id="btL">--</b></span>
            <span>C: <b id="btC">--</b></span>
            <span>RSI: <b id="btRsi">--</b></span>
          </div>
        </div>
        <div style="position:relative;height:460px;width:100%;background:var(--surface-2);border-radius:8px;border:1px solid var(--border-soft);overflow:hidden;" id="btChartViewport">
          <canvas id="btCanvas" style="width:100%;height:100%;display:block;cursor:crosshair;"></canvas>
          <div id="btChartPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--text-faint);font-size:13px;pointer-events:none;">
            Select dates and click "Load Replay" to begin tick-by-tick simulation.
          </div>
        </div>
      </div>

      <!-- Full-Width Point-in-Time Signal & Trade Execution Stacked (Item 18) -->
      <div class="card" style="padding:14px 16px;background:var(--surface);border:1px solid rgba(38,217,166,0.3);margin-bottom:16px;">
        <div class="card-head" style="margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:6px;background:var(--buy-bg);color:var(--buy);font-size:13px;font-weight:700;">✦</span>
            <span class="card-title">CA AI Point-in-Time Signal &amp; Execution</span>
          </div>
          <span class="tag buy" id="btSignalBadge" style="font-size:11.5px;font-weight:700;">BUY</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(130px, 1fr));gap:10px;margin-bottom:12px;">
          <div style="background:var(--surface-2);padding:8px 12px;border-radius:6px;border:1px solid var(--border-soft);text-align:center;cursor:pointer;" id="btSignalEntryBox">
            <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Entry ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--text);text-decoration:underline dashed;" id="btSignalEntry">--</div>
          </div>
          <div style="background:var(--surface-2);padding:8px 12px;border-radius:6px;border:1px solid var(--border-soft);text-align:center;cursor:pointer;" id="btSignalSlBox">
            <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Stop Loss ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--sell);text-decoration:underline dashed;" id="btSignalSl">--</div>
          </div>
          <div style="background:var(--surface-2);padding:8px 12px;border-radius:6px;border:1px solid var(--border-soft);text-align:center;cursor:pointer;" id="btSignalTgtBox">
            <div style="font-size:9.5px;color:var(--text-faint);text-transform:uppercase;">Target ⓘ</div>
            <div style="font-family:var(--font-mono);font-weight:700;font-size:14px;color:var(--buy);text-decoration:underline dashed;" id="btSignalTgt">--</div>
          </div>
          <div class="finder-field" style="margin:0;">
            <label style="font-size:9.5px;">Qty / Lots</label>
            <input id="btOrderQty" type="number" min="1" value="10" class="input" style="padding:6px;border-radius:6px;font-size:12px;height:34px;">
          </div>
          <div style="display:flex;gap:8px;align-items:flex-end;">
            <button class="btn gold" id="btBuyBtn" style="flex:1;height:34px;font-weight:700;background:var(--buy);color:#0B2A1E;justify-content:center;">⚡ Buy / Long</button>
            <button class="btn ghost" id="btSellBtn" style="flex:1;height:34px;font-weight:700;border-color:var(--sell);color:var(--sell);justify-content:center;">⚡ Sell / Short</button>
          </div>
        </div>
        <div class="card-sub" id="btSignalRationale" style="font-size:11.5px;color:var(--text-dim);line-height:1.45;cursor:pointer;">
          Replay signals computed strictly on data up to the current minute with zero lookahead bias. Click Entry/SL/Target to inspect mathematical proof.
        </div>
      </div>'''

assert old_bt_grid in content, "old_bt_grid not found"
content = content.replace(old_bt_grid, new_bt_grid, 1)

# 9. Add News Discussion Modal (Item 17)
news_modal_html = '''
<!-- CA AI News Discussion Modal (Item 17) -->
<div class="tool-modal" id="newsDiscussionModal" aria-hidden="true" style="display:none;">
  <div class="tool-modal-card" style="max-width:720px;">
    <div class="card-head" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <div class="card-title" style="display:flex;align-items:center;gap:8px;">
        <span style="color:var(--gold);">📰 CA AI News Intelligence &amp; Strategy</span>
      </div>
      <button class="btn ghost small" id="newsDiscussionClose">Close</button>
    </div>
    
    <div style="background:var(--surface-2);border-radius:8px;padding:12px 14px;border:1px solid var(--border-soft);margin-bottom:14px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="tag buy" id="newsModalProbBadge" style="font-weight:700;font-size:11px;">100% Buy Signal</span>
        <span style="font-size:11px;color:var(--text-faint);" id="newsModalMeta">—</span>
      </div>
      <div id="newsModalHeadline" style="font-size:14px;font-weight:700;color:var(--text);line-height:1.4;margin-bottom:8px;"></div>
      <div id="newsModalSummary" style="font-size:12px;color:var(--text-dim);line-height:1.5;"></div>
    </div>

    <!-- Interactive Discussion with CA AI -->
    <div class="card" style="padding:12px;background:var(--surface);border:1px solid var(--border-soft);">
      <div style="font-size:12px;font-weight:700;color:var(--text);margin-bottom:6px;display:flex;align-items:center;gap:6px;">
        <span>💬 Interactive Discussion with CA AI</span>
      </div>
      <div id="newsChatLog" class="ai-chat-log" style="height:200px;background:var(--surface-2);border-radius:6px;padding:8px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;font-size:11.5px;"></div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <input id="newsChatInput" class="tool-input" placeholder="Ask CA AI about options play, IV, risks, or timeline for this news…" style="flex:1;">
        <button class="btn gold small" id="newsChatSendBtn">Ask CA AI</button>
      </div>
    </div>
  </div>
</div>
'''

if 'id="newsDiscussionModal"' not in content:
    content = content.replace('</body>', news_modal_html + '\n</body>', 1)

path.write_text(content, encoding="utf-8")
print("UI Layout fixes applied successfully.")

