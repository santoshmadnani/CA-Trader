import subprocess, time, json, urllib.request, asyncio, websockets, tempfile

PORT = 9266
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

            await call("Runtime.enable")

            with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import re
            scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
            print(f"Total script tags: {len(scripts)}")
            for idx, sc in enumerate(scripts):
                res = await call("Runtime.evaluate", {
                    "expression": sc,
                    "returnByValue": True,
                    "awaitPromise": False
                })
                err = res.get("result", {}).get("exceptionDetails")
                if err:
                    print(f"EVAL ERROR in Script {idx}: line {err.get('lineNumber')} - {err.get('text')}: {err.get('exception', {}).get('description')}")
                else:
                    print(f"Script {idx}: EVAL OK")

    asyncio.run(run())
finally:
    proc.terminate()

