import re
import sqlite3
from datetime import datetime

FILE = r"C:\Program Files (x86)\World of Warcraft\_retail_\WTF\Account\124283120#1\SavedVariables\Auctionator.lua"
DB = r"C:\Users\Loic\wow-ah\data\ah.db"


def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        item_id INTEGER,
        price INTEGER
    )
    """)

    conn.commit()
    return conn


def extract_block():
    with open(FILE, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()

    start = data.find("AUCTIONATOR_PRICE_DATABASE")
    if start == -1:
        return ""

    return data[start:]


def parse_prices(block):
    results = []

    # Étape 1: trouver chaque itemID
    items = re.findall(r"\[(\d+)\]\s*=\s*{", block)

    for item_id in items:

        # isoler bloc item (approximation robuste)
        pattern = rf"\[{item_id}\]\s*=\s*\{{(.*?)\}}"
        match = re.search(pattern, block, re.DOTALL)

        if not match:
            continue

        content = match.group(1)

        # récupérer toutes les valeurs numériques plausibles prix
        prices = re.findall(r"(\d{4,})", content)

        for p in prices:
            price = int(p)

            # filtre bruit (très important)
            if 100 <= price <= 10_000_000:
                results.append((int(item_id), price))

    return results


def save(rows):
    conn = init_db()
    cur = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    for item_id, price in rows:
        cur.execute("""
        INSERT INTO price_history (date, item_id, price)
        VALUES (?, ?, ?)
        """, (today, item_id, price))

    conn.commit()
    conn.close()

    print(f"[OK] Imported {len(rows)} rows")


if __name__ == "__main__":
    block = extract_block()
    rows = parse_prices(block)
    save(rows)