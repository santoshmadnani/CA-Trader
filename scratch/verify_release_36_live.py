import subprocess, time, json, urllib.request, asyncio, websockets, sys, base64

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9226

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

            print("[1] Navigating to origin https://catrader.site/login ...")
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2.5)

            # Perform login via API
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
            login_res = await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True, "returnByValue": True})
            print("API Login result:", json.dumps(login_res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Navigate to /terminal
            print("[2] Navigating to /terminal...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(6)

            res = await call("Runtime.evaluate", {"expression": "location.href"})
            curr_url = res.get("result", {}).get("result", {}).get("value")
            print("Current URL:", curr_url)

            # Check orders and positions tab
            print("[3] Inspecting Orders & Positions...")
            portfolio_res = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    await loadPortfolioSnapshot(false);
                    const posTable = document.getElementById('positionsTable')?.innerText || '';
                    const ordersTable = document.getElementById('ordersTable')?.innerText || '';
                    const posHasTimeout = posTable.includes('timed out');
                    const ordersHasTimeout = ordersTable.includes('timed out');
                    const fundCards = document.getElementById('fundCards')?.innerText || '';
                    return {
                        fundCards: fundCards.replace(/\\n+/g, ' | '),
                        posTablePreview: posTable.slice(0, 150),
                        ordersTablePreview: ordersTable.slice(0, 150),
                        posHasTimeout,
                        ordersHasTimeout
                    };
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            port_val = portfolio_res.get("result", {}).get("result", {}).get("value")
            print("Portfolio Status:", json.dumps(port_val, indent=2))

            # Test Recommendation Box, Option Dropdown & Smart Advisory
            print("[4] Testing Recommendation Box, Option Dropdown & Smart Advisory...")
            reco_test = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    const actionEl = document.getElementById('chartRecoAction');
                    const symbolEl = document.getElementById('chartRecoSymbol');
                    const selectEl = document.getElementById('chartRecoOptionSelect');
                    const searchEl = document.getElementById('chartRecoOptionSearch');
                    const advIcon = document.getElementById('chartRecoAdvisoryIcon');
                    const advText = document.getElementById('chartRecoAdvisoryText');
                    const entryEl = document.getElementById('chartRecoEntry');
                    const slEl = document.getElementById('chartRecoSl');
                    const tgtEl = document.getElementById('chartRecoTgt');

                    const initial = {
                        action: actionEl?.textContent,
                        symbol: symbolEl?.textContent,
                        optionSearchVal: searchEl?.value,
                        advisory: advText?.textContent,
                        optionsCount: selectEl?.options?.length || 0,
                        entry: entryEl?.textContent
                    };

                    // Find options in select
                    let putOpt = null;
                    let otmCallOpt = null;
                    if(selectEl && selectEl.options){
                        for(let i=0; i<selectEl.options.length; i++){
                            const val = selectEl.options[i].value;
                            if(val.includes(' PE') && !putOpt) putOpt = val;
                            if(val.includes(' CE') && i >= 6 && !otmCallOpt) otmCallOpt = val;
                        }
                    }

                    // Test A: Selecting Counter-Trend Put
                    let counterTrendResult = null;
                    if(putOpt){
                        selectEl.value = putOpt;
                        selectEl.dispatchEvent(new Event('change'));
                        await new Promise(r => setTimeout(r, 1200));
                        counterTrendResult = {
                            selected: putOpt,
                            action: actionEl?.textContent,
                            symbol: symbolEl?.textContent,
                            advisoryIcon: advIcon?.textContent,
                            advisoryText: advText?.textContent,
                            entry: entryEl?.textContent
                        };
                    }

                    // Test B: Selecting Budget OTM Call
                    let otmResult = null;
                    if(otmCallOpt){
                        selectEl.value = otmCallOpt;
                        selectEl.dispatchEvent(new Event('change'));
                        await new Promise(r => setTimeout(r, 1200));
                        otmResult = {
                            selected: otmCallOpt,
                            action: actionEl?.textContent,
                            symbol: symbolEl?.textContent,
                            advisoryIcon: advIcon?.textContent,
                            advisoryText: advText?.textContent,
                            entry: entryEl?.textContent,
                            target: tgtEl?.textContent,
                            sl: slEl?.textContent
                        };
                    }

                    // Test 5 Pointers in Recommendation Rationale
                    const rationaleGreeks = document.getElementById('recoRationaleGreeks')?.innerText || '';
                    const rationaleTech = document.getElementById('recoRationaleTechnicals')?.innerText || '';
                    const rationaleNews = document.getElementById('recoRationaleNews')?.innerText || '';

                    return {
                        initial,
                        counterTrendResult,
                        otmResult,
                        rationaleGreeksPreview: rationaleGreeks.slice(0, 200),
                        rationaleTechPreview: rationaleTech.slice(0, 150),
                        rationaleNewsPreview: rationaleNews.slice(0, 150)
                    };
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            reco_val = reco_test.get("result", {}).get("result", {}).get("value")
            print("Recommendation & Advisory Test Results:\n", json.dumps(reco_val, indent=2))

            # Take Screenshot
            print("[5] Capturing screenshot...")
            ss = await call("Page.captureScreenshot", {"format": "png"})
            data = ss.get("result", {}).get("data")
            if data:
                with open("scratch/release_36_verified.png", "wb") as f:
                    f.write(base64.b64decode(data))
                print("Screenshot saved to scratch/release_36_verified.png")

    asyncio.run(run())
finally:
    proc.terminate()

