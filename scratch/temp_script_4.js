
(() => {
  /*
   * Authoritative UI quote lane.
   * Primary transport: one bulk quote request to the CA Trader backend.
   * The backend uses the centralized Upstox quote adapter/cache, so the browser
   * never makes one broker request per widget. A received quote is passed through
   * the exact same applyLiveTick() bridge used by the WebSocket path.
   *
   * This lane is deliberately independent of tabs/selection handlers. That is
   * important because a broken optional feature script must never stop LTP updates.
   */
  let __caLiveBusy = false;
  let __caLiveTimer = null;
  let __caWatchlistReadyAt = 0;
  let __caStartupSelected = false;

  const caLiveSymbols = () => {
    const seen = new Set(), out = [];
    document.querySelectorAll('.wl-item[data-symbol]').forEach(row => {
      const s = String(row.dataset.symbol || '').trim().toUpperCase();
      if (s && !seen.has(s)) { seen.add(s); out.push(s); }
    });
    // Include the selected instrument even if the watchlist is filtered.
    const selected = String(window.CATraderSymbol || window.__CA_SELECTED_SYMBOL || '').trim().toUpperCase();
    if (selected && !seen.has(selected)) out.push(selected);

    // Include visible option contracts only when options/dashboard panels are active
    const optionsVisible = document.getElementById('panel-options')?.classList.contains('active') ||
                           document.getElementById('panel-dashboard')?.classList.contains('active');
    if (optionsVisible) {
      document.querySelectorAll(
        '#dashboardOptionMini [data-option-key], #optionChainTable [data-call-key], #optionChainTable [data-put-key]'
      ).forEach(el => {
        const k = String(el.dataset.optionKey || el.dataset.callKey || el.dataset.putKey || '').trim();
        if (k && !seen.has(k) && k.includes('|')) { seen.add(k); out.push(k); }
      });
    }
    return out.slice(0, 100);
  };

  const caApplyFallbackDom = (q) => {
    const sym = String(q?.symbol || q?.instrument || '').trim().toUpperCase();
    const ltp = Number(q?.ltp);
    if (!sym || !Number.isFinite(ltp) || ltp <= 0) return;

    document.querySelectorAll('.wl-item[data-symbol]').forEach(row => {
      if (String(row.dataset.symbol || '').toUpperCase() !== sym) return;
      const el = row.querySelector('.wl-ltp'); if (el) el.textContent = fmt(ltp);
      row.dataset.ltp = String(ltp);
      const ch = row.querySelector('.wl-chg');
      const net = q?.net_change == null ? null : Number(q.net_change);
      const pct = q?.change_pct == null ? null : Number(q.change_pct);
      if (ch && Number.isFinite(net)) {
        ch.textContent = `${net > 0 ? '+' : ''}${fmt(net)}${Number.isFinite(pct) ? ` (${pct > 0 ? '+' : ''}${fmt(pct)}%)` : ''}`;
        ch.className = 'wl-chg ' + (net > 0 ? 'up' : net < 0 ? 'down' : '');
      }
    });

    if (sym === String(window.CATraderSymbol || '').toUpperCase()) {
      const h = document.getElementById('chartSymbolLtp');
      if (h) h.textContent = fmt(ltp);
      const c = document.getElementById('chartSymbolChange');
      const net = q?.net_change == null ? null : Number(q.net_change);
      if (c && Number.isFinite(net)) c.textContent = `${net > 0 ? '+' : ''}${fmt(net)}`;
    }
  };

  async function caFetchLiveQuotes() {
    if (__caLiveBusy || document.visibilityState !== 'visible') return;
    const isOpen = typeof window.isAnyMarketOpen === 'function' ? window.isAnyMarketOpen() : false;
    // When market is closed, avoid hammering the quote endpoint if quotes are already loaded
    if (!isOpen && window.__CA_LAST_LIVE_QUOTE_AT && (Date.now() - window.__CA_LAST_LIVE_QUOTE_AT < 45000)) {
      return;
    }
    const symbols = caLiveSymbols();
    if (!symbols.length) return;

    // On the first successful DOM discovery, select the first watchlist item
    // automatically if no symbol has been selected yet.
    if (!__caStartupSelected) {
      __caWatchlistReadyAt = __caWatchlistReadyAt || Date.now();
      if (!window.CATraderSymbol) {
        const first = document.querySelector('.wl-item[data-symbol]');
        if (first) {
          __caStartupSelected = true;
          try { first.click(); } catch (_) {}
        }
      } else {
        __caStartupSelected = true;
      }
    }

    __caLiveBusy = true;
    try {
      const url = '/api/market/quotes?instruments=' + encodeURIComponent(symbols.join(',')) + '&_ca=' + Date.now();
      const r = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
      if (!r.ok) throw new Error(`live quote HTTP ${r.status}`);
      const d = await r.json();
      for (const q of (d.items || [])) {
        if (!q || q.ltp == null || Number(q.ltp) <= 0) continue;
        if (window.__CA_APPLY_LIVE_TICK) window.__CA_APPLY_LIVE_TICK(q);
        else caApplyFallbackDom(q);
      }
      window.__CA_LAST_LIVE_QUOTE_AT = Date.now();
      window.__CA_LIVE_QUOTE_STATUS = 'ok';
    } catch (e) {
      window.__CA_LIVE_QUOTE_STATUS = 'degraded';
      // Never blank a valid quote because a refresh failed.
      console.debug('[CA Trader continuous quotes]', e);
    } finally {
      __caLiveBusy = false;
    }
  }

  // Single scheduler. Respects healthy rate limits and market hours.
  caFetchLiveQuotes();
  __caLiveTimer = setInterval(caFetchLiveQuotes, 3000);

  // If the first watchlist has not been rendered yet, retry startup selection
  // briefly without creating another quote lane.
  const startupTimer = setInterval(() => {
    if (window.CATraderSymbol || __caStartupSelected) {
      clearInterval(startupTimer);
      return;
    }
    const first = document.querySelector('.wl-item[data-symbol]');
    if (first) {
      __caStartupSelected = true;
      try { first.click(); } catch (_) {}
      clearInterval(startupTimer);
    }
  }, 300);

  window.addEventListener('beforeunload', () => {
    if (__caLiveTimer) clearInterval(__caLiveTimer);
    clearInterval(startupTimer);
  });
})();
