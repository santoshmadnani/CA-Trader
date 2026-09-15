import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9265

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--remote-debugging-port={PORT_CHROME}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(2)

try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT_CHROME}/json/list") as resp:
        targets = json.loads(resp.read().decode())
    
    page_target = next(t for t in targets if t.get("type") == "page")
    ws_url = page_target["webSocketDebuggerUrl"]

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get("id") == cur_id:
                        return d

            await call("Runtime.enable")
            await call("Page.enable")

            print("Navigating to https://catrader.site/terminal ...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(4)

            # Check 1: User name
            user_res = await call("Runtime.evaluate", {
                "expression": "document.getElementById('userDisplayName')?.textContent",
                "returnByValue": True
            })
            print("1. User Name:", user_res.get("result", {}).get("result", {}).get("value"))

            # Check 2: Watchlist CRUDEOIL quote
            wl_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const rows = Array.from(document.querySelectorAll('.wl-item')).map(r => ({
                        sym: r.dataset.symbol,
                        ltp: r.querySelector('.wl-ltp')?.textContent?.trim(),
                        chg: r.querySelector('.wl-chg')?.textContent?.trim(),
                        hasRBtn: !!r.querySelector('.wl-r-btn')
                    }));
                    return rows;
                })()
                """,
                "returnByValue": True
            })
            print("2. Watchlist items:")
            print(json.dumps(wl_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 3: Dashboard Tab Elements
            dash_res = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    if (typeof showTab === 'function') showTab('dashboard');
                    if (typeof window.loadDashboard === 'function') await window.loadDashboard();
                    return {
                        symbolTitle: document.getElementById('dashSymbolTitle')?.textContent,
                        symbolLtp: document.getElementById('dashSymbolLtp')?.textContent,
                        hasAdvisoryBox: !!document.getElementById('chartRecoAdvisoryBox'),
                        autoRecoStrip: !!document.getElementById('dashAutoRecoStrip'),
                        threeRationaleCards: !!document.getElementById('dashRationaleThreeCards'),
                        entryDisplay: document.getElementById('dashEntryPriceDisplay')?.textContent,
                        slDisplay: document.getElementById('dashSlPriceDisplay')?.textContent,
                        targetDisplay: document.getElementById('dashTargetPriceDisplay')?.textContent,
                        confluenceRowCount: document.querySelectorAll('#dashConfluenceTableBody tr').length,
                        simSliderExists: !!document.getElementById('chartSimSlider')
                    };
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            print("3. Dashboard Live Verification:")
            print(json.dumps(dash_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 4: Simulator at +75 Points
            sim_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const s = document.getElementById('chartSimSlider');
                    if (!s) return null;
                    s.value = 75;
                    s.dispatchEvent(new Event('input'));
                    return {
                        sliderDisplay: document.getElementById('chartSimSliderDisplay')?.textContent,
                        pointsBadge: document.getElementById('chartSimPointsBadge')?.textContent,
                        deltaGain: document.getElementById('chartSimDeltaImpact')?.textContent,
                        gammaGain: document.getElementById('chartSimGammaImpact')?.textContent,
                        totalNet: document.getElementById('chartSimTotalImpact')?.textContent,
                        lotPnl: document.getElementById('chartSimLotPnl')?.textContent
                    };
                })()
                """,
                "returnByValue": True
            })
            print("4. Pure Greeks Simulator (+75 Pts):")
            print(json.dumps(sim_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 5: Historical Rationale Modal
            hist_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    openHistoricalRationaleModal({
                        symbol: 'CRUDEOIL',
                        recommendation: 'BUY',
                        entry: 10215,
                        stop_loss: 10060,
                        target: 0,
                        technical_basis: 'Breakout above 20-EMA on 15m timeframe',
                        news_basis: 'OPEC+ supply constraint continuation',
                        option_basis: 'ATM 10200 CE'
                    });
                    const m = document.getElementById('historicalRationaleModal');
                    const visible = m && m.style.display === 'flex';
                    const title = document.getElementById('histModalTitle')?.textContent;
                    const rows = document.querySelectorAll('#histModalTableBody tr').length;
                    closeHistoricalRationaleModal();
                    return { visible, title, rows, closed: m && m.style.display === 'none' };
                })()
                """,
                "returnByValue": True
            })
            print("5. Historical Rationale Modal Test:")
            print(json.dumps(hist_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 6: Reports & Funds tabs
            tabs_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const hasSubTrades = !!document.getElementById('btnRepSubUserTrades');
                    const hasSubRecos = !!document.getElementById('btnRepSubSystemRecos');
                    const hasWalletAuto = !!document.getElementById('walletAutoBalance');
                    return { hasSubTrades, hasSubRecos, hasWalletAuto };
                })()
                """,
                "returnByValue": True
            })
            print("6. Reports & Funds verification:", tabs_res.get("result", {}).get("result", {}).get("value"))

    asyncio.run(run())

finally:
    proc.kill()

