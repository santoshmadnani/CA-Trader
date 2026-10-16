"""Economic calendar: scheduled events that move markets (CPI, jobs, central-bank decisions and speeches, crude and
gas inventories, and speeches by the US President when they are scheduled).

Source: the public weekly calendar feed published by ForexFactory (faireconomy.media). It covers the major currencies
(USD, EUR, GBP, JPY, CNY, AUD, CAD, CHF, NZD), not India. It is fetched at most once an hour by the server and the last
good copy is kept on disk, so a feed outage never empties the calendar. Times are converted to IST for display.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from backend.services import news_topics as NT

log = logging.getLogger("ca-trader.calendar")
IST = timezone(timedelta(hours=5, minutes=30))
FEEDS = ("https://nfs.faireconomy.media/ff_calendar_thisweek.json", "https://nfs.faireconomy.media/ff_calendar_nextweek.json")
CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "econ_calendar_cache.json"
TTL_S = 3600
_STATE: dict[str, Any] = {"at": 0.0, "events": [], "source_ok": None}
_LOCK = threading.Lock()

_SPEECH = re.compile(r"speaks|testif|press conference|remarks|address|speech", re.I)
_RATE = re.compile(r"rate decision|rate statement|fomc|monetary policy|policy rate|cash rate|official bank rate|main refinancing", re.I)
_LEADER = re.compile(r"\btrump\b|^(?:us\s+)?president\b", re.I)   # "President Trump Speaks"; not "ECB President Lagarde Speaks"


def _kind(title: str) -> str:
    if _LEADER.search(title):
        return "leader"
    if _RATE.search(title):
        return "rates"
    if _SPEECH.search(title):
        return "speech"
    return "data"


def _normalize(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for e in raw or []:
        try:
            t = datetime.fromisoformat(str(e.get("date"))).astimezone(timezone.utc)
        except Exception:
            continue
        title, ccy = str(e.get("title") or "").strip(), str(e.get("country") or "").upper()
        if not title:
            continue
        out.append({"id": hashlib.sha1(f"{title}|{ccy}|{t.isoformat()}".encode()).hexdigest()[:12], "title": title, "currency": ccy,
                    "time": t.isoformat(), "impact": str(e.get("impact") or "").title() or "Low", "forecast": e.get("forecast") or None,
                    "previous": e.get("previous") or None, "actual": e.get("actual") or None, "kind": _kind(title)})
    out.sort(key=lambda x: x["time"])
    return out


def _load_disk() -> list[dict[str, Any]]:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8")).get("events") or []
    except Exception:
        return []


def events(force: bool = False) -> list[dict[str, Any]]:
    """All events this week and next (when published), refreshed at most hourly, falling back to the last good copy."""
    with _LOCK:
        if not force and _STATE["events"] and time.time() - _STATE["at"] < TTL_S:
            return _STATE["events"]
        merged: dict[str, dict[str, Any]] = {}
        ok = False
        for url in FEEDS:
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "CA-Trader/1.0 (+https://catrader.site)"})
                if r.status_code == 200:
                    for ev in _normalize(r.json()):
                        merged[ev["id"]] = ev
                    ok = True
            except Exception as exc:
                log.info("calendar feed %s failed: %s", url, exc)
        if ok and merged:
            evs = sorted(merged.values(), key=lambda x: x["time"])
            try:
                CACHE_PATH.write_text(json.dumps({"saved": datetime.now(timezone.utc).isoformat(), "events": evs}), encoding="utf-8")
            except Exception:
                pass
        else:
            evs = _STATE["events"] or _load_disk()
        _STATE.update(at=time.time(), events=evs, source_ok=ok)
        return evs


# ------------------------------------------------------------------ relevance per instrument
def relevance(symbol: str, ev: dict[str, Any]) -> str | None:
    """Why an event matters for `symbol`, or None. High-impact US data moves everything; commodity-specific reports
    matter for that commodity whatever their impact rating; scheduled US President speeches matter for all."""
    title, ccy, imp = ev["title"], ev["currency"], ev["impact"]
    if imp == "Holiday":
        return f"{ccy} market holiday" if ccy in ("USD", "CNY") else None
    if ev["kind"] == "leader":
        return "US President on the record: headline risk for tariffs, oil and risk appetite"
    prof = NT.profile(symbol)
    if prof:
        cw = prof.get("calendar_words")
        if cw and re.search(cw, title, re.I):
            return f"Moves {prof['label'].lower()} directly"
        if ccy == "USD" and imp == "High":
            return "High-impact US event: moves the dollar, which prices this commodity"
        if prof["key"] in ("GOLD", "SILVER") and ccy == "USD" and imp == "Medium" and ev["kind"] in ("speech", "rates"):
            return "Fed speaker: rate expectations drive precious metals"
        if ccy == "CNY" and imp in ("High", "Medium") and prof["key"] in ("CRUDEOIL", "BASEMETALS", "SILVER"):
            return "China data: demand signal for commodities"
        return None
    if ccy == "USD" and imp == "High":
        return "High-impact US event: moves global risk appetite, FII flows and the rupee"
    if ccy == "CNY" and imp == "High":
        return "China data: moves Asian markets and metals"
    if imp == "High" and ev["kind"] == "rates":
        return f"{ccy} central-bank decision"
    return None


def for_symbol(symbol: str, *, scope: str = "relevant", hours_back: float = 12, days_ahead: float = 8) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    lo, hi = now - timedelta(hours=hours_back), now + timedelta(days=days_ahead)
    evs = events()
    out = []
    for ev in evs:
        t = datetime.fromisoformat(ev["time"])
        if not (lo <= t <= hi):
            continue
        why = relevance(symbol, ev)
        if scope == "relevant" and not why:
            continue
        out.append({**ev, "why": why, "time_ist": t.astimezone(IST).isoformat(), "minutes_away": round((t - now).total_seconds() / 60)})
    return {"symbol": symbol, "scope": scope, "events": out, "source": "ForexFactory weekly calendar feed", "source_ok": _STATE.get("source_ok"),
            "covers": "USD, EUR, GBP, JPY, CNY, AUD, CAD, CHF, NZD (no Indian events)", "timestamp": now.isoformat()}


def risk_near(symbol: str, at: datetime | None = None, before_min: int = 30, after_min: int = 15) -> dict[str, Any] | None:
    """The nearest high-impact (or commodity-specific) relevant event from `after_min` ago to `before_min` ahead."""
    at = at or datetime.now(timezone.utc)
    best = None
    for ev in events():
        t = datetime.fromisoformat(ev["time"])
        mins = (t - at).total_seconds() / 60
        if mins < -after_min or mins > before_min:
            continue
        why = relevance(symbol, ev)
        if not why or ev["impact"] == "Holiday" or (ev["impact"] != "High" and ev["kind"] != "leader" and not why.startswith("Moves ")):
            continue
        if best is None or abs(mins) < abs(best["minutes_away"]):
            best = {"title": ev["title"], "currency": ev["currency"], "impact": ev["impact"], "time": ev["time"], "minutes_away": round(mins), "why": why}
    return best
