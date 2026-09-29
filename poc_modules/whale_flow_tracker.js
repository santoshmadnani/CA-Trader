/**
 * Feature 6 POC: Institutional Whale Flow Tracker & Big Block Sweeper
 * Filters live tick streams for block quantities exceeding institutional thresholds.
 */
(function() {
  'use strict';

  window.WhaleFlowTracker = class {
    constructor(thresholdValue = 2500000) { // Default threshold: ₹25 Lakhs per order
      this.threshold = thresholdValue;
      this.whaleEvents = [];
    }

    evaluateTrade(trade) {
      // trade: { symbol, price, qty, time, side }
      const tradeValue = trade.price * trade.qty;
      if (tradeValue >= this.threshold) {
        const event = {
          id: 'whale_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
          symbol: trade.symbol,
          price: trade.price,
          qty: trade.qty,
          value: tradeValue,
          side: trade.side, // 'BUY' or 'SELL'
          time: trade.time || new Date().toLocaleTimeString(),
          isSweep: trade.qty >= 50000,
          label: tradeValue >= 10000000 ? 'MEGA WHALE (FII)' : 'INSTITUTIONAL SWEEP'
        };
        this.whaleEvents.unshift(event);
        if (this.whaleEvents.length > 50) this.whaleEvents.pop();
        return event;
      }
      return null;
    }

    getNetFlow() {
      let buyVal = 0, sellVal = 0;
      this.whaleEvents.forEach(e => {
        if (e.side === 'BUY') buyVal += e.value;
        else sellVal += e.value;
      });
      return {
        buyVal,
        sellVal,
        netFlow: buyVal - sellVal,
        sentiment: (buyVal - sellVal) > 5000000 ? 'ACCUMULATION' : (sellVal - buyVal) > 5000000 ? 'DISTRIBUTION' : 'BALANCED'
      };
    }
  };
})();
