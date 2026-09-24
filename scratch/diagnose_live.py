import asyncio
import json
import os
import pathlib
import subprocess
import time
import urllib.request
import re
import sys
import websockets

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
USER_DATA_DIR = pathlib.Path(r"C:\Users\SantoshMadnani\AppData\Local\Temp\edge_cdp_debug_2")

async def test_live():
    print("Starting Edge in headless mode with remote debugging...")
    edge_proc = subprocess.Popen([
        EDGE_PATH,
        "--headless=new",
        "--remote-debugging-port=9226",
        f"--user-data-dir={USER_DATA_DIR}",
        "--window-size=1920,1080",
        "--disable-gpu",
        "about:blank"
    ])
    
    await asyncio.sleep(2.5)

    print("Logging into https://catrader.site/api/auth/login ...")
    login_data = json.dumps({'email': 'santoshmadnani553@gmail.com', 'password': 'Santosh@9340925132#'}).encode('utf-8')
    req = urllib.request.Request('https://catrader.site/api/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
    
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        res = urllib.request.urlopen(req, context=ctx)
        cookie_header = res.headers.get('Set-Cookie') or ""
        session_match = re.search(r'session=([^;]+)', cookie_header)
        session_val = session_match.group(1) if session_match else ""
        print(f"Logged in successfully. Session cookie length: {len(session_val)}")
    except Exception as e:
        print(f"Login failed: {e}")
        session_val = ""

    with urllib.request.urlopen("http://127.0.0.1:9226/json/list") as r:
        tabs = json.loads(r.read().decode())
    ws_url = tabs[0]["webSocketDebuggerUrl"]
    print(f"Connecting to CDP: {ws_url}")

    console_errors = []
    failed_requests = []

    msg_id = 0
    async with websockets.connect(ws_url, max_size=25*1024*1024) as ws:
        async def send(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cur_id = msg_id
            payload = {"id": cur_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("method") == "Runtime.consoleAPICalled":
                    args = resp.get("params", {}).get("args", [])
                    t = resp.get("params", {}).get("type")
                    text = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                    if t == "error":
                        console_errors.append(f"[CONSOLE ERROR] {text}")
                    elif "error" in text.lower() or "fail" in text.lower():
                        console_errors.append(f"[CONSOLE LOG] {text}")
                elif resp.get("method") == "Runtime.exceptionThrown":
                    details = resp.get("params", {}).get("exceptionDetails", {})
                    exc_text = details.get("text", "")
                    exc_val = details.get("exception", {}).get("description", "")
                    console_errors.append(f"[JS EXCEPTION] {exc_text} - {exc_val}")
                elif resp.get("method") == "Network.responseReceived":
                    resp_data = resp.get("params", {}).get("response", {})
                    status = resp_data.get("status")
                    url = resp_data.get("url")
                    if status and status >= 400:
                        failed_requests.append(f"[HTTP {status}] {url}")
                
                if resp.get("id") == cur_id:
                    return resp.get("result", {})

        await send("Page.enable")
        await send("Network.enable")
        await send("DOM.enable")
        await send("Runtime.enable")

        if session_val:
            await send("Network.setCookie", {
                "name": "session",
                "value": session_val,
                "domain": "catrader.site",
                "path": "/"
            })

        print("Navigating to https://catrader.site/terminal ...")
        await send("Page.navigate", {"url": "https://catrader.site/terminal"})
        
        # Wait 8 seconds to capture all asynchronous API calls and console logs
        for _ in range(8):
            await asyncio.sleep(1.0)
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    parsed = json.loads(msg)
                    if parsed.get("method") == "Runtime.consoleAPICalled":
                        args = parsed.get("params", {}).get("args", [])
                        t = parsed.get("params", {}).get("type")
                        text = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                        if t == "error":
                            console_errors.append(f"[CONSOLE ERROR] {text}")
                        elif "error" in text.lower() or "fail" in text.lower():
                            console_errors.append(f"[CONSOLE LOG] {text}")
                    elif parsed.get("method") == "Runtime.exceptionThrown":
                        details = parsed.get("params", {}).get("exceptionDetails", {})
                        exc_text = details.get("text", "")
                        exc_val = details.get("exception", {}).get("description", "")
                        console_errors.append(f"[JS EXCEPTION] {exc_text} - {exc_val}")
                    elif parsed.get("method") == "Network.responseReceived":
                        resp_data = parsed.get("params", {}).get("response", {})
                        status = resp_data.get("status")
                        url = resp_data.get("url")
                        if status and status >= 400:
                            failed_requests.append(f"[HTTP {status}] {url}")
            except asyncio.TimeoutError:
                pass

        # Check JS state
        state_eval = await send("Runtime.evaluate", {
            "expression": """(() => {
                return {
                    hasState: typeof window.state !== 'undefined',
                    hasApi: typeof window.api === 'function',
                    hasDraw: typeof window.draw === 'function',
                    hasLoadChart: typeof window.loadChart === 'function',
                    hasLoadDashboard: typeof window.loadDashboard === 'function',
                    currentSymbol: (window.state || {}).symbol,
                    currentTimeframe: (window.state || {}).tf,
                    isChartLoading: (window.state || {}).chartLoading,
                    candleCount: ((window.state || {}).candles || []).length,
                    activePanel: (document.querySelector('.panel.active') || {}).id,
                    ceText: (document.getElementById('ceContractSymbol') || {}).textContent,
                    peText: (document.getElementById('peContractSymbol') || {}).textContent,
                    spotLtp: (document.getElementById('dashSpotLtp') || {}).textContent,
                    ceCmp: (document.getElementById('ceCmp') || {}).textContent,
                    peCmp: (document.getElementById('peCmp') || {}).textContent
                };
            })()""",
            "returnByValue": True
        })
        
        print("\n=== JS STATE DIAGNOSTICS ===")
        print(json.dumps(state_eval.get("result", {}).get("value", {}), indent=2))

        # Check Chart Tab specifically
        chart_test = await send("Runtime.evaluate", {
            "expression": """(() => {
                showTab('charts');
                const canvas = document.getElementById('upstoxCandles') || document.getElementById('chartCanvas');
                return {
                    chartsPanelClass: (document.getElementById('panel-charts')||{}).className,
                    canvasFound: !!canvas,
                    canvasWidth: canvas ? canvas.width : 0,
                    canvasHeight: canvas ? canvas.height : 0,
                    candleCountInState: ((window.state||{}).candles||[]).length
                };
            })()""",
            "returnByValue": True
        })
        print("\n=== CHARTS PANEL DIAGNOSTICS ===")
        print(json.dumps(chart_test.get("result", {}).get("value", {}), indent=2))

        print("\n=== FAILED HTTP REQUESTS ===")
        for req_err in failed_requests:
            print(req_err)
        if not failed_requests:
            print("No HTTP >= 400 errors detected.")

        print("\n=== CONSOLE ERRORS & JS EXCEPTIONS ===")
        for cerr in console_errors:
            print(cerr)
        if not console_errors:
            print("No console errors detected.")

    edge_proc.terminate()
    print("\nDiagnostics complete.")

if __name__ == "__main__":
    asyncio.run(test_live())
