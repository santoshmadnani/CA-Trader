import sqlite3
c = sqlite3.connect('ca_trader.sqlite3')
print('tables:', [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
for t in ['watchlists', 'positions', 'orders']:
    try:
        rows = c.execute(f"SELECT symbol FROM {t} LIMIT 20").fetchall()
        print(t, [r[0] for r in rows])
    except Exception as e:
        print(t, e)

