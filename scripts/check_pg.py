import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

for table in ["current_auctions", "price_history", "items"]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(table, cur.fetchone()[0])

cur.execute("""
SELECT realm, COUNT(*)
FROM current_auctions
GROUP BY realm
ORDER BY realm
""")

print(cur.fetchall())

cur.close()
conn.close()