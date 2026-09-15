import subprocess
import time
import json
import urllib.request
import asyncio
import websockets

PORT_CHROME = 9235

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
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

            file_url = "file:///" + r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html".replace("\\", "/")
            await call("Page.navigate", {"url": file_url})
            await asyncio.sleep(2)

            # Switch to other-factors tab
            res_tab = await call("Runtime.evaluate", {"expression": "showTab('other-factors');"})
            print("Switched tab to other-factors:", res_tab)
            await asyncio.sleep(1)

            # Check rendered elements in other factors suite
            checks = [
                "document.getElementById('panel-other-factors')?.classList.contains('active')",
                "document.getElementById('macroNetBiasTag')?.textContent",
                "document.getElementById('giftNiftyLevel')?.textContent",
                "document.getElementById('breadthStatusTag')?.textContent",
                "document.getElementById('breadthAdRatio')?.textContent",
                "document.getElementById('sectorLeaderTag')?.textContent",
                "document.getElementById('sectorRotationRows')?.children.length",
                "document.getElementById('regimeNameTag')?.textContent",
                "document.getElementById('volPricingVerdict')?.textContent",
                "document.getElementById('volAtmIv')?.textContent",
                "document.getElementById('oiPcrValues')?.textContent",
                "document.getElementById('riskSizing')?.textContent",
                "document.getElementById('microImbalance')?.textContent"
            ]

            print("\n--- OTHER FACTORS UI RENDER CHECK ---")
            for expr in checks:
                r = await call("Runtime.evaluate", {"expression": expr})
                val = r.get("result", {}).get("result", {}).get("value")
                print(f"  {expr} => {val}")

    asyncio.run(run())
finally:
    proc.terminate()

