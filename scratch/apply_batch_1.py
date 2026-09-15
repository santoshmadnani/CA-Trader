import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update mid in draw() for state.panY
old_draw_mid = "const baseRange=(hi-lo)||1;const mid=(hi+lo)/2;const scaled=baseRange/state.yScale;"
new_draw_mid = "const baseRange=(hi-lo)||1;const midShift=(state.panY||0)*baseRange*0.005;const mid=((hi+lo)/2)+midShift;const scaled=baseRange/state.yScale;"
if old_draw_mid in content:
    content = content.replace(old_draw_mid, new_draw_mid, 1)
    print("✓ Updated draw() mid calculation for vertical panning")
else:
    print("⚠ Could not find old_draw_mid")

# 2. Update pointerdown, pointermove, pointerup for pan and crosshair
old_pointer_block = """  vp.addEventListener('pointermove',e=>{const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;if(state.dragDrawing){const md=Math.hypot(e.clientX-state.dragDrawing.startX,e.clientY-state.dragDrawing.startY);if(md>=4)state.dragDrawing.moved=true;if(!state.dragDrawing.moved){updateCross(e);return}const dx=e.clientX-state.dragDrawing.x,dy=e.clientY-state.dragDrawing.y;moveDrawing(state.drawings[state.dragDrawing.idx],dx,dy,getView());state.dragDrawing.x=e.clientX;state.dragDrawing.y=e.clientY;vp.classList.add('drawing-hover');showDrawingTooltip(state.dragDrawing.idx,e.clientX,e.clientY);draw();return}updateCross(e);const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;state.hoverDrawing=hit;if(hit>=0){vp.classList.add('drawing-hover');showDrawingTooltip(hit,e.clientX,e.clientY)}else if(ih>=0){vp.classList.add('drawing-hover');showDrawingTooltip(-1,e.clientX,e.clientY,ih)}else{vp.classList.remove('drawing-hover');showDrawingTooltip(-1,0,0)}if(state.drag){const dx=e.clientX-state.drag.x,dy=e.clientY-state.drag.y,view=getView();if(state.drag.axis==='y'){state.yScale=Math.max(.5,Math.min(5,state.drag.startScale*Math.exp(-dy/Math.max(1,vp.clientHeight))))}else{const step=(vp.clientWidth-84)/view.count;state.panX=Math.max(0,Math.min(state.candles.length-view.count,Math.round(state.drag.startX-dx/Math.max(1,step))))}draw()}});
  vp.addEventListener('pointerdown',e=>{if(e.button!==0)return;const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;const view=getView();if(x>vp.clientWidth-72 && !state.pendingDrawing && state.interactionMode!=='pan'){state.drag={x:e.clientX,y:e.clientY,startX:state.panX,startY:state.panY,startScale:state.yScale,axis:'y'};vp.setPointerCapture(e.pointerId);return}if(state.pendingDrawing){applyDrawingPoint(x,y);state.pendingDrawing=null;state.drawingStage=[];state.hoverDrawing=-1;state.interactionMode='crosshair';vp.classList.remove('pan-mode','drawing-hover');return}const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:-1;if(state.interactionMode==='move'&&hit>=0&&!state.panArmed&&!state.yPanArmed&&state.hoverDrawing===hit){state.dragDrawing={idx:hit,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,moved:false};showDrawingTooltip(hit,e.clientX,e.clientY);vp.setPointerCapture(e.pointerId);return}if(state.yPanArmed||state.panArmed||state.interactionMode==='pan'){state.drag={x:e.clientX,y:e.clientY,startX:state.panX,startY:state.panY,axis:state.yPanArmed?'y':'x'};state.yPanArmed=false;state.panArmed=false;vp.setPointerCapture(e.pointerId);return}});
  vp.addEventListener('pointerup',e=>{state.drag=null;state.dragDrawing=null;state.panArmed=false;state.yPanArmed=false;vp.classList.remove('drawing-hover');if(state.interactionMode!=='pan')vp.classList.remove('pan-mode');showDrawingTooltip(-1,0,0);draw();try{vp.releasePointerCapture(e.pointerId)}catch(_){} });
  vp.addEventListener('pointerleave',()=>{if(!state.drag&&!state.dragDrawing){state.cross=null;vp.classList.remove('drawing-hover');draw();showDrawingTooltip(-1,0,0)}});
  vp.addEventListener('dblclick',e=>{const r=vp.getBoundingClientRect(),x=e.clientX-r.left;if(x>vp.clientWidth-72){state.yPanArmed=true;state.panArmed=false;toast('Y-axis pan armed — drag vertically');}else if(!state.pendingDrawing){state.panArmed=true;state.yPanArmed=false;state.interactionMode='pan';document.getElementById('chartModeToggle')?.classList.add('active');toast('Double-click and drag to pan chart')}});
  vp.addEventListener('wheel',e=>{if(!e.ctrlKey)return; e.preventDefault();const view=getView(),r=vp.getBoundingClientRect(),x=e.clientX-r.left,i=indexFromX(x,view),ratio=i/Math.max(1,view.count-1),old=state.zoom;state.zoom=Math.max(.45,Math.min(6,old*(e.deltaY<0?1.12:.89)));const nc=Math.max(20,Math.min(state.candles.length,Math.floor(state.visible/state.zoom)));state.panX=Math.max(0,Math.min(state.candles.length-nc,Math.round(view.start+ratio*(view.count-nc))));draw()},{passive:false});

  document.addEventListener('keydown',e=>{if(e.key==='Escape'){state.pendingDrawing=null;state.drawingStage=[];state.dragDrawing=null;state.drag=null;state.panArmed=false;state.yPanArmed=false;state.interactionMode='crosshair';hideAxisLabels();draw();}});
  document.getElementById('chartFullscreen').onclick=async()=>{try{const shell=document.getElementById('chartShell');if(!document.fullscreenElement)await shell.requestFullscreen();else await document.exitFullscreen()}catch(e){toast('Full screen is unavailable in this browser')}};
  document.addEventListener('fullscreenchange',()=>{state.fullscreen=!!document.fullscreenElement;setTimeout(draw,50)});
  document.getElementById('chartModeToggle')?.addEventListener('click',()=>{state.interactionMode=state.interactionMode==='crosshair'?'pan':state.interactionMode==='pan'?'move':'crosshair';const b=document.getElementById('chartModeToggle');if(b)b.textContent=state.interactionMode==='pan'?'Pan':state.interactionMode==='move'?'Move drawing':'Crosshair';vp.classList.toggle('pan-mode',state.interactionMode==='pan');});"""

new_pointer_block = """  function setChartInteractionMode(mode){
    state.interactionMode = mode;
    const b = document.getElementById('chartModeToggle');
    const isPan = mode === 'pan';
    if(b){
      b.textContent = isPan ? 'Pan' : 'Crosshair';
      b.classList.toggle('active', isPan);
      b.title = isPan ? 'Currently in Pan mode — Drag chart freely horizontally & vertically. Click to switch to Crosshair' : 'Currently in Crosshair mode — Click to switch to Pan';
    }
    vp.classList.toggle('pan-mode', isPan);
    vp.style.cursor = isPan ? 'grab' : 'crosshair';
    if(isPan){
      state.cross = null;
      hideAxisLabels();
    }
    draw();
  }

  vp.addEventListener('pointermove',e=>{
    const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    if(state.dragDrawing){
      const md=Math.hypot(e.clientX-state.dragDrawing.startX,e.clientY-state.dragDrawing.startY);
      if(md>=4) state.dragDrawing.moved=true;
      if(!state.dragDrawing.moved){ updateCross(e); return; }
      const dx=e.clientX-state.dragDrawing.x,dy=e.clientY-state.dragDrawing.y;
      moveDrawing(state.drawings[state.dragDrawing.idx],dx,dy,getView());
      state.dragDrawing.x=e.clientX; state.dragDrawing.y=e.clientY;
      vp.classList.add('drawing-hover');
      showDrawingTooltip(state.dragDrawing.idx,e.clientX,e.clientY);
      draw();
      return;
    }
    if(state.drag){
      const dx=e.clientX-state.drag.x, dy=e.clientY-state.drag.y, view=getView();
      if(state.drag.axis==='y'){
        state.yScale=Math.max(.5,Math.min(5,state.drag.startScale*Math.exp(-dy/Math.max(1,vp.clientHeight))));
      } else if(state.drag.axis==='both'){
        const step=(vp.clientWidth-84)/Math.max(1,view.count);
        state.panX=Math.max(0,Math.min(state.candles.length-view.count,Math.round(state.drag.startX-dx/Math.max(1,step))));
        state.panY=(state.drag.startY||0)+(dy*0.4);
      } else {
        const step=(vp.clientWidth-84)/Math.max(1,view.count);
        state.panX=Math.max(0,Math.min(state.candles.length-view.count,Math.round(state.drag.startX-dx/Math.max(1,step))));
      }
      draw();
      return;
    }
    if(state.interactionMode==='pan'){
      vp.style.cursor = 'grab';
      state.cross = null;
      hideAxisLabels();
      return;
    }
    updateCross(e);
    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;
    state.hoverDrawing=hit;
    if(hit>=0){ vp.classList.add('drawing-hover'); showDrawingTooltip(hit,e.clientX,e.clientY); }
    else if(ih>=0){ vp.classList.add('drawing-hover'); showDrawingTooltip(-1,e.clientX,e.clientY,ih); }
    else { vp.classList.remove('drawing-hover'); showDrawingTooltip(-1,0,0); }
  });

  vp.addEventListener('pointerdown',e=>{
    if(e.button!==0) return;
    const r=vp.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    const view=getView();
    if(x>vp.clientWidth-72 && !state.pendingDrawing && state.interactionMode!=='pan'){
      state.drag={x:e.clientX,y:e.clientY,startX:state.panX,startY:state.panY,startScale:state.yScale,axis:'y'};
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if(state.pendingDrawing){
      applyDrawingPoint(x,y);
      state.pendingDrawing=null;
      state.drawingStage=[];
      state.hoverDrawing=-1;
      state.interactionMode='crosshair';
      vp.classList.remove('pan-mode','drawing-hover');
      return;
    }
    const hit=(Number.isInteger(state.hoverDrawing)&&state.hoverDrawing>=0)?state.hoverDrawing:-1;
    if(state.interactionMode==='move'&&hit>=0&&!state.panArmed&&!state.yPanArmed&&state.hoverDrawing===hit){
      state.dragDrawing={idx:hit,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,moved:false};
      showDrawingTooltip(hit,e.clientX,e.clientY);
      vp.setPointerCapture(e.pointerId);
      return;
    }
    if(state.yPanArmed||state.panArmed||state.interactionMode==='pan'){
      state.drag={
        x:e.clientX,
        y:e.clientY,
        startX:state.panX,
        startY:state.panY||0,
        startScale:state.yScale||1,
        axis:state.yPanArmed?'y':(state.interactionMode==='pan'?'both':'x')
      };
      state.yPanArmed=false;
      state.panArmed=false;
      vp.style.cursor='grabbing';
      vp.setPointerCapture(e.pointerId);
      return;
    }
  });

  vp.addEventListener('pointerup',e=>{
    state.drag=null;
    state.dragDrawing=null;
    state.panArmed=false;
    state.yPanArmed=false;
    vp.classList.remove('drawing-hover');
    if(state.interactionMode==='pan'){
      vp.classList.add('pan-mode');
      vp.style.cursor='grab';
    } else {
      vp.classList.remove('pan-mode');
      vp.style.cursor='crosshair';
    }
    showDrawingTooltip(-1,0,0);
    draw();
    try{vp.releasePointerCapture(e.pointerId)}catch(_){}
  });

  vp.addEventListener('pointerleave',()=>{
    if(!state.drag&&!state.dragDrawing){
      state.cross=null;
      vp.classList.remove('drawing-hover');
      draw();
      showDrawingTooltip(-1,0,0);
    }
  });

  vp.addEventListener('dblclick',e=>{
    const r=vp.getBoundingClientRect(),x=e.clientX-r.left;
    if(x>vp.clientWidth-72){
      state.yPanArmed=true; state.panArmed=false;
      toast('Y-axis pan armed — drag vertically');
    } else if(!state.pendingDrawing){
      setChartInteractionMode('pan');
      toast('Pan mode enabled: Drag chart horizontally and vertically');
    }
  });

  vp.addEventListener('wheel',e=>{
    if(!e.ctrlKey) return;
    e.preventDefault();
    const view=getView(),r=vp.getBoundingClientRect(),x=e.clientX-r.left,i=indexFromX(x,view),ratio=i/Math.max(1,view.count-1),old=state.zoom;
    state.zoom=Math.max(.45,Math.min(6,old*(e.deltaY<0?1.12:.89)));
    const nc=Math.max(20,Math.min(state.candles.length,Math.floor(state.visible/state.zoom)));
    state.panX=Math.max(0,Math.min(state.candles.length-nc,Math.round(view.start+ratio*(view.count-nc))));
    draw();
  },{passive:false});

  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){
      state.pendingDrawing=null; state.drawingStage=[]; state.dragDrawing=null; state.drag=null;
      state.panArmed=false; state.yPanArmed=false;
      setChartInteractionMode('crosshair');
      hideAxisLabels(); draw();
    }
  });

  document.getElementById('chartFullscreen').onclick=async()=>{
    try{ const shell=document.getElementById('chartShell'); if(!document.fullscreenElement) await shell.requestFullscreen(); else await document.exitFullscreen(); }
    catch(e){ toast('Full screen is unavailable in this browser'); }
  };

  document.addEventListener('fullscreenchange',()=>{ state.fullscreen=!!document.fullscreenElement; setTimeout(draw,50); });

  document.getElementById('chartModeToggle')?.addEventListener('click',()=>{
    const next = state.interactionMode === 'pan' ? 'crosshair' : 'pan';
    setChartInteractionMode(next);
    toast(next === 'pan' ? 'Pan mode enabled: Drag chart freely across time & price' : 'Crosshair inspection mode enabled');
  });"""

if old_pointer_block in content:
    content = content.replace(old_pointer_block, new_pointer_block, 1)
    print("✓ Replaced pointer and chartModeToggle controller")
else:
    print("⚠ Could not find old_pointer_block")

# 3. Remove duplicate chartModeToggle listener around line 3442
old_dupe_toggle = "document.getElementById('chartModeToggle')?.addEventListener('click',()=>{state.interactionMode=state.interactionMode==='pan'?'crosshair':'pan';const b=document.getElementById('chartModeToggle');b.textContent=state.interactionMode==='pan'?'Pan':'Crosshair';b.classList.toggle('active',state.interactionMode==='pan');vp.classList.toggle('pan-mode',state.interactionMode==='pan');toast(state.interactionMode==='pan'?'Pan mode enabled':'Crosshair mode enabled')});"
if old_dupe_toggle in content:
    content = content.replace(old_dupe_toggle, "// Duplicate chartModeToggle removed", 1)
    print("✓ Removed duplicate chartModeToggle listener")
else:
    print("⚠ Could not find old_dupe_toggle")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Batch 1 completed successfully.")

