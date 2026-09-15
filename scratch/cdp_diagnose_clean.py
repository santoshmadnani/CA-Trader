import socketserver
import http.server
import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

PORT_HTTP = 8888
PORT_CHROME = 9260

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', PORT_HTTP), QuietHandler)
import threading
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()

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
            
            logs = []
            async def log_reader():
                while True:
                    try:
                        raw = await ws.recv()
                        d = json.loads(raw)
                        method = d.get("method", "")
                        if "exception" in method.lower():
                            logs.append(("EXC", d.get("params", {})))
                        elif "console" in method.lower():
                            logs.append(("CONSOLE", d.get("params", {})))
                    except Exception:
                        break
            
            reader_task = asyncio.create_task(log_reader())

            url = f"http://127.0.0.1:{PORT_HTTP}/terminal.html"
            print(f"Navigating to {url}...")
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(4)
            reader_task.cancel()

            print(f"Logged events ({len(logs)}):")
            for typ, p in logs:
                if typ == "EXC":
                    det = p.get("exceptionDetails", {})
                    print(">>> EXCEPTION:", det.get("text"), det.get("exception", {}).get("description"), "line:", det.get("lineNumber"))
                elif typ == "CONSOLE" and p.get("type") in ["error", "warn", "warning"]:
                    args = [str(a.get("value", a.get("description", ""))) for a in p.get("args", [])]
                    print(f"[{p.get('type')}]", " ".join(args))

            for expr in [
                "document.title",
                "document.getElementById('chartSymbolTitle')?.textContent",
                "document.getElementById('wl-list')?.children.length",
                "Array.from(document.querySelectorAll('.wl-item')).map(x => x.dataset.symbol)",
                "window.CATraderSymbol",
                "typeof window.onSymbolChanged"
            ]:
                res = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
                print(f"EVAL `{expr}` =>", res.get("result", {}).get("result", {}).get("value"))

    asyncio.run(run())
finally:
    proc.terminate()
    server.shutdown()

