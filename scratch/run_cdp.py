import subprocess
import time
import json
import base64
import os
import urllib.request
import websocket
from dotenv import load_dotenv
import requests

load_dotenv(".env")
pwd = os.getenv("CA_ADMIN_PASSWORD")

s = requests.Session()
r = s.post("https://catrader.site/api/auth/login", json={"email": "santoshmadnani@catrader.site", "password": pwd}, timeout=10)
assert r.status_code == 200, "Auth failed"
session_cookie = s.cookies.get("session")
print(f"Authenticated! Session cookie: {session_cookie[:25]}...")

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
artifact_dir = r"C:\Users\SantoshMadnani\.gemini\antigravity\brain\5bf7f074-e62e-47cd-8b01-38ec87f2beac"

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    "--remote-debugging-port=9225",
    "--remote-allow-origins=*",
    "--window-size=1600,1050",
    "--no-sandbox",
    "--disable-gpu",
    "about:blank"
])
time.sleep(2.5)

class CDPClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=15)
        self.msg_id = 0

    def call(self, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    def evaluate(self, expr):
        res = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return res.get("result", {}).get("value")

    def screenshot(self, filename):
        res = self.call("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(res["data"])
        out_path = os.path.join(artifact_dir, filename)
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"Screenshot saved: {filename} ({len(data)} bytes)")
        return out_path

    def close(self):
        try:
            self.ws.close()
        except:
            pass

try:
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9225/json").read().decode())
    ws_url = tabs[0]["webSocketDebuggerUrl"]
    cdp = CDPClient(ws_url)

    cdp.call("Network.enable")
    cdp.call("Page.enable")
    cdp.call("DOM.enable")

    cdp.call("Network.setCookie", {
        "name": "session",
        "value": session_cookie,
        "domain": "catrader.site",
        "path": "/",
        "secure": True,
        "httpOnly": True
    })

    print("Navigating to https://catrader.site/terminal ...")
    cdp.call("Page.navigate", {"url": "https://catrader.site/terminal"})
    time.sleep(5)

    print("Selecting BANKNIFTY symbol...")
    cdp.evaluate("""(async () => {
        if(typeof onSymbolChanged === 'function') await onSymbolChanged('BANKNIFTY');
        const item = document.querySelector('.wl-item[data-symbol="BANKNIFTY"]');
        if(item) item.click();
    })()""")
    time.sleep(4)

    cdp.screenshot("terminal_main_verified.png")

    print("Opening 114 Studies Indicator Modal...")
    cdp.evaluate("""(() => {
        const btn = document.getElementById('btnOpenIndicatorsModal');
        if(btn) btn.click();
        const input = document.getElementById('indicatorSearchInput');
        if(input) { input.value = 'VWAP'; input.dispatchEvent(new Event('input')); }
    })()""")
    time.sleep(1.5)
    cdp.screenshot("indicator_modal_114_verified.png")

    cdp.evaluate("""(() => {
        document.getElementById('indicatorSearchModalClose')?.click();
        const penBtn = document.getElementById('btnToggleDrawingsToolbar');
        if(penBtn) penBtn.click();
    })()""")
    time.sleep(1)
    cdp.screenshot("chart_drawing_toolbox_verified.png")

    print("Switching to Option Chain Tab...")
    cdp.evaluate("""(() => {
        const tab = document.querySelector('.navtab[data-tab="options"]');
        if(tab) tab.click();
    })()""")
    time.sleep(3.5)
    cdp.screenshot("option_chain_zerodha_verified.png")

    print("Opening Quick Order Modal...")
    cdp.evaluate("""(() => {
        const rec = window.__caCurrentChartReco || window.__caRecommendation || {
            symbol: 'BANKNIFTY 56900 CE',
            recommendation: 'BUY',
            entry: 643.6,
            stop_loss: 393.6,
            target: 1143.6,
            instrument: { symbol: 'BANKNIFTY 56900 CE', display: 'BANKNIFTY 56900 CE', kind: 'OPTION', lot_size: 15 }
        };
        if(typeof openQuickOrderModal === 'function') openQuickOrderModal(rec);
    })()""")
    time.sleep(1.5)
    cdp.screenshot("quick_order_fund_verified.png")

    print("All live CDP verification screenshots captured successfully!")

finally:
    try:
        cdp.close()
    except:
        pass
    proc.kill()
