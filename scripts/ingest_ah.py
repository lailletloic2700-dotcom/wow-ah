import sqlite3
import requests
import base64
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

REALM_ID = 1302


def get_token():
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    r = requests.post(
        "https://oauth.battle.net/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    return r.json()["access_token"]


def fetch_ah(token):
    url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{REALM_ID}/auctions"

    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={"namespace": "dynamic-eu", "locale": "fr_FR"}
    )

    return r.json().get("auctions", [])


def init_db():
    conn = sqlite3.connect("data/ah.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER,
        item_id INTEGER,
        buyout INTEGER,
        quantity INTEGER,
        time_left TEXT,
        ts TEXT
    )
    """)

    conn.commit()
    return conn


def insert_data(conn, auctions):
    c = conn.cursor()
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()

    rows = []

    for a in auctions:
        item_id = a.get("item", {}).get("id")
        buyout = a.get("buyout", 0)
        qty = a.get("quantity", 0)
        time_left = a.get("time_left")

        rows.append((a["id"], item_id, buyout, qty, time_left, ts))

    c.executemany("""
        INSERT INTO auctions VALUES (?,?,?,?,?,?)
    """, rows)

    conn.commit()

    print(f"[OK] Inserted {len(rows)} rows at {ts}")


if __name__ == "__main__":
    token = get_token()
    auctions = fetch_ah(token)

    conn = init_db()
    insert_data(conn, auctions)