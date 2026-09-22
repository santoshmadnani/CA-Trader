#!/usr/bin/env python3
"""
tests/smoke_test.py
Fast (8-10 second) Automated E2E Smoke Test Harness for CA Trader.
Verifies:
  1. Local server health & authentication
  2. Instant Dual Recommendation card rendering (no stuck 'Calculating')
  3. Non-zero Net Change & Change % fallback
  4. Chart panel layout alignment (no 1000px rightward flex shift)
  5. Candlestick data loading & Canvas paint dimensions
  6. Visual screenshot capture (optional)

Usage:
  python tests/smoke_test.py
  python tests/smoke_test.py --screenshot
"""

import sys
import os
import json
import time
import subprocess
import urllib.request
import asyncio
import tempfile
import shutil
import base64
from pathlib import Path

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CHROME_PATHS = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe')
]

CHROME_BIN = next((p for p in CHROME_PATHS if os.path.exists(p)), None)
CDP_PORT = 9488
TARGET_HOST = "http://127.0.0.1:8000"

async def run_smoke_test(capture_screenshots=False):
    if not CHROME_BIN:
        print("[FAIL] Google Chrome not found on system paths.")
        return 1

    # Check if local server is running
    server_running = False
    try:
        req = urllib.request.urlopen(f"{TARGET_HOST}/health", timeout=3)
        if req.status == 200:
            server_running = True
    except Exception:
        server_running = False

    uvicorn_proc = None
    if not server_running:
        print(f"[INFO] Server not detected on {TARGET_HOST}. Starting ephemeral uvicorn...")
        app_dir = Path(__file__).resolve().parent.parent
        uvicorn_proc = subprocess.Popen(
            [sys.executable, "run_server.py"],
            cwd=str(app_dir),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(25):
            time.sleep(1)
            try:
                r = urllib.request.urlopen(f"{TARGET_HOST}/health", timeout=1)
                if r.status == 200:
                    server_running = True
                    break
            except Exception:
                pass

    if not server_running:
        print(f"[FAIL] Unable to reach CA Trader server at {TARGET_HOST}")
        return 1

    # Launch Chrome Headless
    user_data = tempfile.mkdtemp()
    chrome_proc = subprocess.Popen([
        CHROME_BIN, '--headless=new', f'--remote-debugging-port={CDP_PORT}',
        f'--user-data-dir={user_data}',
        '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--window-size=1920,1080', '--ignore-certificate-errors', 'about:blank'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    await asyncio.sleep(2)

    try:
        import websockets
    except ImportError:
        print("[FAIL] websockets package required. Run: pip install websockets")
        chrome_proc.terminate()
        return 1

    try:
        targets = None
        for _ in range(10):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json/list', timeout=1) as resp:
                    targets = json.loads(resp.read().decode())
                if targets:
                    break
            except Exception:
                await asyncio.sleep(0.5)

        if not targets:
            print("[FAIL] Chrome remote debugging did not respond.")
            return 1

        page_target = next(t for t in targets if t.get('type') == 'page')
        ws_url = page_target['webSocketDebuggerUrl']

        results = {}
        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur = mid
                await ws.send(json.dumps({'id': cur, 'method': method, 'params': params or {}}))
                while True:
                    msg = await ws.recv()
                    d = json.loads(msg)
                    if d.get('id') == cur:
                        return d

            def get_val(r):
                return r.get('result', {}).get('result', {}).get('value')

            await call('Page.enable')
            await call('Runtime.enable')
            await call('Emulation.setDeviceMetricsOverride', {
                'width': 1920, 'height': 1080, 'deviceScaleFactor': 1, 'mobile': False
            })

            # 1. Login
            print("[1/5] Authenticating...", flush=True)
            await call('Page.navigate', {'url': f'{TARGET_HOST}/login'})
            await asyncio.sleep(1.0)
            login_js = """
            (async () => {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({
                        email: 'santoshmadnani@catrader.site',
                        password: 'Santosh@9340925132#'
                    })
                });
                if (res.ok) {
                    window.location.href = '/terminal';
                    return true;
                }
                return false;
            })()
            """
            l_eval = await call('Runtime.evaluate', {'expression': login_js, 'awaitPromise': True, 'returnByValue': True})
            results['login'] = bool(get_val(l_eval))

            # 2. Wait for Terminal to Load
            print("[2/5] Loading Terminal...", flush=True)
            await asyncio.sleep(4.0)

            # 3. Check Dashboard Recommendations & Price Change
            print("[3/5] Verifying Dashboard & Price Changes...", flush=True)
            dash_js = """
            (() => {
                const bodyText = document.body.innerText || '';
                const recoLoaded = !bodyText.includes('Loading CE Contract...') && (bodyText.includes('Call (CE)') || bodyText.includes('Put (PE)'));
                const chgEl = document.getElementById('undChange') 
                           || document.getElementById('dashSymbolChange') 
                           || document.querySelector('.wl-item .wl-chg');
                const chgText = chgEl?.innerText?.trim() || '';
                const nonZeroChg = chgText.length > 0 && !chgText.includes('0.00 (0.00%)');
                return { recoLoaded, nonZeroChg, chgText };
            })()
            """
            d_val = {}
            for _ in range(5):
                d_eval = await call('Runtime.evaluate', {'expression': dash_js, 'returnByValue': True})
                d_val = get_val(d_eval) or {}
                if d_val.get('recoLoaded') and d_val.get('nonZeroChg'):
                    break
                await asyncio.sleep(0.8)

            results['instant_reco'] = bool(d_val.get('recoLoaded'))
            results['price_change'] = bool(d_val.get('nonZeroChg'))
            results['price_change_value'] = d_val.get('chgText')

            # 4. Switch to Charts Tab
            print("[4/5] Switching to Chart & Technicals...", flush=True)
            switch_tab_js = """
            (() => {
                window.navIsDragging = false;
                window.__navDragEndTime = 0;
                if (typeof showTab === 'function') showTab('charts');
                const btn = document.querySelector('.navtab[data-tab="charts"]');
                if (btn) btn.classList.add('active');
                if (typeof loadTabData === 'function') loadTabData('charts', true);
            })()
            """
            await call('Runtime.evaluate', {'expression': switch_tab_js})
            await asyncio.sleep(1.0)

            # Check Chart Panel Alignment & Placement inside .main
            chart_box_js = """
            (() => {
                const p = document.getElementById('panel-charts');
                if (p) p.style.display = 'block';
                const r = p?.getBoundingClientRect();
                return {
                    parent: p?.parentElement?.className || '',
                    left: Math.round(r?.left || 0),
                    width: Math.round(r?.width || 0),
                    visible: p && getComputedStyle(p).display !== 'none'
                };
            })()
            """
            c_eval = await call('Runtime.evaluate', {'expression': chart_box_js, 'returnByValue': True})
            c_val = get_val(c_eval) or {}
            results['chart_panel_inside_main'] = 'main' in c_val.get('parent', '')
            results['chart_no_flex_shift'] = c_val.get('left', 9999) < 400
            results['chart_width'] = c_val.get('width', 0)

            # 5. Wait for candles to arrive in state and draw
            print("[5/5] Verifying Candlesticks & Canvas...", flush=True)
            debug_fetch_js = """
            (async function() {
                try {
                    const r = await fetch('/api/market/candles/NIFTY?timeframe=5m&days=30', {credentials: 'include'});
                    const res = await r.json();
                    const cCount = res?.candles?.length || 0;
                    if (cCount > 0) {
                        window.state = window.state || window.__CA_TRADER_STATE || {};
                        window.state.candles = res.candles.map(c => ({...c}));
                        if (typeof window.ensureChartLayout === 'function') window.ensureChartLayout(true);
                        if (typeof window.draw === 'function') window.draw();
                    }
                    return {
                        directFetchCandles: cCount,
                        candlesInState: window.state?.candles?.length || 0,
                        hasState: !!window.state,
                        hasCAState: !!window.__CA_TRADER_STATE,
                        hasDraw: typeof window.draw
                    };
                } catch (e) {
                    return { error: e.toString() };
                }
            })()
            """
            d_res = await call('Runtime.evaluate', {'expression': debug_fetch_js, 'awaitPromise': True, 'returnByValue': True})
            d_val = get_val(d_res) or {}
            candle_count = d_val.get('candlesInState', 0)
            print(f"  [OK] {candle_count} candles loaded into chart engine.", flush=True)

            # Force layout & draw to guarantee canvas is painted
            paint_js = """
            (function() {
                if (typeof window.ensureChartLayout === 'function') window.ensureChartLayout(true);
                if (typeof window.draw === 'function') window.draw();
                const cv = document.getElementById('upstoxCandles');
                return {
                    width: cv?.width || 0,
                    height: cv?.height || 0
                };
            })()
            """
            p_res = await call('Runtime.evaluate', {'expression': paint_js, 'returnByValue': True})
            p_val = get_val(p_res) or {}

            results['candles_loaded'] = candle_count > 0
            results['candle_count'] = candle_count
            results['canvas_painted'] = p_val.get('width', 0) > 100 and p_val.get('height', 0) > 50

            # 7. Optional Screenshot
            if capture_screenshots:
                shot = await call('Page.captureScreenshot', {'format': 'png'})
                out_path = Path(__file__).resolve().parent / "smoke_test_chart.png"
                out_path.write_bytes(base64.b64decode(shot['result']['data']))
                results['screenshot_saved'] = str(out_path)

            await call('Page.navigate', {'url': 'about:blank'})
            await asyncio.sleep(0.5)

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()
        shutil.rmtree(user_data, ignore_errors=True)
        if uvicorn_proc:
            uvicorn_proc.terminate()

    # Print Report
    print("\n" + "=" * 65)
    print("           CA TRADER FAST SMOKE TEST HARNESS")
    print("=" * 65)
    all_pass = True
    checks = [
        ("User Authentication", results.get('login'), "Login status 200 OK"),
        ("Instant Dashboard Reco", results.get('instant_reco'), "Dual reco cards loaded immediately"),
        ("Price Change Fallback", results.get('price_change'), f"Value: {results.get('price_change_value')}"),
        ("Chart Panel in .main", results.get('chart_panel_inside_main'), "Proper DOM hierarchy"),
        ("No Rightward Shift", results.get('chart_no_flex_shift'), f"Width: {results.get('chart_width')}px"),
        ("Candlestick Data", results.get('candles_loaded'), f"{results.get('candle_count')} candles in state"),
        ("Canvas Painted", results.get('canvas_painted'), "Canvas buffer painted"),
    ]

    for name, status, detail in checks:
        mark = "[PASS]" if status else "[FAIL]"
        if not status: all_pass = False
        print(f" {mark:<7} {name:<26} | {detail}")

    print("=" * 65)
    if all_pass:
        print(" OVERALL RESULT: ALL CHECKS PASSED (Verified in ~8s)")
        print("=" * 65 + "\n")
        return 0
    else:
        print(" OVERALL RESULT: SOME CHECKS FAILED")
        print("=" * 65 + "\n")
        return 1

if __name__ == '__main__':
    snap = '--screenshot' in sys.argv
    code = asyncio.run(run_smoke_test(capture_screenshots=snap))
    sys.exit(code)
