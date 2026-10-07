# Operator Mimic Engine (StockMantra Reverse-Engineer Sentinel)

## Role & Mandate
The **Operator Mimic Engine** is an autonomous real-time sentinel dedicated to reverse-engineering institutional advisory signals broadcast on `@stockmantraindex` (Stock Mantra Index) in Telegram. 

Its mission is to adjust CA-Trader's internal quantitative indicators, weights, and rationale formulas so that **our native algorithmic engine predicts the exact same signals, entries, targets, and stop-losses independently**, with 0 reliance on external feeds.

---

## Autonomous Trigger Protocol
1. **Event Source**: Listens to the continuous MTProto / Telethon stream on `@stockmantraindex` via `_stockmantra_live_telethon_loop()` in `app.py`.
2. **Signal Parsing**:
   - Underlying (`NIFTY`, `BANKNIFTY`, `SENSEX`, `FINNIFTY`)
   - Strike & Option Type (`CE` / `PE`)
   - Entry Price, Target 1, Target 2, Stop-Loss
   - If Target or SL are omitted by the operator:
     - Target is calculated dynamically from target achieved or `entry * 1.20`.
     - Stop-Loss is bounded at `entry * 0.90`.
3. **Formula Re-Calibration**:
   - Calculates the exact Risk-to-Reward ratio ($R:R$).
   - Re-tunes internal parameters:
     - `adx_threshold`
     - `vwap_pullback_pct`
     - `target_multiplier`
     - `sl_buffer_pct`
     - `orderflow_imbalance_ratio`
   - Updates the recommendation rationale so CA-Trader's native model outputs this setup independently.
4. **Mobile Dispatch**:
   - Pushes an immediate HTML alert to the trader's Telegram chat via `send_telegram_msg`.
   - Logs the adaptation to `OPERATOR_MIMIC_STATE` and SQLite.

---

## Zero-Token Compliance
- The reverse-engineering parser runs in pure Python on the Oracle Cloud VM 24/7.
- Zero LLM tokens consumed during routine signal ingestion and formula adaptation.
- Antigravity AI is engaged only if concordance drops below 95%.
