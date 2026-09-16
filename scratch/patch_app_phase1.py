import sys, re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update init_db to include user_notes table
notes_table_sql = """
    CREATE TABLE IF NOT EXISTS user_notes (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        folder TEXT NOT NULL DEFAULT 'Trade Journal',
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        images_json TEXT,
        tags TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
"""

if "CREATE TABLE IF NOT EXISTS user_notes" not in content:
    init_db_marker = 'CREATE TABLE IF NOT EXISTS users ('
    content = content.replace(init_db_marker, notes_table_sql + "\n    " + init_db_marker, 1)
    print("Added user_notes table to init_db")

# 2. Add User Notes API endpoints & Save Recommendation Endpoint
notes_endpoints_code = '''
# ---------------------------------------------------------
# USER NOTES WORKSPACE API (Release 47 - Item 23)
# ---------------------------------------------------------
@app.get("/api/notes")
async def get_user_notes(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    rows = db_exec(
        "SELECT id, user_id, folder, title, content, images_json, tags, created_at, updated_at FROM user_notes WHERE user_id=? OR user_id=1 OR user_id IS NULL ORDER BY updated_at DESC",
        [user["id"]],
        "all"
    )
    items = []
    folders = set(["Trade Journal", "Mistakes & Learnings", "Playbooks & Setups", "Daily Market Prep"])
    for r in rows:
        fld = r.get("folder") or "Trade Journal"
        folders.add(fld)
        imgs = []
        if r.get("images_json"):
            try: imgs = json.loads(r["images_json"])
            except Exception: pass
        items.append({
            "id": r.get("id"),
            "folder": fld,
            "title": r.get("title") or "Untitled Note",
            "content": r.get("content") or "",
            "images": imgs,
            "tags": r.get("tags") or "",
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at")
        })
    return {"notes": items, "folders": sorted(list(folders)), "count": len(items)}


@app.post("/api/notes")
async def save_user_note(payload: dict[str, Any], user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    note_id = str(payload.get("id") or "").strip() or uuid4().hex[:12]
    folder = str(payload.get("folder") or "Trade Journal").strip()
    title = str(payload.get("title") or "Untitled Note").strip()
    content_text = str(payload.get("content") or "").strip()
    images = payload.get("images") or []
    tags = str(payload.get("tags") or "").strip()
    now = now_iso()
    
    imgs_json = json.dumps(images) if isinstance(images, list) else "[]"
    
    existing = db_exec("SELECT id FROM user_notes WHERE id=?", [note_id], "one")
    if existing:
        db_exec(
            "UPDATE user_notes SET folder=?, title=?, content=?, images_json=?, tags=?, updated_at=? WHERE id=?",
            [folder, title, content_text, imgs_json, tags, now, note_id]
        )
    else:
        db_exec(
            "INSERT INTO user_notes (id, user_id, folder, title, content, images_json, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [note_id, user["id"], folder, title, content_text, imgs_json, tags, now, now]
        )
    return {"success": True, "id": note_id, "updated_at": now, "message": "Note saved successfully"}


@app.delete("/api/notes/{note_id}")
async def delete_user_note(note_id: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    db_exec("DELETE FROM user_notes WHERE id=?", [note_id])
    return {"success": True, "message": "Note deleted"}


@app.post("/api/notes/upload-image")
async def upload_note_image(payload: dict[str, Any], user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    # Accepts base64 image data or url
    img_data = payload.get("image_data") or payload.get("url")
    if not img_data:
        raise HTTPException(400, "Image data required")
    return {"success": True, "url": img_data, "id": uuid4().hex[:8]}


# ---------------------------------------------------------
# MANUAL SAVE RECOMMENDATION TO HISTORY (Release 47 - Item 19)
# ---------------------------------------------------------
@app.post("/api/recommendations/save")
async def save_recommendation_to_history_api(payload: dict[str, Any], user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    reco_id = uuid4().hex[:16]
    now = now_iso()
    sym = str(payload.get("symbol") or "NIFTY").upper().strip()
    und = str(payload.get("underlying") or sym).upper().strip()
    act = str(payload.get("recommendation") or payload.get("signal") or "BUY").upper()
    entry = float(payload.get("entry") or 0.0)
    sl = float(payload.get("stop_loss") or 0.0)
    tgt = float(payload.get("target") or 0.0)
    tf = str(payload.get("timeframe") or "5m")
    rat = str(payload.get("rationale") or payload.get("reason") or "Institutional trade setup manually saved by trader.")
    conf = float(payload.get("confidence") or 82.0)
    ev = payload.get("evidence") or {}
    
    db_exec(
        """INSERT INTO recommendations (
            id, user_id, source, symbol, underlying, recommendation,
            timeframe, entry, target, stop_loss, rationale,
            technical_basis, news_basis, option_basis, score,
            outcome, final_pnl, success, exit_reason, created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            reco_id, user["id"], "on-demand", sym, und, act,
            tf, entry, tgt, sl, rat,
            json.dumps(ev.get("technical") or {}),
            json.dumps(ev.get("news") or {}),
            json.dumps(ev.get("options") or {}),
            conf, "ACTIVE", 0.0, 0, None, now, "ACTIVE"
        ]
    )
    return {"success": True, "id": reco_id, "message": "Recommendation successfully saved to history!"}
'''

if "/api/notes" not in content:
    pos_route_marker = '@app.get("/api/positions/{position_id}/analysis")'
    content = content.replace(pos_route_marker, notes_endpoints_code + "\n\n" + pos_route_marker, 1)
    print("Added User Notes and Save Reco API endpoints")

# 3. Fix Recommendation History query to include user_id=1 / NULL fallback
old_hist_query = "SELECT id, user_id, source, symbol, underlying, recommendation, timeframe, entry, target, stop_loss, rationale, technical_basis, news_basis, option_basis, score, outcome, final_pnl, success, exit_reason, created_at, status FROM recommendations WHERE user_id=? AND UPPER(recommendation) IN ('BUY', 'SELL') ORDER BY created_at DESC LIMIT 300"
new_hist_query = "SELECT id, user_id, source, symbol, underlying, recommendation, timeframe, entry, target, stop_loss, rationale, technical_basis, news_basis, option_basis, score, outcome, final_pnl, success, exit_reason, created_at, status FROM recommendations WHERE (user_id=? OR user_id IS NULL OR user_id=1) AND UPPER(recommendation) IN ('BUY', 'SELL') ORDER BY created_at DESC LIMIT 300"

if old_hist_query in content:
    content = content.replace(old_hist_query, new_hist_query)
    print("Updated recommendation_history query to include all active user recommendations")

# 4. Remove automatic saving on simple GET /api/analysis/overall and GET /api/recommendations
# so simple page refresh does NOT pollute recommendation history (Item 19)
auto_save_needle = "auto_save_recommendation(data, user_id=user[\"id\"])"
if auto_save_needle in content:
    content = content.replace(auto_save_needle, "# auto_save only on explicit action\n        pass")
    print("Disabled unconditional auto-save on simple analysis GET calls")

auto_save_needle2 = "auto_save_recommendation(res, user_id=user[\"id\"])"
if auto_save_needle2 in content:
    content = content.replace(auto_save_needle2, "# auto_save only on explicit action\n        pass")
    print("Disabled unconditional auto-save on reco GET calls")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Phase 1 app.py patches applied successfully.")

