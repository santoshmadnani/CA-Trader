"""News quality layer: who said it, does it move this stock, and which way.

The raw feed mixes real reporting with blogs, press-release farms, recycled roundups and "market is flat" filler, and almost
all of it reads as neutral. This module scores each article already classified by app.py and keeps only what a trader can use:

  trust   tier 1 official/wire/major business press, tier 2 reputable general press, tier 3 unknown (kept only when two
          independent sources carry the same story), blocked (blogs, social, forums, press-release farms: never shown)
  tone    Positive / Negative / Neutral from the headline, with a finer word list than the classifier's
  impact  0-100 = relevance x materiality x trust x freshness (a story older than a day counts for less)
  why     one plain sentence on why it matters for the selected stock

Pure functions: no network, no database. Every number is reproducible from the article.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

TIER1 = (
    "nseindia.com", "bseindia.com", "rbi.org.in", "sebi.gov.in", "pib.gov.in", "mospi.gov.in", "incometax.gov.in", "finmin.gov.in", "cbic.gov.in",
    "reuters.com", "bloomberg.com", "apnews.com", "ft.com", "wsj.com", "cnbc.com", "marketwatch.com",
    "economictimes.indiatimes.com", "livemint.com", "business-standard.com", "financialexpress.com", "cnbctv18.com", "moneycontrol.com",
    "thehindubusinessline.com", "barrons.com", "bbc.com", "bbc.co.uk",
)
TIER2 = (
    "thehindu.com", "indianexpress.com", "timesofindia.indiatimes.com", "ndtv.com", "ndtvprofit.com", "zeebiz.com", "hindustantimes.com",
    "businesstoday.in", "indiatoday.in", "finance.yahoo.com", "forbes.com", "theprint.in", "scroll.in", "news18.com", "firstpost.com",
    "outlookbusiness.com", "fortuneindia.com", "business-standard.com", "investing.com", "aljazeera.com", "theguardian.com", "nytimes.com",
)
BLOCKED = (
    "blogspot.", "wordpress.", "medium.com", "substack.com", "quora.com", "reddit.com", "facebook.com", "twitter.com", "x.com", "youtube.com",
    "instagram.com", "pinterest.com", "tradingview.com", "stocktwits.com", "telegram.", "t.me", "whatsapp.", "linkedin.com", "tumblr.com",
    "seekingalpha.com", "benzinga.com", "fool.com", "tipranks.com", "marketbeat.com", "simplywall.st", "investorplace.com", "zacks.com",
    "prnewswire.com", "businesswire.com", "globenewswire.com", "einpresswire.com", "openpr.com", "accesswire.com",
)
# publisher names when the feed gives a name and no usable URL (aggregators put the publisher in `source`)
NAME_TIER1 = ("reuters", "bloomberg", "associated press", "financial times", "wall street journal", "cnbc", "marketwatch", "economic times", "et markets",
              "et now", "mint", "livemint", "business standard", "financial express", "cnbc-tv18", "cnbctv18", "moneycontrol", "businessline", "barron")
NAME_TIER2 = ("the hindu", "indian express", "times of india", "ndtv", "zee business", "hindustan times", "business today", "india today", "yahoo finance",
              "forbes", "theprint", "news18", "firstpost", "bbc", "al jazeera", "the guardian", "new york times")
NAME_BLOCKED = ("blog", "stocktwits", "tradingview", "seeking alpha", "benzinga", "motley fool", "tipranks", "marketbeat", "simply wall", "zacks",
                "pr newswire", "business wire", "globenewswire", "einpresswire", "openpr", "medium", "substack", "reddit", "telegram", "whatsapp", "youtube")

TRUST_W = {1: 1.0, 2: 0.85, 3: 0.5}
MIN_IMPACT = 38.0          # below this an item is noise for a trader
STRONG_IMPACT = 70.0       # at or above this an item is worth an alert

_POS = ("surge", "jump", "rally", "soar", "climb", "gain", "rise", "record high", "beat", "beats", "strong", "wins", "bags", "order win", "secures", "upgrade",
        "approval", "approves", "approved", "profit rises", "profit jumps", "net profit up", "growth", "dividend", "bonus", "buyback", "acquires", "acquisition",
        "expands", "launches", "rate cut", "cuts rates", "eases", "stake buy", "inflow", "outperform", "all-time high", "positive")
_NEG = ("fall", "falls", "slump", "plunge", "tumble", "crash", "drop", "slide", "sinks", "decline", "miss", "misses", "weak", "loss", "losses", "downgrade",
        "probe", "fraud", "raid", "penalty", "fined", "fine", "ban", "banned", "default", "resigns", "resignation", "layoff", "lay off", "cuts guidance",
        "profit falls", "profit drops", "net loss", "tariff", "sanction", "sanctions", "war", "attack", "strike", "shutdown", "outflow", "selloff", "sell-off",
        "recall", "lawsuit", "scam", "insolvency", "bankruptcy", "negative", "rate hike", "hikes rates", "inflation surges")
_WORD = {w: re.compile(r"\b" + re.escape(w) + r"\b") for w in _POS + _NEG}


def _domain(url: Any) -> str:
    try:
        h = (urlparse(str(url or "")).hostname or "").lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _match(host: str, pats: tuple[str, ...]) -> bool:
    """A pattern ending in '.' (like 'blogspot.') matches anywhere in the host; any other is the domain or one of its subdomains."""
    return any((p in host) if p.endswith(".") else (host == p or host.endswith("." + p)) for p in pats)


def source_tier(source: Any, url: Any = None) -> int:
    """1, 2 or 3, or 0 for a blocked source. The URL host wins; the publisher name is used when the URL is an aggregator link."""
    host = _domain(url)
    if host and not host.endswith("google.com") and not host.endswith("feedburner.com"):
        if _match(host, BLOCKED):
            return 0
        if _match(host, TIER1):
            return 1
        if _match(host, TIER2):
            return 2
    name = str(source or "").lower()
    if name and any(b in name for b in NAME_BLOCKED):
        return 0
    if name and any(n in name for n in NAME_TIER1):
        return 1
    if name and any(n in name for n in NAME_TIER2):
        return 2
    return 3


TIER_LABEL = {0: "Blocked source", 1: "Trusted publisher", 2: "Reputable publisher", 3: "Unverified source"}


def tone(headline: str, summary: str = "") -> tuple[str, int]:
    """Headline tone with a finer word list. Returns (label, score); a story is Neutral only when no direction word is present or they cancel."""
    t = str(headline or "").lower()
    s = sum(1 for w in _POS if _WORD[w].search(t)) - sum(1 for w in _NEG if _WORD[w].search(t))
    if s == 0 and summary:
        first = re.split(r"(?<=[.!?])\s", str(summary).lower(), maxsplit=1)[0]
        s = (sum(1 for w in _POS if _WORD[w].search(first)) - sum(1 for w in _NEG if _WORD[w].search(first))) // 2
    return ("Positive" if s >= 1 else "Negative" if s <= -1 else "Neutral"), s


def _age_hours(published_at: Any, now: datetime | None = None) -> float | None:
    try:
        d = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return max(0.0, ((now or datetime.now(timezone.utc)) - d).total_seconds() / 3600)
    except Exception:
        return None


def freshness(age_h: float | None) -> float:
    if age_h is None:
        return 0.5
    return 1.0 if age_h <= 2 else 0.85 if age_h <= 6 else 0.6 if age_h <= 24 else 0.3 if age_h <= 72 else 0.1


_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "as", "at", "by", "with", "is", "are", "its", "after", "over", "from", "says", "said", "amid", "new"}


def _tokens(h: str) -> frozenset[str]:
    return frozenset(w for w in re.findall(r"[a-z0-9]+", str(h or "").lower()) if len(w) > 2 and w not in _STOP)


def corroboration(items: list[dict[str, Any]]) -> list[int]:
    """For each item, how many distinct sources carry the same story (headline word overlap >= 60%)."""
    toks = [_tokens(i.get("headline") or i.get("event")) for i in items]
    out = []
    for a, ta in enumerate(toks):
        srcs = {str(items[a].get("source") or "").lower()}
        for b, tb in enumerate(toks):
            if a == b or not ta or not tb:
                continue
            if len(ta & tb) / min(len(ta), len(tb)) >= 0.6:
                srcs.add(str(items[b].get("source") or "").lower())
        out.append(len(srcs))
    return out


def _why(item: dict[str, Any], symbol: str, tn: str, tier: int, corro: int) -> str:
    sym = symbol.upper()
    scope = "directly about " + sym if item.get("scope") == "stock" and float(item.get("relevance") or 0) >= 0.85 else "a wider market or sector story that can move " + sym
    kw = str(item.get("matched_keyword") or "").strip()
    direction = {"Positive": "Positive", "Negative": "Negative", "Neutral": "No clear direction"}[tn]
    who = TIER_LABEL[tier].lower() + (f", confirmed by {corro} sources" if corro >= 2 else "")
    return f"{direction}: {scope}" + (f" (matched “{kw}”)" if kw and kw.lower() not in ("none", "") else "") + f". Source: {who}."


def score(items: list[dict[str, Any]], symbol: str, now: datetime | None = None, strict: bool = True) -> dict[str, Any]:
    """Annotate and filter classified articles. Returns {items, hidden, reasons}; items are sorted by impact then recency."""
    corro = corroboration(items)
    kept, hidden = [], {"blocked_source": 0, "unverified_single_source": 0, "low_impact": 0, "neutral_filler": 0}
    for it, cn in zip(items, corro):
        tier = source_tier(it.get("source") or it.get("provider"), it.get("url"))
        head = str(it.get("headline") or it.get("event") or "")
        tn, ts = tone(head, it.get("summary") or "")
        if tn == "Neutral" and str(it.get("sentiment") or "") in ("Positive", "Negative"):
            tn = str(it["sentiment"])
        age = _age_hours(it.get("published_at"), now)
        mat = float(it.get("materiality") or 0)
        rel = float(it.get("relevance") or 0)
        impact = round(max(0.0, min(100.0, rel * mat * TRUST_W.get(tier, 0.5) * freshness(age))), 1) if tier else 0.0
        if cn >= 3 and tier:
            impact = round(min(100.0, impact * 1.1), 1)
        row = {**it, "trust_tier": tier, "trust_label": TIER_LABEL[tier], "corroboration": cn, "tone": tn, "tone_score": ts, "impact": impact,
               "age_hours": None if age is None else round(age, 1), "why": _why(it, symbol, tn, tier, cn)}
        if strict:
            if tier == 0:
                hidden["blocked_source"] += 1
                continue
            if tier == 3 and cn < 2:
                hidden["unverified_single_source"] += 1
                continue
            if impact < MIN_IMPACT:
                hidden["low_impact"] += 1
                continue
            if tn == "Neutral" and impact < STRONG_IMPACT and str(it.get("classification") or "").upper() not in ("NEWS", "SECTOR_DEVELOPMENT"):
                hidden["neutral_filler"] += 1
                continue
        kept.append(row)
    kept.sort(key=lambda r: (r["impact"], -(r["age_hours"] if r["age_hours"] is not None else 999)), reverse=True)
    uniq: list[dict[str, Any]] = []     # the same story from several outlets is shown once, with the number of outlets
    for r in kept:
        t = _tokens(r.get("headline") or r.get("event"))
        if any(t and u["_t"] and len(t & u["_t"]) / min(len(t), len(u["_t"])) >= 0.6 for u in uniq):
            continue
        r["_t"] = t
        uniq.append(r)
    for u in uniq:
        u.pop("_t", None)
    kept = uniq
    return {"items": kept, "hidden": hidden, "hidden_total": sum(hidden.values())}


def summary_line(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Net tone of the kept stories, weighted by impact, for the recommendation model and the main screen."""
    pos = sum(i["impact"] for i in items if i["tone"] == "Positive")
    neg = sum(i["impact"] for i in items if i["tone"] == "Negative")
    tot = pos + neg
    bias = round(100 * (pos - neg) / tot) if tot else 0
    label = "Positive" if bias >= 25 else "Negative" if bias <= -25 else "Mixed / neutral"
    return {"bias": bias, "label": label, "n": len(items), "strong": sum(1 for i in items if i["impact"] >= STRONG_IMPACT)}
