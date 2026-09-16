from app import db_exec
users = db_exec("SELECT id, username, email FROM users", fetch="all")
print("ALL USERS IN DB:")
for u in users:
    print(dict(u))

print("\nDISTINCT USER_IDs IN POSITIONS:")
print(db_exec("SELECT DISTINCT user_id, COUNT(*) as cnt FROM positions GROUP BY user_id", fetch="all"))

print("\nDISTINCT USER_IDs IN ORDERS:")
print(db_exec("SELECT DISTINCT user_id, COUNT(*) as cnt FROM orders GROUP BY user_id", fetch="all"))

