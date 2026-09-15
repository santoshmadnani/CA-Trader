import subprocess, time, json, urllib.request, asyncio, websockets, re, sys, tempfile

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9231
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

    s2_lines = scripts[2][1].split('\n')
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

            # Binary search to find where the brace imbalance is
            low = 1
            high = len(s2_lines)
            
            # Let's check chunks
            step = 100
            for i in range(100, len(s2_lines), step):
                # If we close the IIFE here with '})();', does it compile without unexpected token or unmatched brace?
                # Actually, let's compile: (async() => { ...prefix... })
                code = "(async() => {\n" + "\n".join(s2_lines[1:i]) + "\n})();"
                res = await call("Runtime.compileScript", {"expression": code, "sourceURL": "test.js", "persistScript": False})
                has_err = "exceptionDetails" in res.get("result", {})
                desc = res.get("result", {}).get("exceptionDetails", {}).get("exception", {}).get("description", "")
                print(f"Prefix up to file line {base_line + i}: err={has_err} {desc[:50]}")
                if has_err:
                    # Look closer in this 100-line range
                    for j in range(max(1, i - step), i + 1):
                        c2 = "(async() => {\n" + "\n".join(s2_lines[1:j]) + "\n})();"
                        r2 = await call("Runtime.compileScript", {"expression": c2, "sourceURL": "test.js", "persistScript": False})
                        h2 = "exceptionDetails" in r2.get("result", {})
                        d2 = r2.get("result", {}).get("exceptionDetails", {}).get("exception", {}).get("description", "")
                        if h2:
                            print(f"FIRST ERROR at file line {base_line + j}: {d2[:60]}")
                            print(f"Line content: {s2_lines[j-1]}")
                            return

    asyncio.run(run())
finally:
    proc.terminate()

