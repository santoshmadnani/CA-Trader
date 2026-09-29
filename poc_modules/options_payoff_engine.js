/**
 * Feature 2 POC: Options Strategy Payoff Graph & P&L Visualizer
 * Calculates multi-leg option expiration payoffs, breakevens, and Black-Scholes T+0 curves.
 */
(function() {
  'use strict';

  // Standard Normal CDF approximation
  function normCdf(x) {
    const b1 =  0.319381530;
    const b2 = -0.356563782;
    const b3 =  1.781477937;
    const b4 = -1.821255978;
    const b5 =  1.330274429;
    const p  =  0.2316419;
    const c2 =  0.39894228;
    if (x >= 0.0) {
      const t = 1.0 / (1.0 + p * x);
      return (1.0 - c2 * Math.exp(-x * x / 2.0) * t * (t * (t * (t * (t * b5 + b4) + b3) + b2) + b1));
    } else {
      const t = 1.0 / (1.0 - p * x);
      return (c2 * Math.exp(-x * x / 2.0) * t * (t * (t * (t * (t * b5 + b4) + b3) + b2) + b1));
    }
  }

  // Black-Scholes Theoretical Option Price
  function bsPrice(S, K, T, r, sigma, type) {
    if (T <= 0) {
      return type === 'CE' ? Math.max(0, S - K) : Math.max(0, K - S);
    }
    const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
    const d2 = d1 - sigma * Math.sqrt(T);
    if (type === 'CE') {
      return S * normCdf(d1) - K * Math.exp(-r * T) * normCdf(d2);
    } else {
      return K * Math.exp(-r * T) * normCdf(-d2) - S * normCdf(-d1);
    }
  }

  /**
   * Evaluates a multi-leg option strategy across a price spectrum
   * @param {Array} legs - Array of { strike: number, type: 'CE'|'PE', action: 'BUY'|'SELL', premium: number, qty: number }
   * @param {number} spotPrice - Current spot price
   * @param {number} daysToExpiry - Days remaining
   * @param {number} iv - Implied volatility (e.g. 0.15)
   */
  window.calculateOptionStrategyPayoff = function(legs, spotPrice, daysToExpiry = 4, iv = 0.14) {
    const rangePct = 0.08; // +/- 8% price band
    const minS = Math.round(spotPrice * (1 - rangePct));
    const maxS = Math.round(spotPrice * (1 + rangePct));
    const steps = 60;
    const stepSize = (maxS - minS) / steps;
    const r = 0.065; // RBI repo rate 6.5%
    const T = Math.max(0.001, daysToExpiry / 365.0);

    const pricePoints = [];
    const expiryPayoffs = [];
    const currentPayoffs = [];

    for (let s = minS; s <= maxS; s += stepSize) {
      let expPnl = 0;
      let curPnl = 0;

      legs.forEach(leg => {
        const sign = leg.action === 'BUY' ? 1 : -1;
        const intrinsic = leg.type === 'CE' ? Math.max(0, s - leg.strike) : Math.max(0, leg.strike - s);
        expPnl += sign * (intrinsic - leg.premium) * leg.qty;

        const curVal = bsPrice(s, leg.strike, T, r, iv, leg.type);
        curPnl += sign * (curVal - leg.premium) * leg.qty;
      });

      pricePoints.push(Math.round(s));
      expiryPayoffs.push(Math.round(expPnl));
      currentPayoffs.push(Math.round(curPnl));
    }

    const maxProfit = Math.max(...expiryPayoffs);
    const maxLoss = Math.min(...expiryPayoffs);

    // Compute breakevens
    const breakevens = [];
    for (let i = 0; i < expiryPayoffs.length - 1; i++) {
      if ((expiryPayoffs[i] <= 0 && expiryPayoffs[i+1] > 0) || (expiryPayoffs[i] >= 0 && expiryPayoffs[i+1] < 0)) {
        breakevens.push(pricePoints[i]);
      }
    }

    return {
      pricePoints,
      expiryPayoffs,
      currentPayoffs,
      maxProfit: maxProfit > 1e6 ? 'Unlimited' : maxProfit,
      maxLoss: maxLoss < -1e6 ? 'Unlimited' : maxLoss,
      breakevens,
      riskReward: (maxLoss !== 0 && maxProfit > 0) ? (Math.abs(maxProfit / maxLoss)).toFixed(2) : 'N/A'
    };
  };
})();
