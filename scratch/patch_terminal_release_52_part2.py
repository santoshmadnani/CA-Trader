import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Insert Turbo Refresh button in topbar
target_notif_wrap = '<div class="top-icon-wrap"><button class="icon-btn" id="notificationBtn" title="Notifications">'
replacement_notif_wrap = '<button id="turboLoadBtn" class="btn gold small" onclick="turboLoadAll()" title="Refresh all sections without reloading the browser" style="padding:3px 10px;font-size:11px;font-weight:600;border-radius:12px;margin-right:6px;display:inline-flex;align-items:center;gap:4px;">⚡ Turbo Refresh</button><div class="top-icon-wrap"><button class="icon-btn" id="notificationBtn" title="Notifications">'

if target_notif_wrap in text:
    text = text.replace(target_notif_wrap, replacement_notif_wrap, 1)
    print('[OK] Injected ⚡ Turbo Refresh button into topbar')
else:
    print('[FAIL] target_notif_wrap not found')
    sys.exit(1)

# 2. Add Right-Side Notification Container to body
target_body_end = "</body>"
notif_container_html = """  <!-- Right-Side High Alert & Golden Trade Notification Drawer (Item 19 & 20) -->
  <div id="rightSideNotificationContainer" style="position:fixed;top:64px;right:18px;z-index:99999;display:flex;flex-direction:column;gap:10px;pointer-events:none;max-width:360px;width:90vw;"></div>

</body>"""

if target_body_end in text:
    text = text.replace(target_body_end, notif_container_html, 1)
    print('[OK] Injected rightSideNotificationContainer into body')
else:
    print('[FAIL] target_body_end not found')
    sys.exit(1)

# 3. Add Dedicated Notifications Center Panel & Admin Passbook Panel
# Place right after panel-orders or panel-settings
target_panel_orders = '</div\n\n    <!-- ============ RISK & TRADING FITNESS ============'
# Let's find end of panel-settings
idx_settings = text.find('id="panel-settings"')
if idx_settings == -1: idx_settings = text.find("id='panel-settings'")
print('idx_settings:', idx_settings)

end_settings = text.find('</div>\n    </div>', idx_settings)
if end_settings == -1: end_settings = text.find('</div\n    </div', idx_settings)
print('end_settings:', end_settings)

new_panels_html = """
    <!-- ============ DEDICATED NOTIFICATIONS CENTER (Item 22) ============ -->
    <div class="panel" id="panel-notifications" style="display:none;">
      <div class="page-head">
        <div>
          <div class="page-title">Notifications &amp; Alert Center</div>
          <div class="page-sub">Institutional alerts, Golden Trade triggers, Sentinel risk advisories, and breaking news</div>
        </div>
        <div class="head-actions" style="display:flex;gap:8px;">
          <button class="btn ghost small" onclick="loadDedicatedNotifications(true)">↻ Refresh</button>
          <button class="btn small" onclick="markAllNotificationsRead()">✓ Mark All Read</button>
        </div>
      </div>

      <div class="card" style="margin-bottom:16px;">
        <div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;border-bottom:1px solid var(--border-soft);margin-bottom:12px;">
          <button class="tab-sub-btn active" onclick="filterDedicatedNotifications('all', this)">All Notifications</button>
          <button class="tab-sub-btn" onclick="filterDedicatedNotifications('golden', this)">🌟 Golden Trades</button>
          <button class="tab-sub-btn" onclick="filterDedicatedNotifications('risk', this)">🛡️ Risk Advisories</button>
          <button class="tab-sub-btn" onclick="filterDedicatedNotifications('news', this)">📰 High-Impact News</button>
        </div>

        <div id="dedicatedNotifList" style="display:flex;flex-direction:column;gap:8px;min-height:200px;">
          <div class="muted" style="text-align:center;padding:24px;">Loading notifications…</div>
        </div>
      </div>
    </div>

    <!-- ============ ADMIN API & RESOURCE PASSBOOK STATEMENT (Item 12) ============ -->
    <div class="panel" id="panel-api-passbook" style="display:none;">
      <div class="page-head">
        <div>
          <div class="page-title">Admin API &amp; Resource Statement Passbook</div>
          <div class="page-sub">Real-time Upstox rate limits (RPM vs actual), Gemini AI token usage, and live audit trail (Admin Only)</div>
        </div>
        <div class="head-actions" style="display:flex;gap:8px;">
          <span id="passbookAutoSyncBadge" class="tag buy" style="font-size:10px;">● Live 3s Meter</span>
          <button class="btn ghost small" onclick="loadAdminApiPassbook()">↻ Refresh Statement</button>
        </div>
      </div>

      <!-- Real-time Quota & Usage Meters -->
      <div class="grid grid-2" style="margin-bottom:16px;gap:12px;">
        <!-- Upstox Meter -->
        <div class="card" style="border-left:4px solid var(--buy);background:var(--surface);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:13px;color:var(--text);">Upstox API Live Meter</b>
            <span id="upstoxMeterStatus" class="tag buy" style="font-size:10px;">HEALTHY</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
            <span class="muted" style="font-size:11px;">Current Requests / Minute:</span>
            <b id="upstoxRpmText" style="font-family:var(--font-mono);font-size:15px;color:var(--buy);">18 / 250 RPM</b>
          </div>
          <div style="width:100%;height:6px;background:var(--surface-2);border-radius:3px;overflow:hidden;margin-bottom:8px;">
            <div id="upstoxRpmBar" style="width:7%;height:100%;background:var(--buy);transition:width 0.3s;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);">
            <span>Today's Total REST Calls: <b id="upstoxTotalCallsText" style="color:var(--text);">1,420</b></span>
            <span>Limit: 250 req/min</span>
          </div>
        </div>

        <!-- Gemini AI Meter -->
        <div class="card" style="border-left:4px solid var(--gold);background:var(--surface);">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
            <b style="font-size:13px;color:var(--text);">Google Gemini 2.0 AI Engine</b>
            <span id="geminiMeterStatus" class="tag gold" style="font-size:10px;">OPTIMAL</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
            <span class="muted" style="font-size:11px;">Tokens Consumed Today:</span>
            <b id="geminiTodayTokensText" style="font-family:var(--font-mono);font-size:15px;color:var(--gold);">42,500 tokens</b>
          </div>
          <div style="width:100%;height:6px;background:var(--surface-2);border-radius:3px;overflow:hidden;margin-bottom:8px;">
            <div id="geminiTpmBar" style="width:4%;height:100%;background:var(--gold);transition:width 0.3s;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-faint);">
            <span>Estimated Cost: <b id="geminiCostText" style="color:var(--text);">₹0.38</b></span>
            <span>Limit: 1,000,000 TPM</span>
          </div>
        </div>
      </div>

      <!-- Data Feeds Health Grid -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-title" style="margin-bottom:10px;font-size:13px;">Connected Data Feeds &amp; Quotas</div>
        <div id="apiDataSourcesGrid" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:10px;font-size:11.5px;">
          <div class="muted" style="padding:10px;">Loading data feeds…</div>
        </div>
      </div>

      <!-- Chronological Statement / Passbook Ledger -->
      <div class="card">
        <div class="card-title" style="margin-bottom:10px;font-size:13px;display:flex;justify-content:space-between;align-items:center;">
          <span>API &amp; AI Usage Statement Ledger (Audit Trail)</span>
          <span class="muted" style="font-size:11px;">Chronological Trail</span>
        </div>
        <div class="table-wrap">
          <table style="width:100%;font-size:11.5px;">
            <thead>
              <tr style="background:var(--surface-2);">
                <th>Timestamp (IST)</th>
                <th>Provider / Service</th>
                <th>Activity / Feature</th>
                <th>Usage / Volume</th>
                <th>Rate / Quota</th>
                <th>Estimated Cost</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody id="apiPassbookLedgerBody">
              <tr><td colspan="7" class="data-empty" style="text-align:center;padding:16px;">Loading statement…</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
"""

# Inject before the end of main layout panels
panels_anchor = "    <!-- ============ RISK & TRADING FITNESS ============"
if panels_anchor in text:
    text = text.replace(panels_anchor, new_panels_html + "\n\n" + panels_anchor, 1)
    print('[OK] Injected panel-notifications and panel-api-passbook into workspace')
else:
    print('[FAIL] panels_anchor not found')
    sys.exit(1)

# Write updated file
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Part 2 HTML applied successfully')

