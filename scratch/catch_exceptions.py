import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9255

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
            
            exceptions = []
            console_msgs = []
            
            async def listener():
                while True:
                    try:
                        raw = await ws.recv()
                        msg = json.loads(raw)
                        method = msg.get("method", "")
                        if "exception" in method.lower():
                            d = msg.get("params", {}).get("exceptionDetails", {})
                            exceptions.append({
                                "text": d.get("text"),
                                "line": d.get("lineNumber"),
                                "col": d.get("columnNumber"),
                                "desc": d.get("exception", {}).get("description")
                            })
                        elif "console" in method.lower():
                            params = msg.get("params", {})
                            args = [str(a.get("value", a.get("description", ""))) for a in params.get("args", [])]
                            console_msgs.append(f"[{params.get('type')}] {' '.join(args)}")
                    except Exception:
                        break

            l_task = asyncio.create_task(listener())

            url = f"file:///{os.path.abspath('terminal.html').replace(os.sep, '/')}"
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(4)
            l_task.cancel()

            print(f"=== EXCEPTIONS ({len(exceptions)}) ===")
            for e in exceptions:
                print(f"Line {e['line']}: {e['text']}\n  {e['desc']}")

            print(f"\n=== CONSOLE MESSAGES ({len(console_msgs)}) ===")
            for m in console_msgs[:20]:
                print(" ", m)

    asyncio.run(run())
finally:
    proc.terminate()

