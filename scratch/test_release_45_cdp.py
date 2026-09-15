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
PORT_CHROME = 9260

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
            
            url = f"file:///{os.path.abspath('terminal.html').replace(os.sep, '/')}"
            print("Loading local terminal:", url)
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(3)

            # Test 1: Check userDisplayName
            user_res = await call("Runtime.evaluate", {
                "expression": "document.getElementById('userDisplayName')?.textContent",
                "returnByValue": True
            })
            print("User display name:", user_res.get("result", {}).get("result", {}).get("value"))

            # Test 2: Switch to Dashboard tab and call loadDashboard
            dash_switch = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    if (typeof showTab === 'function') showTab('dashboard');
                    if (typeof window.loadDashboard === 'function') await window.loadDashboard();
                    return {
                        symbolTitle: document.getElementById('dashSymbolTitle')?.textContent,
                        symbolLtp: document.getElementById('dashSymbolLtp')?.textContent,
                        confluenceRows: document.querySelectorAll('#dashConfluenceTableBody tr').length,
                        entryPriceDisplay: document.getElementById('dashEntryPriceDisplay')?.textContent,
                        slPriceDisplay: document.getElementById('dashSlPriceDisplay')?.textContent,
                        targetPriceDisplay: document.getElementById('dashTargetPriceDisplay')?.textContent,
                        simSliderExists: !!document.getElementById('chartSimSlider'),
                        simDeltaDisplay: document.getElementById('chartSimDeltaImpact')?.textContent
                    };
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            print("Dashboard evaluation:")
            print(json.dumps(dash_switch.get("result", {}).get("result", {}).get("value"), indent=2))

            # Test 3: Test Pure Greeks Simulator Slider at 50 points
            sim_test = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const slider = document.getElementById('chartSimSlider');
                    if (!slider) return { error: 'Slider not found' };
                    slider.value = 50;
                    slider.dispatchEvent(new Event('input'));
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
            print("Simulator 50-pts test:")
            print(json.dumps(sim_test.get("result", {}).get("result", {}).get("value"), indent=2))

            # Test 4: Test Historical Rationale Modal
            modal_test = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    if (typeof openHistoricalRationaleModal !== 'function') return { error: 'openHistoricalRationaleModal missing' };
                    openHistoricalRationaleModal({
                        symbol: 'BANKNIFTY',
                        recommendation: 'BUY',
                        entry: 55800,
                        stop_loss: 55400,
                        target: 56600,
                        technical_basis: 'Breakout above 20-EMA',
                        news_basis: 'Positive earnings flow',
                        option_basis: 'ATM 55800 CE'
                    });
                    const modal = document.getElementById('historicalRationaleModal');
                    const visible = modal && modal.style.display === 'flex';
                    const rows = document.querySelectorAll('#histModalTableBody tr').length;
                    closeHistoricalRationaleModal();
                    const closed = modal && modal.style.display === 'none';
                    return { visible, rows, closed };
                })()
                """,
                "returnByValue": True
            })
            print("Historical modal test:")
            print(json.dumps(modal_test.get("result", {}).get("result", {}).get("value"), indent=2))

            # Test 5: Check Auto-Reco Toggle
            reco_test = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    if (typeof toggleAutoRecoSymbol !== 'function') return { error: 'toggleAutoRecoSymbol missing' };
                    const before = window.__caAutoRecoSymbols.has('CRUDEOIL');
                    toggleAutoRecoSymbol('CRUDEOIL');
                    const after = window.__caAutoRecoSymbols.has('CRUDEOIL');
                    toggleAutoRecoSymbol('CRUDEOIL'); // toggle back
                    return { before, after, restored: window.__caAutoRecoSymbols.has('CRUDEOIL') };
                })()
                """,
                "returnByValue": True
            })
            print("Auto-reco toggle test:")
            print(json.dumps(reco_test.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())

finally:
    proc.kill()
