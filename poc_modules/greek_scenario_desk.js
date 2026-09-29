/**
 * Feature 5 POC: Greek Sensitivity Sliders & What-If Scenario Desk
 * Simulates instantaneous portfolio P&L and Greek shocks under dynamic spot price and IV shifts.
 */
(function() {
  'use strict';

  window.simulatePortfolioGreekShock = function(positions, spotShiftPct, ivShiftPct) {
    // positions: [{ type: 'CE'|'PE', strike: 55600, delta: 0.52, gamma: 0.0012, vega: 14.5, theta: -18.2, qty: 30 }]
    let deltaPnl = 0;
    let gammaPnl = 0;
    let vegaPnl = 0;
    let totalPnlShock = 0;

    positions.forEach(pos => {
      const spotChangeVal = (pos.strike * spotShiftPct);
      const ivChangePoints = ivShiftPct * 100; // e.g. +5% IV shock = +5 points

      const posDeltaPnl = pos.delta * spotChangeVal * pos.qty;
      const posGammaPnl = 0.5 * pos.gamma * Math.pow(spotChangeVal, 2) * pos.qty;
      const posVegaPnl = pos.vega * ivChangePoints * pos.qty;

      deltaPnl += posDeltaPnl;
      gammaPnl += posGammaPnl;
      vegaPnl += posVegaPnl;
      totalPnlShock += (posDeltaPnl + posGammaPnl + posVegaPnl);
    });

    return {
      spotShiftPct: (spotShiftPct * 100).toFixed(1) + '%',
      ivShiftPct: (ivShiftPct * 100).toFixed(1) + '%',
      deltaPnl: Math.round(deltaPnl),
      gammaPnl: Math.round(gammaPnl),
      vegaPnl: Math.round(vegaPnl),
      totalPnlShock: Math.round(totalPnlShock),
      riskStatus: totalPnlShock < -5000 ? 'HIGH RISK' : totalPnlShock > 3000 ? 'BENEFICIAL' : 'NEUTRAL BUFFER'
    };
  };
})();
