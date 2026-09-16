#!/usr/bin/env python3
import sys, re

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    code = f.read()

print(f"Loaded terminal.html ({len(code):,} bytes)")

# -----------------------------------------------------------------------------
# 1. Update updateFloatingPositionsWidget to handle posData.items || posData.positions
# -----------------------------------------------------------------------------
old_pos_parse = '''      const posData = await api('/api/positions?status=OPEN');
      const positions = posData.positions || [];'''

new_pos_parse = '''      const posData = await api('/api/positions?status=OPEN');
      const rawList = posData.items || posData.positions || [];
      const positions = rawList.filter(p => String(p.status || 'OPEN').toUpperCase() === 'OPEN' && Number(p.quantity || 0) > 0);'''

if old_pos_parse in code:
    code = code.replace(old_pos_parse, new_pos_parse, 1)
    print("Fixed floating position widget data mapping (items || positions)")
else:
    print("Warning: old_pos_parse not matched")

# -----------------------------------------------------------------------------
# 2. Update toggleMobileLandscapeFullscreen to request true video-style fullscreen
# -----------------------------------------------------------------------------
old_fs = '''function toggleMobileLandscapeFullscreen(){
    const shell = document.getElementById('chartShell') || document.getElementById('panel-charts');
    if(!shell) return;
    const isMobile = window.innerWidth <= 768;
    
    if(isMobile){
      const isForced = shell.classList.toggle('chart-forced-landscape');
      if(isForced){
        toast('🔄 Rotated to Landscape Fullscreen');
      }
    } else {
      if(!document.fullscreenElement){
        if(shell.requestFullscreen) await shell.requestFullscreen();
      } else {
        if(document.exitFullscreen) await document.exitFullscreen();
      }
    }
  }'''

new_fs = '''async function toggleMobileLandscapeFullscreen(){
    const shell = document.getElementById('chartShell') || document.getElementById('panel-charts');
    if(!shell) return;
    const isMobile = window.innerWidth <= 768;
    
    try {
      if(!document.fullscreenElement && !document.webkitFullscreenElement){
        if(shell.requestFullscreen) await shell.requestFullscreen();
        else if(shell.webkitRequestFullscreen) await shell.webkitRequestFullscreen();
        if(screen.orientation && typeof screen.orientation.lock === 'function'){
          screen.orientation.lock('landscape').catch(() => {});
        }
        if(isMobile) shell.classList.add('chart-forced-landscape');
        toast('📺 Fullscreen Landscape Activated');
      } else {
        if(document.exitFullscreen) await document.exitFullscreen();
        else if(document.webkitExitFullscreen) await document.webkitExitFullscreen();
        if(screen.orientation && typeof screen.orientation.unlock === 'function'){
          screen.orientation.unlock().catch(() => {});
        }
        shell.classList.remove('chart-forced-landscape');
        toast('Exited Fullscreen');
      }
    } catch(err){
      // Fallback for iOS Safari which restricts requestFullscreen to video elements
      const isForced = shell.classList.toggle('chart-forced-landscape');
      toast(isForced ? '🔄 Rotated Landscape Mode' : 'Normal View');
    }
  }'''

if old_fs in code:
    code = code.replace(old_fs, new_fs, 1)
    print("Updated fullscreen toggle with true video-style requestFullscreen & orientation lock")
else:
    print("Warning: old_fs not matched")

# -----------------------------------------------------------------------------
# 3. Fix Drawing Lock check in pointerdown so unlocking allows moving drawings
# -----------------------------------------------------------------------------
old_lock_down = '''    const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:findDrawingAt(x,y);
    const ih = hit < 0 ? indicatorHit(x, y) : -1;
    state.selectedDrawingIdx = hit;
    state.selectedIndicatorIdx = ih;
    draw();
    if(hit>=0&&!state.panArmed&&!state.yPanArmed&&state.interactionMode!=='pan'){
      const handle = getDrawingHandleAt(hit, x, y, view) || 'body';
      state.dragDrawing={
        idx:hit,
        handle:handle,
        startX:e.clientX,
        startY:e.clientY,
        orig:JSON.parse(JSON.stringify(state.drawings[hit])),
        moved:false
      };
      showDrawingTooltip(hit,e.clientX,e.clientY);
      vp.setPointerCapture(e.pointerId);
      return;
    }'''

new_lock_down = '''    const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:findDrawingAt(x,y);
    const ih = hit < 0 ? indicatorHit(x, y) : -1;
    state.selectedDrawingIdx = (state.drawingsLocked ? -1 : hit);
    state.selectedIndicatorIdx = ih;
    draw();
    if(hit>=0 && !state.drawingsLocked && !state.panArmed && !state.yPanArmed && state.interactionMode!=='pan'){
      const handle = getDrawingHandleAt(hit, x, y, view) || 'body';
      state.dragDrawing={
        idx:hit,
        handle:handle,
        startX:e.clientX,
        startY:e.clientY,
        orig:JSON.parse(JSON.stringify(state.drawings[hit])),
        moved:false
      };
      showDrawingTooltip(hit,e.clientX,e.clientY);
      try { vp.setPointerCapture(e.pointerId); } catch(_) {}
      return;
    }'''

if old_lock_down in code:
    code = code.replace(old_lock_down, new_lock_down, 1)
    print("Updated pointerdown with strict drawingsLocked respect for handle moving")
else:
    print("Warning: old_lock_down not matched")

# -----------------------------------------------------------------------------
# 4. Attach universal draggable handlers and initialize Release 49 components
# -----------------------------------------------------------------------------
RELEASE_49_INIT = '''
  // Release 49 Initialization
  setTimeout(() => {
    // Make Floating Positions Widget movable
    const fpWidget = document.getElementById('floatingPositionWidget');
    const fpHead = document.getElementById('floatingPosHead');
    if(fpWidget && fpHead && typeof makeUniversalDraggable === 'function') {
      makeUniversalDraggable(fpWidget, fpHead);
    }

    // Make Quick Order Modal movable
    const qoCard = document.querySelector('#quickOrderModal .tool-modal-card');
    const qoHead = document.querySelector('#quickOrderModal .card-head');
    if(qoCard && qoHead && typeof makeUniversalDraggable === 'function') {
      makeUniversalDraggable(qoCard, qoHead);
    }

    // Make Regular Order Modal movable
    const ordCard = document.querySelector('#orderModal .tool-modal-card');
    const ordHead = document.querySelector('#orderModal .card-head');
    if(ordCard && ordHead && typeof makeUniversalDraggable === 'function') {
      makeUniversalDraggable(ordCard, ordHead);
    }

    // Make CA AI Chat Modal movable
    const aiCard = document.querySelector('#caAiModal .tool-modal-card');
    const aiHead = document.querySelector('#caAiModal .card-head');
    if(aiCard && aiHead && typeof makeUniversalDraggable === 'function') {
      makeUniversalDraggable(aiCard, aiHead);
    }

    // Make CA AI Indicator Drawer movable on desktop
    const aiPanel = document.getElementById('chartAiPanel');
    const aiPanelHead = aiPanel ? aiPanel.querySelector('div:first-child') : null;
    if(aiPanel && aiPanelHead && typeof makeUniversalDraggable === 'function') {
      makeUniversalDraggable(aiPanel, aiPanelHead);
    }

    // Initial sync of floating positions widget
    if(typeof updateFloatingPositionsWidget === 'function') {
      updateFloatingPositionsWidget();
    }
  }, 1200);
'''

if '// Release 49 Initialization' not in code:
    code = code.replace('</body>', f'<script>{RELEASE_49_INIT}</script>\n</body>', 1)
    print("Injected draggable initialization into terminal.html")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(code)

print("Saved core terminal updates.")

