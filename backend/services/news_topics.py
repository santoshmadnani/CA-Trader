"""What news belongs to which instrument.

Indian indices and stocks follow Indian market news plus global macro. Commodities follow their own world: crude oil
news is about OPEC, supply, inventories and the Middle East, not the Nifty. Each profile gives the search queries and
a relevance pattern that every headline must match before it is shown for that instrument.
"""
from __future__ import annotations

import re
from typing import Any

PROFILES: dict[str, dict[str, Any]] = {
    "CRUDEOIL": {
        "label": "Crude oil",
        "query": '"crude oil" OR "oil prices" OR Brent OR WTI OR OPEC OR "oil supply" OR "oil demand"',
        "macro_query": "OPEC+ output Saudi Russia Iran sanctions Middle East oil supply EIA crude inventories refinery shale rig count",
        "words": r"crude|oil|brent|wti|opec|petroleum|refiner|refinery|barrel|bbl|gasoline|diesel|distillate|eia|api inventor|inventor(?:y|ies)|"
                 r"iran|saudi|aramco|russia|urals|hormuz|red sea|houthi|shale|rig count|energy prices|fuel",
    },
    "NATURALGAS": {
        "label": "Natural gas",
        "query": '"natural gas" OR LNG OR "Henry Hub" OR "gas prices" OR "gas storage"',
        "macro_query": "natural gas storage LNG exports Henry Hub weather forecast heating demand Europe gas TTF pipeline",
        "words": r"natural gas|\bgas\b|lng|henry hub|ttf|gas storage|storage report|pipeline|heating|cooling demand|weather|freeze|cold snap|heatwave|"
                 r"hurricane|gulf of mexico|qatar|norway|gazprom",
    },
    "GOLD": {
        "label": "Gold",
        "query": 'gold OR bullion OR "gold prices" OR "precious metals"',
        "macro_query": "gold bullion Fed rate cut Treasury yields dollar index safe haven central bank gold buying ETF flows",
        "words": r"gold|bullion|precious metal|safe[- ]haven|fed\b|federal reserve|fomc|treasury|yield|dollar|dxy|inflation|cpi|rate cut|rate hike|"
                 r"central bank|geopolitic|war|tariff",
    },
    "SILVER": {
        "label": "Silver",
        "query": 'silver OR "silver prices" OR "precious metals" OR bullion',
        "macro_query": "silver precious metals industrial demand solar Fed dollar Treasury yields China manufacturing",
        "words": r"silver|precious metal|bullion|gold|industrial metal|solar|fed\b|federal reserve|fomc|treasury|yield|dollar|dxy|inflation|"
                 r"china|manufacturing|pmi",
    },
    "BASEMETALS": {
        "label": "Base metals",
        "query": 'copper OR aluminium OR aluminum OR zinc OR "base metals" OR LME',
        "macro_query": "copper aluminium zinc LME China demand manufacturing PMI property stimulus smelter",
        "words": r"copper|alumin(?:i)?um|zinc|lead|nickel|base metal|lme|smelter|china|manufacturing|pmi|stimulus|property|construction",
    },
}

_ALIASES = [("CRUDE", "CRUDEOIL"), ("NATGAS", "NATURALGAS"), ("NATURALGAS", "NATURALGAS"), ("GOLD", "GOLD"), ("SILVER", "SILVER"),
            ("COPPER", "BASEMETALS"), ("ALUMIN", "BASEMETALS"), ("ZINC", "BASEMETALS"), ("LEAD", "BASEMETALS"), ("NICKEL", "BASEMETALS")]

_COMPILED: dict[str, re.Pattern] = {k: re.compile(r"\b(?:" + v["words"] + r")", re.I) for k, v in PROFILES.items()}


def profile_key(symbol: str) -> str | None:
    """Commodity profile for an instrument name (CRUDEOILM, GOLDM, SILVERMIC, NATGASMINI ... map to their parent)."""
    s = str(symbol or "").upper().replace(" ", "")
    for prefix, key in _ALIASES:
        if s.startswith(prefix):
            return key
    return None


def profile(symbol: str) -> dict[str, Any] | None:
    k = profile_key(symbol)
    return {**PROFILES[k], "key": k} if k else None


def is_relevant(symbol: str, item: dict[str, Any]) -> bool:
    """For commodities: the headline or summary must be about that commodity's drivers. Others: always True here."""
    k = profile_key(symbol)
    if not k:
        return True
    text = f"{item.get('headline') or item.get('event') or ''} {item.get('summary') or ''}"
    return bool(_COMPILED[k].search(text))
