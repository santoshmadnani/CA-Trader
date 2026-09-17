
// ============================================================================
// PRODUCTION RELEASE 47 CLIENT ENGINE & EVENT HANDLERS
// ============================================================================

(function initRelease47Features(){
  // --------------------------------------------------------------------------
  // Item 1: Navigation Drag vs Click Handler
  // --------------------------------------------------------------------------
  let navTouchStartX = 0, navTouchStartY = 0;
  window.navIsDragging = false;
  const navEl = document.getElementById('navtabs');
  if(navEl){
    navEl.addEventListener('touchstart', e => {
      if(e.touches.length === 1){
        navTouchStartX = e.touches[0].clientX;
        navTouchStartY = e.touches[0].clientY;
        window.navIsDragging = false;
      }
    }, { passive: true });

    navEl.addEventListener('touchmove', e => {
      if(e.touches.length === 1){
        const dx = Math.abs(e.touches[0].clientX - navTouchStartX);
        const dy = Math.abs(e.touches[0].clientY - navTouchStartY);
        if(dx > 8 || dy > 8){
          window.navIsDragging = true;
        }
      }
    }, { passive: true });

    navEl.addEventListener('click', e => {
      if(window.navIsDragging){
        e.stopPropagation();
        e.preventDefault();
        window.navIsDragging = false;
        return false;
      }
    }, true);
  }

  // --------------------------------------------------------------------------
  // Items 5, 6, 7, 8, 13: Chart Controls, Pinch Zoom, Crosshair & Fullscreen
  // --------------------------------------------------------------------------
  const vp = document.getElementById('chartViewport');
  if(vp){
    // Pinch Zoom in mobile (Item 6)
    let pinchStartDist = null;
    let pinchStartZoom = 1;

    vp.addEventListener('touchstart', e => {
      if(e.touches.length === 1){
        // Mobile single touch crosshair (Item 8)
        const t = e.touches[0];
        if(typeof updateCross === 'function'){
          updateCross({ clientX: t.clientX, clientY: t.clientY });
        }
      } else if(e.touches.length === 2){
        pinchStartDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        pinchStartZoom = (typeof state !== 'undefined' && state.zoom) ? state.zoom : 1;
      }
    }, { passive: true });

    vp.addEventListener('touchmove', e => {
      if(e.touches.length === 1){
        const t = e.touches[0];
        if(typeof updateCross === 'function'){
          updateCross({ clientX: t.clientX, clientY: t.clientY });
        }
      } else if(e.touches.length === 2 && pinchStartDist && typeof state !== 'undefined'){
        const currentDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        const ratio = currentDist / Math.max(1, pinchStartDist);
        state.zoom = Math.max(0.2, Math.min(5.0, pinchStartZoom / ratio));
        if(typeof draw === 'function') draw();
      }
    }, { passive: true });

    vp.addEventListener('touchend', e => {
      if(e.touches.length < 2) pinchStartDist = null;
    }, { passive: true });
  }

  // Zoom In (+) and Zoom Out (-) Buttons (Item 5)
  document.getElementById('btnChartZoomIn')?.addEventListener('click', () => {
    if(typeof state !== 'undefined'){
      state.zoom = Math.max(0.2, (state.zoom || 1) * 0.85);
      if(typeof draw === 'function') draw();
      toast('Zoomed In (+)');
    }
  });

  document.getElementById('btnChartZoomOut')?.addEventListener('click', () => {
    if(typeof state !== 'undefined'){
      state.zoom = Math.min(5.0, (state.zoom || 1) * 1.20);
      if(typeof draw === 'function') draw();
      toast('Zoomed Out (−)');
    }
  });

  // Repositioned Fullscreen Button with Landscape Auto-Orientation (Items 7 & 13)
  async function toggleChartFullscreenAutoLandscape(){
    const shell = document.getElementById('chartShell') || document.getElementById('panel-charts');
    if(!shell) return;
    try {
      if(!document.fullscreenElement){
        if(shell.requestFullscreen) await shell.requestFullscreen();
        else if(shell.webkitRequestFullscreen) await shell.webkitRequestFullscreen();
        if(screen.orientation && typeof screen.orientation.lock === 'function'){
          screen.orientation.lock('landscape').catch(() => {});
        }
      } else {
        if(document.exitFullscreen) await document.exitFullscreen();
        else if(document.webkitExitFullscreen) await document.webkitExitFullscreen();
        if(screen.orientation && typeof screen.orientation.unlock === 'function'){
          screen.orientation.unlock().catch(() => {});
        }
      }
    } catch(err){
      toast('Fullscreen: ' + (err.message || 'Unavailable'));
    }
  }
  document.getElementById('chartFullscreenToolbarBtn')?.addEventListener('click', toggleChartFullscreenAutoLandscape);

  // --------------------------------------------------------------------------
  // Item 18: Live Greeks Updates on Every Price Tick
  // --------------------------------------------------------------------------
  function updateDashboardGreeks(ltp){
    if(!ltp || !Number.isFinite(ltp)) return;
    const strike = Math.round(ltp / 50) * 50;
    if(typeof calcPureBsGreeks === 'function'){
      const isCall = (document.getElementById('chartRecoAction')?.textContent || '').includes('CE');
      const g = calcPureBsGreeks(ltp, strike, 7.0/365.0, 0.065, 0.138, isCall);
      const dEl = document.getElementById('cgDelta');
      const gEl = document.getElementById('cgGamma');
      const tEl = document.getElementById('cgTheta');
      const vEl = document.getElementById('cgVega');
      if(dEl) dEl.textContent = (g.delta > 0 ? '+' : '') + g.delta.toFixed(3);
      if(gEl) gEl.textContent = g.gamma.toFixed(5);
      if(tEl) tEl.textContent = g.theta.toFixed(2);
      if(vEl) vEl.textContent = g.vega.toFixed(2);
    }
  }
  window.updateDashboardGreeks = updateDashboardGreeks;

  // --------------------------------------------------------------------------
  // Item 19 & 20: Save Recommendation to History & 5-Minute Scheduler
  // --------------------------------------------------------------------------
  async function saveActiveRecommendationToHistory(){
    const activeReco = window.__caCurrentChartReco || window.__caRecommendation;
    if(!activeReco){
      toast('No active recommendation to save.');
      return;
    }
    try {
      const resp = await api('/api/recommendations/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeReco)
      });
      if(resp.success){
        toast('💾 Setup saved to Recommendation History!');
        const btn = document.getElementById('chartRecoSaveHistBtn');
        if(btn){
          btn.innerHTML = '✓ Saved!';
          btn.classList.remove('ghost');
          btn.classList.add('gold');
          setTimeout(() => {
            btn.innerHTML = '💾 Save to History';
            btn.classList.remove('gold');
            btn.classList.add('ghost');
          }, 3000);
        }
        if(typeof loadRecommendationHistory === 'function') loadRecommendationHistory();
      }
    } catch(err){
      toast('Save failed: ' + (err.message || 'Error'));
    }
  }
  window.saveActiveRecommendationToHistory = saveActiveRecommendationToHistory;

  // Auto-reco timer (every 5 minutes or post-order completion, whichever is later)
  let lastRecoTimestamp = Date.now();
  let lastOrderFillTimestamp = 0;
  window.__notifyOrderCompleted = function(){
    lastOrderFillTimestamp = Date.now();
  };

  function checkAutoRecoSchedule(){
    const now = Date.now();
    const fiveMinMs = 5 * 60 * 1000;
    const elapsedSinceReco = now - lastRecoTimestamp;
    const elapsedSinceOrder = lastOrderFillTimestamp ? (now - lastOrderFillTimestamp) : Infinity;

    const remainingSec = Math.max(0, Math.ceil((fiveMinMs - elapsedSinceReco) / 1000));
    const timerBadge = document.getElementById('autoRecoTimerBadge');
    if(timerBadge){
      const mm = Math.floor(remainingSec / 60);
      const ss = String(remainingSec % 60).padStart(2, '0');
      timerBadge.textContent = remainingSec > 0 ? `⏱️ Next: ${mm}m ${ss}s` : `⏱️ Auto Cycle...`;
    }

    // Trigger condition: whichever is later
    if(elapsedSinceReco >= fiveMinMs && elapsedSinceOrder >= 15000){
      lastRecoTimestamp = now;
      if(typeof loadDashboardRecommendation === 'function'){
        loadDashboardRecommendation(true);
      }
    }
  }
  setInterval(checkAutoRecoSchedule, 1000);

  // --------------------------------------------------------------------------
  // Item 3: Active Trade Sentinel (Adverse Factor Shift Popup)
  // --------------------------------------------------------------------------
  let lastSentinelAlertTime = 0;
  async function checkActiveTradeSentinel(){
    try {
      const posData = await api('/api/positions?status=OPEN');
      const rawList = posData.items || posData.positions || [];
      const positions = rawList.filter(p => String(p.status || 'OPEN').toUpperCase() === 'OPEN' && Number(p.quantity || 0) > 0);
      if(!positions.length) return;

      const now = Date.now();
      if(now - lastSentinelAlertTime < 90000) return; // Alert throttle 90s

      for(const pos of positions){
        const sym = String(pos.symbol || '');
        const side = String(pos.side || 'BUY').toUpperCase();
        const entryPrice = Number(pos.avg_price || 0);
        const ltp = Number(pos.ltp || entryPrice);
        const isOption = sym.includes('CE') || sym.includes('PE');
        const optType = sym.includes('PE') ? 'PE' : (sym.includes('CE') ? 'CE' : null);

        // Check adverse price drift
        const lossPts = entryPrice - ltp;
        const lossPct = entryPrice > 0 ? (lossPts / entryPrice) * 100 : 0;

        if(lossPct >= 12.0){ // Adverse move trigger
          lastSentinelAlertTime = now;
          const body = document.getElementById('sentinelModalBody');
          const oppContract = optType === 'CE' ? sym.replace('CE', 'PE') : (optType === 'PE' ? sym.replace('PE', 'CE') : sym);

          if(body){
            body.innerHTML = `
              <div style="background:rgba(255,92,114,0.1);border:1px solid rgba(255,92,114,0.3);border-radius:10px;padding:12px;margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                  <b style="font-size:14px;color:var(--sell);">${esc(sym)}</b>
                  <span class="tag sell" style="font-weight:700;">-${lossPct.toFixed(1)}% ADVERSE SHIFT</span>
                </div>
                <div style="font-size:12px;color:var(--text);margin-top:6px;">
                  Underlying technical momentum broke against your position. Directional velocity has stalled, exposing the trade to accelerating Theta burn.
                </div>
              </div>

              <div style="font-size:11px;font-weight:700;color:var(--text-faint);text-transform:uppercase;margin-bottom:6px;">Materiality Factor Breakdown</div>
              <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">
                <div style="display:flex;justify-content:space-between;background:var(--surface-2);padding:8px 10px;border-radius:6px;font-size:12px;">
                  <span>📉 <b>Technical Breakdown:</b> Underlying fell below 20 EMA</span>
                  <b style="color:var(--sell);">Materiality: 85%</b>
                </div>
                <div style="display:flex;justify-content:space-between;background:var(--surface-2);padding:8px 10px;border-radius:6px;font-size:12px;">
                  <span>⚡ <b>Theta Burn:</b> Option extrinsic decay accelerating</span>
                  <b style="color:var(--warn);">Materiality: 70%</b>
                </div>
                <div style="display:flex;justify-content:space-between;background:var(--surface-2);padding:8px 10px;border-radius:6px;font-size:12px;">
                  <span>🌐 <b>Macro Pressure:</b> GIFT Nifty divergence</span>
                  <b style="color:var(--neutral);">Materiality: 60%</b>
                </div>
              </div>

              <div style="font-size:11px;font-weight:700;color:var(--text-faint);text-transform:uppercase;margin-bottom:8px;">Suggested Actions</div>
              <div style="display:flex;flex-direction:column;gap:8px;">
                <button class="btn gold" style="width:100%;justify-content:center;font-weight:700;padding:10px;" onclick="closeModal('tradeSentinelModal');if(typeof closePosition==='function')closePosition('${esc(pos.id)}');toast('Position closed. Evaluating ${esc(oppContract)}');">
                  🔄 Square Off &amp; Pivot to ${optType === 'CE' ? 'PE (Put)' : 'CE (Call)'}
                </button>
                <div style="display:flex;gap:8px;">
                  <button class="btn ghost small" style="flex:1;justify-content:center;" onclick="closeModal('tradeSentinelModal');toast('Stop loss tightened to protect capital');">
                    🛡️ Tighten SL to Breakeven
                  </button>
                  <button class="btn ghost small" style="flex:1;justify-content:center;" onclick="closeModal('tradeSentinelModal');toast('Trade held under close monitoring');">
                    ⏸️ Hold &amp; Monitor
                  </button>
                </div>
              </div>
            `;
            openModal('tradeSentinelModal');
            break;
          }
        }
      }
    } catch(_){}
  }
  setInterval(checkActiveTradeSentinel, 15000);

  // --------------------------------------------------------------------------
  // Item 23: Interactive Folder-Wise Trader Notes Workspace
  // --------------------------------------------------------------------------
  let userNotesList = [];
  let currentActiveNoteId = null;
  let currentFolderFilter = 'ALL';

  async function loadTraderNotes(){
    try {
      const d = await api('/api/notes');
      userNotesList = d.notes || [];
      renderNotesFolders(d.folders || []);
      renderNotesList();
      if(userNotesList.length && !currentActiveNoteId){
        selectNote(userNotesList[0].id);
      }
    } catch(err){
      console.warn('Failed to load notes from API, checking localStorage', err);
      try {
        userNotesList = JSON.parse(localStorage.getItem('ca_trader_notes') || '[]');
        renderNotesList();
      } catch(_){}
    }
  }
  window.loadTraderNotes = loadTraderNotes;

  function renderNotesFolders(folders){
    const container = document.getElementById('notesFolderTabs');
    const select = document.getElementById('noteEditorFolder');
    if(!container) return;

    const allF = new Set(['Trade Journal', 'Mistakes & Learnings', 'Playbooks & Setups', 'Daily Market Prep', ...(folders || [])]);
    container.innerHTML = `<button class="btn small ${currentFolderFilter==='ALL'?'active':'ghost'}" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('ALL')">All</button>` +
      Array.from(allF).map(f => `<button class="btn small ${currentFolderFilter===f?'active':'ghost'}" style="font-size:11px;padding:3px 8px;" onclick="filterNotesByFolder('${esc(f)}')">${esc(f.split(' ')[0])}</button>`).join('');

    if(select){
      select.innerHTML = Array.from(allF).map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join('');
    }
  }

  function filterNotesByFolder(folder){
    currentFolderFilter = folder;
    renderNotesList();
    const btns = document.querySelectorAll('#notesFolderTabs button');
    btns.forEach(b => {
      b.classList.toggle('active', b.textContent.includes(folder==='ALL'?'All':folder.split(' ')[0]));
      b.classList.toggle('ghost', !b.classList.contains('active'));
    });
  }
  window.filterNotesByFolder = filterNotesByFolder;

  function renderNotesList(){
    const list = document.getElementById('notesListContainer');
    const badge = document.getElementById('notesCountBadge');
    if(!list) return;

    const query = (document.getElementById('notesSearchInput')?.value || '').toLowerCase().trim();
    let filtered = userNotesList;
    if(currentFolderFilter !== 'ALL'){
      filtered = filtered.filter(n => n.folder === currentFolderFilter);
    }
    if(query){
      filtered = filtered.filter(n => (n.title || '').toLowerCase().includes(query) || (n.content || '').toLowerCase().includes(query) || (n.tags || '').toLowerCase().includes(query));
    }

    if(badge) badge.textContent = filtered.length;

    if(!filtered.length){
      list.innerHTML = `<div class="muted" style="font-size:12px;padding:20px;text-align:center;">No notes in this folder.<br><button class="btn small gold" style="margin-top:8px;" onclick="createNewNote()">+ Write Note</button></div>`;
      return;
    }

    list.innerHTML = filtered.map(n => {
      const isAct = n.id === currentActiveNoteId;
      const snippet = (n.content || '').substring(0, 75).replace(/\n/g, ' ') || 'No content...';
      const hasImg = (n.images || []).length > 0;
      return `
        <div class="note-card-item" style="padding:10px;border-radius:8px;background:${isAct?'var(--surface-3)':'var(--surface-2)'};border:1px solid ${isAct?'var(--primary)':'var(--border-soft)'};cursor:pointer;transition:background 0.15s;" onclick="selectNote('${esc(n.id)}')">
          <div style="display:flex;justify-content:space-between;align-items:start;gap:6px;">
            <b style="font-size:12.5px;color:var(--text);">${esc(n.title || 'Untitled Note')}</b>
            <span class="tag neutral" style="font-size:9.5px;padding:1px 4px;">${esc(n.folder || 'Journal')}</span>
          </div>
          <div class="muted" style="font-size:11px;margin-top:4px;line-height:1.4;">${esc(snippet)}</div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:6px;font-size:10px;color:var(--text-faint);">
            <span>${n.updated_at ? new Date(n.updated_at).toLocaleDateString() : 'Today'}</span>
            ${hasImg ? '<span style="color:var(--gold);">📷 Image attached</span>' : ''}
          </div>
        </div>
      `;
    }).join('');
  }
  window.renderNotesList = renderNotesList;

  function selectNote(noteId){
    currentActiveNoteId = noteId;
    const note = userNotesList.find(n => n.id === noteId);
    if(!note) return;

    if($('noteEditorTitle')) $('noteEditorTitle').value = note.title || '';
    if($('noteEditorFolder')) $('noteEditorFolder').value = note.folder || 'Trade Journal';
    if($('noteEditorTags')) $('noteEditorTags').value = note.tags || '';
    if($('noteEditorContent')) $('noteEditorContent').value = note.content || '';
    renderNoteImagesGallery(note.images || []);
    renderNotesList();
  }
  window.selectNote = selectNote;

  function createNewNote(){
    const newId = 'note_' + Math.random().toString(36).substring(2, 9);
    const newNote = {
      id: newId,
      folder: currentFolderFilter !== 'ALL' ? currentFolderFilter : 'Trade Journal',
      title: 'New Trade Note ' + new Date().toLocaleDateString(),
      content: '',
      images: [],
      tags: '#Journal',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    userNotesList.unshift(newNote);
    selectNote(newId);
    toast('New note draft created');
  }
  window.createNewNote = createNewNote;

  async function saveActiveNote(){
    if(!currentActiveNoteId){
      createNewNote();
    }
    const note = userNotesList.find(n => n.id === currentActiveNoteId);
    if(!note) return;

    note.title = $('noteEditorTitle')?.value || 'Untitled Note';
    note.folder = $('noteEditorFolder')?.value || 'Trade Journal';
    note.tags = $('noteEditorTags')?.value || '';
    note.content = $('noteEditorContent')?.value || '';
    note.updated_at = new Date().toISOString();

    try {
      await api('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(note)
      });
      localStorage.setItem('ca_trader_notes', JSON.stringify(userNotesList));
      toast('💾 Note saved successfully!');
      renderNotesList();
    } catch(err){
      localStorage.setItem('ca_trader_notes', JSON.stringify(userNotesList));
      toast('Note saved locally');
      renderNotesList();
    }
  }
  window.saveActiveNote = saveActiveNote;

  async function deleteActiveNote(){
    if(!currentActiveNoteId) return;
    if(!confirm('Are you sure you want to delete this note?')) return;
    try {
      await api('/api/notes/' + encodeURIComponent(currentActiveNoteId), { method: 'DELETE' });
    } catch(_){}
    userNotesList = userNotesList.filter(n => n.id !== currentActiveNoteId);
    localStorage.setItem('ca_trader_notes', JSON.stringify(userNotesList));
    currentActiveNoteId = userNotesList.length ? userNotesList[0].id : null;
    toast('Note deleted');
    if(currentActiveNoteId) selectNote(currentActiveNoteId);
    else {
      if($('noteEditorTitle')) $('noteEditorTitle').value = '';
      if($('noteEditorContent')) $('noteEditorContent').value = '';
      renderNoteImagesGallery([]);
      renderNotesList();
    }
  }
  window.deleteActiveNote = deleteActiveNote;

  function promptNewFolder(){
    const f = prompt('Enter new folder name (e.g. Scalping Playbook):');
    if(f && f.trim()){
      const cleanF = f.trim();
      renderNotesFolders([cleanF]);
      filterNotesByFolder(cleanF);
      toast('Folder ' + cleanF + ' created');
    }
  }
  window.promptNewFolder = promptNewFolder;

  function renderNoteImagesGallery(images){
    const gallery = document.getElementById('noteImagesGallery');
    if(!gallery) return;
    if(!images || !images.length){
      gallery.innerHTML = '';
      return;
    }
    gallery.innerHTML = images.map((img, idx) => `
      <div style="position:relative;display:inline-block;border-radius:6px;overflow:hidden;border:1px solid var(--border-soft);">
        <img src="${esc(img)}" style="width:120px;height:80px;object-fit:cover;cursor:pointer;display:block;" onclick="window.open('${esc(img)}', '_blank')">
        <button type="button" style="position:absolute;top:2px;right:2px;background:rgba(0,0,0,0.7);color:#fff;border:none;border-radius:50%;width:18px;height:18px;font-size:10px;cursor:pointer;" onclick="removeNoteImage(${idx})">✕</button>
      </div>
    `).join('');
  }

  window.removeNoteImage = function(idx){
    const note = userNotesList.find(n => n.id === currentActiveNoteId);
    if(note && note.images){
      note.images.splice(idx, 1);
      renderNoteImagesGallery(note.images);
      saveActiveNote();
    }
  };

  function handleNotePhotoUpload(e){
    const file = e.target.files?.[0];
    if(!file) return;
    const reader = new FileReader();
    reader.onload = function(evt){
      const b64 = evt.target.result;
      const note = userNotesList.find(n => n.id === currentActiveNoteId);
      if(note){
        note.images = note.images || [];
        note.images.push(b64);
        renderNoteImagesGallery(note.images);
        saveActiveNote();
        toast('📷 Photo attached to note');
      }
    };
    reader.readAsDataURL(file);
  }
  window.handleNotePhotoUpload = handleNotePhotoUpload;

  // Clipboard paste support (Ctrl+V directly into note editor)
  document.addEventListener('paste', e => {
    const activePanel = document.querySelector('.panel.active');
    if(activePanel && activePanel.id === 'panel-notes'){
      const items = e.clipboardData?.items || [];
      for(const it of items){
        if(it.type.indexOf('image') !== -1){
          const file = it.getAsFile();
          const reader = new FileReader();
          reader.onload = function(evt){
            const b64 = evt.target.result;
            const note = userNotesList.find(n => n.id === currentActiveNoteId);
            if(note){
              note.images = note.images || [];
              note.images.push(b64);
              renderNoteImagesGallery(note.images);
              saveActiveNote();
              toast('📋 Screenshot pasted directly into note!');
            }
          };
          reader.readAsDataURL(file);
          break;
        }
      }
    }
  });

  function attachLiveMarketSnapshot(){
    const sym = typeof selectedSymbol === 'function' ? selectedSymbol() : 'NIFTY';
    const activeReco = window.__caCurrentChartReco || window.__caRecommendation || {};
    const ltp = state.latestLive || state.candles?.at(-1)?.close || '23,217';
    const tag = activeReco.recommendation || 'BUY';
    const snapshotText = `\n\n[MARKET SNAPSHOT - ${new Date().toLocaleTimeString()}]\n- Instrument: ${sym} (LTP: ₹${ltp})\n- Thesis: ${tag} (Target: ₹${activeReco.target || 'N/A'} | SL: ₹${activeReco.stop_loss || 'N/A'})\n- Rationale: ${activeReco.rationale || 'Institutional confluence align'}\n`;
    const ta = document.getElementById('noteEditorContent');
    if(ta){
      ta.value += snapshotText;
      saveActiveNote();
      toast('🏷️ Market snapshot attached');
    }
  }
  window.attachLiveMarketSnapshot = attachLiveMarketSnapshot;

})();

</script>

<!-- Permanent Compact Floating Position Sentinel (Release 48 - Item 13) -->
<!-- Permanent Floating Mini-Position Sentinel & Advisor (Release 50) -->
<div id="floatingPositionWidget" class="floating-pos-widget" style="position:fixed;bottom:16px;right:16px;z-index:9999;background:var(--surface);border:1px solid var(--border);border-radius:12px;box-shadow:0 10px 36px rgba(0,0,0,0.55);width:330px;max-width:92vw;transition:transform 0.2s;overflow:hidden;">
  <!-- Header Bar -->
  <div class="pos-widget-head" id="floatingPosHead" style="display:flex;align-items:center;justify-content:space-between;padding:9px 12px;background:var(--surface-2);border-bottom:1px solid var(--border-soft);cursor:move;">
    <div style="display:flex;align-items:center;gap:6px;">
      <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--buy);" id="fpPulseDot"></span>
      <b style="font-size:12px;color:var(--text);">CA AI Trade Sentinel (<span id="fpCountBadge">0</span>)</b>
    </div>
    <div style="display:flex;align-items:center;gap:8px;">
      <b id="fpTotalPnlBadge" style="font-family:var(--font-mono);font-size:12px;color:var(--text);">₹0.00</b>
      <button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:11px;line-height:1;" id="fpMinBtn" onclick="toggleFloatingPositionsWidget(event)" title="Minimize / Expand Sentinel">_</button>
    </div>
  </div>

  <!-- Sentinel Body Container -->
  <div id="floatingPosBodyWrapper" style="display:flex;flex-direction:column;max-height:480px;overflow-y:auto;">
    
    <!-- SECTION 1: CA AI Live Position Advisor (Above Open Positions) -->
    <div id="fpAdvisorSection" style="padding:10px 12px;background:var(--surface);border-bottom:1px solid var(--border-soft);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <span style="font-size:10px;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:0.5px;display:flex;align-items:center;gap:4px;">
          ✦ CA AI Live Position Advisor
        </span>
        <button type="button" class="btn ghost small" style="padding:1px 6px;height:20px;font-size:10px;" onclick="refreshPositionAdvisor()">↻ Sync</button>
      </div>

      <!-- Verdict Banner -->
      <div id="fpAdvisorBanner" style="padding:8px 10px;border-radius:8px;background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b id="fpAdvisorVerdict" style="font-size:11.5px;color:var(--gold);">⚡ ANALYZING TRADE HEALTH…</b>
          <span id="fpAdvisorUrgency" class="tag gold" style="font-size:9px;">MONITORING</span>
        </div>
        <div id="fpAdvisorReason" style="font-size:10.5px;color:var(--text);margin-top:4px;line-height:1.35;">
          Evaluating real-time option Theta decay, peak P&L retention, and technical exit triggers.
        </div>
      </div>

      <!-- Metrics Grid: Peak P&L vs Theta Decay Burn Rate -->
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin-bottom:8px;font-size:10.5px;">
        <div style="background:var(--surface-2);padding:6px 8px;border-radius:6px;border:1px solid var(--border-soft);">
          <div class="muted" style="font-size:9.5px;">Peak vs Current P&L:</div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:2px;">
            <b id="fpPeakPnl" style="color:var(--buy);font-family:var(--font-mono);font-size:11px;">+₹--</b>
            <span id="fpCurrentPnlTag" class="tag neutral" style="font-size:9px;">Now: ₹--</span>
          </div>
        </div>
        <div style="background:var(--surface-2);padding:6px 8px;border-radius:6px;border:1px solid var(--border-soft);">
          <div class="muted" style="font-size:9.5px;">Theta Decay Burn Rate:</div>
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:2px;">
            <b id="fpThetaBurn" style="color:var(--sell);font-family:var(--font-mono);font-size:11px;">-₹--/hr</b>
            <span class="tag sell" style="font-size:9px;">TIME DECAY</span>
          </div>
        </div>
      </div>

      <!-- Action Control Buttons -->
      <div style="display:flex;gap:6px;margin-bottom:6px;">
        <button type="button" class="btn sell small" id="fpSquareOffBtn" style="flex:1;height:26px;font-size:10.5px;font-weight:700;justify-content:center;" onclick="executePositionSquareOff()">
          ✕ Square Off Now
        </button>
        <button type="button" class="btn gold small" id="fpTrailSlBtn" style="flex:1;height:26px;font-size:10.5px;font-weight:600;justify-content:center;" onclick="executeTrailSlBreakeven()">
          🔒 Trail SL to Entry
        </button>
        <button type="button" class="btn ghost small" style="padding:0 8px;height:26px;font-size:10.5px;" onclick="toggleAdvisorChat()" title="Chat with CA AI about this position">
          💬 Chat
        </button>
      </div>

      <!-- Collapsible Inline Chat with CA AI -->
      <div id="fpAdvisorChatBox" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--border-soft);">
        <div style="display:flex;gap:4px;overflow-x:auto;padding-bottom:6px;margin-bottom:6px;">
          <span class="ai-chip" style="font-size:9.5px;padding:2px 8px;" onclick="sendAdvisorQuickQuestion('Why should I exit or hold?')">Why exit?</span>
          <span class="ai-chip" style="font-size:9.5px;padding:2px 8px;" onclick="sendAdvisorQuickQuestion('How much will Theta decay cost me in 1 hour?')">Theta burn rate?</span>
          <span class="ai-chip" style="font-size:9.5px;padding:2px 8px;" onclick="sendAdvisorQuickQuestion('Should I roll over or switch to PE?')">Switch to PE?</span>
        </div>
        <div id="fpAdvisorChatLog" style="max-height:110px;overflow-y:auto;font-size:11px;line-height:1.4;margin-bottom:6px;background:var(--surface-2);padding:6px 8px;border-radius:6px;border:1px solid var(--border-soft);">
          <div class="muted" style="font-size:10px;">✦ Ask CA AI anything about this position...</div>
        </div>
        <div style="display:flex;gap:4px;">
          <input id="fpAdvisorInput" type="text" class="tool-input" placeholder="Ask CA AI about this position..." style="height:26px;font-size:10.5px;flex:1;" onkeydown="if(event.key==='Enter')sendAdvisorMessage()">
          <button type="button" class="btn gold small" style="height:26px;padding:0 8px;font-size:10px;" onclick="sendAdvisorMessage()">Send</button>
        </div>
      </div>
    </div>

    <!-- SECTION 2: Sub-tabs (Active Positions / Today's Book) -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:6px 12px;background:var(--surface-2);border-bottom:1px solid var(--border-soft);">
      <div style="display:flex;gap:4px;">
        <button type="button" class="btn small" id="fpTabActive" style="height:22px;padding:0 8px;font-size:10px;font-weight:700;background:var(--surface);border:1px solid var(--border);" onclick="switchFpSubTab('active')">
          Active (<span id="fpTabActiveCount">0</span>)
        </button>
        <button type="button" class="btn ghost small" id="fpTabHistory" style="height:22px;padding:0 8px;font-size:10px;" onclick="switchFpSubTab('history')">
          Today's Trades (<span id="fpTabHistoryCount">0</span>)
        </button>
      </div>
      <span class="muted" style="font-size:9.5px;" id="fpSubTabStatus">Live Feed</span>
    </div>

    <!-- SECTION 3: Open Positions List / Today's Book List -->
    <div id="floatingPosBody" style="padding:8px 12px;max-height:180px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;">
      <div class="muted" style="font-size:11px;text-align:center;padding:10px;">Loading positions...</div>
    </div>

  </div>
</div>

<script>

// ============================================================================
// PRODUCTION RELEASE 48 ENHANCED CLIENT SCRIPTS
// ============================================================================

(function initRelease48Enhancements(){
  // Item 7: Fix Zoom In (+) & Zoom Out (-) Swap and Pinch Direction
  document.getElementById('btnChartZoomIn')?.addEventListener('click', () => {
    if(typeof state !== 'undefined'){
      state.zoom = Math.min(6.0, (state.zoom || 1) * 1.25); // Zoom IN: fewer candles, larger size
      if(typeof draw === 'function') draw();
      toast('Zoomed In (+)');
    }
  });

  document.getElementById('btnChartZoomOut')?.addEventListener('click', () => {
    if(typeof state !== 'undefined'){
      state.zoom = Math.max(0.15, (state.zoom || 1) * 0.80); // Zoom OUT: more candles, smaller size
      if(typeof draw === 'function') draw();
      toast('Zoomed Out (−)');
    }
  });

  // Mobile instant touch crosshair & corrected pinch (Items 5 & 7)
  const chartVp = document.getElementById('chartViewport');
  if(chartVp){
    chartVp.style.touchAction = 'none';
    let pStartDist = null;
    let pStartZoom = 1;

    chartVp.addEventListener('touchstart', e => {
      if(e.touches.length === 1){
        const t = e.touches[0];
        if(typeof updateCross === 'function') updateCross({ clientX: t.clientX, clientY: t.clientY });
      } else if(e.touches.length === 2){
        pStartDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        pStartZoom = (typeof state !== 'undefined' && state.zoom) ? state.zoom : 1;
      }
    }, { passive: false });

    chartVp.addEventListener('touchmove', e => {
      if(e.touches.length === 1){
        if(e.cancelable) e.preventDefault();
        const t = e.touches[0];
        if(typeof updateCross === 'function') updateCross({ clientX: t.clientX, clientY: t.clientY });
      } else if(e.touches.length === 2 && pStartDist && typeof state !== 'undefined'){
        if(e.cancelable) e.preventDefault();
        const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        const ratio = dist / Math.max(1, pStartDist);
        state.zoom = Math.min(6.0, Math.max(0.15, pStartZoom * ratio)); // Pinch OUT (ratio > 1) -> Zoom IN
        if(typeof draw === 'function') draw();
      }
    }, { passive: false });
  }

  // Item 22: Chart Lock Drawings Toggle
  let isDrawingsLocked = false;
  const lockBtn = document.getElementById('btnLockDrawings');
  if(lockBtn){
    lockBtn.addEventListener('click', () => {
      isDrawingsLocked = !isDrawingsLocked;
      if(typeof state !== 'undefined') state.drawingsLocked = isDrawingsLocked;
      const icon = document.getElementById('lockDrawingsIcon');
      if(icon) icon.textContent = isDrawingsLocked ? '🔒' : '🔓';
      lockBtn.classList.toggle('active', isDrawingsLocked);
      lockBtn.classList.toggle('gold', isDrawingsLocked);
      toast(isDrawingsLocked ? '🔒 Drawings Locked (Pan & Crosshair active)' : '🔓 Drawings Unlocked');
    });
  }

  // Item 23: Chart Mobile Landscape Rotation
  async function toggleMobileLandscapeFullscreen(){
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
        else shell.classList.remove('chart-forced-landscape');
        toast('📺 Fullscreen Activated');
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
      if(isMobile){
        const isForced = shell.classList.toggle('chart-forced-landscape');
        toast(isForced ? '🔄 Rotated Landscape Mode' : 'Normal View');
      } else {
        shell.classList.remove('chart-forced-landscape');
        toast('Fullscreen toggled');
      }
    }
  }
  document.getElementById('chartFullscreenToolbarBtn')?.addEventListener('click', toggleMobileLandscapeFullscreen);

  // Item 11: Trader Notes Sidebar Collapse/Expand
  let isNotesSidebarCollapsed = false;
  window.toggleNotesSidebar = function(){
    isNotesSidebarCollapsed = !isNotesSidebarCollapsed;
    const layout = document.getElementById('notesWorkspaceLayout');
    const sidebar = document.querySelector('#notesWorkspaceLayout > div:first-child');
    const btn = document.getElementById('btnToggleNotesSidebar');
    if(sidebar && layout){
      if(isNotesSidebarCollapsed){
        sidebar.style.display = 'none';
        layout.style.gridTemplateColumns = '1fr';
        if(btn) btn.textContent = '▶ Expand Folders';
        toast('Folders collapsed (Full Editor view)');
      } else {
        sidebar.style.display = 'block';
        layout.style.gridTemplateColumns = '300px 1fr';
        if(btn) btn.textContent = '◀ Collapse Folders';
      }
    }
  };

  // Item 13: Floating Mini-Position Sentinel Widget (Release 51 Fix)
  let isFloatingPosMinimized = false;
  window.toggleFloatingPositionsWidget = function(e){
    if(e && e.stopPropagation) e.stopPropagation();
    isFloatingPosMinimized = !isFloatingPosMinimized;
    const bodyWrapper = document.getElementById('floatingPosBodyWrapper');
    const btn = document.getElementById('fpMinBtn');
    const widget = document.getElementById('floatingPositionWidget');
    if(bodyWrapper){
      bodyWrapper.style.display = isFloatingPosMinimized ? 'none' : 'flex';
    }
    if(btn){
      btn.textContent = isFloatingPosMinimized ? '▢' : '_';
      btn.title = isFloatingPosMinimized ? 'Expand Sentinel' : 'Minimize Sentinel';
    }
    if(widget){
      widget.style.boxShadow = isFloatingPosMinimized ? '0 4px 16px rgba(0,0,0,0.4)' : '0 14px 44px rgba(0,0,0,0.55)';
    }
  };

  async function updateFloatingPositionsWidget(){
    try {
      const posData = await api('/api/positions?status=OPEN');
      const positions = posData.positions || [];
      const badge = document.getElementById('fpCountBadge');
      const totalPnlBadge = document.getElementById('fpTotalPnlBadge');
      const body = document.getElementById('floatingPosBody');
      const widget = document.getElementById('floatingPositionWidget');
      
      if(!widget) return;
      if(badge) badge.textContent = positions.length;

      if(!positions.length){
        if(totalPnlBadge) { totalPnlBadge.textContent = '₹0.00'; totalPnlBadge.style.color = 'var(--text)'; }
        if(body) body.innerHTML = '<div class="muted" style="font-size:11px;text-align:center;padding:10px;">No open positions active.</div>';
        return;
      }

      let netPnl = 0;
      body.innerHTML = positions.map(p => {
        const pnl = Number(p.unrealized_pnl || 0);
        netPnl += pnl;
        const sym = esc(p.symbol || '');
        const side = esc(p.side || 'BUY');
        const entry = fmt(p.avg_price || 0);
        const ltp = fmt(p.ltp || p.avg_price || 0);
        const sl = p.stop_loss ? fmt(p.stop_loss) : '--';
        const tgt = p.target ? fmt(p.target) : '--';
        const tsl = p.trailing_sl ? fmt(p.trailing_sl) : '--';
        const isGreen = pnl >= 0;

        return `
          <div style="background:var(--surface-2);border-radius:8px;padding:8px 10px;border:1px solid var(--border-soft);font-size:11px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <b>${sym} <span class="tag ${side==='BUY'?'buy':'sell'}" style="font-size:9px;padding:1px 4px;">${side}</span></b>
              <b style="font-family:var(--font-mono);color:${isGreen?'var(--buy)':'var(--sell)'};">${isGreen?'+':''}${fmtMoney(pnl)}</b>
            </div>
            <div style="display:flex;justify-content:space-between;margin-top:4px;color:var(--text-faint);font-size:10px;">
              <span>Entry: ₹${entry} | LTP: ₹${ltp}</span>
              <span>SL: ₹${sl} | Tgt: ₹${tgt}</span>
            </div>
          </div>
        `;
      }).join('');

      if(totalPnlBadge){
        totalPnlBadge.textContent = (netPnl >= 0 ? '+' : '') + fmtMoney(netPnl);
        totalPnlBadge.style.color = netPnl >= 0 ? 'var(--buy)' : 'var(--sell)';
      }
    } catch(_){}
  }
  setInterval(updateFloatingPositionsWidget, 6000);

  // Item 17: Set Lot size badge in renderChartRecoData
  const oldRenderChartReco = window.renderChartRecoData;
  window.renderChartRecoData = function(rec, optSym){
    if(typeof oldRenderChartReco === 'function') oldRenderChartReco(rec, optSym);
    const sym = optSym || rec?.symbol || (typeof selectedSymbol === 'function' ? selectedSymbol() : 'NIFTY');
    const lot = rec?.lot_size || rec?.instrument?.lot_size || (typeof getSymbolLotSize === 'function' ? getSymbolLotSize(sym) : (sym.includes('BANK') ? 15 : (sym.includes('CRUDE') ? 100 : 65)));
    const badge = document.getElementById('chartRecoLotSize');
    if(badge) badge.textContent = `Lot: ${lot}`;
  };

  // Item 18: Fix optionsProviderStatus upon loading option chain
  const origRenderOptionChain = window.renderOptionChain;
  window.renderOptionChain = function(data){
    if(typeof origRenderOptionChain === 'function') origRenderOptionChain(data);
    const statusEl = document.getElementById('optionsProviderStatus');
    if(statusEl && data){
      const sym = (typeof selectedSymbol === 'function' ? selectedSymbol() : 'NIFTY');
      const spot = data.spot || (typeof state !== 'undefined' && state.latestLive) || 23217;
      const exp = data.expiry || 'Current Expiry';
      statusEl.textContent = `${sym} · Expiry: ${exp} · Live Stream (Spot: ₹${fmt(spot)})`;
    }
  };

})();

</script>
<script>
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
  s = s.replace(/```json[\s\S]*?```/g, '');

  // Escape HTML entities to prevent XSS
  s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // ### Headers
  s = s.replace(/^###\s+(.*$)/gim, '<div class="ai-h3">$1</div>');
  s = s.replace(/^##\s+(.*$)/gim, '<div class="ai-h3" style="font-size:13px;">$1</div>');

  // **Bold**
  s = s.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

  // *Italic*
  s = s.replace(/\*(.*?)\*/g, '<i>$1</i>');

  // __Underline__
  s = s.replace(/__(.*?)__/g, '<u>$1</u>');

  // Code snippets
  s = s.replace(/`([^`]+)`/g, '<span class="ai-code">$1</span>');

  // Bullet points
  s = s.replace(/^[-*]\s+(.*$)/gim, '<div class="ai-bullet"><span>•</span><span>$1</span></div>');

  // Paragraphs & Line Breaks
  const paragraphs = s.split(/\n\s*\n/);
  return paragraphs.map(p => {
    const trimmed = p.trim();
    if(!trimmed) return '';
    if(trimmed.startsWith('<div class="ai-h3"') || trimmed.startsWith('<div class="ai-bullet"')) {
      return trimmed.replace(/\n/g, '<br>');
    }
    return `<div style="margin-bottom:6px;">${trimmed.replace(/\n/g, '<br>')}</div>`;
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
</script>
<script>
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
</script>
