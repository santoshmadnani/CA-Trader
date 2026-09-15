# -*- coding: utf-8 -*-
"""
Release 32 Comprehensive Fixes:
1. Option Search Dropdown: overflow visible on #chartRecoBanner & #chartRecoOptionWrap, high z-index, smart typing filter.
2. Default Option Recommendation: Automatically recommend best Greeks Option (ATM CE for Bullish, ATM PE for Bearish) with entry, SL, target, R:R, lot size.
3. Speed & Turbo Load: Fix 25s/45s hanging timeouts in api() & A(), instant local synthesis for candlestick patterns, chart patterns, and indicators.
4. Hanging Tabs: Auto-fallback for News by CA AI, Fundamentals, Recommendation History, and Market Movers so they never hang on Loading.
5. Font Name: Replace Zerodha Kite (System Clean) with Segoe UI / SF Pro (System Clean).
6. Recommendation Rationale Overhaul: New heading 'Recommendation Rationale', exactly 1 section per row (5 rows stacked vertically).
7. Crosshair Dotted Lines & Badges: Canvas rendering of crisp dotted crosshair and sharp X/Y axis badges for time & LTP.
8. Move to Latest Candle Button: Permanently accessible #chartFastForward button with >> icon.
9. Eliminate Flickering Text: Remove .badge positioning from chartGreeksIvBadge.
10. Strict rule: NO EMOJIS anywhere.
"""

import re
import sys

def patch_app_py():
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Parallelize news gathering in news_ca_ai_feed
    old_news_gather = """        if mode in ("all", "stock"):
            stk_res = news_result(_target_news_query(sym), 30, sym, uid)
            for ev in (stk_res.get("events") or []):
                ev["scope"] = "stock"
                events_raw.append(ev)
        if mode in ("all", "global"):
            glo_res = news_result("crude oil OPEC inflation Fed RBI interest rates rupee dollar markets budget GDP", 30, "GLOBAL", uid)
            for ev in (glo_res.get("events") or []):
                ev["scope"] = "global"
                events_raw.append(ev)"""

    new_news_gather = """        loop = asyncio.get_running_loop()
        tasks = []
        if mode in ("all", "stock"):
            tasks.append(loop.run_in_executor(None, news_result, _target_news_query(sym), 30, sym, uid))
        if mode in ("all", "global"):
            tasks.append(loop.run_in_executor(None, news_result, "crude oil OPEC inflation Fed RBI interest rates rupee dollar markets budget GDP", 30, "GLOBAL", uid))
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, sc in zip(results, ["stock", "global"] if len(tasks) == 2 else [mode]):
                if isinstance(res, dict):
                    for ev in (res.get("events") or []):
                        ev["scope"] = sc
                        events_raw.append(ev)"""

    if old_news_gather in content:
        content = content.replace(old_news_gather, new_news_gather)
        print("app.py: Parallelized news gathering in news_ca_ai_feed")
    else:
        print("app.py: news gathering already updated or pattern not found")

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("app.py updated successfully.")

def patch_terminal_html():
    with open('terminal.html', 'r', encoding='utf-8') as f:
        c = f.read()

    # -------------------------------------------------------------------------
    # 1. Fix Hanging Timeouts in A() and api() - was 25000 / 45000 ms!
    # -------------------------------------------------------------------------
    old_A_timeout = "const timeoutMs=Math.max(25000,Number(o.timeoutMs||35000))"
    new_A_timeout = "const timeoutMs=Math.max(1200,Number(o.timeoutMs||4500))"
    if old_A_timeout in c:
        c = c.replace(old_A_timeout, new_A_timeout)
        print("terminal.html: Fixed timeout in function A()")

    old_A_retry = "timeoutMs:45000"
    new_A_retry = "timeoutMs:4000"
    c = c.replace(old_A_retry, new_A_retry)

    old_api_timeout = "const timeoutMs = Math.max(25000, Number(options.timeoutMs || 35000));"
    new_api_timeout = "const timeoutMs = Math.max(1200, Number(options.timeoutMs || 4500));"
    if old_api_timeout in c:
        c = c.replace(old_api_timeout, new_api_timeout)
        print("terminal.html: Fixed timeout in window.api()")

    old_api_retry = "timeoutMs: 45000"
    new_api_retry = "timeoutMs: 4000"
    c = c.replace(old_api_retry, new_api_retry)

    # -------------------------------------------------------------------------
    # 2. Fix Item 9: Flickering glitchy IV: --% text above Sell button
    # -------------------------------------------------------------------------
    old_iv_badge = '<span class="badge ghost" id="chartGreeksIvBadge" style="font-family:var(--font-mono);font-size:11px;">IV: --%</span>'
    new_iv_badge = '<span class="tag neutral" id="chartGreeksIvBadge" style="font-family:var(--font-mono);font-size:11px;position:static !important;display:inline-flex;">IV: --%</span>'
    if old_iv_badge in c:
        c = c.replace(old_iv_badge, new_iv_badge)
        print("terminal.html: Fixed chartGreeksIvBadge class from badge ghost to tag neutral")

    # -------------------------------------------------------------------------
    # 3. Fix Item 5: Zerodha Kite Style label -> Segoe UI / SF Pro (System Clean)
    # -------------------------------------------------------------------------
    old_font_opt = '<option value="system" selected>Zerodha Kite (System Clean)</option>'
    new_font_opt = '<option value="system" selected>Segoe UI / SF Pro (System Clean)</option>'
    if old_font_opt in c:
        c = c.replace(old_font_opt, new_font_opt)
        print("terminal.html: Updated font label to Segoe UI / SF Pro (System Clean)")

    # -------------------------------------------------------------------------
    # 4. Fix Item 1: Option Search Dropdown visibility & parent overflow
    # -------------------------------------------------------------------------
    # In CSS or inline styles, ensure #chartRecoBanner and #chartRecoOptionWrap are overflow: visible !important
    c = c.replace(
        'id="chartRecoBanner" style="margin-bottom:12px;padding:12px 16px;background:var(--surface);border:1px solid rgba(38,217,166,0.3);box-shadow:0 6px 20px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;"',
        'id="chartRecoBanner" style="margin-bottom:12px;padding:12px 16px;background:var(--surface);border:1px solid rgba(38,217,166,0.3);box-shadow:0 6px 20px rgba(0,0,0,0.2);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;overflow:visible !important;position:relative;z-index:1000;"'
    )
    c = c.replace(
        '<div id="chartRecoOptionWrap" style="position:relative;display:inline-flex;align-items:center;">',
        '<div id="chartRecoOptionWrap" style="position:relative;display:inline-flex;align-items:center;z-index:1001;overflow:visible !important;">'
    )
    c = c.replace(
        '<div id="chartRecoOptionSuggestions" class="auto-suggestions-menu" style="display:none;position:absolute;top:calc(100% + 4px);left:0;width:280px;z-index:2500;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 14px 32px rgba(0,0,0,0.45);max-height:260px;overflow-y:auto;"></div>',
        '<div id="chartRecoOptionSuggestions" class="auto-suggestions-menu" style="display:none;position:absolute;top:calc(100% + 6px);left:0;min-width:340px;width:340px;z-index:99999 !important;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 18px 45px rgba(0,0,0,0.85);max-height:280px;overflow-y:auto;"></div>'
    )

    # -------------------------------------------------------------------------
    # 5. Fix Item 8: Move to latest candle button styling & visibility
    # -------------------------------------------------------------------------
    c = re.sub(
        r'\.chart-fast-forward\s*\{[^}]*\}',
        '.chart-fast-forward{position:absolute;right:86px;bottom:36px;z-index:100;width:34px;height:30px;display:flex !important;align-items:center;justify-content:center;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:7px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.3);opacity:0.95;} .chart-fast-forward:hover{opacity:1;border-color:var(--gold);color:var(--gold);}',
        c
    )

    # -------------------------------------------------------------------------
    # 6. Fix Item 6: Replace old Institutional Recommendation Rationale & Evidence Matrix
    #    with the 1 section per row "Recommendation Rationale"
    # -------------------------------------------------------------------------
    evidence_start = c.find('<!-- Institutional Recommendation Rationale & Evidence Matrix')
    if evidence_start != -1:
        evidence_end = c.find('<div class="chart-shell"', evidence_start)
        if evidence_end != -1:
            new_rationale_html = """<!-- Recommendation Rationale Section (Item 6 - Exactly 1 Section Per Row) -->
      <div class="card" id="chartRecoEvidenceSection" style="margin-bottom:14px;padding:16px 18px;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:0 4px 18px rgba(0,0,0,0.14);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;border-bottom:1px solid var(--border-soft);padding-bottom:10px;flex-wrap:wrap;gap:8px;">
          <div style="display:flex;align-items:center;gap:10px;">
            <span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;background:rgba(24,144,255,0.15);color:var(--primary);font-size:13px;font-weight:700;">R</span>
            <b style="font-size:15px;color:var(--text);font-family:var(--font-display);">Recommendation Rationale</b>
            <span class="tag buy" id="recoRationaleSignalTag" style="font-size:11px;font-weight:700;">BUY OPTION SETUP</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="muted" style="font-size:11px;">1 Section Per Row Institutional Proof Engine</span>
            <button type="button" class="btn ghost small" id="toggleEvidenceCollapse" style="padding:2px 8px;font-size:10.5px;height:24px;">Collapse</button>
          </div>
        </div>

        <div id="recoEvidenceBody" style="display:flex;flex-direction:column;gap:12px;">
          <!-- Row 1: Technical Indicators -->
          <div class="card" style="padding:12px 14px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
              <b style="font-size:11.5px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">1. Technicals (All Indicators Aligning with Recommendation Signal)</b>
              <span class="tag neutral" id="recoTechConfluenceCount" style="font-size:10px;">Confluent Indicators</span>
            </div>
            <div id="recoRationaleTechnicals" style="display:flex;flex-wrap:wrap;gap:8px;">
              <div class="muted" style="font-size:11.5px;">Loading technical indicators aligned with overall signal...</div>
            </div>
          </div>

          <!-- Row 2: News Catalysts -->
          <div class="card" style="padding:12px 14px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
              <b style="font-size:11.5px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">2. News (Top Bullish/Bearish High-Impact Catalysts from News by CA AI)</b>
              <a href="javascript:void(0)" onclick="showTab('news')" class="btn-link" style="font-size:11px;color:var(--gold);text-decoration:none;">View All News by CA AI &gt;</a>
            </div>
            <div id="recoRationaleNews" style="display:flex;flex-direction:column;gap:7px;">
              <div class="muted" style="font-size:11.5px;">Loading top high-impact news catalysts...</div>
            </div>
          </div>

          <!-- Row 3: Option Greeks -->
          <div class="card" style="padding:12px 14px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
              <b style="font-size:11.5px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">3. Greeks (Live Contract Delta, Gamma, Theta, Vega, IV &amp; Moneyness)</b>
              <span id="recoRationaleGreeksContract" class="tag gold" style="font-size:10.5px;font-family:var(--font-mono);">ATM Option</span>
            </div>
            <div id="recoRationaleGreeks" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(130px, 1fr));gap:8px;">
              <!-- Populated with Greeks -->
            </div>
          </div>

          <!-- Row 4: Candlestick & Chart Patterns -->
          <div class="card" style="padding:12px 14px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
              <b style="font-size:11.5px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">4. Candlestick &amp; Chart Patterns (Detected Trend Confirmations)</b>
              <span class="muted" style="font-size:10.5px;">Price Action Evidence</span>
            </div>
            <div id="recoRationalePatterns" style="display:flex;flex-wrap:wrap;gap:8px;">
              <div class="muted" style="font-size:11.5px;">Scanning candlestick and chart patterns...</div>
            </div>
          </div>

          <!-- Row 5: Other Factors -->
          <div class="card" style="padding:12px 14px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px;">
              <b style="font-size:11.5px;color:var(--text);text-transform:uppercase;letter-spacing:0.5px;">5. Other Factors (Global Macro Drivers, VIX Regime &amp; Benchmarks)</b>
              <span class="muted" style="font-size:10.5px;">Macro Drivers &amp; Regime</span>
            </div>
            <div id="recoRationaleOtherFactors" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:8px;">
              <!-- Populated with Macro Factors -->
            </div>
          </div>
        </div>
      </div>

      """
            c = c[:evidence_start] + new_rationale_html + c[evidence_end:]
            print("terminal.html: Replaced Evidence Matrix with 5-Row Recommendation Rationale")

    with open('terminal.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print("terminal.html part 1 written.")

if __name__ == '__main__':
    patch_app_py()
    patch_terminal_html()

