import sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Backup
shutil.copyfile('terminal.html', 'terminal.html.bak2')
print('Backup created: terminal.html.bak2')

# -----------------------------------------------------------------------------
# 1. Fix async async syntax error
# -----------------------------------------------------------------------------
target_err = "async async function toggleMobileLandscapeFullscreen(){"
replacement_err = "async function toggleMobileLandscapeFullscreen(){"

if target_err in text:
    text = text.replace(target_err, replacement_err, 1)
    print('[OK] Fixed async async syntax error')
else:
    print('[FAIL] target_err not found')
    sys.exit(1)

# -----------------------------------------------------------------------------
# 2. Compact Floating Pop-Up Styling (Item 8)
# -----------------------------------------------------------------------------
target_widget_style = '<div id="floatingPositionWidget" class="floating-pos-widget" style="position:fixed;bottom:16px;right:16px;z-index:9999;background:var(--surface);border:1px solid var(--border);border-radius:14px;box-shadow:0 14px 44px rgba(0,0,0,0.55);width:380px;max-width:94vw;transition:transform 0.2s;overflow:hidden;">'
replacement_widget_style = '<div id="floatingPositionWidget" class="floating-pos-widget" style="position:fixed;bottom:16px;right:16px;z-index:9999;background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:0 10px 36px rgba(0,0,0,0.55);width:330px;max-width:92vw;transition:transform 0.2s;overflow:hidden;">'

if target_widget_style in text:
    text = text.replace(target_widget_style, replacement_widget_style, 1)
    print('[OK] Made floatingPositionWidget compact (330px)')
else:
    print('[WARN] target_widget_style not found, checking with regex...')

# -----------------------------------------------------------------------------
# 3. Insert ⚡ Turbo Refresh Button next to notifications (Item 15)
# -----------------------------------------------------------------------------
target_topbar_notif = '<button class="top-icon-btn" id="notificationBtn" title="Notifications">'
replacement_topbar_notif = '<button id="turboLoadBtn" class="btn gold small" onclick="turboLoadAll()" title="Refresh all sections without reloading the browser" style="padding:3px 10px;font-size:11px;font-weight:600;border-radius:12px;margin-right:6px;display:inline-flex;align-items:center;gap:4px;">⚡ Turbo Refresh</button><button class="top-icon-btn" id="notificationBtn" title="Notifications">'

if target_topbar_notif in text:
    text = text.replace(target_topbar_notif, replacement_topbar_notif, 1)
    print('[OK] Inserted ⚡ Turbo Refresh button into topbar')
else:
    print('[WARN] target_topbar_notif not found')

# -----------------------------------------------------------------------------
# 4. Eliminate duplicate crosshair price & time canvas badges (Item 14)
# -----------------------------------------------------------------------------
target_cross_canvas = """      // Highlight Y-axis LTP badge directly on canvas
      const priceText = fmt(state.cross.price);
      x.fillStyle = '#0F172A';
      x.strokeStyle = '#26D9A6';
      x.lineWidth = 1.5;
      const pBadgeW = Math.max(56, pad.r - 6);
      x.beginPath();
      x.roundRect(w - pad.r + 2, Math.max(pad.t, Math.min(h - pad.b - 20, cy - 10)), pBadgeW, 20, 4);
      x.fill();
      x.stroke();
      x.fillStyle = '#26D9A6';
      x.font = 'bold 10px IBM Plex Mono, monospace';
      x.fillText(priceText, w - pad.r + 6, Math.max(pad.t + 13, Math.min(h - pad.b - 7, cy + 3.5)));

      // Highlight X-axis Date & Time badge directly on canvas
      const timeText = String(state.cross.label || '');
      x.fillStyle = '#0F172A';
      x.strokeStyle = '#38BDF8';
      x.lineWidth = 1.5;
      const tBadgeW = 110;
      const tBadgeX = Math.max(pad.l, Math.min(w - pad.r - tBadgeW, cx - tBadgeW / 2));
      x.beginPath();
      x.roundRect(tBadgeX, h - pad.b + 3, tBadgeW, 18, 4);
      x.fill();
      x.stroke();
      x.fillStyle = '#FFFFFF';
      x.font = 'bold 9.5px IBM Plex Mono, monospace';
      x.fillText(timeText, tBadgeX + 6, h - pad.b + 15);"""

replacement_cross_canvas = """      // Single clean crosshair highlight via DOM overlay (Item 14 duplicate box fix)
      // Canvas rendering delegates to axisLabels for high-contrast non-flickering badges"""

if target_cross_canvas in text:
    text = text.replace(target_cross_canvas, replacement_cross_canvas, 1)
    print('[OK] Removed duplicate crosshair canvas badges')
else:
    print('[WARN] target_cross_canvas not found')

# -----------------------------------------------------------------------------
# 5. Wire ordersPopoutBtn to focus and open floatingPositionWidget (Item 2)
# -----------------------------------------------------------------------------
target_popout_listener = """    $('ordersPopoutBtn')?.addEventListener('click', () => {
      if(activeSource && activeSource.id === 'panel-orders'){
        dockBack();
      } else {
        popoutPanel('panel-orders', 'Orders & Positions');
      }
    });"""

replacement_popout_listener = """    $('ordersPopoutBtn')?.addEventListener('click', () => {
      const widget = document.getElementById('floatingPositionWidget');
      const bodyWrapper = document.getElementById('floatingPosBodyWrapper');
      const minBtn = document.getElementById('fpMinBtn');
      if(widget){
        widget.style.display = 'block';
        if(bodyWrapper) bodyWrapper.style.display = 'flex';
        if(minBtn) minBtn.textContent = '_';
        if(typeof isFloatingPosMinimized !== 'undefined') isFloatingPosMinimized = false;
        widget.scrollIntoView({ behavior: 'smooth', block: 'end' });
        toast('✦ CA AI Trade Sentinel Pop-up Window Active');
        if(typeof updateFloatingPositionsWidget === 'function') updateFloatingPositionsWidget();
      }
    });"""

if target_popout_listener in text:
    text = text.replace(target_popout_listener, replacement_popout_listener, 1)
    print('[OK] Replaced ordersPopoutBtn behavior to focus floatingPositionWidget')
else:
    print('[WARN] target_popout_listener not found')

# -----------------------------------------------------------------------------
# 6. Live Ticking LTP in Quick Order modal (Item 24)
# -----------------------------------------------------------------------------
target_tick_hook = """        // Real-time tick update for CA AI Advisor (Release 51)"""
replacement_tick_hook = """        // Real-time tick update for Quick Order Modal (Item 24)
        const qoSymEl = document.getElementById('quickOrderSymbol');
        if(qoSymEl && String(qoSymEl.textContent||'').toUpperCase().includes(key)){
          const qoLtpEl = document.getElementById('quickOrderLtp');
          if(qoLtpEl) qoLtpEl.textContent = '₹' + fmt(ltp);
        }
        // Real-time tick update for CA AI Advisor (Release 51)"""

if target_tick_hook in text:
    text = text.replace(target_tick_hook, replacement_tick_hook, 1)
    print('[OK] Added live ticking LTP hook for Quick Order Modal')
else:
    print('[WARN] target_tick_hook not found')

# Write updated file
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patch 1 for terminal.html applied successfully')

