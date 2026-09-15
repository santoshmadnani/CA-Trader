import subprocess, time, json, urllib.request, asyncio, websockets, re, sys, tempfile

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9233
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

    scripts = []
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL):
        start_line = html[:m.start()].count('\n') + 1
        scripts.append((start_line, m.group(1)))

    s2 = scripts[2][1]
    base_line = scripts[2][0]

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
            res = await call("Runtime.compileScript", {"expression": s2, "sourceURL": "s2.js", "persistScript": False})
            print("Compile whole s2:", json.dumps(res, indent=2))

    asyncio.run(run())
finally:
    proc.terminate()

