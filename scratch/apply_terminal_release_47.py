import sys, re

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("Original terminal.html length:", len(content))

# 1. Turn off press and hold to copy paste on mobile (Item 14)
mobile_app_css = """
/* Native App Styling - Disable press-and-hold copy-paste callouts (Release 47 - Item 14) */
html, body, .navtabs, .card, .chart-shell, .tool-modal, .btn, .tag, table, .sidebar, .watchlist-item {
  -webkit-touch-callout: none !important;
  -webkit-user-select: none !important;
  user-select: none !important;
}
input, textarea, [contenteditable="true"], .notepad-content, .notepad-title, .note-editor-area {
  -webkit-touch-callout: default !important;
  -webkit-user-select: text !important;
  user-select: text !important;
}
"""

if "Release 47 - Item 14" not in content:
    content = content.replace("</style>", mobile_app_css + "\n</style>", 1)
    print("Added native app styling (no press & hold copy callouts)")

# 2. Add Notes Navtab in #navtabs (Item 23)
notes_navtab = """  <div class="navtab" data-tab="notes" role="button" tabindex="0" onclick="showTab('notes')">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
    Trader Notes
  </div>"""

if 'data-tab="notes"' not in content:
    reco_navtab_marker = '<div class="navtab" data-tab="reco"'
    content = content.replace(reco_navtab_marker, notes_navtab + "\n  " + reco_navtab_marker, 1)
    print("Added Trader Notes navtab to #navtabs")

# 3. Add Trader Notes Panel (#panel-notes) after #panel-reco (Item 23)
notes_panel_html = """
    <!-- TRADER NOTES WORKSPACE PANEL (Release 47 - Item 23) -->
    <div class="panel" id="panel-notes">
      <div class="page-head" style="margin-bottom:12px;">
        <div>
          <div class="page-title" style="display:flex;align-items:center;gap:8px;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            Interactive Trader Journal &amp; Folder Notes
          </div>
          <div class="page-sub">Folder-wise trade journaling, strategy playbooks, mistake analysis, and screenshot attachments.</div>
        </div>
        <div class="head-actions">
          <button class="btn small gold" id="btnNewNote" onclick="createNewNote()">+ New Note</button>
          <button class="btn small ghost" id="btnNewFolder" onclick="promptNewFolder()">+ New Folder</button>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:300px 1fr;gap:14px;align-items:start;" id="notesWorkspaceLayout">
        <!-- Sidebar: Folders & Note List -->
        <div class="card" style="padding:12px;background:var(--surface);border:1px solid var(--border-soft);border-radius:10px;">
          <div style="font-size:11px;font-weight:700;color:var(--text-faint);text-transform:uppercase;margin-bottom:8px;">Folders</div>
          <div id="notesFolderTabs" style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:12px;">
            <button class="btn small active" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('ALL')">All</button>
            <button class="btn small ghost" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('Trade Journal')">Journal</button>
            <button class="btn small ghost" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('Mistakes & Learnings')">Mistakes</button>
            <button class="btn small ghost" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('Playbooks & Setups')">Playbooks</button>
            <button class="btn small ghost" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('Daily Market Prep')">Prep</button>
          </div>

          <div style="position:relative;margin-bottom:10px;">
            <input type="text" id="notesSearchInput" class="tool-input" placeholder="Search notes..." style="width:100%;font-size:12px;padding:6px 8px;" oninput="renderNotesList()">
          </div>

          <div style="font-size:11px;font-weight:700;color:var(--text-faint);text-transform:uppercase;margin-bottom:6px;">Notes List (<span id="notesCountBadge">0</span>)</div>
          <div id="notesListContainer" style="max-height:550px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;">
            <div class="muted" style="font-size:12px;padding:12px;text-align:center;">Loading trader notes...</div>
          </div>
        </div>

        <!-- Note Editor Area -->
        <div class="card" style="padding:16px;background:var(--surface);border:1px solid var(--border-soft);border-radius:10px;min-height:600px;display:flex;flex-direction:column;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
            <div style="flex:1;min-width:200px;">
              <input type="text" id="noteEditorTitle" class="notepad-title" placeholder="Note Title (e.g. Nifty 15m Breakout Trap)..." style="width:100%;background:transparent;border:none;border-bottom:1px solid var(--border-soft);font-size:18px;font-weight:700;color:var(--text);padding:4px 0;outline:none;">
            </div>
            <div style="display:flex;align-items:center;gap:6px;">
              <select id="noteEditorFolder" class="tool-input" style="font-size:11.5px;padding:4px 8px;">
                <option value="Trade Journal">Trade Journal</option>
                <option value="Mistakes & Learnings">Mistakes &amp; Learnings</option>
                <option value="Playbooks & Setups">Playbooks &amp; Setups</option>
                <option value="Daily Market Prep">Daily Market Prep</option>
              </select>
              <button class="btn small gold" id="btnSaveNote" onclick="saveActiveNote()">💾 Save Note</button>
              <button class="btn small ghost" id="btnDeleteNote" onclick="deleteActiveNote()" style="color:var(--sell);">🗑️ Delete</button>
            </div>
          </div>

          <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
            <input type="text" id="noteEditorTags" class="tool-input" placeholder="Tags: #Nifty #Loss #Theta #FailedBreakout" style="flex:1;min-width:180px;font-size:11.5px;padding:4px 8px;">
            <label class="btn small ghost" style="cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;">
              📷 Upload Photo
              <input type="file" id="noteImageUploadInput" accept="image/*" style="display:none;" onchange="handleNotePhotoUpload(event)">
            </label>
            <button class="btn small ghost" style="font-size:11px;" onclick="attachLiveMarketSnapshot()">🏷️ Attach Market Snapshot</button>
          </div>

          <!-- Note Content Area -->
          <div style="flex:1;display:flex;flex-direction:column;gap:10px;">
            <textarea id="noteEditorContent" class="note-editor-area" placeholder="Write detailed trade observations, rationale, mistakes made, execution notes, or paste screenshots (Ctrl+V supported)..." style="width:100%;flex:1;min-height:300px;background:var(--surface-2);border:1px solid var(--border-soft);border-radius:8px;padding:12px;font-family:var(--font-body);font-size:13px;color:var(--text);line-height:1.6;resize:vertical;outline:none;"></textarea>

            <!-- Image Attachments Gallery -->
            <div id="noteImagesGallery" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:6px;">
              <!-- Uploaded/Pasted screenshot thumbnails render here -->
            </div>
          </div>
        </div>
      </div>
    </div>
"""

if 'id="panel-notes"' not in content:
    charts_panel_marker = '<div class="panel" id="panel-charts"'
    content = content.replace(charts_panel_marker, notes_panel_html + "\n    " + charts_panel_marker, 1)
    print("Added Trader Notes panel to HTML")

# 4. Remove AT button from watchlist row (Item 21)
wl_at_button_regex = r'<button type="button" class="wl-bs at [^"]*" data-wl-at="[^"]*" title="[^"]*">AT</button>'
if re.search(wl_at_button_regex, content):
    content = re.sub(wl_at_button_regex, '', content)
    print("Removed AT button from watchlist template")

# 5. Add Zoom In (+), Zoom Out (-), and Fullscreen buttons to chart toolbar (Items 5, 7, 13)
chart_buttons_snippet = """          <!-- Zoom In (+) and Zoom Out (-) Buttons (Release 47 - Item 5) -->
          <button type="button" class="tf-btn" id="btnChartZoomIn" title="Zoom In (+)" style="font-size:14px;font-weight:700;padding:4px 9px;">+</button>
          <button type="button" class="tf-btn" id="btnChartZoomOut" title="Zoom Out (−)" style="font-size:14px;font-weight:700;padding:4px 9px;">−</button>

          <!-- Fullscreen Button (Release 47 - Item 7 & 13) -->
          <button type="button" class="tf-btn" id="chartFullscreenToolbarBtn" title="Full Screen (Auto Landscape)" style="display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M21 16v5h-5"/></svg>
          </button>"""

if 'id="btnChartZoomIn"' not in content:
    ind_btn_marker = '<button type="button" class="tf-btn" id="btnOpenIndicatorsModal"'
    content = content.replace(ind_btn_marker, chart_buttons_snippet + "\n\n          " + ind_btn_marker, 1)
    print("Added Zoom In, Zoom Out, and Fullscreen buttons to chart toolbar")

# Hide old floating chart-fullscreen button
old_fs_btn = '<button class="chart-fullscreen" id="chartFullscreen" title="Full screen" aria-label="Full screen">'
if old_fs_btn in content:
    content = content.replace(old_fs_btn, '<button class="chart-fullscreen" id="chartFullscreen" title="Full screen" aria-label="Full screen" style="display:none !important;">', 1)
    print("Hidden old floating chart-fullscreen canvas button")

# 6. Add Active Trade Sentinel Modal to Modals section (Item 3)
trade_sentinel_modal_html = """
<!-- Active Trade Sentinel Alert Modal (Release 47 - Item 3) -->
<div class="tool-modal" id="tradeSentinelModal" aria-hidden="true" style="display:none;">
  <div class="tool-modal-card" style="max-width:540px;border-radius:14px;border:1.5px solid #FF5C72;box-shadow:0 25px 60px rgba(0,0,0,0.65);background:var(--surface);">
    <div class="card-head" style="border-bottom:1px solid var(--border-soft);padding-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="tag sell" style="font-weight:800;font-size:11px;letter-spacing:0.5px;padding:3px 8px;">⚠️ MATERIAL REGIME SHIFT</span>
        <div class="card-title" id="sentinelModalTitle" style="font-size:15px;font-weight:700;">Adverse Trade Factors Detected</div>
      </div>
      <button class="btn ghost small" onclick="closeModal('tradeSentinelModal')">✕</button>
    </div>
    <div id="sentinelModalBody" style="margin-top:14px;">
      <div class="data-empty">Evaluating active trade factors...</div>
    </div>
  </div>
</div>
"""

if 'id="tradeSentinelModal"' not in content:
    pos_modal_marker = '<div class="tool-modal" id="posAnalysisModal"'
    content = content.replace(pos_modal_marker, trade_sentinel_modal_html + "\n" + pos_modal_marker, 1)
    print("Added Trade Sentinel Alert Modal")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("HTML structure updates applied successfully.")

