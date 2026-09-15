import sys
import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9236

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
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(2)

            res1 = await call("Runtime.evaluate", {
                "expression": "typeof window.loadDashboard",
                "returnByValue": True
            })
            print("typeof window.loadDashboard:", res1)

            res2 = await call("Runtime.evaluate", {
                "expression": "typeof wirePureGreeksSim",
                "returnByValue": True
            })
            print("typeof wirePureGreeksSim:", res2)

            res3 = await call("Runtime.evaluate", {
                "expression": "wirePureGreeksSim()",
                "returnByValue": True
            })
            print("wirePureGreeksSim result:", res3)

            # Test slider input
            res4 = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const s = document.getElementById('chartSimSlider');
                    s.value = 50;
                    s.dispatchEvent(new Event('input'));
                    return {
                        val: s.value,
                        disp: document.getElementById('chartSimSliderDisplay')?.textContent,
                        delta: document.getElementById('chartSimDeltaImpact')?.textContent,
                        gamma: document.getElementById('chartSimGammaImpact')?.textContent,
                        pnl: document.getElementById('chartSimLotPnl')?.textContent
                    };
                })()
                """,
                "returnByValue": True
            })
            print("Slider test result:", res4)

            # Test Confluence table
            res5 = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    updateDashboardConfluenceTable(true, 23118.6, 'NIFTY');
                    const rows = document.querySelectorAll('#dashConfluenceTableBody tr');
                    return {
                        rowCount: rows.length,
                        firstRow: rows[0]?.textContent?.trim(),
                        dowRow: Array.from(rows).find(r => r.textContent.includes('Dow'))?.textContent?.trim()
                    };
                })()
                """,
                "returnByValue": True
            })
            print("Confluence table test:", res5)

    asyncio.run(run())

finally:
    proc.kill()
