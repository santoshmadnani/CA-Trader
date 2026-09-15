import http.server
import socketserver
import threading
import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

PORT_HTTP = 8766
PORT_CHROME = 9230

os.chdir(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7")

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

socketserver.TCPServer.allow_reuse_address = True
httpd = socketserver.TCPServer(("127.0.0.1", PORT_HTTP), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

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

            await ws.send(json.dumps({"id": 100, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 101, "method": "Page.enable"}))
            
            url = f"http://127.0.0.1:{PORT_HTTP}/terminal.html"
            print(f"Navigating to {url}...")
            await ws.send(json.dumps({"id": 103, "method": "Page.navigate", "params": {"url": url}}))

            t0 = time.time()
            exceptions = []
            while time.time() - t0 < 5:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    msg = json.loads(raw)
                    method = msg.get("method", "")
                    if "exception" in method.lower():
                        details = msg.get("params", {}).get("exceptionDetails", {})
                        exceptions.append(details)
                        print(">>> EXCEPTION:", details.get("text"), details.get("exception", {}).get("description"))
                except asyncio.TimeoutError:
                    pass

            print(f"\n--- RUNTIME EXCEPTIONS: {len(exceptions)} ---")
            for expr in [
                "document.title",
                "typeof window.loadChart",
                "typeof window.CATraderAnalysis",
                "typeof window.CATraderLiveMarket",
                "document.getElementById('marketClock')?.textContent",
                "typeof window.state",
                "window.state?.symbol || 'none'",
                "document.getElementById('wl-list')?.children.length",
                "document.getElementById('wl-list')?.innerText.slice(0, 150)"
            ]:
                res = await call("Runtime.evaluate", {"expression": expr})
                val = res.get("result", {}).get("result", {})
                print(f"EVAL `{expr}` => {val.get('value', val)}")

    asyncio.run(run())
finally:
    proc.terminate()
    httpd.shutdown()
