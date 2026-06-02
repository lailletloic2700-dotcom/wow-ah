import sqlite3
import requests
from datetime import datetime

# =========================
# BNET API
# =========================
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

DB_PATH = "data/ah.db"

REALMS = {
    "Archimonde": 1302,
    "Hyjal": 1390,
    "Draenor": 1403
}


# =========================
# TOKEN
# =========================
print("Getting token...")

token_res = requests.post(
    "https://oauth.battle.net/token",
    data={
        "grant_type": "client_credentials"
    },
    auth=(
        CLIENT_ID,
        CLIENT_SECRET
    )
)

token_data = token_res.json()

if "access_token" not in token_data:

    print(token_data)
    raise Exception("Unable to get token")

token = token_data["access_token"]

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
# CLEAN AUCTIONS
# =========================
print("Cleaning old auctions...")

cur.execute("""
DELETE FROM auctions
""")

conn.commit()


# =========================
# QUALITY PARSER
# =========================
def get_quality(auction):

    bonus_lists = auction["item"].get(
        "bonus_lists",
        []
    )

    QUALITY_MAP = {
        10289: 1,
        10288: 2,
        10287: 3
    }

    for bonus in bonus_lists:

        if bonus in QUALITY_MAP:
            return QUALITY_MAP[bonus]

    return 1


# =========================
# IMPORT REALMS
# =========================
for realm_name, realm_id in REALMS.items():

    print(f"\n=== {realm_name} ===")

    url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions"

    res = requests.get(
        url,
        headers=headers,
        params={
            "namespace": "dynamic-eu",
            "locale": "en_US"
        }
    )

    data = res.json()

    auctions = data.get("auctions", [])

    print(f"Auctions found: {len(auctions)}")

    now = datetime.now().isoformat()

    imported = 0

    for auc in auctions:

        try:

            item_id = auc["item"]["id"]

            buyout = auc.get("buyout")

            if not buyout:
                continue

            quantity = auc.get(
                "quantity",
                1
            )

            auction_id = auc["id"]

            time_left = auc.get(
                "time_left",
                ""
            )

            quality = get_quality(auc)

            cur.execute("""

            INSERT OR REPLACE INTO auctions (
                id,
                item_id,
                buyout,
                quantity,
                time_left,
                ts,
                realm,
                quality
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            """, (
                auction_id,
                item_id,
                buyout,
                quantity,
                time_left,
                now,
                realm_name,
                quality
            ))

            imported += 1

        except Exception:
            pass

    conn.commit()

    print(f"Imported {imported} auctions")


# =========================
# IMPORT COMMODITIES
# =========================
print("\n=== COMMODITIES ===")

url = "https://eu.api.blizzard.com/data/wow/auctions/commodities"

res = requests.get(
    url,
    headers=headers,
    params={
        "namespace": "dynamic-eu",
        "locale": "en_US"
    }
)

data = res.json()

commodities = data.get(
    "auctions",
    []
)

print(f"Commodities found: {len(commodities)}")

now = datetime.now().isoformat()

imported = 0

for auc in commodities:

    try:

        item_id = auc["item"]["id"]

        buyout = auc.get("unit_price")

        if not buyout:
            continue

        quantity = auc.get(
            "quantity",
            1
        )

        auction_id = auc["id"]

        quality = get_quality(auc)

        cur.execute("""

        INSERT OR REPLACE INTO auctions (
            id,
            item_id,
            buyout,
            quantity,
            time_left,
            ts,
            realm,
            quality
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        """, (
            auction_id,
            item_id,
            buyout,
            quantity,
            "COMMODITY",
            now,
            "EU Commodities",
            quality
        ))

        imported += 1

    except Exception:
        pass

conn.commit()

print(f"Imported {imported} commodities")


# =========================
# SAVE HISTORY
# =========================
print("\nSaving history...")

query = """

SELECT
    a.item_id,
    i.name,
    a.realm,
    a.quality,

    AVG(sub.buyout) / 10000.0 as avg_price,

    SUM(sub.quantity) as total_qty

FROM auctions a

JOIN (

    SELECT
        item_id,
        realm,
        quality,
        buyout,
        quantity

    FROM auctions

) sub

ON a.item_id = sub.item_id
AND a.realm = sub.realm
AND a.quality = sub.quality

LEFT JOIN items i
ON a.item_id = i.item_id

WHERE sub.buyout <= (

    SELECT MIN(buyout) * 1.04

    FROM auctions x

    WHERE
        x.item_id = a.item_id
        AND x.realm = a.realm
        AND x.quality = a.quality
)

GROUP BY
    a.item_id,
    a.realm,
    a.quality

"""

rows = conn.execute(query).fetchall()

saved = 0

for row in rows:

    item_id = row[0]
    item_name = row[1]
    realm = row[2]
    quality = row[3]

    avg_price = row[4]

    quantity = row[5]

    cur.execute("""

    INSERT INTO price_history (
        item_id,
        item_name,
        realm,
        avg_price,
        quantity,
        ts,
        quality
    )

    VALUES (?, ?, ?, ?, ?, ?, ?)

    """, (
        item_id,
        item_name,
        realm,
        avg_price,
        quantity,
        now,
        quality
    ))

    saved += 1

conn.commit()

print(f"Saved {saved} history rows")


# =========================
# OPTIMIZE SQLITE
# =========================
print("Optimizing DB...")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_auctions_search
ON auctions(item_id, realm, quality, buyout)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_history_search
ON price_history(item_id, realm, quality, ts)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_items_name
ON items(name)
""")

conn.commit()

conn.close()

print("\nDONE")