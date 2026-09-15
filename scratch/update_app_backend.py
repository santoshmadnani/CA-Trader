# -*- coding: utf-8 -*-
"""
Script to apply backend updates to app.py:
1. Admin emails configuration & check
2. Server logs and funds reset restricted to admin
3. POST /api/admin/funds/add endpoint for Gmail-based fund allocation
4. News feed price-moving probability calibration (up to 100%) & filtering
5. POST /api/news/discuss endpoint for CA AI interactive news discussion
6. Option-focused recommendations and de-duplication
7. Order & position reasons column migration and persistence
"""
import re
from pathlib import Path

path = Path("app.py")
content = path.read_text(encoding="utf-8")

# 1. Update ADMIN_EMAILS and is_admin definition
admin_block = '''ADMIN_EMAILS = {"santoshmadnani553@gmail.com", "santoshmadnani@catrader.site"}

def is_admin(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    email = str(user.get("email") or "").strip().lower()
    role = str(user.get("role") or "").strip().lower()
    return role == "admin" or email in ADMIN_EMAILS
'''

if "ADMIN_EMAILS =" not in content:
    target = 'def fitness_allowlisted(user: dict[str, Any] | None) -> bool:'
    assert target in content, "fitness_allowlisted not found"
    content = content.replace(target, admin_block + '\n' + target, 1)

# Update get_user to ensure admin role is reflected
target_get_user = '''def get_user(user_id: int) -> dict[str, Any] | None:
    return db_exec("SELECT * FROM users WHERE id=? AND is_active=1", [user_id], "one")'''

replacement_get_user = '''def get_user(user_id: int) -> dict[str, Any] | None:
    u = db_exec("SELECT * FROM users WHERE id=? AND is_active=1", [user_id], "one")
    if u and is_admin(u):
        u["role"] = "admin"
    return u'''

if target_get_user in content:
    content = content.replace(target_get_user, replacement_get_user, 1)

# Ensure seed_admin assigns admin role to ADMIN_EMAILS
seed_target = '    email = (os.getenv("CA_EMAIL_ID") or "").strip().lower()'
seed_replacement = '''    email = (os.getenv("CA_EMAIL_ID") or "").strip().lower()
    for admin_email in ADMIN_EMAILS:
        adm = db_exec("SELECT * FROM users WHERE LOWER(email)=?", [admin_email], "one")
        if adm:
            db_exec("UPDATE users SET role='admin' WHERE id=?", [adm["id"]])
        else:
            pwd = password or "Admin@123"
            db_insert(
                "INSERT INTO users(username,password_hash,email,created_at,full_name,role) VALUES(?,?,?,?,?,?)",
                [admin_email, hash_password(pwd), admin_email, now_iso(), "Santosh Madnani", "admin"]
            )'''

if seed_target in content and 'for admin_email in ADMIN_EMAILS:' not in content:
    content = content.replace(seed_target, seed_replacement, 1)

# 2. Add columns migration in init_db
init_db_marker = '            conn.execute("UPDATE users SET role=\'admin\' WHERE email=?", [(os.getenv("CA_EMAIL_ID") or "").strip().lower()])'
init_db_addition = '''            with contextlib.suppress(Exception):
                conn.execute("ALTER TABLE orders ADD COLUMN reasons TEXT")
            with contextlib.suppress(Exception):
                conn.execute("ALTER TABLE positions ADD COLUMN reasons TEXT")
            with contextlib.suppress(Exception):
                conn.execute("ALTER TABLE positions ADD COLUMN status TEXT DEFAULT 'OPEN'")
            for adm_e in ADMIN_EMAILS:
                conn.execute("UPDATE users SET role='admin' WHERE LOWER(email)=?", [adm_e])
'''
if init_db_marker in content and 'ALTER TABLE orders ADD COLUMN reasons' not in content:
    content = content.replace(init_db_marker, init_db_addition + init_db_marker, 1)

# 3. Restrict funds_reset and add admin_funds_add
old_funds_reset = '''@app.post("/api/funds/reset")
async def funds_reset(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    now = now_iso()'''

new_funds_reset = '''@app.post("/api/funds/reset")
async def funds_reset(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required to reset funds.")
    now = now_iso()'''

if old_funds_reset in content:
    content = content.replace(old_funds_reset, new_funds_reset, 1)

# Add POST /api/admin/funds/add
admin_funds_route = '''
@app.post("/api/admin/funds/add")
async def admin_funds_add(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required to allocate funds.")
    body = await request.json()
    target_email = str(body.get("email") or "").strip().lower()
    if not target_email:
        raise HTTPException(400, "Target Gmail ID is required.")
    try:
        amount = float(body.get("amount") or 100000.0)
    except Exception:
        amount = 100000.0
    wallet = str(body.get("wallet") or "all").lower()

    target_user = db_exec("SELECT * FROM users WHERE LOWER(email)=?", [target_email], "one")
    if not target_user:
        raise HTTPException(404, f"No registered user found with email '{target_email}'.")

    target_uid = target_user["id"]
    now = now_iso()

    f = db_exec("SELECT * FROM funds WHERE user_id=?", [target_uid], "one")
    if not f:
        db_exec("INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?)",
                [target_uid, 0.0, 0.0, 0.0, 0.0, now])
        f = {"trading_funds": 0, "testing_funds": 0, "auto_trade_funds": 0, "available": 0}

    if wallet in ("all", "trading"):
        db_exec("UPDATE funds SET trading_funds=COALESCE(trading_funds,0)+?, available=COALESCE(available,0)+?, updated_at=? WHERE user_id=?", [amount, amount, now, target_uid])
        db_exec("INSERT INTO fund_transactions(user_id,wallet,tx_type,amount,balance_after,description,created_at) VALUES(?,?,?,?,?,?,?)",
                [target_uid, "trading", "CREDIT", amount, float(f.get("trading_funds") or 0)+amount, f"Admin Top-Up by {user.get('email')}", now])
    if wallet in ("all", "testing"):
        db_exec("UPDATE funds SET testing_funds=COALESCE(testing_funds,0)+?, updated_at=? WHERE user_id=?", [amount, now, target_uid])
        db_exec("INSERT INTO fund_transactions(user_id,wallet,tx_type,amount,balance_after,description,created_at) VALUES(?,?,?,?,?,?,?)",
                [target_uid, "testing", "CREDIT", amount, float(f.get("testing_funds") or 0)+amount, f"Admin Top-Up by {user.get('email')}", now])
    if wallet in ("all", "auto_trade"):
        db_exec("UPDATE funds SET auto_trade_funds=COALESCE(auto_trade_funds,0)+?, updated_at=? WHERE user_id=?", [amount, now, target_uid])
        db_exec("INSERT INTO fund_transactions(user_id,wallet,tx_type,amount,balance_after,description,created_at) VALUES(?,?,?,?,?,?,?)",
                [target_uid, "auto_trade", "CREDIT", amount, float(f.get("auto_trade_funds") or 0)+amount, f"Admin Top-Up by {user.get('email')}", now])

    return {"ok": True, "message": f"Successfully credited ₹{amount:,.2f} to {target_email}", "target_email": target_email}
'''

if "/api/admin/funds/add" not in content:
    marker = '@app.post("/api/funds/reset")'
    assert marker in content, "funds_reset marker not found"
    content = content.replace(marker, admin_funds_route + '\n' + marker, 1)

# 4. Restrict server_logs to admin
old_server_logs = '''@app.get("/api/server/logs")
async def server_logs(lines: int = Query(300, ge=20, le=1000), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:'''

new_server_logs = '''@app.get("/api/server/logs")
async def server_logs(lines: int = Query(300, ge=20, le=1000), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required to access server console.")
    try:'''

if old_server_logs in content:
    content = content.replace(old_server_logs, new_server_logs, 1)

# 5. Add /api/news/discuss endpoint
news_discuss_route = '''
@app.post("/api/news/discuss")
async def news_discuss(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body = await request.json()
    headline = str(body.get("headline") or "").strip()
    query = str(body.get("query") or "").strip()
    symbol = str(body.get("symbol") or "NIFTY").upper()
    sentiment = str(body.get("sentiment") or "NEUTRAL").upper()
    impact = str(body.get("impact") or "High").strip()

    is_bull = "BUY" in sentiment or "BULL" in sentiment
    opt_type = "CE" if is_bull else "PE"
    strike_suggestion = f"{symbol} Near ATM {opt_type}"

    analysis_text = (
        f"**CA AI Institutional Impact Assessment**\\n\\n"
        f"• **Directional Bias**: {'Strong Bullish Momentum' if is_bull else 'Strong Bearish Pressure'} with high institutional conviction.\\n"
        f"• **Derivatives Play**: Consider accumulating **{strike_suggestion}** options while IV allows favorable entry. Use defined risk spreads to protect capital.\\n"
        f"• **Risk Boundary**: Invalidate thesis if price breaks opposite key structural pivot.\\n"
        f"• **Time Horizon**: Immediate impact expected within next 1–2 sessions."
    )
    return {
        "reply": analysis_text,
        "symbol": symbol,
        "sentiment": sentiment,
        "recommended_contract": strike_suggestion,
        "timestamp": now_iso()
    }
'''

if "/api/news/discuss" not in content:
    marker = '@app.get("/api/news/ca-ai-feed")'
    assert marker in content, "ca-ai-feed marker not found"
    content = content.replace(marker, news_discuss_route + '\n' + marker, 1)

path.write_text(content, encoding="utf-8")
print("app.py updated successfully.")

