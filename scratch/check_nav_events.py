import subprocess, time, json, urllib.request, asyncio, websockets, tempfile, os

PORT = 9243
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
temp_dir = tempfile.mkdtemp()

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--user-data-dir={temp_dir}",
    f"--remote-debugging-port={PORT}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list") as resp:
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
                    d = json.loads(await ws.recv())
                    if d.get("id") == cur_id:
                        return d

            async def listen():
                try:
                    while True:
                        msg = json.loads(await ws.recv())
                        method = msg.get("method", "")
                        if "exception" in method.lower():
                            print("EVENT EXCEPTION:", json.dumps(msg, indent=2))
                        elif "console" in method.lower():
                            args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                            print("EVENT CONSOLE:", msg.get("params", {}).get("type"), " ".join(args))
                except asyncio.CancelledError:
                    pass

            await call("Runtime.enable")
            await call("Page.enable")
            await call("Log.enable")

            listener = asyncio.create_task(listen())

            p = os.path.abspath("terminal.html").replace("\\", "/")
            url = f"file:///{p}"
            print("Navigating to:", url)
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(4)
            listener.cancel()

            # Check scripts in DOM
            res = await call("Runtime.evaluate", {"expression": "document.querySelectorAll('script').length"})
            print("Script tags in DOM:", res.get("result", {}).get("result", {}).get("value"))

            res = await call("Runtime.evaluate", {"expression": "[typeof window.A, typeof window.state, typeof window.onSymbolChanged, typeof window.W0]"})
            print("Types in window:", res.get("result", {}).get("result", {}).get("value"))

    asyncio.run(run())
finally:
    proc.terminate()

