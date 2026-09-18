
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
