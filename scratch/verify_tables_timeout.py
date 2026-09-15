import subprocess, time, json, urllib.request, asyncio, websockets, sys

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9258

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
                nonlocal mid; mid += 1; cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get("id") == cur_id: return d

            await call("Runtime.enable")
            await call("Page.enable")

            # Login
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)
            await call("Runtime.evaluate", {
                "expression": """
                fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({email: 'santoshmadnani@catrader.site', password: 'Santosh@9340925132#'})
                })
                """,
                "awaitPromise": True
            })

            # Go to terminal
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(4)

            # Call loadPortfolioSnapshot directly and await it
            check_result = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    try {
                        const snap = await loadPortfolioSnapshot(true);
                        const posTable = document.getElementById('positionsTable')?.innerHTML || '';
                        const ordTable = document.getElementById('ordersTable')?.innerHTML || '';
                        return {
                            success: true,
                            snapCount: {
                                positions: snap?.positions?.length,
                                orders: snap?.orders?.length,
                                funds: snap?.funds
                            },
                            posHasTimeout: posTable.toLowerCase().includes('timed out'),
                            ordHasTimeout: ordTable.toLowerCase().includes('timed out'),
                            posHasTable: posTable.includes('<table'),
                            ordHasTable: ordTable.includes('<table'),
                            posTableSnippet: posTable.slice(0, 300),
                            ordTableSnippet: ordTable.slice(0, 300)
                        };
                    } catch(e) {
                        return { error: e.message, stack: e.stack };
                    }
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            print("Direct loadPortfolioSnapshot Check:")
            print(json.dumps(check_result.get("result", {}).get("result", {}).get("value"), indent=2))
            print("Orders & Positions Table Timeout Check:")
            print(json.dumps(check_result.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()
