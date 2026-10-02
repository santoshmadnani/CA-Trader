#!/usr/bin/env python3
"""
Recommendation Model Random Dates & Time Validation Engine
Tests CA Trader recommendation model across random historical timestamps,
validating logical consistency, risk-reward ratios, confidence scores,
and point-in-time forward walk-forward outcomes.
"""

import sys
import json
import random
from pathlib import Path
from datetime import datetime

# Ensure project root is in python path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

import app

def run_random_reco_validation(num_tests: int = 25, seed: int = 42) -> dict[str, any]:
    random.seed(seed)
    cache_file = WORKSPACE_ROOT / "data" / "candles_cache.json"
    if not cache_file.exists():
        raise FileNotFoundError(f"Missing {cache_file}")

    with open(cache_file, "r", encoding="utf-8") as f:
        cache = json.load(f)

    test_keys = ["NIFTY:5m", "NIFTY:15m", "BANKNIFTY:5m", "BANKNIFTY:15m", "CRUDEOIL:5m", "RELIANCE:5m", "RELIANCE:15m"]
    available_keys = [k for k in test_keys if k in cache and len(cache[k]) >= 50]
    if not available_keys:
        available_keys = [k for k, v in cache.items() if len(v) >= 50]

    results = []
    wins = 0
    losses = 0
    neutral_or_no_trade = 0
    consistencies = 0

    print("=" * 95)
    print(" CA TRADER - RECOMMENDATION MODEL RANDOM DATES & TIME TEST SUITE")
    print("=" * 95)
    print(f"{'#':<3} | {'Symbol:TF':<14} | {'Cutoff Timestamp':<20} | {'Signal':<7} | {'Entry':<8} | {'Target':<8} | {'SL':<8} | {'Conf':<5} | {'Outcome'}")
    print("-" * 95)

    for test_idx in range(1, num_tests + 1):
        key = random.choice(available_keys)
        symbol, tf = key.split(":")
        all_candles = cache[key]

        min_idx = 30
        max_idx = len(all_candles) - 10
        if max_idx <= min_idx:
            continue

        cutoff_idx = random.randint(min_idx, max_idx)
        past_candles = all_candles[:cutoff_idx]
        future_candles = all_candles[cutoff_idx:cutoff_idx + 15]
        cutoff_ts = (past_candles[-1].get("timestamp") or f"Index {cutoff_idx}")[:19].replace("T", " ")

        reco = app.overall_recommendation(
            symbol=symbol,
            timeframe=tf,
            candles_override=past_candles
        )

        action = str(reco.get("recommendation") or reco.get("action") or "NO_TRADE").upper()
        signal = str(reco.get("signal") or action).upper()
        entry = float(reco.get("entry") or past_candles[-1].get("close") or 0.0)
        target = float(reco.get("target") or 0.0)
        sl = float(reco.get("stop_loss") or 0.0)
        conf = float(reco.get("confidence") or 0.0)

        is_consistent = True
        if "BUY" in action:
            if not (target > entry and entry > sl):
                is_consistent = False
        elif "SELL" in action:
            if not (target < entry and entry < sl):
                is_consistent = False

        if is_consistent:
            consistencies += 1

        outcome = "NO_TRADE"
        if "BUY" in action and is_consistent and target > 0 and sl > 0:
            hit_target = False
            hit_sl = False
            for fc in future_candles:
                f_high = float(fc.get("high") or fc.get("close") or 0.0)
                f_low = float(fc.get("low") or fc.get("close") or 0.0)
                if f_high >= target:
                    hit_target = True
                    break
                if f_low <= sl:
                    hit_sl = True
                    break
            if hit_target:
                outcome = "WIN (Target)"
                wins += 1
            elif hit_sl:
                outcome = "LOSS (SL)"
                losses += 1
            else:
                outcome = "OPEN (In Progress)"
        elif "SELL" in action and is_consistent and target > 0 and sl > 0:
            hit_target = False
            hit_sl = False
            for fc in future_candles:
                f_high = float(fc.get("high") or fc.get("close") or 0.0)
                f_low = float(fc.get("low") or fc.get("close") or 0.0)
                if f_low <= target:
                    hit_target = True
                    break
                if f_high >= sl:
                    hit_sl = True
                    break
            if hit_target:
                outcome = "WIN (Target)"
                wins += 1
            elif hit_sl:
                outcome = "LOSS (SL)"
                losses += 1
            else:
                outcome = "OPEN (In Progress)"
        else:
            neutral_or_no_trade += 1
            outcome = "FILTERED / NEUTRAL"

        results.append({
            "test": test_idx,
            "symbol": symbol,
            "timeframe": tf,
            "timestamp": cutoff_ts,
            "action": action,
            "entry": entry,
            "target": target,
            "stop_loss": sl,
            "confidence": conf,
            "is_consistent": is_consistent,
            "outcome": outcome
        })

        print(f"{test_idx:<3} | {key:<14} | {cutoff_ts:<20} | {signal:<7} | {entry:<8.2f} | {target:<8.2f} | {sl:<8.2f} | {conf:<5.1f} | {outcome}")

    total_resolved = wins + losses
    win_rate = (wins / total_resolved * 100.0) if total_resolved > 0 else 0.0
    consistency_rate = (consistencies / len(results) * 100.0) if results else 0.0

    print("=" * 95)
    print(" SUMMARY PERFORMANCE & RESILIENCY METRICS:")
    print(f" Total Random Slices Tested : {len(results)}")
    print(f" Mathematical Consistency   : {consistency_rate:.1f}% ({consistencies}/{len(results)})")
    print(f" Resolved Simulated Trades  : {total_resolved} (Wins: {wins}, Losses: {losses})")
    print(f" Win Rate on Resolved Trades: {win_rate:.1f}%")
    print(f" Neutral / Filtered Trades  : {neutral_or_no_trade}")
    print("=" * 95)

    return {
        "total_tests": len(results),
        "consistency_rate": consistency_rate,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "neutral_count": neutral_or_no_trade
    }

if __name__ == "__main__":
    count = 25
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        count = int(sys.argv[1])
    run_random_reco_validation(num_tests=count)

