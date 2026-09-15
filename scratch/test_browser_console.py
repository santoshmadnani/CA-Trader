import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
port = 9222

# Launch chrome headless
proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--remote-debugging-port={port}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(2)

try:
    # Get targets
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as resp:
        targets = json.loads(resp.read().decode())
    
    ws_url = targets[0]["webSocketDebuggerUrl"]
    print(f"Connected to Chrome CDP: {ws_url}")

    async def run_cdp():
        async with websockets.connect(ws_url) as ws:
            msg_id = 1
            async def send(method, params=None):
                nonlocal msg_id
                msg_id += 1
                await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
                return msg_id

            await send("Page.enable")
            await send("Console.enable")
            await send("Runtime.enable")
            
            # Navigate to file or local server
            file_url = "file:///" + r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html".replace("\\", "/")
            print(f"Navigating to {file_url}")
            await send("Page.navigate", {"url": file_url})

            console_logs = []
            exceptions = []
            
            start_t = time.time()
            while time.time() - start_t < 6:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    method = data.get("method")
                    if method == "Runtime.exceptionThrown":
                        details = data["params"]["exceptionDetails"]
                        text = details.get("text", "")
                        exc = details.get("exception", {}).get("description", "")
                        line = details.get("lineNumber", 0)
                        url = details.get("url", "")
                        exceptions.append(f"[EXCEPTION] Line {line}: {text} - {exc}")
                        print(f"EXCEPTION at line {line}: {text} - {exc}")
                    elif method == "Runtime.consoleAPICalled":
                        c_type = data["params"]["type"]
                        args = [str(a.get("value", a.get("description", ""))) for a in data["params"]["args"]]
                        console_logs.append(f"[{c_type}] " + " ".join(args))
                        if c_type in ["error", "warning"]:
                            print(f"[{c_type.upper()}] " + " ".join(args))
                except asyncio.TimeoutError:
                    pass

            print(f"\n--- TOTAL EXCEPTIONS: {len(exceptions)} ---")
            for e in exceptions:
                print(e)
            print(f"\n--- CONSOLE LOGS (first 20): ---")
            for cl in console_logs[:20]:
                print(cl)

    asyncio.run(run_cdp())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except:
        proc.kill()

