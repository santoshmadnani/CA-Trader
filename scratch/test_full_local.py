import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys

# Start backend on 8001
env = os.environ.copy()
env["PORT"] = "8001"
env["CA_AUTH_ENABLED"] = "0"

app_proc = subprocess.Popen([
    sys.executable, "app.py"
], cwd=r"c:\Users\SantoshMadnani\Documents\CA_Trader\7", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

time.sleep(3)

PORT_CHROME = 9228
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
chrome_proc = subprocess.Popen([
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
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get("id") == cur_id:
                        return d

            await ws.send(json.dumps({"id": 100, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 101, "method": "Page.enable"}))
            await ws.send(json.dumps({"id": 102, "method": "Log.enable"}))
            
            url = "http://127.0.0.1:8001/terminal"
            print(f"Navigating to {url}...")
            await ws.send(json.dumps({"id": 103, "method": "Page.navigate", "params": {"url": url}}))

            exceptions = []
            console_msgs = []

            t0 = time.time()
            while time.time() - t0 < 8:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    msg = json.loads(raw)
                    method = msg.get("method", "")
                    if "exception" in method.lower():
                        details = msg.get("params", {}).get("exceptionDetails", {})
                        exc_text = details.get("text", "")
                        exc_desc = details.get("exception", {}).get("description", "")
                        line = details.get("lineNumber", 0)
                        exceptions.append(f"Line {line}: {exc_text} - {exc_desc}")
                        print(f">>> EXCEPTION at line {line}: {exc_text}\n    {exc_desc}")
                    elif "console" in method.lower():
                        c_type = msg.get("params", {}).get("type")
                        args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                        console_msgs.append(f"[{c_type}] " + " ".join(args))
                        if c_type in ["error", "warning"]:
                            print(f"[{c_type.upper()}] " + " ".join(args))
                except asyncio.TimeoutError:
                    pass

            print(f"\nTotal exceptions: {len(exceptions)}")
            print(f"Total console messages: {len(console_msgs)}")
            for m in console_msgs[-20:]:
                print(" ", m)

            for expr in [
                "document.title",
                "location.href",
                "typeof window.loadChart",
                "typeof window.CATraderAnalysis",
                "document.getElementById('marketClock')?.textContent",
                "document.getElementById('wl-list')?.children.length",
                "document.getElementById('wl-list')?.innerHTML.slice(0, 200)",
                "window.state?.symbol",
                "window.state?.candles?.length"
            ]:
                res = await call("Runtime.evaluate", {"expression": expr})
                val = res.get("result", {}).get("result", {})
                print(f"EVAL `{expr}` => {repr(val.get('value', val))[:150]}")

    asyncio.run(run())
finally:
    chrome_proc.terminate()
    app_proc.terminate()

