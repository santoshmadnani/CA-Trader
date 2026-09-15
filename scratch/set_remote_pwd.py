import sqlite3, secrets, hashlib, base64

salt = secrets.token_bytes(16)
key = hashlib.pbkdf2_hmac("sha256", "Trader@123".encode(), salt, 210_000)
pwd_hash = base64.urlsafe_b64encode(salt + key).decode()

conn = sqlite3.connect("/home/ubuntu/ca-trader-data/ca_trader.db")
conn.execute("UPDATE users SET password_hash=? WHERE id=1 AND email='santoshmadnani@catrader.site'", [pwd_hash])
conn.commit()
print("Updated user 1 in ca_trader.db with Trader@123!")
conn.close()

