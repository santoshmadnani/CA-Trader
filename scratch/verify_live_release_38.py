import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9245

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
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == cur_id:
                        return resp.get("result", {})

            await call("Page.enable")
            await call("Runtime.enable")

            print("Navigating to login...")
            await call("Page.navigate", {"url": "https://catrader.site/CA_Trader_Login.html"})
            await asyncio.sleep(2)

            login_js = """(async () => {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({ email: 'santoshmadnani@catrader.site', password: 'Santosh@9340925132#' })
                });
                return res.status;
            })()"""

            res = await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True})
            print("Login response status:", res.get("result", {}).get("value"))

            print("Navigating to terminal...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(4)

            # 1. Inspect Master Summary Executive Thesis Card
            summary_js = """(() => {
                return JSON.stringify({
                    hasCard: !!document.getElementById('masterSummaryCard'),
                    signalBadge: document.getElementById('msSignalBadge')?.textContent,
                    conviction: document.getElementById('msConvictionBadge')?.textContent,
                    targetInst: document.getElementById('msTargetInstrument')?.textContent,
                    thesisHeadline: document.getElementById('msThesisHeadline')?.textContent,
                    thesisNarrative: document.getElementById('msThesisNarrative')?.textContent,
                    pillarTech: document.getElementById('msPillarTech')?.textContent,
                    pillarGreeks: document.getElementById('msPillarGreeks')?.textContent,
                    pillarFlow: document.getElementById('msPillarFlow')?.textContent,
                    pillarNews: document.getElementById('msPillarNews')?.textContent
                });
            })()"""

            eval_res = await call("Runtime.evaluate", {"expression": summary_js})
            print("Master Executive Thesis Card:")
            print(json.dumps(json.loads(eval_res.get("result", {}).get("value", "{}")), indent=2))

            # 2. Test Tab Loading for all sections
            tab_test_js = """(async () => {
                const results = {};
                const tabs = ["options", "news", "fundamentals", "movers", "other-factors", "reco", "orders", "funds"];
                for (const t of tabs) {
                    try {
                        const tabBtn = document.querySelector(`.navtab[data-tab="${t}"]`);
                        if (!tabBtn) { results[t] = "no navtab"; continue; }
                        tabBtn.click();
                        await new Promise(r => setTimeout(r, 1200));
                        const panel = document.getElementById(`panel-${t}`);
                        const active = panel?.classList.contains('active');
                        const len = panel?.innerHTML?.length || 0;
                        results[t] = { active, contentLen: len };
                    } catch(e) {
                        results[t] = { err: String(e) };
                    }
                }
                return JSON.stringify(results);
            })()"""

            tabs_res = await call("Runtime.evaluate", {"expression": tab_test_js, "awaitPromise": True})
            print("\nAll Tabs Loading Test:")
            print(json.dumps(json.loads(tabs_res.get("result", {}).get("value", "{}")), indent=2))

    asyncio.run(run())

finally:
    proc.terminate()

