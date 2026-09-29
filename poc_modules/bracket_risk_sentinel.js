/**
 * Feature 9 POC: Smart Bracket Order & Dynamic Break-Even Trailing Sentinel
 * Shifts Stop-Loss to Cost-to-Cost immediately when Target 1 is achieved.
 */
(function() {
  'use strict';

  window.BracketRiskSentinel = class {
    constructor(positions = []) {
      this.positions = positions;
      this.activeAlerts = [];
    }

    evaluatePositionRisk(posId, currentLtp) {
      const pos = this.positions.find(p => p.id === posId);
      if (!pos) return null;

      const isLong = pos.side === 'BUY';
      const unrealizedR = isLong
        ? (currentLtp - pos.entryPrice) / (pos.entryPrice - pos.initialSl)
        : (pos.entryPrice - currentLtp) / (pos.initialSl - pos.entryPrice);

      let status = 'MONITORING';
      let slModified = false;

      // Trailing Rule: If +1.5R achieved and SL not yet at Break-Even, trail SL to entry
      if (unrealizedR >= 1.5 && !pos.isTrailedToBreakEven) {
        pos.currentSl = pos.entryPrice;
        pos.isTrailedToBreakEven = true;
        status = 'TRAILED_TO_BREAK_EVEN';
        slModified = true;
        this.triggerChime();
      } else if (unrealizedR >= 2.5 && !pos.isTrailedToT1) {
        pos.currentSl = pos.target1;
        pos.isTrailedToT1 = true;
        status = 'TRAILED_TO_T1_PROFIT';
        slModified = true;
        this.triggerChime();
      }

      return {
        posId,
        currentLtp,
        unrealizedR: unrealizedR.toFixed(2),
        currentSl: pos.currentSl,
        isTrailedToBreakEven: pos.isTrailedToBreakEven,
        status,
        slModified
      };
    }

    triggerChime() {
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.4);
      } catch(_) {}
    }
  };
})();
