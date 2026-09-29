/**
 * Feature 3 POC: Real-time Orderflow Imbalance & Delta Footprint Matrix
 * Computes bid/ask volume clusters, cumulative volume delta (CVD), and trapped buyer/seller signals.
 */
(function() {
  'use strict';

  window.OrderflowFootprintEngine = class {
    constructor() {
      this.bars = [];
      this.cumulativeDelta = 0;
      this.imbalanceThreshold = 3.0; // 300% bid/ask volume imbalance ratio
    }

    processTick(price, qty, side) {
      if (!this.currentBar) {
        this.currentBar = {
          startTime: Date.now(),
          priceLevels: {},
          totalVolume: 0,
          barDelta: 0
        };
      }

      const pKey = price.toFixed(1);
      if (!this.currentBar.priceLevels[pKey]) {
        this.currentBar.priceLevels[pKey] = { bidVol: 0, askVol: 0, delta: 0 };
      }

      const lvl = this.currentBar.priceLevels[pKey];
      if (side === 'BUY' || side === 'BID') {
        lvl.askVol += qty; // Aggressive buy lifts ask
        lvl.delta += qty;
        this.currentBar.barDelta += qty;
        this.cumulativeDelta += qty;
      } else {
        lvl.bidVol += qty; // Aggressive sell hits bid
        lvl.delta -= qty;
        this.currentBar.barDelta -= qty;
        this.cumulativeDelta -= qty;
      }
      this.currentBar.totalVolume += qty;

      // Identify trapped traders & imbalances
      lvl.isBuyImbalance = lvl.askVol > (lvl.bidVol * this.imbalanceThreshold) && lvl.askVol > 500;
      lvl.isSellImbalance = lvl.bidVol > (lvl.askVol * this.imbalanceThreshold) && lvl.bidVol > 500;

      return {
        price,
        barDelta: this.currentBar.barDelta,
        cumulativeDelta: this.cumulativeDelta,
        isBuyImbalance: lvl.isBuyImbalance,
        isSellImbalance: lvl.isSellImbalance
      };
    }

    closeBar() {
      if (this.currentBar) {
        this.bars.push(this.currentBar);
        this.currentBar = null;
      }
    }
  };
})();
