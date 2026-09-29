/**
 * Feature 4 POC: Multi-Timeframe Confluence Radar (MTC Radar)
 * Synthesizes 1m, 5m, 15m, 1h, and 1D EMA (9/21/50/200), RSI, and Supertrend into a single directional consensus score.
 */
(function() {
  'use strict';

  window.calculateMtcRadarScore = function(multiTfData) {
    // Expected structure: { '1m': { emaBull: true, rsi: 58, stBull: true }, '5m': {...}, ... }
    const timeframes = ['1m', '5m', '15m', '1h', '1d'];
    const weights = { '1m': 0.10, '5m': 0.25, '15m': 0.30, '1h': 0.20, '1d': 0.15 };

    let totalScore = 0;
    const tfScores = {};

    timeframes.forEach(tf => {
      const d = multiTfData?.[tf] || { emaBull: false, rsi: 50, stBull: false };
      let subScore = 50;
      if (d.emaBull) subScore += 25; else subScore -= 25;
      if (d.stBull) subScore += 20; else subScore -= 20;
      if (d.rsi > 55) subScore += Math.min(20, (d.rsi - 50) * 1.5);
      else if (d.rsi < 45) subScore -= Math.min(20, (50 - d.rsi) * 1.5);

      subScore = Math.max(0, Math.min(100, Math.round(subScore)));
      tfScores[tf] = subScore;
      totalScore += subScore * weights[tf];
    });

    const consensusScore = Math.round(totalScore);
    const consensusLabel = consensusScore >= 65 ? 'STRONG BULL' : consensusScore >= 55 ? 'MILD BULL' : consensusScore <= 35 ? 'STRONG BEAR' : consensusScore <= 45 ? 'MILD BEAR' : 'NEUTRAL CONGESTION';

    return {
      consensusScore,
      consensusLabel,
      tfScores,
      isTradeActionable: consensusScore >= 65 || consensusScore <= 35
    };
  };
})();
