with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# Replace lines between <!-- NAV TABS --> and <div class="layout">
start_marker = '<!-- NAV TABS -->'
end_marker = '<div class="layout">'

idx1 = text.find(start_marker)
idx2 = text.find(end_marker)

clean_navtabs = """<!-- NAV TABS -->
<div class="navtabs" id="navtabs">
  <div class="navtab active" data-tab="charts" role="button" tabindex="0" onclick="showTab('charts')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M7 15l3-4 3 2 5-7"/></svg>
    Chart &amp; Technicals
  </div>
  <div class="navtab" data-tab="options" role="button" tabindex="0" onclick="showTab('options')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M9 9h.01M15 9h.01M9 15c1-1.5 5-1.5 6 0"/></svg>
    Option Chain
  </div>
  <div class="navtab" data-tab="reco" role="button" tabindex="0" onclick="showTab('reco')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20"/><circle cx="12" cy="12" r="9"/></svg>
    Recommendation History
  </div>
  <div class="navtab" data-tab="news" role="button" tabindex="0" onclick="showTab('news')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h13a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3z"/><path d="M8 8h8M8 12h8M8 16h4"/></svg>
    News by CA AI
  </div>
  <div class="navtab" data-tab="fundamentals" role="button" tabindex="0" onclick="showTab('fundamentals')">Fundamentals</div>
  <div class="navtab" data-tab="movers" role="button" tabindex="0" onclick="showTab('movers')">Market Movers</div>
  <div class="navtab" data-tab="other-factors" role="button" tabindex="0" onclick="showTab('other-factors')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
    Other Factors
  </div>
  <div class="navtab" data-tab="orders" role="button" tabindex="0" onclick="showTab('orders')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 2h6l1 4H8z"/><rect x="4" y="6" width="16" height="16" rx="2"/><path d="M9 12h6M9 16h6"/></svg>
    Orders &amp; Positions
  </div>
  <div class="navtab" data-tab="funds" id="tab-funds" role="button" tabindex="0" onclick="showTab('funds')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
    Funds
  </div>
  <div class="navtab" data-tab="console" role="button" tabindex="0" onclick="showTab('console')">Server Console</div>
  <div class="navtab" data-tab="reports" role="button" tabindex="0" onclick="showTab('reports')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
    Reports &amp; P&amp;L
  </div>
  <div class="navtab" data-tab="quiz" role="button" tabindex="0" onclick="showTab('quiz')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><circle cx="12" cy="12" r="10"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    Trader Quiz
  </div>
  <div class="navtab" data-tab="tutorial" role="button" tabindex="0" onclick="showTab('tutorial')">Tutorial</div>
</div>

"""

new_text = text[:idx1] + clean_navtabs + text[idx2:]

# Also make sure on startup that S is initialized to NIFTY and onSymbolChanged is called!
# Look at W0()
new_text = new_text.replace(
    "try { await R(); } catch(e) { console.warn('Render watchlist error:', e); }\n    try { void subscribeAllLive(); } catch(_) {}",
    "try { await R(); } catch(e) { console.warn('Render watchlist error:', e); }\n    try { void subscribeAllLive(); } catch(_) {}\n    if(S) { void onSymbolChanged(S); }"
)

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("terminal.html updated successfully!")

