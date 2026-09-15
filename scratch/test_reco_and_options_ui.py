import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys

sys.stdout.reconfigure(encoding='utf-8')

PORT_CHROME = 9238

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
            await asyncio.sleep(2.5)

            # Test tab name
            tab_name = await call("Runtime.evaluate", {"expression": "document.querySelector('.navtab[data-tab=\"charts\"]')?.textContent.trim()"})
            print(f"Tab name: {tab_name.get('result', {}).get('result', {}).get('value')}")

            # Test option recommendation
            reco_action = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoAction')?.textContent"})
            reco_sym = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoOptionSearch')?.value || document.getElementById('chartRecoSymbol')?.textContent"})
            reco_entry = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoEntry')?.textContent"})
            reco_sl = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoSl')?.textContent"})
            reco_tgt = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoTgt')?.textContent"})
            
            print(f"Reco Action: {reco_action.get('result', {}).get('result', {}).get('value')}")
            print(f"Reco Symbol: {reco_sym.get('result', {}).get('result', {}).get('value')}")
            print(f"Reco Entry: {reco_entry.get('result', {}).get('result', {}).get('value')}")
            print(f"Reco SL: {reco_sl.get('result', {}).get('result', {}).get('value')}")
            print(f"Reco Target: {reco_tgt.get('result', {}).get('result', {}).get('value')}")

            # Test Option Search input and suggestions
            await call("Runtime.evaluate", {"expression": "const inp = document.getElementById('chartRecoOptionSearch'); if(inp){ inp.focus(); inp.value = '23500'; inp.dispatchEvent(new Event('input')); }"})
            await asyncio.sleep(1)
            sugg_count = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoOptionSuggestions')?.children.length"})
            sugg_first = await call("Runtime.evaluate", {"expression": "document.getElementById('chartRecoOptionSuggestions')?.firstElementChild?.textContent.replace(/\\s+/g, ' ').trim()"})
            print(f"Option Suggestions count for '23500': {sugg_count.get('result', {}).get('result', {}).get('value')}")
            print(f"First suggestion: {sugg_first.get('result', {}).get('result', {}).get('value')}")

            # Test Recommendation Rationale Row 5 (Other Factors)
            r5_count = await call("Runtime.evaluate", {"expression": "document.getElementById('recoRationaleOtherFactors')?.children.length"})
            r5_first = await call("Runtime.evaluate", {"expression": "document.getElementById('recoRationaleOtherFactors')?.firstElementChild?.textContent.replace(/\\s+/g, ' ').trim()"})
            print(f"Rationale Row 5 cards count: {r5_count.get('result', {}).get('result', {}).get('value')}")
            print(f"Rationale Row 5 card 1: {r5_first.get('result', {}).get('result', {}).get('value')}")

            # Test Technical indicators rows clickable
            ind_count = await call("Runtime.evaluate", {"expression": "document.getElementById('indicatorRows')?.children.length"})
            ind_clickable = await call("Runtime.evaluate", {"expression": "document.getElementById('indicatorRows')?.firstElementChild?.classList.contains('clickable-indicator-row')"})
            print(f"Indicators rows count: {ind_count.get('result', {}).get('result', {}).get('value')}")
            print(f"First indicator row clickable: {ind_clickable.get('result', {}).get('result', {}).get('value')}")

    asyncio.run(run())
finally:
    proc.terminate()

