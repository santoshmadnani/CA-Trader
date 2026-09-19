# CA Trader - Formula and Dashboard Specification

## Purpose

This document consolidates the four calculation blocks shown in the uploaded CA Trader Terminal PDF and replaces the internally inconsistent arithmetic with a single, auditable framework for:

1. Dashboard confluence score
2. Pullback entry price
3. Stop-loss / risk budget
4. Target price
5. Risk-reward validation
6. CE/PE symmetry

The goal is not to claim a universally optimal formula. The specification is a robust starting model that keeps the dashboard inputs in the roles they are actually suited for and makes every calculation reproducible.

## Source dashboard snapshot

The uploaded terminal shows NIFTY 23,346.40, NIFTY 23,350 CE CMP 219.46, pullback entry 212.87, stop 192.65, target 253.31 and displayed R:R 1:2.0. It also shows 40 factors with displayed weights summing to 135%, plus a separate displayed consensus of 73.9% bullish.

### Important arithmetic audit

The current popups contain three calculation inconsistencies:

- **Entry:** the displayed formula with Delta 0.52, Spot-VWAP 42, RSI 58.4 and order-flow factor 0.58 gives a discount of about 5.27, so CMP 219.46 would produce about 214.19, not 212.87.
- **Stop:** the displayed formula uses `max(34.53, 27.16) * 1.138 + 0.40`, which is about 39.70 of option premium risk, not the displayed 20.22.
- **Target:** the displayed target formula shows a catalyst multiplier of about 1.077, but the displayed arithmetic uses exactly 2.0 x risk, giving 253.31.

The revised specification below removes those contradictions by separating **model target**, **risk budget**, and **R:R validation**.

---

## 1. Dashboard confluence score

### 1.1 Normalize all indicator signals

Each factor `i` should produce a signed signal:

```text
s_i in [-1, +1]

+1   = strongly bullish for the selected direction
 0   = neutral / no directional information
-1   = strongly bearish for the selected direction
```

Do not average raw values such as RSI, rupee prices, contracts, percentages and option Greeks directly. Convert each raw input to a comparable bounded signal first.

### 1.2 Normalize the dashboard weights

The dashboard currently displays weights that sum to 135%. Treat those weights as relative weights and normalize them:

```text
w_i* = w_i / SUM(w_i)
```

Therefore the normalized weights always sum to 1.00 (100%). This preserves the relative importance already encoded in the dashboard without inventing a new weighting scheme.

### 1.3 Weighted confluence

```text
ConfluenceScore = SUM(w_i* x s_i)
```

Convert to a dashboard percentage only for presentation:

```text
BullishPercent = 50 x (ConfluenceScore + 1)
BearishPercent = 100 - BullishPercent
```

This prevents the current display from mixing a **135% weight total** with a **73.9% directional consensus**.

### 1.4 Reliability / freshness adjustment

A factor that is stale, missing, low-liquidity or unverified should contribute less:

```text
EffectiveWeight_i = w_i* x Reliability_i x Freshness_i
```

Re-normalize effective weights before calculating the score. Keep `Reliability_i` and `Freshness_i` in [0,1].

---

## 2. Direction gate before any CE/PE trade

Calculate the directional score separately for CE and PE.

For CE:

```text
Score_CE = ConfluenceScore
```

For PE:

```text
Score_PE = -ConfluenceScore
```

Suggested **starting gates for backtesting** (not universal constants):

```text
Trade allowed only if:
    abs(ConfluenceScore) >= 0.20
AND liquidity/spread checks pass
AND DTE / expiry checks pass
AND target feasibility check passes
```

Avoid using a single high-level bullish percentage as the trade trigger. A trade needs both **directional agreement** and **acceptable execution/risk geometry**.

---

## 3. Pullback entry formula

### 3.1 Estimate the underlying pullback distance

For a CE setup, define:

```text
VWAPGap = max(Spot - VWAP, 0)
```

For a PE setup, use:

```text
VWAPGap = max(VWAP - Spot, 0)
```

Convert the gap into option-price units using Delta and include a volatility-based component:

```text
BasePullbackOption = a_vwap x abs(Delta) x VWAPGap
                    + a_atr x ATR_opt
                    + NoiseBuffer
```

Then adapt it to the directional confluence score:

```text
PullbackFactor = clip(1 - lambda x abs(ConfluenceScore), F_min, F_max)
```

The idea is simple: when directional/trend confluence is strong, do not force an unnecessarily deep limit price; when confluence is weaker, require more price improvement.

### 3.2 Translate to the option entry

```text
Entry = CMP - BasePullbackOption x PullbackFactor
Entry = clip(Entry, LowerPriceBound, UpperPriceBound)
```

A practical implementation can use:

```text
LowerPriceBound = max(Bid, 0.90 x CMP)
UpperPriceBound = min(CMP, Ask)
```

Use the real bid/ask/mid instead of LTP whenever available.

### 3.3 Optional Greek refinement

For a small underlying pullback `dS`:

```text
dOption ~= Delta x dS + 0.5 x Gamma x dS^2 + Vega x dIV - abs(Theta) x dt
```

For a downward CE pullback, `dS` is negative. This Taylor approximation is preferable to blindly multiplying several unrelated percentages together, provided the move is sufficiently small for the approximation to remain reasonable.

---

## 4. Stop-loss / risk-budget formula

The stop should represent **invalidation risk**, not simply a fixed percentage of premium.

### 4.1 Structural risk in option-price units

For CE:

```text
D_invalidation = max(Spot - Support, 0)
```

For PE:

```text
D_invalidation = max(Resistance - Spot, 0)
```

Then:

```text
StructuralRisk = abs(Delta) x D_invalidation
VolatilityRisk = k_atr x ATR_opt
RawRisk = max(StructuralRisk, VolatilityRisk)
```

### 4.2 Volatility and execution buffer

Use an IV/volatility multiplier only as a bounded buffer:

```text
VolMultiplier = clip(IV / IV_reference, 0.90, 1.25)

RiskBeforeCap = RawRisk x VolMultiplier + NoiseBuffer
```

### 4.3 Risk cap

A hard cap avoids absurdly wide stops when the structural level is far away:

```text
RiskBudget = min(RiskBeforeCap, MaxRiskPct x Entry)
```

Then:

```text
CE Stop = Entry - RiskBudget
PE Stop = Entry + RiskBudget
```

A reasonable starting test range for `MaxRiskPct` is 8%-12% of option premium. Calibrate with out-of-sample results rather than treating one value as universally correct.

### 4.4 Key correction to the current dashboard

The current screenshot's displayed stop arithmetic does not reconcile with its own formula. The revised version should always show:

```text
StructuralRisk
VolatilityRisk
RiskBeforeCap
RiskCap
FinalRiskBudget
Stop
```

That makes the stop reproducible and auditable.

---

## 5. Target-price formula

Do not hard-code `2 x risk` and call the result the model target. First estimate a plausible underlying move and option repricing, then use R:R as a feasibility filter.

### 5.1 Underlying target move

For CE:

```text
D_target = max(0, Resistance - Spot)
```

For PE:

```text
D_target = max(0, Spot - Support)
```

Cap the move using ATR:

```text
D_target_capped = min(D_target, k_target_atr x ATR_underlying)
```

### 5.2 Option target using Greeks

```text
dOption_target ~= Delta x D_target_capped
                  + 0.5 x Gamma x D_target_capped^2
                  + Vega x ExpectedIVChange
                  - abs(Theta) x ExpectedTimeElapsed
```

Then:

```text
ModelTarget = Entry + dOption_target
```

For an even simpler production version where full Greek projection is not trusted:

```text
ModelTarget = Entry + abs(Delta) x D_target_capped
```

and treat Gamma/Vega/Theta as second-order adjustments.

### 5.3 2R target as a validation floor

```text
MinimumTarget = Entry + RR_min x RiskBudget
```

For a 1:2 requirement:

```text
RR_min = 2.0
MinimumTarget = Entry + 2 x RiskBudget
```

A trade passes only when the modeled target is high enough:

```text
TargetFeasible = ModelTarget >= MinimumTarget
```

If not, the correct output is **NO TRADE / WAIT**, not a mathematically forced target.

---

## 6. Risk-reward formula

```text
Risk  = abs(Entry - Stop)
Reward = abs(Target - Entry)
R:R = Reward / Risk
```

If the model uses dynamic targets, the dashboard must display the **actual computed R:R**, not a hard-coded 2.0.

Recommended display:

```text
R:R = 1 : 2.15
```

rather than claiming `1 : 2.0` when the target formula contains a multiplier that changes the reward.

---

## 7. Dashboard factor map (all visible source factors)

| Dashboard factor | Primary role | Used in |
|---|---|---|
| Underlying Spot Price | Price anchor | Entry, Stop, Target |
| Strike Price & Moneyness | Contract selection | Candidate filter |
| Time to Expiry | Time-value / execution risk | Entry, Stop, Target |
| Delta | Spot-to-option translation | Entry, Stop, Target |
| Gamma | Convexity adjustment | Entry, Target |
| Theta | Time decay | Entry, Target |
| Vega | IV sensitivity | Entry, Stop, Target |
| Implied Volatility | Volatility regime | Entry, Stop |
| Volatility Skew & Surface | Relative IV context | Direction filter / Entry |
| Gamma Exposure (GEX) | Dealer positioning | Direction / volatility regime |
| Order Flow Delta Volume | Immediate demand/supply | Entry, Direction |
| Liquidity & Spread | Execution quality | Entry / hard gate |
| Option Trading Volume | Participation | Direction / confidence |
| Open Interest (OI) Walls | Structural positioning | Target / Direction |
| Change in OI | Position build-up | Direction |
| Put-Call Ratio | Cross-option positioning | Direction |
| Dealer Delta Hedging | Mechanical flow | Direction / Entry |
| ADX / MACD | Trend strength | Direction / Entry factor |
| VWAP | Intraday fair-value anchor | Entry |
| RVOL | Participation / expansion | Direction / Entry |
| Clustered Support & Resistance | Invalidation / target | Stop / Target |
| RSI Momentum & Divergence | Momentum state | Entry / Direction |
| ATR Realized Volatility | Move-size estimate | Stop / Target |
| Benchmark Index Dominance | Market regime | Direction |
| Sector Rotation | Cross-sectional regime | Direction |
| Global Markets & GIFT cues | Overnight macro context | Direction |
| Currency Swings | Macro sensitivity | Context / Direction |
| Commodity Prices | Macro regime | Context / Direction |
| Economic Data | Macro regime | Context / Direction |
| Central Bank Policy & Repo Rate | Macro regime | Context |
| Institutional Flows | Capital-flow regime | Direction |
| Futures Basis & Roll Spread | Derivative positioning | Direction |
| Short Interest & Squeeze Ratio | Positioning risk | Direction / Risk |
| Consensus Earnings Estimates | Event context | Context |
| Earnings Beat / Miss | Event catalyst | Direction / Target |
| Management Commentary & Capex | Forward guidance | Context |
| T-Bill & 10Y Sovereign Yield | Discount-rate / macro context | Context |
| Dividend Yield & Ex-Dates | Option adjustment context | Target / Event filter |
| Corporate Actions | Contract / event adjustment | Hard event filter |
| CA AI Live News Intelligence | Event sentiment | Direction / Target |
| Market Sentiment & Breadth | Broad risk appetite | Direction |

The PDF UI shows an `All (40)` counter and 22 in-app live + 18 exchange/macro verified factors, but the supplied two-page PDF visibly contains two additional rows on page 2: `CA AI Live News Intelligence` and `Market Sentiment & Breadth`. The map above therefore covers all visible factor rows rather than silently dropping those two rows. The model should preserve source labels and feed provenance for auditability.

---

## 8. Recommended production architecture

### Layer A - Data quality

```text
Feed -> freshness check -> missing-value check -> sanity check -> normalized signal
```

### Layer B - Direction

```text
40 factor signals
    -> normalized weights
    -> ConfluenceScore in [-1,+1]
    -> CE/PE directional gate
```

### Layer C - Entry timing

```text
ConfluenceScore
+ VWAP distance
+ order flow
+ ATR
+ option spread
+ Greeks
    -> Pullback distance
    -> Limit Entry
```

### Layer D - Risk

```text
Support/Resistance
+ Delta
+ ATR_opt
+ IV
+ spread/noise
    -> capped RiskBudget
    -> Stop
```

### Layer E - Reward

```text
Resistance/Support
+ ATR_underlying
+ Delta/Gamma/Vega/Theta
    -> ModelTarget
    -> MinimumTarget (2R or configurable)
    -> Target feasibility gate
```

### Layer F - Final state

```text
IF direction gate passes
AND liquidity gate passes
AND risk cap passes
AND ModelTarget >= MinimumTarget
THEN
    output trade setup
ELSE
    output WAIT / NO TRADE
```

---

## 9. Dashboard fields to show for every setup

### Required

```text
Direction score
Data quality / freshness
CMP / Bid / Ask / Mid
Pullback Entry
Entry discount
Structural distance to invalidation
ATR_opt
RiskBudget
Stop
ModelTarget
2R MinimumTarget
Actual R:R
Target feasibility: PASS / FAIL
Liquidity: PASS / FAIL
```

### Recommended transparency fields

```text
Top 5 positive contributors
Top 5 negative contributors
Largest weight groups
Current volatility regime
Reason for entry adjustment
Reason for stop width
Reason target is capped
```

### Replace ambiguous labels

Instead of:

```text
135% BULLISH
Optimal Institutional Quality
```

use:

```text
Weighted factor mass: 100% (normalized)
Directional score: +0.478
Bullish probability-style display: 73.9%  [presentation only]
```

Do not present a normalized score as a literal probability unless it has been statistically calibrated to an observed event frequency.

---

## 10. Worked audit using the screenshot values

The source screenshot shows approximately:

```text
Spot          = 23,346.40
VWAP          = 23,304.40
CE CMP        = 219.456
Delta         = 0.52
RSI           = 58.4
Order flow    = 58.4% buyers
Support       = 23,280
Resistance    = 23,420
ATR_opt       = 18.73
IV            = 13.8%
Entry shown   = 212.87
Stop shown    = 192.65
Target shown  = 253.31
```

The source dashboard's own displayed formula arithmetic does not reproduce all three shown prices. The revised framework therefore treats the displayed 212.87 / 192.65 / 253.31 values as **example UI outputs**, not as mathematical ground truth.

For production, each popup should print the exact formula inputs and intermediate values used to produce the final price.

---

## 11. Backtesting and calibration requirements

No coefficient in this document should be assumed optimal merely because it looks sensible.

Calibrate using:

```text
in-sample training set
-> walk-forward validation
-> out-of-sample test
-> regime split (low/normal/high volatility)
-> expiry/DTE split
-> slippage + spread + brokerage + taxes
```

Track at minimum:

```text
Win rate
Average R
Median R
Profit factor
Maximum drawdown
Expectancy
Slippage-adjusted expectancy
Signal frequency
Missed-trade rate due to limit entry
Stop-out rate before target
Target feasibility pass rate
```

The dashboard should retain the raw factor snapshot for every signal so that later model calibration can identify which factors are actually adding information.

---

## 12. Final formula set (compact production version)

### Direction

```text
w_i* = w_i / SUM(w_i)
Score = SUM(w_i* x s_i x Reliability_i x Freshness_i)
(re-normalize effective weights)
```

### Entry

```text
D_entry = clip(
    a_vwap x abs(Delta) x VWAPGap
  + a_atr  x ATR_opt
  + NoiseBuffer,
    D_min, D_max
)

Entry = CMP - D_entry x clip(1 - lambda x abs(Score), F_min, F_max)
```

### Stop

```text
StructuralRisk = abs(Delta) x D_invalidation
VolatilityRisk = k_atr x ATR_opt
RiskBeforeCap = max(StructuralRisk, VolatilityRisk) x VolMultiplier + NoiseBuffer
RiskBudget = min(RiskBeforeCap, MaxRiskPct x Entry)

CE Stop = Entry - RiskBudget
PE Stop = Entry + RiskBudget
```

### Target

```text
D_target = min(distance_to_structure, k_target_atr x ATR_underlying)

ModelTarget = Entry
            + abs(Delta) x D_target
            + 0.5 x Gamma x D_target^2
            + Vega x ExpectedIVChange
            - abs(Theta) x ExpectedTimeElapsed
```

### R:R gate

```text
Risk = abs(Entry - Stop)
Reward = abs(ModelTarget - Entry)
RR = Reward / Risk

Trade allowed only if RR >= RR_min
```

For a 2R policy:

```text
RR_min = 2.0
```

This is the cleanest separation of concerns: **the dashboard estimates direction, the entry model estimates execution price, the stop model estimates risk, and the target model estimates reward. R:R validates the setup rather than manufacturing the target.**

---

## Source

Prepared from the uploaded **CA Trader - Terminal2.pdf**, especially the dashboard and metric blocks on pages 1-2.
