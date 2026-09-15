import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
    content = f.read()

# ==============================================================================
# 1. Add populateRecoOptionDropdown and update applyOptionRecommendation
# ==============================================================================

reco_replacement = """  // Populate option strikes dropdown in recommendation box (Release 36)
  function populateRecoOptionDropdown(baseSym, atmStrike, step, selectedOpt){
    const recoSelect = document.getElementById('chartRecoOptionSelect');
    if(!recoSelect) return;
    const currentVal = selectedOpt || recoSelect.value || window.__caPinnedOptionContract || '';
    const isCrude = /CRUDE/i.test(baseSym);
    const expTag = isCrude ? '17 SEP' : (window.__caOptionExpiry || '25 SEP');
    const strikes = [];
    for(let k = -8; k <= 8; k++){
      strikes.push(atmStrike + k * step);
    }

    let optHtml = `<option value="">Auto (Best Option)</option>`;
    let foundCurrent = false;

    strikes.forEach(stk => {
      const cSym = isCrude ? `CRUDEOIL FUT ${expTag} ${stk}CE` : `${baseSym} ${stk} CE`;
      const pSym = isCrude ? `CRUDEOIL FUT ${expTag} ${stk}PE` : `${baseSym} ${stk} PE`;
      const cSel = currentVal === cSym ? ' selected' : '';
      const pSel = currentVal === pSym ? ' selected' : '';
      if(cSel || pSel) foundCurrent = true;
      optHtml += `<option value="${esc(cSym)}"${cSel}>${esc(cSym)} (Call)</option>`;
      optHtml += `<option value="${esc(pSym)}"${pSel}>${esc(pSym)} (Put)</option>`;
    });

    if(currentVal && !foundCurrent){
      optHtml = `<option value="${esc(currentVal)}" selected>${esc(currentVal)} (Selected)</option>` + optHtml;
    }

    recoSelect.innerHTML = optHtml;

    if(!recoSelect.dataset.bound){
      recoSelect.dataset.bound = '1';
      recoSelect.addEventListener('change', async (e) => {
        const chosen = e.target.value;
        if(!chosen) return;
        window.__caPinnedOptionContract = chosen;
        const optSearch = document.getElementById('chartRecoOptionSearch');
        if(optSearch) optSearch.value = chosen;
        let chosenLtp = (window.__CA_WL_QUOTES && window.__CA_WL_QUOTES[chosen]?.ltp) || null;
        if(!chosenLtp){
          try {
            const apiFn = window.A || window.api || (async(u,o={})=>fetch(u,{credentials:'include',...o}).then(r=>r.json()));
            const qr = await apiFn('/api/market/quote/' + encodeURIComponent(chosen));
            if(qr && qr.ltp) chosenLtp = Number(qr.ltp);
          } catch(_) {}
        }
        applyOptionRecommendation(chosen, chosenLtp, baseSym);
      });
    }
  }
  window.populateRecoOptionDropdown = populateRecoOptionDropdown;

  function applyOptionRecommendation(optSym, ltp, underlying, lotSize, userActionInitiated=true){
    const baseSym = underlying || optSym.split(' ')[0].toUpperCase();
    const isCrude = /CRUDE/i.test(baseSym);
    const lot = lotSize || (isCrude ? 100 : (/NATURALGAS/i.test(baseSym) ? 1250 : (/GOLD/i.test(baseSym) ? 100 : (baseSym.includes('BANK') ? 15 : (baseSym.includes('NIFTY') ? 25 : 1)))));
    
    // Determine underlying spot price and ATM strike
    const curLtp = Number(window.state?.latestLive || (window.__CA_WL_QUOTES||{})[baseSym]?.ltp || (window.__CA_WL_QUOTES||{})[baseSym]?.close || 23400);
    const step = baseSym.includes('BANK') ? 100 : (isCrude ? 50 : 50);
    const atmStrike = Math.round(curLtp / step) * step;

    // Populate or sync the dropdown with strikes around ATM
    populateRecoOptionDropdown(baseSym, atmStrike, step, optSym);

    // Determine Underlying Trend & Directional Conviction (Release 36 Item 2)
    const baseAnalysis = (APP_CACHE.recoOverall && APP_CACHE.recoOverall[baseSym]) || window.__caCurrentChartReco || window.__caRecommendation || {};
    const rawAction = String(baseAnalysis.recommendation || baseAnalysis.action || baseAnalysis.signal || '').toUpperCase();
    const rsiVal = Number((state.appliedIndicators && state.indicatorValues?.RSI) || baseAnalysis.evidence?.technical?.rsi || 52);

    let isUnderlyingBull = rawAction.includes('BUY') || rawAction.includes('ACCUMULATE') || rawAction.includes('LONG');
    let isUnderlyingBear = rawAction.includes('SELL') || rawAction.includes('SHORT');
    let isChop = false;

    // Rule: Never give recommendations in both call and put at the same time.
    // If neutral/no-trade, resolve based on technical momentum (do not give NO TRADE every time).
    if(!isUnderlyingBull && !isUnderlyingBear){
      if(rawAction === 'NO_TRADE' || rawAction === 'NEUTRAL'){
        if(rsiVal >= 53 || curLtp > (baseAnalysis.evidence?.technical?.ema20 || curLtp)){
          isUnderlyingBull = true;
        } else if(rsiVal <= 47 || curLtp < (baseAnalysis.evidence?.technical?.ema20 || curLtp)){
          isUnderlyingBear = true;
        } else {
          isChop = true; // True sideways chop
        }
      } else {
        if(rsiVal >= 50) isUnderlyingBull = true;
        else isUnderlyingBear = true;
      }
    }

    // Determine option characteristics: Call (CE) vs Put (PE)
    const isCall = /\\bCE\\b/i.test(optSym) || optSym.toUpperCase().endsWith('CE');
    const isPut = /\\bPE\\b/i.test(optSym) || optSym.toUpperCase().endsWith('PE');

    // Parse Strike Price
    const m = optSym.match(/\\b(\\d+(?:\\.\\d+)?)\\s*(?:CE|PE)?\\b/i);
    const strike = m ? parseFloat(m[1]) : atmStrike;

    // Calculate Moneyness (ITM, ATM, OTM, FAR_OTM)
    let moneyness = 'ATM';
    let isOtm = false;
    let isItm = false;

    if(isCall){
      if(strike >= curLtp + step * 3.5){
        moneyness = 'FAR_OTM'; isOtm = true;
      } else if(strike >= curLtp + step * 1.5){
        moneyness = 'OTM'; isOtm = true;
      } else if(strike <= curLtp - step * 1.5){
        moneyness = 'ITM'; isItm = true;
      } else {
        moneyness = 'ATM';
      }
    } else if(isPut){
      if(strike <= curLtp - step * 3.5){
        moneyness = 'FAR_OTM'; isOtm = true;
      } else if(strike <= curLtp - step * 1.5){
        moneyness = 'OTM'; isOtm = true;
      } else if(strike >= curLtp + step * 1.5){
        moneyness = 'ITM'; isItm = true;
      } else {
        moneyness = 'ATM';
      }
    }

    // Price and Levels Calculation
    let entry = Number(ltp) || 0;
    if(entry <= 0){
      const dist = Math.abs(curLtp - strike);
      if(moneyness === 'ATM') entry = Math.max(15, roundVal(curLtp * 0.007 + 85));
      else if(isOtm) entry = Math.max(6, roundVal(Math.max(10, 115 - (dist / step) * 22)));
      else entry = Math.max(35, roundVal(dist * 0.9 + 55));
    }

    // Realistic Option Buying Target: 14% - 22% gain in 30-45m (≥ ₹500/lot)
    const targetGain = roundVal(Math.max(4.0, Math.min(entry * 0.22, Math.max(entry * 0.14, 500.0 / lot))));
    const tgt = roundVal(entry + targetGain);
    // Stop Loss: 1:1.8 Risk:Reward ratio
    const slDist = roundVal(Math.max(2.0, targetGain / 1.8));
    const sl = roundVal(Math.max(0.05, entry - slDist));
    const risk = Math.abs(entry - sl);
    const reward = Math.abs(tgt - entry);
    const rr = (reward / Math.max(0.01, risk)).toFixed(1);
    const estProfit = Math.round(reward * lot);
    const capitalReq = Math.round(entry * lot);

    // Directional Recommendation & Smart Advisory Evaluation (Release 36 Items 2 & 3)
    let recoAction = 'BUY';
    let qualifies = true;
    let advisoryIcon = '💡';
    let advisoryComment = '';
    let rationale = '';
    let suggestedContract = '';

    if(isUnderlyingBull && isCall){
      // Aligned Call in Bullish Market
      recoAction = 'BUY';
      qualifies = true;
      advisoryIcon = isOtm ? '💡' : '✅';
      if(isOtm){
        advisoryComment = `💡 Budget-Friendly OTM Call Selected: ${optSym} (Capital: ~₹${fmtMoney(capitalReq)}/lot). Trade is aligned with ${baseSym} Bullish market structure. ⚠️ Advisory: Out-of-the-Money options have lower Delta (~0.25-0.35) and faster Theta decay closer to expiry. Do NOT hold for prolonged periods—trail stop loss closely once in profit.`;
        rationale = `OTM Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot, +${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Budget-friendly capital layout (~₹${capitalReq}/lot) accommodating lower funds.`;
      } else if(isItm){
        advisoryComment = `✅ High-Delta ITM Call Selected: ${optSym} (Capital: ~₹${fmtMoney(capitalReq)}/lot). High Delta (~0.65) captures direct underlying trend momentum with lower Theta erosion. Fully aligned with ${baseSym} Bullish trend.`;
        rationale = `ITM Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (+${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Deep intrinsic protection.`;
      } else {
        advisoryComment = `✅ Optimal ATM Call Selected: ${optSym} (Capital: ~₹${fmtMoney(capitalReq)}/lot). Balanced Greeks (Delta ~0.50) with maximum liquidity. High conviction institutional trend following on ${baseSym}.`;
        rationale = `ATM Call Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot, +${Math.round((reward/entry)*100)}%), SL ₹${fmt(sl)} (R:R 1:${rr}). Greeks & intraday momentum aligned.`;
      }
    } else if(isUnderlyingBear && isPut){
      // Aligned Put in Bearish Market
      recoAction = 'BUY';
      qualifies = true;
      advisoryIcon = isOtm ? '💡' : '✅';
      if(isOtm){
        advisoryComment = `💡 Budget-Friendly OTM Put Selected: ${optSym} (Capital: ~₹${fmtMoney(capitalReq)}/lot). Trade is aligned with ${baseSym} Bearish market structure. ⚠️ Advisory: Out-of-the-Money options have lower Delta (~0.25-0.35) and faster Theta decay. Scalp with tight trailing SL aligned with downward trend.`;
        rationale = `OTM Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot), SL ₹${fmt(sl)}. Budget-friendly layout (~₹${capitalReq}/lot) for capital preservation.`;
      } else if(isItm){
        advisoryComment = `✅ High-Delta ITM Put Selected: ${optSym} (Capital: ~₹${fmtMoney(capitalReq)}/lot). High Delta protection capturing downward institutional breakdown with lower time decay sensitivity.`;
        rationale = `ITM Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)}, SL ₹${fmt(sl)}. Strong downward tracking.`;
      } else {
        advisoryComment = `✅ Optimal ATM Put Selected: ${optSym} (Capital: ~₹${fmtMoney(capitalReq)}/lot). Balanced Greeks (Delta -0.50) and high liquidity. Aligned with downward institutional breakdown on ${baseSym}.`;
        rationale = `ATM Put Setup: ${optSym} · Action: BUY · Entry ₹${fmt(entry)}, Target ₹${fmt(tgt)} (Est. +₹${estProfit}/lot), SL ₹${fmt(sl)} (R:R 1:${rr}). High conviction trade.`;
      }
    } else if(isUnderlyingBull && isPut){
      // Counter-Trend Selection: Bullish market, but user selected Put
      recoAction = 'CAUTION (COUNTER-TREND)';
      qualifies = false;
      advisoryIcon = '⚠️';
      suggestedContract = isCrude ? `CRUDEOIL FUT ${expTag} ${atmStrike}CE` : `${baseSym} ${atmStrike} CE`;
      advisoryComment = `⚠️ Counter-Trend Advisory: Market structure for ${baseSym} is strongly Bullish. The algorithm recommends buying a CALL option (${suggestedContract}). You have selected a PUT option (${optSym}). Buying puts against prevailing upward momentum carries elevated risk of rapid capital loss. 💡 Suggestion: Switch to a Call option (${suggestedContract}) to trade in sync with institutional momentum.`;
      rationale = `Counter-Trend Warning: ${baseSym} technical structure is Bullish. Recommended: ${suggestedContract}. You selected Put (${optSym}). Risk elevated against trend momentum.`;
    } else if(isUnderlyingBear && isCall){
      // Counter-Trend Selection: Bearish market, but user selected Call
      recoAction = 'CAUTION (COUNTER-TREND)';
      qualifies = false;
      advisoryIcon = '⚠️';
      suggestedContract = isCrude ? `CRUDEOIL FUT ${expTag} ${atmStrike}PE` : `${baseSym} ${atmStrike} PE`;
      advisoryComment = `⚠️ Counter-Trend Advisory: Market structure for ${baseSym} is Bearish. The algorithm recommends buying a PUT option (${suggestedContract}). You have selected a CALL option (${optSym}). Buying calls against downward momentum carries significant risk. 💡 Suggestion: Switch to a Put option (${suggestedContract}) to trade in sync with market direction.`;
      rationale = `Counter-Trend Warning: ${baseSym} technical structure is Bearish. Recommended: ${suggestedContract}. You selected Call (${optSym}). Risk elevated against trend momentum.`;
    } else if(isChop){
      // Rangebound / Sideways Chop
      recoAction = 'NO TRADE';
      qualifies = false;
      advisoryIcon = '⏸';
      advisoryComment = `⏸ No Favourable Trade: ${baseSym} is currently rangebound in low-volatility consolidation. Option buying in choppy conditions suffers rapid Theta decay without directional payoff. Stand aside until a decisive breakout occurs.`;
      rationale = `No Favourable Trade: ${baseSym} lacks directional breakout momentum. Avoid option buying during sideways chop.`;
    }

    const reco = {
      symbol: optSym,
      display_symbol: optSym,
      underlying: baseSym,
      recommendation: recoAction,
      action: recoAction,
      qualifies: qualifies,
      entry: entry,
      target: tgt,
      stop_loss: sl,
      confidence: qualifies ? 86 : 45,
      risk_reward: rr,
      moneyness: moneyness,
      capital_required: capitalReq,
      advisory: {
        comment: advisoryComment,
        icon: advisoryIcon,
        suggested_sym: suggestedContract,
        suggested_switch: !!suggestedContract,
        moneyness: moneyness
      },
      rationale: rationale,
      instrument: { kind: 'OPTION', symbol: optSym, display: optSym, underlying: baseSym, entry: entry, lot_size: lot }
    };

    window.__caCurrentChartReco = reco;
    renderChartRecoData(reco, optSym);
    showTab('charts');
    const banner = $('chartRecoBanner');
    if(banner){
      banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
      banner.style.boxShadow = qualifies ? '0 0 16px rgba(59,130,246,0.6)' : '0 0 16px rgba(245,158,11,0.6)';
      setTimeout(() => { banner.style.boxShadow = ''; }, 3000);
    }
    if(userActionInitiated){
      toast(`Option recommendation updated for ${optSym}`);
    }
  }
  window.applyOptionRecommendation = applyOptionRecommendation;"""

# Replace the existing applyOptionRecommendation function
pattern_apply = re.compile(
    r"function applyOptionRecommendation\(optSym, ltp, underlying, lotSize\)\{.*?window\.applyOptionRecommendation = applyOptionRecommendation;",
    re.DOTALL
)

if pattern_apply.search(content):
    content = pattern_apply.sub(lambda m: reco_replacement, content, count=1)
    print("Replaced applyOptionRecommendation successfully!")
else:
    print("Could not find applyOptionRecommendation block with regex!")

# ==============================================================================
# 2. Update renderChartRecoData to handle advisory callout box, dropdown & tag
# ==============================================================================

old_render_start = """    const isOption = true;
    const action = qualifies ? 'BUY' : (rawAction === 'NO_TRADE' ? 'NO TRADE' : 'NEUTRAL');

    const actionEl = $('chartRecoAction');
    if(actionEl){
      actionEl.textContent = action;
      actionEl.className = `tag ${action === 'BUY' ? 'buy' : action === 'SELL' ? 'sell' : 'neutral'}`;
      actionEl.style.cursor = 'pointer';
      actionEl.onclick = () => openRecoCalculationModal(rec, 'signal');
    }"""

new_render_start = """    const isOption = true;
    const recAction = String(rec?.action || rec?.recommendation || '').toUpperCase();
    const action = qualifies ? 'BUY' : (recAction.includes('CAUTION') || recAction.includes('COUNTER') ? 'CAUTION (COUNTER-TREND)' : (rawAction === 'NO_TRADE' ? 'NO TRADE' : 'NEUTRAL'));

    const actionEl = $('chartRecoAction');
    if(actionEl){
      actionEl.textContent = action;
      if(action === 'BUY'){
        actionEl.className = 'tag buy';
      } else if(action.includes('CAUTION') || action.includes('COUNTER')){
        actionEl.className = 'tag sell';
      } else {
        actionEl.className = 'tag neutral';
      }
      actionEl.style.cursor = 'pointer';
      actionEl.onclick = () => openRecoCalculationModal(rec, 'signal');
    }"""

if old_render_start in content:
    content = content.replace(old_render_start, new_render_start, 1)
    print("Updated renderChartRecoData actionEl block!")
else:
    print("Could not find old_render_start!")

# Update Advisory Box in renderChartRecoData
old_rationale_block = """    if($('chartRecoRationale')){
      const rat = rec?.rationale || (rec?.evidence?.news?.stock?.reasons || []).join(' · ') || rec?.reason || 'Multi-factor alignment verified across moving average structure, volume confirmation, and news materiality.';
      $('chartRecoRationale').textContent = rat;
      $('chartRecoRationale').onclick = () => openRecoCalculationModal(rec);
      $('chartRecoRationale').style.cursor = 'pointer';
    }"""

new_rationale_block = """    if($('chartRecoRationale')){
      const rat = rec?.rationale || (rec?.evidence?.news?.stock?.reasons || []).join(' · ') || rec?.reason || 'Multi-factor alignment verified across moving average structure, volume confirmation, and news materiality.';
      $('chartRecoRationale').textContent = rat;
      $('chartRecoRationale').onclick = () => openRecoCalculationModal(rec);
      $('chartRecoRationale').style.cursor = 'pointer';
    }

    // Dynamic Prominent Advisory Callout Box (Release 36 Item 3)
    const advBox = $('chartRecoAdvisoryBox');
    const advIcon = $('chartRecoAdvisoryIcon');
    const advText = $('chartRecoAdvisoryText');
    if(advBox && advText){
      const advisory = rec?.advisory || {};
      const msg = advisory.comment || rec?.rationale || 'Consensus levels synchronized.';
      const icon = advisory.icon || (action === 'BUY' ? (rec?.moneyness === 'OTM' ? '💡' : '✅') : (action.includes('CAUTION') ? '⚠️' : '⏸'));
      if(advIcon) advIcon.textContent = icon;
      if(advisory.suggested_switch && advisory.suggested_sym){
        advText.innerHTML = `${esc(msg)} <a href="javascript:void(0)" onclick="applyOptionRecommendation('${esc(advisory.suggested_sym)}', null, '${esc(baseSym)}')" style="color:var(--gold);font-weight:700;margin-left:6px;text-decoration:underline;">Switch to ${esc(advisory.suggested_sym)} ↗</a>`;
      } else {
        advText.textContent = msg;
      }
      advBox.style.display = 'flex';
      if(action.includes('CAUTION') || action.includes('COUNTER')){
        advBox.style.background = 'rgba(239,68,68,0.12)';
        advBox.style.borderColor = 'rgba(239,68,68,0.4)';
      } else if(rec?.moneyness === 'OTM' || rec?.moneyness === 'FAR_OTM'){
        advBox.style.background = 'rgba(245,158,11,0.12)';
        advBox.style.borderColor = 'rgba(245,158,11,0.4)';
      } else if(action === 'BUY'){
        advBox.style.background = 'rgba(16,185,129,0.12)';
        advBox.style.borderColor = 'rgba(16,185,129,0.4)';
      } else {
        advBox.style.background = 'rgba(148,163,184,0.12)';
        advBox.style.borderColor = 'rgba(148,163,184,0.3)';
      }
    }"""

if old_rationale_block in content:
    content = content.replace(old_rationale_block, new_rationale_block, 1)
    print("Updated advisory callout box rendering!")
else:
    print("Could not find old_rationale_block!")

# Update Greeks Moneyness in updateRecommendationRationale
old_moneyness_line = "{ label: 'Moneyness', val: 'ATM (Optimal)', desc: 'Max liquidity strike' },"
new_moneyness_line = """{ label: 'Moneyness', val: reco?.moneyness ? `${reco.moneyness} (${reco.moneyness.includes('OTM') ? 'Budget-Friendly' : reco.moneyness === 'ITM' ? 'Deep Delta' : 'Optimal'})` : 'ATM (Optimal)', desc: reco?.moneyness?.includes('OTM') ? 'Low capital, fast Theta decay' : (reco?.moneyness === 'ITM' ? 'High intrinsic protection' : 'Max liquidity strike') },"""

if old_moneyness_line in content:
    content = content.replace(old_moneyness_line, new_moneyness_line, 1)
    print("Updated Moneyness badge in Recommendation Rationale Row 3!")
else:
    print("Could not find old_moneyness_line!")

with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Finished applying recommendation patch.")
