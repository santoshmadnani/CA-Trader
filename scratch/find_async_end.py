import subprocess, time, json, urllib.request, asyncio, websockets, re, sys, tempfile

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9234
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
            
            # Test each line from 3950 to 4030: if we add "await 1;" after s2_lines[:i] + "}", does it compile?
            # Or better: let's test `await 1;` inside s2 directly.
            for i in range(3900, 4026):
                # Replace line i with `await 1;`
                test_lines = list(s2_lines[:4026])
                test_lines[i] = "/*test*/ await 1;"
                code = "\n".join(test_lines[:i+1]) + "\n}})();" # tentative close
                # Or just compile test_lines[:4026] up to line i with closing
                # Even simpler: compile s2_lines[:i] + "\nawait 1;\n}})();"
                test_code = "\n".join(s2_lines[:i]) + "\nawait 1;\n}})();"
                res = await call("Runtime.compileScript", {"expression": test_code, "sourceURL": "test.js", "persistScript": False})
                has_err = "exceptionDetails" in res.get("result", {})
                desc = res.get("result", {}).get("exceptionDetails", {}).get("exception", {}).get("description", "")
                if "await is only valid in async" in desc:
                    print(f"Line {i} ({s2_lines[i-1][:40]}): await is invalid!")
                    return
                elif i % 20 == 0:
                    print(f"Line {i}: ok")

    asyncio.run(run())
finally:
    proc.terminate()

