import os
import sqlite3
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

SQLITE_DB = "data/ah.sqlite.db"

print("Checking SQLite file:", SQLITE_DB)
print("Exists:", os.path.exists(SQLITE_DB))

if not os.path.exists(SQLITE_DB):
    raise Exception("SQLite DB not found")

sqlite_conn = sqlite3.connect(SQLITE_DB)
cur = sqlite_conn.cursor()

tables = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

print("SQLite tables:", tables)

rows = cur.execute("""
SELECT item_id, name
FROM items
WHERE name IS NOT NULL
""").fetchall()

sqlite_conn.close()

print(f"Items found in SQLite: {len(rows)}")

if len(rows) == 0:
    raise Exception("No items found in SQLite")

pg_conn = psycopg2.connect(DATABASE_URL)
pg_cur = pg_conn.cursor()

execute_values(
    pg_cur,
    """
    INSERT INTO items (
        item_id,
        name
    )
    VALUES %s
    ON CONFLICT (item_id)
    DO UPDATE SET
        name = EXCLUDED.name
    """,
    rows,
    page_size=5000
)

pg_conn.commit()

pg_cur.close()
pg_conn.close()

print(f"Synced {len(rows)} items to PostgreSQL.")