import sqlite3
import requests
import time

# =========================
# CONFIG
# =========================
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

DB_PATH = "data/ah.db"

SLEEP_TIME = 0.05


# =========================
# GET TOKEN
# =========================
print("Getting Blizzard token...")

token_res = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET),
)

token = token_res.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}

print("Token OK")


# =========================
# DB
# =========================
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


# =========================
# SYNC ITEMS TABLE
# =========================
print("Syncing items table...")

cur.execute("""
INSERT OR IGNORE INTO items (item_id)
SELECT DISTINCT item_id
FROM auctions
""")

conn.commit()


# =========================
# GET ITEMS WITHOUT NAMES
# =========================
rows = cur.execute("""
SELECT item_id
FROM items
WHERE name IS NULL
OR name = ''
""").fetchall()

total_items = cur.execute("""
SELECT COUNT(*)
FROM items
""").fetchone()[0]

print(f"Total items: {total_items}")
print(f"Missing names: {len(rows)}")


# =========================
# FETCH NAMES
# =========================
success = 0
failed = 0


for index, (item_id,) in enumerate(rows, start=1):

    name = None

    # =========================
    # STANDARD ITEM API
    # =========================
    url = (
        f"https://eu.api.blizzard.com/data/wow/item/{item_id}"
        f"?namespace=static-eu&locale=en_US"
    )

    try:

        r = requests.get(
            url,
            headers=headers
        )

        # =========================
        # CLASSIC ITEM
        # =========================
        if r.status_code == 200:

            data = r.json()

            name = data.get("name")

        # =========================
        # FALLBACK SEARCH API
        # =========================
        else:

            search_url = (
                "https://eu.api.blizzard.com/data/wow/search/item"
                f"?namespace=static-eu"
                f"&locale=en_US"
                f"&id={item_id}"
            )

            search_r = requests.get(
                search_url,
                headers=headers
            )

            if search_r.status_code == 200:

                search_data = search_r.json()

                results = search_data.get(
                    "results",
                    []
                )

                if results:

                    data = results[0]["data"]

                    name = data.get(
                        "name",
                        {}
                    ).get("en_US")

        # =========================
        # SAVE NAME
        # =========================
        if name:

            cur.execute("""
            UPDATE items
            SET name=?
            WHERE item_id=?
            """, (name, item_id))

            conn.commit()

            success += 1

            print(
                f"[{index}/{len(rows)}] "
                f"{item_id} -> {name}"
            )

        # =========================
        # FAILED
        # =========================
        else:

            failed += 1

            print(
                f"[{index}] "
                f"{item_id} -> NOT FOUND"
            )

            with open(
                "missing_items.txt",
                "a",
                encoding="utf-8"
            ) as f:

                f.write(
                    f"{item_id}\n"
                )

    except Exception as e:

        failed += 1

        print(
            f"[{index}] "
            f"{item_id} -> ERROR {e}"
        )

    # avoid rate limit
    time.sleep(SLEEP_TIME)


# =========================
# DONE
# =========================
conn.close()

print("\nDONE")
print(f"Success: {success}")
print(f"Failed: {failed}")

print("\nMissing items saved to:")
print("missing_items.txt")