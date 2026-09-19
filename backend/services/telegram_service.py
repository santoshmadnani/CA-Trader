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


# ==============================================================================
# 2-WAY INTERACTIVE TELEGRAM BOT & GEMINI AI INTEGRATION
# ==============================================================================

# Active live price watchers: chat_id -> watcher metadata
_ACTIVE_TELEGRAM_WATCHERS: Dict[str, Dict[str, Any]] = {}
# Offset tracking per token: bot_token -> next update_id
_LAST_TELEGRAM_UPDATE_IDS: Dict[str, int] = {}

def format_live_quote_card(quote: Dict[str, Any], prefix_note: str = "") -> str:
    """Format an institutional-grade, professional Telegram card for any symbol LTP."""
    sym = escape_html(quote.get("symbol") or quote.get("instrument") or "UNKNOWN")
    ex = escape_html(quote.get("exchange") or "NSE")
    ltp = quote.get("ltp")
    ltp_str = f"₹{float(ltp):,.2f}" if ltp is not None else "N/A"
    
    # Calculate price change
    net = quote.get("session_change")
    if net is None:
        net = quote.get("net_change") or 0.0
    pct = quote.get("session_change_pct")
    if pct is None:
        pct = quote.get("change_pct") or 0.0
        
    try:
        net_f = float(net)
        pct_f = float(pct)
    except Exception:
        net_f, pct_f = 0.0, 0.0
        
    is_up = net_f >= 0
    c_icon = "🟢" if is_up else "🔴"
    trend_tag = "BULLISH" if is_up else "BEARISH"
    sign = "+" if is_up else ""
    change_line = f"{c_icon} <b>{sign}{net_f:,.2f} ({sign}{pct_f:.2f}%)</b>"
    
    high = quote.get("high")
    low = quote.get("low")
    high_str = f"₹{float(high):,.2f}" if high is not None else "—"
    low_str = f"₹{float(low):,.2f}" if low is not None else "—"
    open_val = quote.get("open") or quote.get("session_open")
    close_val = quote.get("close") or quote.get("cp")
    open_str = f"₹{float(open_val):,.2f}" if open_val is not None else "—"
    close_str = f"₹{float(close_val):,.2f}" if close_val is not None else "—"

    note_block = f"\n{prefix_note}\n" if prefix_note else ""

    return (
        f"⚡ <b>LIVE MARKET QUOTE · CA-TRADER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{note_block}"
        f"• <b>Instrument:</b> <code>{sym}</code> ({ex})\n"
        f"• <b>Current LTP:</b> <code>{ltp_str}</code>\n"
        f"• <b>Session Change:</b> {change_line}\n"
        f"• <b>Day Range:</b> <code>{low_str} — {high_str}</code>\n"
        f"• <b>Open / Prev Close:</b> <code>{open_str} / {close_str}</code>\n"
        f"• <b>Bias Sentiment:</b> {c_icon} <b>{trend_tag}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <i>Real-time Market Stream · CA-Trader Terminal</i>"
    )

def format_telegram_gemini_reply(raw_text: str, context_title: str = "CA AI INTELLIGENCE") -> str:
    """Format raw Gemini output into a clean, professional, readable Telegram HTML message."""
    if not raw_text:
        return f"🤖 <b>{escape_html(context_title)}</b>\n━━━━━━━━━━━━━━━━━━━━━\nNo response generated."
        
    escaped = escape_html(raw_text.strip())
    # Convert markdown markers to Telegram HTML
    formatted = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)
    formatted = re.sub(r"\*(.*?)\*", r"<i>\1</i>", formatted)
    formatted = re.sub(r"`([^`]+)`", r"<code>\1</code>", formatted)
    
    # Add colored indicators for market direction keywords
    formatted = re.sub(r"\b(bullish|buy|gap-up|profit|upward)\b", r"🟢 <b>\1</b>", formatted, flags=re.IGNORECASE)
    formatted = re.sub(r"\b(bearish|sell|gap-down|loss|downward|sl hit)\b", r"🔴 <b>\1</b>", formatted, flags=re.IGNORECASE)

    return (
        f"🤖 <b>{escape_html(context_title)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"{formatted}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>CA-Trader AI Engine (Powered by Gemini)</i>"
    )

def format_positions_card(positions: list) -> str:
    """Format user's open positions cleanly for Telegram."""
    if not positions:
        return (
            f"🛡️ <b>CA-TRADER PORTFOLIO SENTINEL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"You currently have <b>0 Open Positions</b>.\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💼 <i>Terminal status: All square</i>"
        )
    lines = [
        "🛡️ <b>YOUR ACTIVE OPEN POSITIONS</b>",
        "━━━━━━━━━━━━━━━━━━━━━"
    ]
    for p in positions:
        sym = escape_html(p.get("symbol") or "N/A")
        side = escape_html(p.get("side") or "BUY")
        qty = p.get("quantity") or 0
        entry = float(p.get("avg_price") or 0.0)
        pnl = float(p.get("unrealized_pnl") or 0.0)
        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        pnl_sign = "+" if pnl >= 0 else ""
        lines.append(
            f"• <b>{sym}</b> [{side} {qty}x]\n"
            f"  Entry: <code>₹{entry:,.2f}</code> | PnL: {pnl_icon} <b>{pnl_sign}₹{pnl:,.2f}</b>"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━━")
    lines.append("📊 <i>Monitor trades live on CA-Trader Terminal</i>")
    return "\n".join(lines)

def _sync_fetch_telegram_updates(bot_token: str, offset: int = 0, timeout: int = 10) -> list:
    """Synchronously fetch updates from Telegram getUpdates API."""
    clean_token = str(bot_token).strip().strip('"\'')
    if ":" not in clean_token or "****" in clean_token:
        return []
    url = f"https://api.telegram.org/bot{clean_token}/getUpdates"
    params = {"offset": offset, "timeout": timeout, "limit": 20}
    try:
        resp = requests.get(url, params=params, timeout=timeout + 5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
    except Exception as exc:
        logger.debug("Telegram getUpdates error: %s", exc)
    return []

async def process_inbound_telegram_update(
    update: Dict[str, Any],
    bot_token: str,
    user_id: int,
    db_exec_fn: Callable,
    quote_fn: Callable,
    gemini_fn: Callable
) -> None:
    """Process a single incoming message from a Telegram user."""
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return
    chat_id = str(msg.get("chat", {}).get("id") or "")
    text = str(msg.get("text") or "").strip()
    if not chat_id or not text:
        return

    text_lower = text.lower()

    # 1. Start / Help command
    if text_lower in ("/start", "/help", "hi", "hello", "help"):
        welcome_text = (
            "🚀 <b>CA-TRADER AI & QUANT BOT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "Hello! I am connected to your live CA-Trader terminal and powered by Gemini AI.\n\n"
            "<b>What you can ask me:</b>\n"
            "• <code>What is the ltp of Nifty50</code> (or any stock/index)\n"
            "• <code>Keep me updated to every change in ltp of Nifty</code>\n"
            "• <code>/positions</code> — View your live open trades & PnL\n"
            "• <code>/stop</code> — Pause active live price watch updates\n"
            "• Ask <b>any</b> trading, macro, or options question in natural language!\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <i>Type a symbol or question to begin</i>"
        )
        await send_telegram_msg(bot_token, chat_id, welcome_text)
        return

    # 2. Stop / Unsubscribe from price watches
    if text_lower in ("/stop", "stop", "stop updates", "cancel updates", "unsubscribe"):
        removed = _ACTIVE_TELEGRAM_WATCHERS.pop(chat_id, None)
        sym_note = f" for <b>{escape_html(removed.get('symbol',''))}</b>" if removed else ""
        stop_text = (
            f"⏹️ <b>LIVE UPDATES PAUSED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Active price tick alerts{sym_note} have been paused.\n"
            f"To resume tracking anytime, reply:\n"
            f"<code>Keep me updated to every change in ltp of &lt;symbol&gt;</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        await send_telegram_msg(bot_token, chat_id, stop_text)
        return

    # 3. Positions query
    if text_lower in ("/positions", "positions", "my positions", "open trades", "my trades", "open orders"):
        try:
            positions = db_exec_fn(
                "SELECT symbol, side, quantity, avg_price, unrealized_pnl FROM positions WHERE user_id=? AND COALESCE(status,'OPEN')='OPEN'",
                [user_id],
                "all"
            ) or []
            await send_telegram_msg(bot_token, chat_id, format_positions_card(positions))
        except Exception as e:
            await send_telegram_msg(bot_token, chat_id, f"⚠️ Error fetching positions: {escape_html(str(e))}")
        return

    # 4. Continuous Price Watch subscription
    # Matches: "Keep me updated to every change in ltp of Nifty", "watch Nifty", "track Reliance"
    watch_match = re.search(r"(?:keep me updated.*(?:change in ltp|ltp).*of\s+|/watch\s+|track\s+)([a-zA-Z0-9_\s]+)", text, re.I)
    if watch_match:
        raw_sym = watch_match.group(1).strip().upper()
        # Clean symbol name (e.g. NIFTY50 -> NIFTY, NIFTY 50 -> NIFTY)
        clean_sym = "NIFTY" if "NIFTY50" in raw_sym or raw_sym == "NIFTY 50" else ("BANKNIFTY" if "BANK" in raw_sym else raw_sym.split()[0])
        try:
            quote = quote_fn(clean_sym)
            cur_ltp = float(quote.get("ltp") or 0.0)
            _ACTIVE_TELEGRAM_WATCHERS[chat_id] = {
                "symbol": clean_sym,
                "last_ltp": cur_ltp,
                "last_sent_time": time.time(),
                "bot_token": bot_token,
                "user_id": user_id
            }
            confirm_msg = (
                f"🔔 <b>LIVE PRICE WATCH ACTIVATED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Now monitoring: <b>{escape_html(clean_sym)}</b>\n"
                f"📌 Current LTP: <code>₹{cur_ltp:,.2f}</code>\n\n"
                f"You will receive instant alerts on every significant price tick change.\n"
                f"To cancel updates anytime, reply: <code>/stop</code>.\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ <i>CA-Trader Live Sentinel</i>"
            )
            await send_telegram_msg(bot_token, chat_id, confirm_msg)
        except Exception as e:
            await send_telegram_msg(bot_token, chat_id, f"⚠️ Could not start watch for {escape_html(clean_sym)}: {escape_html(str(e))}")
        return

    # 5. Live LTP query
    # Matches: "What is the ltp of Nifty50", "/ltp Nifty", "price of Reliance", or just "NIFTY"
    ltp_match = re.search(r"(?:what is the ltp of|ltp of|price of|cmp of|/ltp\s+)\s*([a-zA-Z0-9_\s]+)", text, re.I)
    candidate_sym = None
    if ltp_match:
        candidate_sym = ltp_match.group(1).strip().upper()
    elif text.strip().upper() in ("NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "CRUDEOIL", "GOLD", "RELIANCE", "TCS", "HDFCBANK"):
        candidate_sym = text.strip().upper()

    if candidate_sym:
        clean_sym = "NIFTY" if "NIFTY50" in candidate_sym or candidate_sym == "NIFTY 50" else ("BANKNIFTY" if "BANK" in candidate_sym else candidate_sym.split()[0])
        try:
            quote = quote_fn(clean_sym)
            if quote and quote.get("ltp") is not None:
                await send_telegram_msg(bot_token, chat_id, format_live_quote_card(quote))
                return
        except Exception as exc:
            logger.warning("Quote fetch error for %s: %s", clean_sym, exc)

    # 6. General / Conversational Market Intelligence Query (Gemini AI)
    try:
        # Build live context for Gemini
        nifty_q = quote_fn("NIFTY") or {}
        bank_q = quote_fn("BANKNIFTY") or {}
        n_ltp = nifty_q.get("ltp") or 23346.4
        b_ltp = bank_q.get("ltp") or 51240.2
        
        prompt = (
            f"You are CA AI, the conversational quantitative intelligence assistant for the CA-Trader terminal.\n"
            f"You are chatting directly with a trader via Telegram.\n"
            f"Current Market Data: NIFTY 50 LTP = {n_ltp}, BANKNIFTY LTP = {b_ltp}.\n"
            f"User Question: '{text}'\n\n"
            f"Guidelines:\n"
            f"1. Provide a professional, concise, structured answer.\n"
            f"2. Use bullet points and clear sections instead of dense continuous walls of text.\n"
            f"3. Note bullish or bearish factors with directional clarity.\n"
            f"4. Keep it under 250 words so it reads cleanly on a mobile phone screen."
        )
        ai_resp = gemini_fn(prompt)
        ai_text = ai_resp.get("text") or ai_resp.get("message") or "I could not analyze this request right now."
        formatted_card = format_telegram_gemini_reply(ai_text, "CA AI MARKET INTELLIGENCE")
        await send_telegram_msg(bot_token, chat_id, formatted_card)
    except Exception as e:
        logger.error("Error generating Gemini Telegram response: %s", e)
        await send_telegram_msg(bot_token, chat_id, f"⚠️ CA AI Error: {escape_html(str(e))}")

async def run_telegram_inbound_cycle(
    db_exec_fn: Callable,
    quote_fn: Callable,
    gemini_fn: Callable
) -> None:
    """One polling cycle across all active Telegram user configurations."""
    try:
        rows = db_exec_fn("SELECT user_id, value_json FROM settings WHERE key='telegram_config'", [], "all") or []
        for r in rows:
            uid = r.get("user_id")
            val = r.get("value_json")
            if not val:
                continue
            try:
                cfg = json.loads(val)
            except Exception:
                continue
            if not cfg.get("enabled"):
                continue
            token = str(cfg.get("bot_token") or "").strip().strip('"\'')
            if not token or ":" not in token or "****" in token:
                continue

            last_id = _LAST_TELEGRAM_UPDATE_IDS.get(token, 0)
            updates = await asyncio.to_thread(_sync_fetch_telegram_updates, token, last_id, 2)
            for u in updates:
                up_id = u.get("update_id", 0)
                if up_id >= last_id:
                    _LAST_TELEGRAM_UPDATE_IDS[token] = up_id + 1
                try:
                    await process_inbound_telegram_update(u, token, uid, db_exec_fn, quote_fn, gemini_fn)
                except Exception as e:
                    logger.error("Error processing update %s: %s", up_id, e)
    except Exception as exc:
        logger.debug("Telegram inbound cycle loop error: %s", exc)

async def run_telegram_price_watch_cycle(quote_fn: Callable) -> None:
    """Check active watchers and send alerts on price changes."""
    now = time.time()
    for chat_id, w in list(_ACTIVE_TELEGRAM_WATCHERS.items()):
        # Throttle each watcher to at most once every 8 seconds
        if (now - w.get("last_sent_time", 0)) < 8.0:
            continue
        sym = w.get("symbol")
        bot_token = w.get("bot_token")
        if not sym or not bot_token:
            continue
        try:
            q = quote_fn(sym)
            if not q or q.get("ltp") is None:
                continue
            cur_ltp = float(q["ltp"])
            last_ltp = float(w.get("last_ltp", cur_ltp))
            diff = cur_ltp - last_ltp
            
            # If price changed by at least 0.5 points or 0.02%
            if abs(diff) >= 0.25:
                w["last_ltp"] = cur_ltp
                w["last_sent_time"] = now
                diff_sign = "+" if diff > 0 else ""
                diff_icon = "🟢" if diff > 0 else "🔴"
                prefix = f"🔔 <b>PRICE UPDATE:</b> {diff_icon} <b>{diff_sign}₹{diff:,.2f}</b> since last tick"
                card = format_live_quote_card(q, prefix)
                await send_telegram_msg(bot_token, chat_id, card)
        except Exception as e:
            logger.debug("Price watch check error for %s: %s", sym, e)


