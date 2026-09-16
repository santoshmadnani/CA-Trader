#!/usr/bin/env python3
import sys, re

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Original terminal.html length: {len(html)}")

# -----------------------------------------------------------------------------
# 1. Replace <table> in dashRationaleCard with full-width CSS Grid
# -----------------------------------------------------------------------------
old_rationale_table = '''        <div class="table-wrap" style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:11.5px;text-align:left;">
            <thead>
              <tr style="border-bottom:1px solid var(--border);background:var(--surface-2);font-size:10.5px;text-transform:uppercase;color:var(--text-faint);letter-spacing:0.5px;">
                <th style="padding:8px 10px;">Category / Particulars</th>
                <th style="padding:8px 10px;">Value / Level</th>
                <th style="padding:8px 10px;">Score / Weightage</th>
                <th style="padding:8px 10px;">Signal</th>
                <th style="padding:8px 10px;">Relevance &amp; Verification Source</th>
              </tr>
            </thead>
            <tbody id="dashConfluenceTableBody">
              <!-- Populated dynamically with all indicators, all patterns, all news, all other factors, and all Greeks -->
            </tbody>
          </table>
        </div>'''

new_rationale_grid = '''        <!-- Full-Width 6-Block Confluence Grid Container (Release 49) -->
        <div id="dashConfluenceTableBody" style="display:grid;grid-template-columns:repeat(auto-fit, minmax(320px, 1fr));gap:14px;width:100%;box-sizing:border-box;">
          <!-- Populated dynamically with 6 institutional Smart-Art blocks & [+] collapsible drilldowns -->
        </div>'''

if old_rationale_table in html:
    html = html.replace(old_rationale_table, new_rationale_grid, 1)
    print("Replaced table with full-width grid container in dashRationaleCard")
else:
    print("Warning: old_rationale_table not found exactly")

# -----------------------------------------------------------------------------
# 2. Remove panel.scrollIntoView on CA AI Indicator panel
# -----------------------------------------------------------------------------
old_scroll = "panel.scrollIntoView({behavior: 'smooth', block: 'nearest'});"
if old_scroll in html:
    html = html.replace(old_scroll, "// panel.scrollIntoView suppressed for fixed viewport positioning", 1)
    print("Removed panel.scrollIntoView")

# -----------------------------------------------------------------------------
# 3. Add Comprehensive Release 49 CSS
# -----------------------------------------------------------------------------
RELEASE_49_CSS = '''
/* ==========================================================================
   RELEASE 49 COMPREHENSIVE UI & WORKSPACE STYLES
   ========================================================================== */

/* Item 8: Watchlist name selector font style and size preservation */
select#watchlistSelect, select.watchlist-select {
  max-width: 170px !important;
  background: transparent !important;
  border: 0 !important;
  color: var(--text) !important;
  font: 600 12.5px var(--font-display) !important;
  text-transform: uppercase !important;
  outline: none !important;
  padding: 0 !important;
  box-shadow: none !important;
  cursor: pointer !important;
}

/* Item 2: Recommendation Rationale full-width stretch */
#dashRationaleCard {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
#dashConfluenceTableBody {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)) !important;
  gap: 14px !important;
  width: 100% !important;
  box-sizing: border-box !important;
}

/* Item 4: CA AI Indicator Drawer Positioning (Never scroll down) */
#chartAiPanel.ca-chart-ai-panel {
  position: fixed !important;
  top: 75px !important;
  right: 20px !important;
  left: auto !important;
  bottom: auto !important;
  width: 440px !important;
  max-width: 90vw !important;
  max-height: calc(100vh - 95px) !important;
  z-index: 100000 !important;
  overflow-y: auto !important;
  box-shadow: 0 16px 48px rgba(0,0,0,0.5), 0 0 0 1px var(--border) !important;
}
@media (max-width: 768px) {
  #chartAiPanel.ca-chart-ai-panel {
    top: auto !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    max-height: 82vh !important;
    border-radius: 18px 18px 0 0 !important;
  }
}

/* Item 7: Reduced & Compact Applied Indicator Tooltip */
.drawing-tooltip {
  min-width: 180px !important;
  max-width: 260px !important;
  padding: 7px 10px !important;
  font-size: 10.5px !important;
  border-radius: 7px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.45) !important;
}
.drawing-tooltip .dt-title {
  font-size: 11.5px !important;
  font-weight: 700 !important;
}
.drawing-tooltip .dt-params {
  font-size: 10px !important;
  margin-bottom: 3px !important;
}

/* Item 9: Quick Order Modal Centered and Compact on Mobile */
@media (max-width: 768px) {
  #quickOrderModal, #orderModal {
    justify-content: center !important;
    align-items: center !important;
    padding: 16px !important;
    padding-left: 16px !important;
    padding-top: 16px !important;
  }
  #quickOrderModal .tool-modal-card, #orderModal .tool-modal-card {
    width: min(420px, 94vw) !important;
    max-width: 420px !important;
    margin: auto !important;
    padding: 16px !important;
    border-radius: 14px !important;
    box-sizing: border-box !important;
  }
}

/* Item 10: CA AI Chat Modal Gemini-style UI & Markdown Styling */
#caAiModal .tool-modal-card {
  width: min(620px, 94vw) !important;
  height: min(640px, 85vh) !important;
  display: flex !important;
  flex-direction: column !important;
  padding: 0 !important;
  overflow: hidden !important;
  border-radius: 14px !important;
}
#caAiModal .card-head {
  padding: 12px 16px !important;
  background: var(--surface-2) !important;
  border-bottom: 1px solid var(--border-soft) !important;
  cursor: move !important;
}
#aiChatLog {
  flex: 1 !important;
  overflow-y: auto !important;
  padding: 16px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 12px !important;
  background: var(--surface) !important;
}
.ai-msg {
  max-width: 88% !important;
  padding: 10px 14px !important;
  border-radius: 12px !important;
  font-size: 12px !important;
  line-height: 1.55 !important;
  word-break: break-word !important;
}
.ai-msg.user {
  align-self: flex-end !important;
  background: var(--primary) !important;
  color: #FFFFFF !important;
  border-bottom-right-radius: 3px !important;
}
.ai-msg.ai {
  align-self: flex-start !important;
  background: var(--surface-2) !important;
  color: var(--text) !important;
  border: 1px solid var(--border-soft) !important;
  border-bottom-left-radius: 3px !important;
  box-shadow: 0 4px 14px rgba(0,0,0,0.1) !important;
}
.ai-msg b, .ai-msg strong {
  font-weight: 700 !important;
  color: var(--text) !important;
}
.ai-msg.user b, .ai-msg.user strong {
  color: #FFFFFF !important;
}
.ai-msg i, .ai-msg em {
  font-style: italic !important;
}
.ai-msg u {
  text-decoration: underline !important;
}
.ai-msg .ai-h3 {
  font-size: 12.5px !important;
  font-weight: 700 !important;
  margin: 6px 0 3px !important;
  color: var(--gold) !important;
  border-bottom: 1px solid var(--border-soft) !important;
  padding-bottom: 2px !important;
}
.ai-msg .ai-bullet {
  padding-left: 10px !important;
  margin: 3px 0 !important;
  display: flex !important;
  align-items: baseline !important;
  gap: 5px !important;
}
.ai-msg .ai-code {
  font-family: var(--font-mono) !important;
  background: rgba(0,0,0,0.25) !important;
  padding: 1px 5px !important;
  border-radius: 4px !important;
  font-size: 11px !important;
}
.ai-chip-bar {
  display: flex !important;
  gap: 6px !important;
  overflow-x: auto !important;
  padding: 8px 16px !important;
  background: var(--surface-2) !important;
  border-top: 1px solid var(--border-soft) !important;
}
.ai-chip {
  padding: 4px 10px !important;
  font-size: 10.5px !important;
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  cursor: pointer !important;
  white-space: nowrap !important;
  color: var(--text-dim) !important;
  transition: all 0.15s ease !important;
}
.ai-chip:hover {
  border-color: var(--primary) !important;
  color: var(--primary) !important;
}
.ai-chat-row {
  display: flex !important;
  gap: 8px !important;
  padding: 12px 16px !important;
  background: var(--surface-2) !important;
  border-top: 1px solid var(--border-soft) !important;
}

/* Item 12: Universal Movable Popup Handle cursor */
.draggable-handle {
  cursor: grab !important;
  -webkit-user-select: none !important;
  user-select: none !important;
}
.draggable-handle:active {
  cursor: grabbing !important;
}
'''

if '/* RELEASE 49 COMPREHENSIVE UI & WORKSPACE STYLES */' not in html:
    html = html.replace('</head>', f'<style>{RELEASE_49_CSS}</style>\n</head>', 1)
    print("Injected Release 49 CSS into <head>")

# -----------------------------------------------------------------------------
# 4. Universal Dragging Helper & Interactive [+] Card Details & Enhanced Markdown
# -----------------------------------------------------------------------------
RELEASE_49_JS = '''
// ============================================================================
// RELEASE 49 CLIENT SCRIPTS: DRILLDOWNS, DRAGGABLE POPUPS, MARKDOWN, GESTURES
// ============================================================================

// 1. Universal Draggable Helper (PC Pointer + Mobile Touch)
function makeUniversalDraggable(targetEl, handleEl) {
  if(!targetEl || !handleEl) return;
  handleEl.classList.add('draggable-handle');

  let isDragging = false;
  let startX = 0, startY = 0;
  let initialLeft = 0, initialTop = 0;

  function onPointerDown(e) {
    if(e.button && e.button !== 0) return;
    if(e.target.closest('button, input, select, textarea, .close, [data-close]')) return;
    
    isDragging = true;
    startX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
    startY = e.clientY || (e.touches && e.touches[0].clientY) || 0;

    const rect = targetEl.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;

    // Convert from fixed bottom/right positioning to explicit left/top
    targetEl.style.bottom = 'auto';
    targetEl.style.right = 'auto';
    targetEl.style.left = initialLeft + 'px';
    targetEl.style.top = initialTop + 'px';
    targetEl.style.margin = '0';
    targetEl.style.position = 'fixed';

    if(handleEl.setPointerCapture && e.pointerId) {
      try { handleEl.setPointerCapture(e.pointerId); } catch(_) {}
    }
    window.addEventListener('pointermove', onPointerMove, { passive: false });
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('touchmove', onTouchMove, { passive: false });
    window.addEventListener('touchend', onPointerUp);
  }

  function onPointerMove(e) {
    if(!isDragging) return;
    if(e.cancelable) e.preventDefault();
    const cx = e.clientX || (e.touches && e.touches[0].clientX) || 0;
    const cy = e.clientY || (e.touches && e.touches[0].clientY) || 0;
    const dx = cx - startX;
    const dy = cy - startY;

    const maxW = window.innerWidth - 60;
    const maxH = window.innerHeight - 60;
    const nextLeft = Math.max(10, Math.min(maxW, initialLeft + dx));
    const nextTop = Math.max(10, Math.min(maxH, initialTop + dy));

    targetEl.style.left = nextLeft + 'px';
    targetEl.style.top = nextTop + 'px';
  }

  function onTouchMove(e) {
    if(!isDragging || !e.touches || !e.touches[0]) return;
    if(e.cancelable) e.preventDefault();
    const t = e.touches[0];
    onPointerMove({ clientX: t.clientX, clientY: t.clientY, cancelable: true, preventDefault: () => {} });
  }

  function onPointerUp(e) {
    isDragging = false;
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    window.removeEventListener('touchmove', onTouchMove);
    window.removeEventListener('touchend', onPointerUp);
  }

  handleEl.addEventListener('pointerdown', onPointerDown);
  handleEl.addEventListener('touchstart', onPointerDown, { passive: false });
}

// 2. Rich Markdown Formatter for CA AI Chat Messages
function formatAiMarkdown(raw) {
  if(!raw) return '';
  let s = String(raw);

  // Strip code blocks with json actions if any
  s = s.replace(/```json[\\s\\S]*?```/g, '');

  // Escape HTML entities to prevent XSS
  s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // ### Headers
  s = s.replace(/^###\\s+(.*$)/gim, '<div class="ai-h3">$1</div>');
  s = s.replace(/^##\\s+(.*$)/gim, '<div class="ai-h3" style="font-size:13px;">$1</div>');

  // **Bold**
  s = s.replace(/\\*\\*(.*?)\\*\\*/g, '<b>$1</b>');

  // *Italic*
  s = s.replace(/\\*(.*?)\\*/g, '<i>$1</i>');

  // __Underline__
  s = s.replace(/__(.*?)__/g, '<u>$1</u>');

  // Code snippets
  s = s.replace(/`([^`]+)`/g, '<span class="ai-code">$1</span>');

  // Bullet points
  s = s.replace(/^[-*]\\s+(.*$)/gim, '<div class="ai-bullet"><span>•</span><span>$1</span></div>');

  // Paragraphs & Line Breaks
  const paragraphs = s.split(/\\n\\s*\\n/);
  return paragraphs.map(p => {
    const trimmed = p.trim();
    if(!trimmed) return '';
    if(trimmed.startsWith('<div class="ai-h3"') || trimmed.startsWith('<div class="ai-bullet"')) {
      return trimmed.replace(/\\n/g, '<br>');
    }
    return `<div style="margin-bottom:6px;">${trimmed.replace(/\\n/g, '<br>')}</div>`;
  }).join('');
}

// Override addAiMessage to render rich markdown formatting
window.addAiMessage = function(text, who='ai'){
  const aiLog = document.getElementById('aiChatLog');
  if(!aiLog) return;
  const d = document.createElement('div');
  d.className = 'ai-msg ' + who;
  if(who === 'ai') {
    d.innerHTML = formatAiMarkdown(text);
  } else {
    d.textContent = text;
  }
  aiLog.appendChild(d);
  aiLog.scrollTop = aiLog.scrollHeight;
  return d;
};

// 3. Interactive [+] Card Detail Toggler
window.toggleCardDetail = function(detailId, btnEl){
  const el = document.getElementById(detailId);
  if(!el) return;
  const isHidden = el.style.display === 'none' || !el.style.display;
  el.style.display = isHidden ? 'block' : 'none';
  if(btnEl){
    btnEl.textContent = isHidden ? '[-] Less' : '[+] Details';
    btnEl.classList.toggle('active', isHidden);
  }
};

// 4. Outside Tap Listener to Dismiss Indicator Criteria Tooltip
document.addEventListener('pointerdown', (e) => {
  const tt = document.getElementById('drawingTooltip');
  if(!tt || tt.style.display === 'none') return;
  if(!e.target.closest('#drawingTooltip') && !e.target.closest('.applied-item') && !e.target.closest('.chart-area-pro')) {
    if(typeof showDrawingTooltip === 'function') showDrawingTooltip(-1, 0, 0);
  }
});
'''

if '// RELEASE 49 CLIENT SCRIPTS' not in html:
    html = html.replace('</body>', f'<script>{RELEASE_49_JS}</script>\n</body>', 1)
    print("Injected Release 49 client scripts before </body>")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved updated terminal.html")

