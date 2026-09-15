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
PORT_CHROME = 9275

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

            # 1. Login
            print("Logging in to https://catrader.site/login ...")
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)

            login_js = """
            (async function() {
                try {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        credentials: 'include',
                        body: JSON.stringify({
                            email: 'santoshmadnani@catrader.site',
                            password: 'Santosh@9340925132#'
                        })
                    });
                    const data = await res.json();
                    return { status: res.status, data: data };
                } catch(e) {
                    return { error: e.message };
                }
            })()
            """
            lres = await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True, "returnByValue": True})
            print("API Login response:", lres.get("result", {}).get("result", {}).get("value"))

            # 2. Navigate to /terminal
            print("Navigating to https://catrader.site/terminal ...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(4)

            # Check 1: User name next to avatar
            user_res = await call("Runtime.evaluate", {
                "expression": "document.getElementById('userDisplayName')?.textContent",
                "returnByValue": True
            })
            print("\n[Item 20] User Display Name:", user_res.get("result", {}).get("result", {}).get("value"))

            # Check 2: Watchlist CRUDEOIL quote resolution and 'R' buttons
            wl_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    return Array.from(document.querySelectorAll('.wl-item')).map(r => ({
                        sym: r.dataset.symbol,
                        ltp: r.querySelector('.wl-ltp')?.textContent?.trim(),
                        chg: r.querySelector('.wl-chg')?.textContent?.trim(),
                        hasR: !!r.querySelector('.wl-r-btn')
                    }));
                })()
                """,
                "returnByValue": True
            })
            print("\n[Item 10 & 21] Watchlist Items:")
            print(json.dumps(wl_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 3: Switch to Dashboard Tab
            dash_res = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    if (typeof showTab === 'function') showTab('dashboard');
                    await new Promise(r => setTimeout(r, 1000));
                    return {
                        symbolTitle: document.getElementById('dashSymbolTitle')?.textContent,
                        symbolLtp: document.getElementById('dashSymbolLtp')?.textContent,
                        symbolChange: document.getElementById('dashSymbolChange')?.textContent,
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
            print("\n[Item 1, 3, 4, 5, 10] Dashboard Live State:")
            print(json.dumps(dash_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 4: Confluence Table Content
            conf_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const rows = Array.from(document.querySelectorAll('#dashConfluenceTableBody tr')).map(r => r.textContent.replace(/\\s+/g, ' ').trim());
                    return {
                        totalRows: rows.length,
                        firstThree: rows.slice(0, 3),
                        dowRow: rows.find(r => r.includes('Dow Jones')),
                        summaryRow: rows.at(-1)
                    };
                })()
                """,
                "returnByValue": True
            })
            print("\n[Item 4, 14, 18, 19] Confluence Table Snapshot:")
            print(json.dumps(conf_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 5: Pure Greeks Price Sensitivity Simulator at 50 pts
            sim_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const s = document.getElementById('chartSimSlider');
                    if (!s) return null;
                    s.value = 50;
                    s.dispatchEvent(new Event('input'));
                    return {
                        sliderDisplay: document.getElementById('chartSimSliderDisplay')?.textContent,
                        pointsBadge: document.getElementById('chartSimPointsBadge')?.textContent,
                        deltaImpact: document.getElementById('chartSimDeltaImpact')?.textContent,
                        gammaImpact: document.getElementById('chartSimGammaImpact')?.textContent,
                        totalImpact: document.getElementById('chartSimTotalImpact')?.textContent,
                        lotPnl: document.getElementById('chartSimLotPnl')?.textContent
                    };
                })()
                """,
                "returnByValue": True
            })
            print("\n[Item 6] Pure Greeks Simulator Live Test (+50 Pts):")
            print(json.dumps(sim_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 6: Compact date pickers and Historical Rationale Modal
            hist_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const fromInput = document.getElementById('recoFilterFrom');
                    const toInput = document.getElementById('recoFilterTo');
                    const hasCompactClass = fromInput && fromInput.classList.contains('compact-date-input');

                    openHistoricalRationaleModal({
                        symbol: 'BANKNIFTY',
                        recommendation: 'BUY',
                        entry: 55794.75,
                        stop_loss: 54957.83,
                        target: 0,
                        technical_basis: 'Breakout above 20-EMA on 15m timeframe',
                        news_basis: 'Positive earnings flow',
                        option_basis: 'ATM 55800 CE'
                    });
                    const m = document.getElementById('historicalRationaleModal');
                    const visible = m && m.style.display === 'flex';
                    const title = document.getElementById('histModalTitle')?.textContent;
                    const rows = document.querySelectorAll('#histModalTableBody tr').length;
                    closeHistoricalRationaleModal();
                    const closed = m && m.style.display === 'none';

                    return { hasCompactClass, modalVisible: visible, modalTitle: title, modalRows: rows, modalClosed: closed };
                })()
                """,
                "returnByValue": True
            })
            print("\n[Item 7 & 8] Date Pickers & Historical Modal Test:")
            print(json.dumps(hist_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Check 7: Funds and Reports Tab
            funds_res = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const hasWalletAuto = !!document.getElementById('walletAutoBalance');
                    const hasUserSub = !!document.getElementById('btnRepSubUserTrades');
                    const hasSysSub = !!document.getElementById('btnRepSubSystemRecos');
                    return { hasWalletAuto, hasUserSub, hasSysSub };
                })()
                """,
                "returnByValue": True
            })
            print("\n[Item 23] Funds & Reports Tabs:")
            print(json.dumps(funds_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Take a full screenshot
            screenshot = await call("Page.captureScreenshot", {"format": "png"})
            import base64
            with open("scratch/release_45_live_verified.png", "wb") as f:
                f.write(base64.b64decode(screenshot["result"]["data"]))
            print("\nSaved live screenshot to scratch/release_45_live_verified.png")

    asyncio.run(run())

finally:
    proc.kill()

