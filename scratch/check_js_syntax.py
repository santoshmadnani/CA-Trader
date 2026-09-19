import os, glob, subprocess, json, urllib.request, time, sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9260

proc = subprocess.Popen([
    CHROME,
    "--headless=new",
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

    import asyncio, websockets
    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 0
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

            js_files = glob.glob("static/**/*.js", recursive=True)
            print(f"Found {len(js_files)} JS files to check.")
            for fpath in sorted(js_files):
                with open(fpath, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Check for tags
                has_open = "<script" in code
                has_close = "</script" in code
                if has_open or has_close:
                    print(f"\n[TAG ERROR] {fpath}: contains <script or </script> tags! (open: {has_open}, close: {has_close})")

                # Test compile script via CDP
                res = await call("Runtime.compileScript", {
                    "expression": code,
                    "sourceURL": fpath.replace("\\", "/"),
                    "persistScript": False
                })
                
                if "exceptionDetails" in res.get("result", {}):
                    ex = res["result"]["exceptionDetails"]
                    print(f"\n[SYNTAX ERROR] {fpath}:")
                    print(f"  Line {ex.get('lineNumber')}, Col {ex.get('columnNumber')}: {ex.get('text')}")
                    if "exception" in ex:
                        print(f"  Description: {ex['exception'].get('description')}")
                else:
                    print(f"[OK] {fpath}")

    asyncio.run(run())
finally:
    proc.kill()

