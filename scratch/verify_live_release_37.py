import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9235

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
    print(f"Connecting to page target: {page_target['id']}")

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == cur_id:
                        return resp.get("result", {})

            await call("Page.enable")
            await call("Runtime.enable")

            print("Navigating to login...")
            await call("Page.navigate", {"url": "https://catrader.site/CA_Trader_Login.html"})
            await asyncio.sleep(2)

            # Direct fetch login
            print("Direct fetch login...")
            login_js = """(async () => {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({ email: 'santoshmadnani@catrader.site', password: 'Santosh@9340925132#' })
                });
                const d = await res.json();
                return JSON.stringify({ status: res.status, data: d });
            })()"""

            res = await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True})
            print("Login response:", res.get("result", {}).get("value"))

            # Navigate directly to terminal
            print("Navigating to terminal...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(5)

            # Inspect elements
            check_js = """(() => {
                const searchInputs = document.querySelectorAll("#chartRecoOptionSearch");
                const selectDropdown = document.querySelectorAll("#chartRecoOptionSelect");
                const masterSummary = document.getElementById("masterSummaryCard");
                const mtfTitle = document.getElementById("mtfCardTitle");
                const indicatorTitle = document.getElementById("indicatorSummaryTitle");
                const greeksTitle = document.getElementById("chartGreeksTitle");
                const entryPill = document.getElementById("chartRecoEntryPill");
                const newsModeActive = document.querySelector("[data-ca-news-mode].active")?.dataset?.caNewsMode;
                const recoHistory = document.getElementById("recommendationHistory");
                
                return JSON.stringify({
                    currentUrl: window.location.href,
                    searchInputCount: searchInputs.length,
                    selectDropdownCount: selectDropdown.length,
                    hasMasterSummary: !!masterSummary,
                    masterSummarySym: document.getElementById("msSym")?.textContent,
                    masterSummaryLtp: document.getElementById("msLtp")?.textContent,
                    masterSummarySignal: document.getElementById("msSignal")?.textContent,
                    mtfTitleText: mtfTitle?.textContent,
                    indicatorTitleText: indicatorTitle?.textContent,
                    greeksTitleText: greeksTitle?.textContent,
                    entryPillFlexWrap: entryPill?.parentElement?.style?.flexWrap,
                    newsModeActive: newsModeActive,
                    hasRecoHistoryContainer: !!recoHistory
                });
            })()"""

            eval_res = await call("Runtime.evaluate", {"expression": check_js})
            val_str = eval_res.get("result", {}).get("value", "{}")
            print("UI Verification Result:")
            print(json.dumps(json.loads(val_str), indent=2))

    asyncio.run(run())

finally:
    proc.terminate()

