/**
 * CA Trader — Automated Global Client Error Telemetry
 * Captures unhandled exceptions and promise rejections and transmits diagnostics
 * to the backend logging & passbook telemetry endpoint.
 */
(() => {
  const sendTelemetry = (payload) => {
    try {
      const data = JSON.stringify({
        ...payload,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        screen: `${window.innerWidth}x${window.innerHeight}`,
        activeSymbol: typeof window.selectedSymbol === 'function' ? window.selectedSymbol() : window.CATraderSymbol || 'NIFTY'
      });
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/logs/client-error', data);
      } else {
        fetch('/api/logs/client-error', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: data,
          keepalive: true
        }).catch(() => {});
      }
    } catch (_) {}
  };

  window.addEventListener('error', (event) => {
    sendTelemetry({
      type: 'JAVASCRIPT_ERROR',
      message: event.message || 'Unknown script error',
      source: event.filename || 'inline',
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error?.stack || ''
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    sendTelemetry({
      type: 'UNHANDLED_PROMISE_REJECTION',
      message: event.reason?.message || String(event.reason || 'Unhandled Promise'),
      stack: event.reason?.stack || ''
    });
  });
})();

