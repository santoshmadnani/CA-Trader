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

PORT_HTTP = 8765
PORT_CHROME = 9224

os.chdir(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7")

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT_CHROME}/json") as resp:
        targets = json.loads(resp.read().decode())
    
    ws_url = targets[0]["webSocketDebuggerUrl"]

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
            
            url = f"http://127.0.0.1:{PORT_HTTP}/terminal.html"
            print(f"Navigating to {url}...")
            await ws.send(json.dumps({"id": 103, "method": "Page.navigate", "params": {"url": url}}))

            t0 = time.time()
            while time.time() - t0 < 6:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    msg = json.loads(raw)
                    method = msg.get("method", "")
                    if "exception" in method.lower():
                        details = msg.get("params", {}).get("exceptionDetails", {})
                        print(">>> JS EXCEPTION:", details.get("text"), details.get("exception", {}).get("description"), "line:", details.get("lineNumber"))
                    elif "console" in method.lower():
                        args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                        print("CONSOLE:", msg.get("params", {}).get("type"), " ".join(args))
                except asyncio.TimeoutError:
                    pass

            for expr in [
                "document.title",
                "typeof window.loadChart",
                "typeof window.CATraderAnalysis",
                "document.getElementById('marketClock')?.textContent",
                "document.getElementById('wl-list')?.children.length",
                "window.state?.candles?.length"
            ]:
                res = await call("Runtime.evaluate", {"expression": expr})
                val = res.get("result", {}).get("result", {})
                print(f"EVAL `{expr}` => {val.get('value', val)}")

    asyncio.run(run())
finally:
    proc.terminate()
    httpd.shutdown()

