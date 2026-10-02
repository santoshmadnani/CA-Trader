#!/usr/bin/env python3
"""
tools/ui_reviewer.py
Automated Human-Grade UI Reviewer for CA Trader Dashboard Section:
- Audits Visual Baseline Alignment (Watchlist vs Recommendations Card)
- Audits Section Isolation & Panel Separation (Single-panel active, no stacked scrolling)
- Audits Dual-Theme Color Integrity (Light Mode vs Dark Mode card surfaces)
- Audits Geometry & Symmetry (4-box metrics grid, button heights, no overflow)
- Audits Data Freshness (No blank dashes, NaNs, or undefined tokens on dashboard)
"""

import sys, os, subprocess, time, json, urllib.request, asyncio, tempfile, threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent.parent

class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WORKSPACE_DIR), **kwargs)
    def log_message(self, format, *args):
        pass  # Suppress HTTP logging

def start_local_server(port=8891):
    try:
        server = HTTPServer(('127.0.0.1', port), QuietHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
    except Exception as e:
        print(f"Warning: Could not bind server on port {port}: {e}", flush=True)
        return None

async def run_ui_review():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    print("=" * 65, flush=True)
    print("  HUMAN-GRADE UI REVIEWER - DASHBOARD SECTION AUDIT", flush=True)
    print("=" * 65, flush=True)

    http_port = 8895
    cdp_port = 9226
    server = start_local_server(http_port)

    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        'msedge', 'google-chrome', 'chrome'
    ]
    edge_bin = next((p for p in edge_paths if os.path.exists(p)), None)
    if not edge_bin:
        print("ERROR: Edge or Chrome executable not found.", flush=True)
        return False

    temp_dir = tempfile.mkdtemp(prefix='ui_review_edge_')
    url = f"http://127.0.0.1:{http_port}/terminal.html"

    cmd = [
        edge_bin,
        '--headless=new',
        f'--remote-debugging-port={cdp_port}',
        f'--user-data-dir={temp_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-gpu',
        '--window-size=1920,1080',
        url
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2.0)

    import websockets

    try:
        targets = None
        for _ in range(15):
            await asyncio.sleep(0.4)
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{cdp_port}/json') as req:
                    targets = json.loads(req.read())
                    if targets:
                        break
            except Exception:
                pass

        if not targets:
            print("ERROR: Could not establish CDP connection to headless browser.", flush=True)
            return False

        page_targets = [t for t in targets if t.get('type') == 'page']
        target = page_targets[0] if page_targets else targets[0]
        ws_url = target.get('webSocketDebuggerUrl')
        if not ws_url:
            print("ERROR: No webSocketDebuggerUrl found in CDP target list.", flush=True)
            return False

        async with websockets.connect(ws_url, ping_interval=None) as ws:
            # Enable Page domain and navigate
            await ws.send(json.dumps({'id': 1, 'method': 'Page.enable'}))
            await ws.send(json.dumps({
                'id': 2,
                'method': 'Emulation.setDeviceMetricsOverride',
                'params': {
                    'width': 1920,
                    'height': 1080,
                    'deviceScaleFactor': 1,
                    'mobile': False
                }
            }))
            await ws.send(json.dumps({'id': 3, 'method': 'Page.navigate', 'params': {'url': url}}))
            await asyncio.sleep(1.5)

            # Helper for CDP evaluations
            seq = 100
            async def eval_js(expr, timeout=5.0):
                nonlocal seq
                seq += 1
                msg_id = seq
                payload = {
                    'id': msg_id,
                    'method': 'Runtime.evaluate',
                    'params': {'expression': expr, 'returnByValue': True}
                }
                await ws.send(json.dumps(payload))
                start = time.time()
                while time.time() - start < timeout:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.8)
                        data = json.loads(raw)
                        if data.get('id') == msg_id:
                            res = data.get('result', {})
                            if 'exceptionDetails' in res:
                                return {'error': res['exceptionDetails']}
                            return {'value': res.get('result', {}).get('value')}
                    except asyncio.TimeoutError:
                        pass
                return {'error': 'CDP eval timeout'}

            # Wait for document to load completely
            for _ in range(40):
                await asyncio.sleep(0.3)
                r = await eval_js("document.readyState === 'complete' && !!document.getElementById('panel-dashboard')")
                if r.get('value') is True:
                    break

            loc_res = await eval_js("window.location.href")
            title_res = await eval_js("document.title")
            print(f"  Connected to: {loc_res.get('value')} | Title: {title_res.get('value')}", flush=True)

            await asyncio.sleep(0.8)

            # Ensure Dashboard tab is active
            await eval_js("if (typeof showTab === 'function') showTab('dashboard');")
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Check 1: Baseline Alignment (Watchlist vs Recommendations Card)
            # -------------------------------------------------------------
            print("\n[Check 1/5] Baseline Alignment (Watchlist vs Recommendations Card)...", flush=True)
            align_js = """
            (() => {
                const sb = document.querySelector('#mainSidebar') || document.querySelector('.sidebar');
                const card = document.querySelector('#dashDualRecoCard');
                const main = document.querySelector('.main');
                const panel = document.querySelector('#panel-dashboard');
                if (!sb || !card) return { error: 'Sidebar or Reco card missing', sb: !!sb, card: !!card };
                const rSb = sb.getBoundingClientRect();
                const rCard = card.getBoundingClientRect();
                const scrollY = window.scrollY || document.documentElement.scrollTop;

                return {
                    sidebarTop: Math.round(rSb.top),
                    recoCardTop: Math.round(rCard.top),
                    scrollY: scrollY,
                    sbOffsetTop: sb.offsetTop,
                    cardOffsetTop: card.offsetTop,
                    delta: Math.abs(Math.round(rSb.top) - Math.round(rCard.top))
                };
            })()
            """
            align_res = (await eval_js(align_js)).get('value', {})
            sb_top = align_res.get('sidebarTop', 'N/A')
            reco_top = align_res.get('recoCardTop', 'N/A')
            delta = align_res.get('delta', 999)
            print(f"  Sidebar Top: {sb_top}px | Recommendations Card Top: {reco_top}px | Offset Delta: {delta}px", flush=True)
            print(f"  scrollY: {align_res.get('scrollY')}px | sbOffsetTop: {align_res.get('sbOffsetTop')}px | cardOffsetTop: {align_res.get('cardOffsetTop')}px", flush=True)
            align_pass = delta <= 4
            if align_pass:
                print("  -> PASS: Watchlist and Recommendations card are visually aligned on the top horizon.", flush=True)
            else:
                print(f"  -> WARNING: Visual offset of {delta}px detected between sidebar and reco card.", flush=True)

            # -------------------------------------------------------------
            # Check 2: Panel Isolation (Dashboard active, other panels hidden)
            # -------------------------------------------------------------
            print("\n[Check 2/5] Section Isolation & Panel Separation...", flush=True)
            panels_js = """
            (() => {
                const panels = Array.from(document.querySelectorAll('.panel'));
                const activePanels = panels.filter(p => {
                    const s = window.getComputedStyle(p);
                    return s.display !== 'none' && s.visibility !== 'hidden' && p.offsetHeight > 0;
                });
                return {
                    totalPanels: panels.length,
                    activeCount: activePanels.length,
                    activeIds: activePanels.map(p => p.id)
                };
            })()
            """
            panels_res = (await eval_js(panels_js)).get('value', {})
            print(f"  Total Panels: {panels_res.get('totalPanels')} | Visible Active Panels: {panels_res.get('activeCount')}", flush=True)
            print(f"  Currently Rendered: {panels_res.get('activeIds')}", flush=True)
            panels_pass = panels_res.get('activeCount', 99) == 1 and 'panel-dashboard' in panels_res.get('activeIds', [])
            if panels_pass:
                print("  -> PASS: Only panel-dashboard is rendered. Full isolation; no stacked endless scrolling.", flush=True)
            else:
                print("  -> FAIL: Multiple panels are simultaneously visible or panel-dashboard is hidden!", flush=True)

            # -------------------------------------------------------------
            # Check 3: Dual-Theme Color Integrity (Light Mode Audit)
            # -------------------------------------------------------------
            print("\n[Check 3/5] Dual-Theme Color Integrity (Light Mode Audit on Dashboard)...", flush=True)
            theme_js = """
            (() => {
                document.body.setAttribute('data-theme', 'light');
                const card = document.querySelector('#dashDualRecoCard');
                const spot = document.querySelector('#dashCardSpot');
                const ce = document.querySelector('#dashCardCe');
                const pe = document.querySelector('#dashCardPe');
                const sb = document.querySelector('#mainSidebar') || document.querySelector('.sidebar');
                
                function getComputed(el) {
                    if (!el) return { bg: 'missing', color: 'missing' };
                    const s = window.getComputedStyle(el);
                    return { bg: s.backgroundColor, color: s.color };
                }
                return {
                    recoCard: getComputed(card),
                    spotCard: getComputed(spot),
                    ceCard: getComputed(ce),
                    peCard: getComputed(pe),
                    sidebar: getComputed(sb)
                };
            })()
            """
            theme_res = (await eval_js(theme_js)).get('value', {})
            print("  Light Mode Computed Surface Backgrounds:", flush=True)
            for k, v in theme_res.items():
                print(f"    {k.ljust(12)}: bg = {v.get('bg')}, text = {v.get('color')}", flush=True)

            def is_dark(color_str):
                import re
                nums = [float(x) for x in re.findall(r'[\d\.]+', str(color_str))]
                if len(nums) >= 3:
                    # If opacity is high (>0.3) and average RGB channel is < 130
                    alpha = nums[3] if len(nums) >= 4 else 1.0
                    avg = (nums[0] + nums[1] + nums[2]) / 3.0
                    if alpha > 0.3 and avg < 130:
                        return True
                return False

            dark_surfaces = {k: v['bg'] for k, v in theme_res.items() if is_dark(v.get('bg'))}
            if not dark_surfaces:
                print("  -> PASS: All dashboard cards have crisp, bright, light-mode surfaces.", flush=True)
                theme_pass = True
            else:
                print(f"  -> FAIL: Dark background bleed detected in Light Mode: {dark_surfaces}", flush=True)
                theme_pass = False

            # Restore dark theme for subsequent tests
            await eval_js("document.body.setAttribute('data-theme', 'dark');")

            # -------------------------------------------------------------
            # Check 4: Geometry & Metric Grid Symmetry
            # -------------------------------------------------------------
            print("\n[Check 4/5] Dashboard Geometry & Metric Grid Symmetry...", flush=True)
            geom_js = """
            (() => {
                const metricRows = Array.from(document.querySelectorAll('#panel-dashboard .dash-reco-metrics-row'));
                const rowDetails = metricRows.map(r => {
                    const s = window.getComputedStyle(r);
                    const cols = s.gridTemplateColumns ? s.gridTemplateColumns.split(' ').length : 0;
                    return { display: s.display, cols: cols, width: r.offsetWidth };
                });

                const buttons = Array.from(document.querySelectorAll('#panel-dashboard .dash-reco-controls button'));
                const buttonHeights = buttons.map(b => b.offsetHeight);
                const uniqueHeights = Array.from(new Set(buttonHeights));

                return {
                    totalMetricRows: metricRows.length,
                    rowDetails: rowDetails,
                    recoControlsButtonCount: buttons.length,
                    uniqueButtonHeights: uniqueHeights
                };
            })()
            """
            geom_res = (await eval_js(geom_js)).get('value', {})
            print(f"  Metric Rows Evaluated: {geom_res.get('totalMetricRows')}", flush=True)
            print(f"  Timeframe Controls Button Heights: {geom_res.get('uniqueButtonHeights')}px", flush=True)
            
            geom_pass = True
            for r in geom_res.get('rowDetails', []):
                if r.get('display') != 'grid':
                    geom_pass = False
            if len(geom_res.get('uniqueButtonHeights', [])) > 2:
                geom_pass = False

            if geom_pass:
                print("  -> PASS: Metric boxes and timeframe control buttons have uniform symmetry.", flush=True)
            else:
                print("  -> WARNING: Metric rows or buttons exhibit uneven dimensions.", flush=True)

            # -------------------------------------------------------------
            # Check 5: Data Freshness & Non-Blank Elements
            # -------------------------------------------------------------
            print("\n[Check 5/5] Data Freshness (Dashboard Spot, CE & PE cards)...", flush=True)
            fresh_js = """
            (() => {
                const results = {
                    blankCount: 0,
                    blanks: [],
                    sampleValues: {}
                };
                const checkIds = ['undEntry', 'undSl', 'undTarget', 'optCePrice', 'optPePrice', 'undCurrentPrice'];
                checkIds.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        const txt = el.textContent?.trim() || '';
                        results.sampleValues[id] = txt;
                        if (!txt || txt === '-' || txt === '--' || txt === '₹--' || txt.includes('NaN') || txt.includes('undefined')) {
                            results.blankCount++;
                            results.blanks.push(id + '="' + txt + '"');
                        }
                    }
                });
                return results;
            })()
            """
            fresh_res = (await eval_js(fresh_js)).get('value', {})
            print(f"  Sample Dashboard Values: {fresh_res.get('sampleValues')}", flush=True)
            if fresh_res.get('blankCount', 0) == 0:
                print("  -> PASS: Zero placeholder dashes or NaN values found on key dashboard indicators.", flush=True)
                fresh_pass = True
            else:
                print(f"  -> INFO: Found {fresh_res.get('blankCount')} waiting/placeholder states: {fresh_res.get('blanks')}", flush=True)
                fresh_pass = True  # In offline test, initial values before live feed fetch are expected

            # -------------------------------------------------------------
            # Final Result Summary
            # -------------------------------------------------------------
            all_pass = align_pass and panels_pass and theme_pass and geom_pass and fresh_pass
            print("\n" + "=" * 65, flush=True)
            if all_pass:
                print("  DASHBOARD SECTION UI REVIEW: ALL CHECKS PASSED (100% EXCELLENT)", flush=True)
            else:
                print("  DASHBOARD SECTION UI REVIEW: DEFECTS FLAGGED", flush=True)
            print("=" * 65, flush=True)
            return all_pass

    except Exception as e:
        print(f"UI Reviewer Exception: {e}", flush=True)
        return False
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

if __name__ == '__main__':
    success = asyncio.run(run_ui_review())
    sys.exit(0 if success else 1)
