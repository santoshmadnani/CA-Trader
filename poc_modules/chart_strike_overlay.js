/**
 * Feature 8 POC: Chart-to-Strike Overlay Bands
 * Projects Call and Put strike levels, Max Pain, and highest OI bands directly onto TradingView charts.
 */
(function() {
  'use strict';

  window.renderStrikeOverlayOnChart = function(chartInstance, optionStrikes, maxPainStrike) {
    if (!chartInstance || !Array.isArray(optionStrikes)) return;

    // Filter top 3 highest OI calls and top 3 highest OI puts
    const sortedCalls = [...optionStrikes].sort((a,b) => (b.call?.oi || 0) - (a.call?.oi || 0)).slice(0, 3);
    const sortedPuts = [...optionStrikes].sort((a,b) => (b.put?.oi || 0) - (a.put?.oi || 0)).slice(0, 3);

    const overlayLines = [];

    // Max Pain Line
    if (maxPainStrike) {
      overlayLines.push({
        price: maxPainStrike,
        color: '#e8b84b',
        lineWidth: 2,
        lineStyle: 2, // Dashed
        title: `Max Pain: ₹${maxPainStrike}`
      });
    }

    // Call Resistance Bands
    sortedCalls.forEach((c, idx) => {
      overlayLines.push({
        price: c.strike,
        color: 'rgba(255, 92, 114, 0.8)',
        lineWidth: 1,
        lineStyle: 1,
        title: `Call OI Wall #${idx+1}: ₹${c.strike} (${(c.call?.oi || 0).toLocaleString()} OI)`
      });
    });

    // Put Support Bands
    sortedPuts.forEach((p, idx) => {
      overlayLines.push({
        price: p.strike,
        color: 'rgba(38, 217, 166, 0.8)',
        lineWidth: 1,
        lineStyle: 1,
        title: `Put OI Wall #${idx+1}: ₹${p.strike} (${(p.put?.oi || 0).toLocaleString()} OI)`
      });
    });

    return overlayLines;
  };
})();
