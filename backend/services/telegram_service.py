import asyncio
import json
import logging
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple
import requests

logger = logging.getLogger("ca_trader.telegram")

# Cache to avoid duplicate messages within 2 minutes: key -> timestamp
_SENT_DEDUPE_CACHE: Dict[str, float] = {}

def mask_token(token: str) -> str:
    """Mask Telegram bot token for safe display in UI."""
    if not token:
        return ""
    token = token.strip()
    if ":" in token:
        bot_id, secret = token.split(":", 1)
        if len(secret) > 8:
            return f"{bot_id}:{secret[:3]}****{secret[-4:]}"
        return f"{bot_id}:****"
    if len(token) > 8:
        return f"{token[:3]}****{token[-4:]}"
    return "****"

def escape_html(text: str) -> str:
    """Escape special HTML characters for Telegram HTML parse_mode."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _sync_send_telegram(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> Tuple[bool, str]:
    """Synchronous send message to Telegram API with token sanitization, plain-text fallback, and clear error diagnostics."""
    if not bot_token or not chat_id or not text:
        return False, "Bot token, chat ID, and text are required."
    
    # Sanitize token
    clean_token = str(bot_token).strip().strip('"\'')
    if "api.telegram.org/bot" in clean_token:
        clean_token = clean_token.split("api.telegram.org/bot")[-1].split("/")[0].strip()
    if clean_token.lower().startswith("bot") and ":" in clean_token:
        clean_token = clean_token[3:].strip()
        
    if "****" in clean_token or "•" in clean_token:
        return False, "Token appears masked or incomplete. Please paste the full Bot Token from @BotFather."
    if ":" not in clean_token:
        return False, "Invalid Bot Token format. Tokens from @BotFather look like '7123456789:AAFx9z-kOpq...'"
        
    clean_chat_id = str(chat_id).strip().strip('"\'')
    url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
    payload = {
        "chat_id": clean_chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=8.0)
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            return True, "Message sent successfully."
        
        # If Telegram rejected HTML tags, retry as plain text
        if not data.get("ok") and "can't parse entities" in str(data.get("description", "")).lower():
            clean_text = re.sub(r"<[^>]+>", "", text)
            payload["text"] = clean_text
            payload.pop("parse_mode", None)
            retry_resp = requests.post(url, json=payload, timeout=8.0)
            retry_data = retry_resp.json()
            if retry_resp.status_code == 200 and retry_data.get("ok"):
                return True, "Message sent (fallback to plain text)."
            return False, retry_data.get("description", "Failed to send message.")
            
        desc = str(data.get("description", "")).strip()
        if resp.status_code == 404 or desc.lower() == "not found":
            return False, "Bot Token not found by Telegram. Please check the token provided by @BotFather. Also open your bot in Telegram and press 'Start'."
        if "chat not found" in desc.lower():
            return False, "Chat ID not found. Open your bot in Telegram and send /start or any message to it first."
        if "blocked" in desc.lower():
            return False, "The bot was blocked by the user. Please unblock the bot in Telegram."
            
        return False, desc or f"HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "Telegram API request timed out. Please check your internet connection."
    except Exception as exc:
        logger.warning(f"Telegram dispatch error: {exc}")
        return False, str(exc)

async def send_telegram_msg(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> Tuple[bool, str]:
    """Asynchronously dispatches message to Telegram in worker thread to avoid blocking event loop."""
    return await asyncio.to_thread(_sync_send_telegram, bot_token, chat_id, text, parse_mode)

def format_test_msg() -> str:
    """Format an instant verification test message."""
    return (
        "🚀 <b>CA-Trader Alert Bot Connected!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ Telegram alert channel is now active.\n"
        "📈 You will receive instant notifications for:\n"
        "  • 🎯 High-Conviction Trade Setups\n"
        "  • 🛡️ Stop Loss & Target Executions\n"
        "  • ⚡ Breaking Institutional Market News\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⏰ <i>CA-Trader Terminal · Institutional Quant Engine</i>"
    )

def format_recommendation_alert(rec: Dict[str, Any]) -> str:
    """Format a high-conviction trade recommendation setup."""
    rec_type = str(rec.get("recommendation") or rec.get("signal") or "BUY").upper()
    action_icon = "🟢" if "BUY" in rec_type else "🔴"
    
    symbol = escape_html(rec.get("symbol") or rec.get("trade_instrument", {}).get("symbol") or "NIFTY")
    underlying = escape_html(rec.get("underlying") or symbol.split()[0])
    
    entry = rec.get("entry") or rec.get("trade_instrument", {}).get("entry") or 0.0
    target = rec.get("target") or rec.get("trade_instrument", {}).get("target") or 0.0
    sl = rec.get("stop_loss") or rec.get("trade_instrument", {}).get("stop_loss") or 0.0
    score = rec.get("score") or 0.0
    timeframe = escape_html(rec.get("timeframe") or "5m")
    rationale = escape_html(rec.get("rationale") or rec.get("reason") or "Quant Momentum + Confluence Setup")
    
    # Calculate R:R
    rr_str = "1 : 1.5+"
    try:
        entry_f = float(entry)
        target_f = float(target)
        sl_f = float(sl)
        if entry_f > 0 and abs(entry_f - sl_f) > 0:
            reward = abs(target_f - entry_f)
            risk = abs(entry_f - sl_f)
            rr_val = round(reward / risk, 1)
            rr_str = f"1 : {rr_val}"
    except Exception:
        pass
        
    entry_str = f"₹{float(entry):,.2f}" if entry else "Market Order"
    target_str = f"₹{float(target):,.2f}" if target else "Open Target"
    sl_str = f"₹{float(sl):,.2f}" if sl else "Strict Trailing"

    return (
        f"{action_icon} <b>CA-TRADER AI SIGNAL: {rec_type} {symbol}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Instrument:</b> {symbol}\n"
        f"• <b>Underlying:</b> {underlying}\n"
        f"• <b>Entry:</b> {entry_str}\n"
        f"• <b>Target:</b> {target_str}\n"
        f"• <b>Stop Loss:</b> {sl_str}\n"
        f"• <b>Risk / Reward:</b> {rr_str}\n"
        f"• <b>AI Confidence:</b> <b>{float(score):.0f}%</b>\n"
        f"• <b>Timeframe:</b> {timeframe}\n"
        f"• <b>Rationale:</b> {rationale}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Actionable setup generated by CA-Trader Quant Engine</i>"
    )

def format_risk_alert(title: str, body: str, severity: str = "warning") -> str:
    """Format position risk events, trailing stops, or target fills."""
    icon = "🛡️" if severity == "success" else ("⚠️" if severity == "warning" else "ℹ️")
    return (
        f"{icon} <b>CA-TRADER POSITION ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{escape_html(title)}</b>\n"
        f"{escape_html(body)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <i>Check open positions on terminal dashboard</i>"
    )

def format_news_alert(headline: str, summary: str = "", sentiment: str = "NEUTRAL", materiality: float = 85.0, source: str = "Institutional Feed") -> str:
    """Format breaking institutional market news."""
    s_upper = str(sentiment).upper()
    s_icon = "🟢" if "BULL" in s_upper else ("🔴" if "BEAR" in s_upper else "🟡")
    clean_headline = escape_html(headline)
    clean_summary = escape_html(summary)[:280] if summary else ""
    summary_line = f"\n{clean_summary}..." if clean_summary else ""
    
    return (
        f"⚡ <b>BREAKING MARKET NEWS</b> {s_icon} [{s_upper}]\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{clean_headline}</b>{summary_line}\n"
        f"• <b>Impact:</b> Materiality {float(materiality):.0f}%\n"
        f"• <b>Source:</b> {escape_html(source)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📰 <i>Real-time Market Driver</i>"
    )

def get_user_telegram_config(db_exec_fn: Callable, user_id: int) -> Dict[str, Any]:
    """Retrieve user's telegram configuration from database settings."""
    row = db_exec_fn("SELECT value_json FROM settings WHERE user_id=? AND key='telegram_config'", [user_id], "one")
    if not row or not row.get("value_json"):
        return {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "notify_recos": True,
            "min_reco_score": 75,
            "notify_risk": True,
            "notify_news": True
        }
    try:
        cfg = json.loads(row["value_json"])
        return {
            "enabled": bool(cfg.get("enabled", False)),
            "bot_token": str(cfg.get("bot_token", "")),
            "chat_id": str(cfg.get("chat_id", "")),
            "notify_recos": bool(cfg.get("notify_recos", True)),
            "min_reco_score": int(cfg.get("min_reco_score", 75)),
            "notify_risk": bool(cfg.get("notify_risk", True)),
            "notify_news": bool(cfg.get("notify_news", True))
        }
    except Exception:
        return {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "notify_recos": True,
            "min_reco_score": 75,
            "notify_risk": True,
            "notify_news": True
        }

def save_user_telegram_config(db_exec_fn: Callable, user_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
    """Save or update user's telegram configuration."""
    existing = get_user_telegram_config(db_exec_fn, user_id)
    
    # If user submitted a masked token or left empty, preserve the existing token
    new_token = str(config.get("bot_token", "")).strip().strip('"\'')
    if ("****" in new_token or "•" in new_token or not new_token) and existing.get("bot_token"):
        new_token = existing["bot_token"]
    
    merged = {
        "enabled": bool(config.get("enabled", existing.get("enabled", False))),
        "bot_token": new_token,
        "chat_id": str(config.get("chat_id", existing.get("chat_id", ""))).strip().strip('"\''),
        "notify_recos": bool(config.get("notify_recos", existing.get("notify_recos", True))),
        "min_reco_score": int(config.get("min_reco_score", existing.get("min_reco_score", 75))),
        "notify_risk": bool(config.get("notify_risk", existing.get("notify_risk", True))),
        "notify_news": bool(config.get("notify_news", existing.get("notify_news", True)))
    }
    
    # Save to SQLite settings table
    row = db_exec_fn("SELECT 1 FROM settings WHERE user_id=? AND key='telegram_config'", [user_id], "one")
    val_json = json.dumps(merged)
    if row:
        db_exec_fn("UPDATE settings SET value_json=? WHERE user_id=? AND key='telegram_config'", [val_json, user_id], "commit")
    else:
        db_exec_fn("INSERT INTO settings(user_id, key, value_json) VALUES(?, 'telegram_config', ?)", [user_id, val_json], "commit")
    
    return merged

async def dispatch_telegram_alert(db_exec_fn: Callable, user_id: int, category: str, text: str, dedupe_key: Optional[str] = None) -> bool:
    """Check user preference and asynchronously send telegram alert if enabled and not duplicate."""
    # Deduplication check
    now = time.time()
    if dedupe_key:
        if dedupe_key in _SENT_DEDUPE_CACHE and (now - _SENT_DEDUPE_CACHE[dedupe_key]) < 120.0:
            return False
        _SENT_DEDUPE_CACHE[dedupe_key] = now
        
    # Clean old cache entries occasionally
    if len(_SENT_DEDUPE_CACHE) > 500:
        keys_to_del = [k for k, ts in _SENT_DEDUPE_CACHE.items() if (now - ts) > 300.0]
        for k in keys_to_del:
            _SENT_DEDUPE_CACHE.pop(k, None)

    cfg = get_user_telegram_config(db_exec_fn, user_id)
    if not cfg.get("enabled") or not cfg.get("bot_token") or not cfg.get("chat_id"):
        return False
        
    # Check category filter
    if category == "recommendation" and not cfg.get("notify_recos", True):
        return False
    if category in ("risk", "order", "position") and not cfg.get("notify_risk", True):
        return False
    if category == "news" and not cfg.get("notify_news", True):
        return False
        
    ok, _ = await send_telegram_msg(cfg["bot_token"], cfg["chat_id"], text)
    return ok

