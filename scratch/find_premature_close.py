import subprocess, time, json, urllib.request, asyncio, websockets, re, sys, tempfile

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9236
temp_dir = tempfile.mkdtemp()
proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--user-data-dir={temp_dir}",
    f"--remote-debugging-port={PORT_CHROME}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
        html = f.read()

    scripts = [m.group(1) for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL)]
    s2_lines = scripts[2].split('\n')

    with urllib.request.urlopen(f"http://127.0.0.1:{PORT_CHROME}/json/list") as resp:
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

            await call("Runtime.enable")
            
            # Binary search:
            # At line i, if we append:
            # "await 1;\n}})();"
            # If the outermost function is closed, `await 1;` is either at top-level OR there's an extra `}`.
            low = 1
            high = 4020
            
            # Let's binary search
            while low < high:
                mid = (low + high) // 2
                code = "\n".join(s2_lines[:mid]) + "\nawait 1;\n}})();"
                res = await call("Runtime.compileScript", {"expression": code, "sourceURL": "test.js", "persistScript": False})
                desc = res.get("result", {}).get("exceptionDetails", {}).get("exception", {}).get("description", "")
                if "await is only valid in async" in desc or "Unexpected token ')'" in desc:
                    high = mid
                else:
                    low = mid + 1
            
            print(f"Discrepancy at line {low} (file line {4060 + low}):")
            for k in range(max(0, low - 5), min(len(s2_lines), low + 5)):
                print(f"  {4060 + k}: {s2_lines[k]}")

    asyncio.run(run())
finally:
    proc.terminate()

