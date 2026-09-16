from app import db_exec
rows = db_exec("SELECT id, user_id, symbol, side, quantity, avg_price, status, unrealized_pnl, final_pnl, updated_at FROM positions ORDER BY updated_at DESC LIMIT 10", fetch="all")
print("--- RECENT POSITIONS ---")
for r in rows:
    print(dict(r))

orders = db_exec("SELECT id, user_id, symbol, side, quantity, price, status, created_at FROM orders ORDER BY created_at DESC LIMIT 10", fetch="all")
print("\n--- RECENT ORDERS ---")
for o in orders:
    print(dict(o))

