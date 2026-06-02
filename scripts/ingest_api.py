import json
import sqlite3
from datetime import datetime
import os

DB = r"C:\Users\Loic\wow-ah\data\ah.db"
DATA_FILE = r"C:\Users\Loic\wow-ah\data\auction_data.json"


def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ah_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        item_id INTEGER,
        price REAL,
        quantity INTEGER
    )
    """)

    conn.commit()
    return conn


def load_data():
    if not os.path.exists(DATA_FILE):
        print("No data file yet")
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(rows):
    conn = init_db()
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    for r in rows:
        cur.execute("""
        INSERT INTO ah_prices (date, item_id, price, quantity)
        VALUES (?, ?, ?, ?)
        """, (today, r["item_id"], r["price"], r.get("quantity", 1)))

    conn.commit()
    conn.close()

    print(f"[OK] Imported {len(rows)} rows")


if __name__ == "__main__":
    data = load_data()
    save(data)