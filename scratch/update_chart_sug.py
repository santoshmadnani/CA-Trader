with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''@app.get("/api/analysis/chart-ai-suggestions/{instrument}")
async def analysis_chart_ai_suggestions(
    instrument: str,
    timeframe: str = "5m",
    days: int = 7,
    user: dict[str, Any] = Depends(require_user)
) -> dict[str, Any]:
    try:
        d = 30 if timeframe in {"1m", "3m", "5m", "15m"} else 90 if timeframe in {"30m", "60m"} else 365
        d = max(d, days)
        candles = analysis_candles_robust(instrument, timeframe, d)
        if not candles:
            raise ProviderUnavailable("No historical candles returned for this instrument")
        res = detect_chart_ai_suggestions(candles)
        return {
            "instrument": instrument,
            "timeframe": timeframe,
            "days": d,
            "candles_count": len(candles),
            **res,
            "provider": "ca_ai",
            "timestamp": now_iso()
        }
    except Exception as exc:
        return error_json("CHART_AI_SUGGESTIONS_UNAVAILABLE", safe_text(exc), 503)'''

replacement = '''@app.get("/api/analysis/chart-ai-suggestions/{instrument}")
async def analysis_chart_ai_suggestions(
    instrument: str,
    timeframe: str = "5m",
    days: int = 5,
    user: dict[str, Any] = Depends(require_user)
) -> dict[str, Any]:
    sym = instrument.upper()
    cache_key = f"chart-ai-sug:{sym}:{timeframe}:{days}"
    cached = CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        d = min(max(days, 3), 7) if timeframe in {"1m", "3m", "5m", "15m"} else min(max(days, 10), 30)
        candles = analysis_candles_robust(sym, timeframe, d)
        if not candles:
            raise ProviderUnavailable("No historical candles returned for this instrument")
        res = detect_chart_ai_suggestions(candles)
        data = {
            "instrument": sym,
            "timeframe": timeframe,
            "days": d,
            "candles_count": len(candles),
            **res,
            "provider": "ca_ai",
            "timestamp": now_iso()
        }
        CACHE.set(cache_key, data, 60.0)
        return data
    except Exception as exc:
        return error_json("CHART_AI_SUGGESTIONS_UNAVAILABLE", safe_text(exc), 503)'''

if target in text:
    text = text.replace(target, replacement)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Successfully updated analysis_chart_ai_suggestions')
else:
    print('Target not found in app.py')

