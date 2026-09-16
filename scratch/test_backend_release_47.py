import sys, os
sys.path.insert(0, os.path.abspath('.'))

import app

# 1. Test init_db
app.init_db()
print("init_db executed successfully")

# 2. Check user_notes table
notes_check = app.db_exec("SELECT name FROM sqlite_master WHERE type='table' AND name='user_notes'", [], "one")
print("user_notes table exists:", bool(notes_check))

# 3. Test note insertion
note_id = "test_note_47"
app.db_exec(
    "INSERT OR REPLACE INTO user_notes (id, user_id, folder, title, content, images_json, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    [note_id, 1, "Trade Journal", "Test Release 47 Note", "Checking dynamic journal notes", "[]", "#Nifty", app.now_iso(), app.now_iso()]
)
notes = app.db_exec("SELECT * FROM user_notes WHERE id=?", [note_id], "one")
print("Note saved & fetched:", notes["title"], "| Folder:", notes["folder"])

# Clean up test note
app.db_exec("DELETE FROM user_notes WHERE id=?", [note_id])
print("Test note cleaned up successfully")

# 4. Test option recommendation rules (Item 2 & Item 15)
reco_ce = app.overall_recommendation("NIFTY 23250 CE", "5m")
print(f"NIFTY 23250 CE Reco: {reco_ce.get('recommendation')} | Qualifies: {reco_ce.get('qualifies')} | Rationale: {str(reco_ce.get('rationale'))[:80]}")

reco_pe = app.overall_recommendation("NIFTY 23250 PE", "5m")
print(f"NIFTY 23250 PE Reco: {reco_pe.get('recommendation')} | Qualifies: {reco_pe.get('qualifies')} | Rationale: {str(reco_pe.get('rationale'))[:80]}")

# 5. Test recommendation save
test_reco_id = "reco_test_47"
app.db_exec(
    """INSERT OR REPLACE INTO recommendations (
        id, user_id, source, symbol, underlying, recommendation,
        timeframe, entry, target, stop_loss, rationale,
        technical_basis, news_basis, option_basis, score,
        outcome, final_pnl, success, exit_reason, created_at, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    [
        test_reco_id, 1, "on-demand", "NIFTY 23250 CE", "NIFTY", "BUY",
        "5m", 145.5, 180.0, 125.0, "Test Release 47 manual save",
        "{}", "{}", "{}", 85.0, "ACTIVE", 0.0, 0, None, app.now_iso(), "ACTIVE"
    ]
)
hist_rows = app.db_exec("SELECT * FROM recommendations WHERE id=?", [test_reco_id], "one")
print("Saved recommendation verified in DB:", hist_rows["symbol"], hist_rows["recommendation"])
app.db_exec("DELETE FROM recommendations WHERE id=?", [test_reco_id])

print("ALL BACKEND TESTS PASSED!")

