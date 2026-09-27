"""CA Trader runtime guardrails.

Loaded automatically by Python's site initialization. This module waits for the
CA Trader application module and applies small, isolated production guardrails
without modifying the large monolithic app.py file.
"""
from __future__ import annotations

import asyncio
import importlib
import re
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any

_PATCHED = False
_IST = timezone(timedelta(hours=5, minutes=30))
_MCX_ROOTS = {"CRUDEOIL", "GOLD", "SILVER", "NATURALGAS", "COPPER", "ZINC", "LEAD", "ALUMINIUM"}


def _norm_expiry(value: Any) -> str:
    s = str(value or "").strip().upper()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%d %b %Y").upper()
        except Exception:
            pass
    m = re.search(r"(\d{1,2})\s*[- ]\s*([A-Z]{3,9})\s*[- ]\s*(20\d{2})", s)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)[:3]} {m.group(3)}", "%d %b %Y").strftime("%d %b %Y").upper()
        except Exception:
            pass
    return s


def _expiry_date(value: Any):
    s = _norm_expiry(value)
    try:
        return datetime.strptime(s, "%d %b %Y").date()
    except Exception:
        return None


def _live_mcx_chain(mod, underlying: str, expiry: str | None = None) -> dict[str, Any]:
    root = mod.extract_root_symbol(underlying).upper()
    if root not in _MCX_ROOTS:
        return mod._CA_ORIGINAL_GENERATE_OPTION_CHAIN(underlying, expiry)

    cache_key = f"live-mcx-chain:{root}:{_norm_expiry(expiry) or 'nearest'}"
    cached = mod.CACHE.get(cache_key)
    if cached is not None:
        return cached

    payload = mod.UPSTOX.search_instruments(root, exchanges="MCX", segments="ALL")
    rows = payload.get("data") or []
    opts = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        typ = str(row.get("instrument_type") or "").upper()
        if typ not in {"CE", "PE"}:
            continue
        fif str(row.get("segment") or "").upper() not in {"MCX_FO", "MCX"}:
            continue
