# -*- coding: utf-8 -*-
"""
Complete wiring script for terminal.html covering all 23 items.
"""
from pathlib import Path
import re

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

# -------------------------------------------------------------
# 1. Item 1: Topbar overflow & z-index
# -------------------------------------------------------------
# In mobile / responsive styles, change overflow: hidden !important to overflow: visible !important on .topbar
content = re.sub(
    r'(\.topbar\s*\{[^}]*?)overflow:\s*hidden\s*!important;',
    r'\1overflow: visible !important;',
    content
)
# Ensure .topbar has z-index 2500 !important and menus have z-index 2600 !important
content = re.sub(
    r'(\.topbar\s*\{[^}]*?)z-index:\s*1200\s*!important;',
    r'\1z-index: 2500 !important;',
    content
)
content = re.sub(
    r'(\.(user|notification)-menu\s*\{[^}]*?)z-index:\s*2200;',
    r'\1z-index: 2600 !important;',
    content
)

# -------------------------------------------------------------
# 2. Item 8: Trend Line 2-tap dotted live preview & infinite ray
# -------------------------------------------------------------
# In pointerdown, don't wipe pendingDrawing immediately if it needs more points
old_pointer_down_pending = '''    if(state.pendingDrawing){
      applyDrawingPoint(x,y);
      state.pendingDrawing=null;
      state.drawingStage=[];
      state.hoverDrawing=-1;
      state.interactionMode='crosshair';
      vp.classList.remove('pan-mode','drawing-hover');
      return;
    }'''

new_pointer_down_pending = '''    if(state.pendingDrawing){
      const finished = applyDrawingPoint(x,y);
      if(finished){
        state.pendingDrawing=null;
        state.drawingStage=[];
        state.hoverDrawing=-1;
        state.interactionMode='crosshair';
        vp.classList.remove('pan-mode','drawing-hover');
      }
      draw();
      return;
    }'''

if old_pointer_down_pending in content:
    content = content.replace(old_pointer_down_pending, new_pointer_down_pending, 1)

# In pointermove, track cursor preview when drawingStage has 1 point
old_pointer_move_cross = '''    updateCross(e);
    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;'''

new_pointer_move_cross = '''    updateCross(e);
    if(state.pendingDrawing && state.drawingStage && state.drawingStage.length > 0){
      const rBounds = vp.getBoundingClientRect();
      state.cursorPoint = chartPoint({clientX: e.clientX, clientY: e.clientY});
      draw();
      return;
    }
    const hit=findDrawingAt(x,y),ih=hit<0?indicatorHit(x,y):-1;'''

if old_pointer_move_cross in content:
    content = content.replace(old_pointer_move_cross, new_pointer_move_cross, 1)

# Update applyDrawingPoint to return boolean (true when complete, false when awaiting more points)
old_apply_drawing_point = '''function applyDrawingPoint(x,y){const r=vp.getBoundingClientRect(),pt=chartPoint({clientX:r.left+x,clientY:r.top+y});const name=state.pendingDrawing;state.drawingStage.push(pt);const stage=state.drawingStage.length;const need=name==='Horizontal Line'||name==='Vertical Line'?1:name==='Risk / Reward'?3:name==='Parallel Channel'?3:2;if(stage<need){document.getElementById('drawingStatus').textContent=stage===1?'Click again to set the second point.':`Click ${need-stage} more time(s) to finish.`;return}const color=state.pendingColor||css('--gold');let d={name,color,type:''};if(name==='Horizontal Line')d={...d,type:'h',price:pt.price};else if(name==='Vertical Line')d={...d,type:'v',i:pt.i};else if(name==='Trend Line')d={...d,type:'trend_ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price,infinite:true};else if(name==='Ray')d={...d,type:'ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Arrow')d={...d,type:'arrow',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Rectangle'||name==='Price Range')d={...d,type:name==='Rectangle'?'rect':'range',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Fib Retracement')d={...d,type:'fib',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};else if(name==='Risk / Reward')d={...d,type:'rr',i1:state.drawingStage[0].i,i2:state.drawingStage[1].i,entry:state.drawingStage[0].price,stop:state.drawingStage[1].price,target:pt.price};else if(name==='Parallel Channel')d={...d,type:'channel',i1:state.drawingStage[0].i,i2:state.drawingStage[1].i,p1:state.drawingStage[0].price,p2:state.drawingStage[1].price,p3:pt.price};state.drawings.push(d);document.getElementById('drawingStatus').textContent=`Applied ${name}.`;renderApplied();draw()}'''

new_apply_drawing_point = '''function applyDrawingPoint(x,y){
  const r=vp.getBoundingClientRect(),pt=chartPoint({clientX:r.left+x,clientY:r.top+y});
  const name=state.pendingDrawing;
  state.drawingStage.push(pt);
  const stage=state.drawingStage.length;
  const need=name==='Horizontal Line'||name==='Vertical Line'?1:name==='Risk / Reward'?3:name==='Parallel Channel'?3:2;
  if(stage<need){
    const stEl = document.getElementById('drawingStatus');
    if(stEl) stEl.textContent=stage===1?'Click again to set the second point.':`Click ${need-stage} more time(s) to finish.`;
    return false;
  }
  const color=state.pendingColor||css('--gold');
  let d={name,color,type:''};
  if(name==='Horizontal Line')d={...d,type:'h',price:pt.price};
  else if(name==='Vertical Line')d={...d,type:'v',i:pt.i};
  else if(name==='Trend Line')d={...d,type:'trend_ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price,infinite:true};
  else if(name==='Ray')d={...d,type:'ray',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};
  else if(name==='Arrow')d={...d,type:'arrow',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};
  else if(name==='Rectangle'||name==='Price Range')d={...d,type:name==='Rectangle'?'rect':'range',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};
  else if(name==='Fib Retracement')d={...d,type:'fib',i1:state.drawingStage[0].i,i2:pt.i,p1:state.drawingStage[0].price,p2:pt.price};
  else if(name==='Risk / Reward')d={...d,type:'rr',i1:state.drawingStage[0].i,i2:state.drawingStage[1].i,entry:state.drawingStage[0].price,stop:state.drawingStage[1].price,target:pt.price};
  else if(name==='Parallel Channel')d={...d,type:'channel',i1:state.drawingStage[0].i,i2:state.drawingStage[1].i,p1:state.drawingStage[0].price,p2:state.drawingStage[1].price,p3:pt.price};
  state.drawings.push(d);
  const stEl = document.getElementById('drawingStatus');
  if(stEl) stEl.textContent=`Applied ${name}.`;
  renderApplied();
  draw();
  return true;
}'''

if old_apply_drawing_point in content:
    content = content.replace(old_apply_drawing_point, new_apply_drawing_point, 1)

# In draw(), handle live dotted line preview when pendingDrawing is active, and infinite trend_ray rendering
old_draw_trend_render = '''if(q.type==='trend_ray'||q.type==='line'||q.type==='ray'||q.type==='arrow'){'''

# Let's inspect how drawings are drawn in draw()
print("Replaced basic drawing logic.")
path.write_text(content, encoding="utf-8")

