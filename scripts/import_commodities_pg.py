import os
import requests
import psycopg2

from datetime import datetime, UTC
from dotenv import load_dotenv
from psycopg2.extras import execute_values


load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")

REALMS = {
    "Archimonde": 1302,
    "Hyjal": 1390,
    "Draenor": 1403
}

BATCH_SIZE = 5000


def get_token():
    print("Getting token...")

    res = requests.post(
        "https://oauth.battle.net/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=30
    )

    data = res.json()

    if "access_token" not in data:
        print(data)
        raise Exception("Unable to get token")

    print("Token OK")
    return data["access_token"]


def get_quality(auction):
    bonus_lists = auction.get("item", {}).get("bonus_lists", [])

    quality_map = {
        10289: 1,
        10288: 2,
        10287: 3
    }

    for bonus in bonus_lists:
        if bonus in quality_map:
            return quality_map[bonus]

    return 1


def flush(cur, rows):
    if not rows:
        return

    execute_values(
        cur,
        """
        INSERT INTO current_auctions (
            auction_id,
            item_id,
            realm,
            buyout,
            quantity,
            time_left,
            quality,
            ts
        )
        VALUES %s
        """,
        rows
    )


def import_realm(cur, headers, realm_name, realm_id, now):
    print(f"\n=== {realm_name} ===")

    url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions"

    res = requests.get(
        url,
        headers=headers,
        params={"namespace": "dynamic-eu", "locale": "en_US"},
        timeout=60
    )

    auctions = res.json().get("auctions", [])
    print(f"Auctions found: {len(auctions)}")

    batch = []
    imported = 0

    for auc in auctions:
        item_id = auc.get("item", {}).get("id")
        buyout = auc.get("buyout")

        if not item_id or not buyout:
            continue

        batch.append((
            auc["id"],
            item_id,
            realm_name,
            buyout,
            auc.get("quantity", 1),
            auc.get("time_left", ""),
            get_quality(auc),
            now
        ))

        imported += 1

        if len(batch) >= BATCH_SIZE:
            flush(cur, batch)
            print(f"  inserted {imported}/{len(auctions)}")
            batch = []

    flush(cur, batch)
    print(f"Imported {imported} auctions")

    return imported


def import_commodities(cur, headers, now):
    print("\n=== COMMODITIES ===")

    url = "https://eu.api.blizzard.com/data/wow/auctions/commodities"

    res = requests.get(
        url,
        headers=headers,
        params={"namespace": "dynamic-eu", "locale": "en_US"},
        timeout=60
    )

    commodities = res.json().get("auctions", [])
    print(f"Commodities found: {len(commodities)}")

    batch = []
    imported = 0

    for auc in commodities:
        item_id = auc.get("item", {}).get("id")
        buyout = auc.get("unit_price")

        if not item_id or not buyout:
            continue

        batch.append((
            auc["id"],
            item_id,
            "EU Commodities",
            buyout,
            auc.get("quantity", 1),
            "COMMODITY",
            get_quality(auc),
            now
        ))

        imported += 1

        if len(batch) >= BATCH_SIZE:
            flush(cur, batch)
            print(f"  inserted {imported}/{len(commodities)}")
            batch = []

    flush(cur, batch)
    print(f"Imported {imported} commodities")

    return imported


def save_history(cur, now):
    print("\nSaving history...")

    cur.execute(
        """
        INSERT INTO price_history (
            item_id,
            item_name,
            realm,
            quality,
            avg_price,
            quantity,
            ts
        )

        WITH ranked AS (
            SELECT
                ca.item_id,
                ca.realm,
                ca.quality,
                ca.buyout,
                ca.quantity,
                i.name AS item_name,
                ROW_NUMBER() OVER (
                    PARTITION BY ca.item_id, ca.realm, ca.quality
                    ORDER BY ca.buyout ASC
                ) AS rn,
                COUNT(*) OVER (
                    PARTITION BY ca.item_id, ca.realm, ca.quality
                ) AS total_count
            FROM current_auctions ca
            LEFT JOIN items i
            ON ca.item_id = i.item_id
        ),

        cheapest AS (
            SELECT *
            FROM ranked
            WHERE rn <= GREATEST(CEIL(total_count * 0.04), 3)
        )

        SELECT
            item_id,
            item_name,
            realm,
            quality,
            ROUND(
                (
                    SUM(buyout::numeric * quantity::numeric)
                    / NULLIF(SUM(quantity::numeric), 0)
                ) / 10000.0,
                2
            ) AS avg_price,
            SUM(quantity) AS quantity,
            %s AS ts
        FROM cheapest
        GROUP BY item_id, item_name, realm, quality
        """,
        (now,)
    )

    print("History saved")


def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(UTC).replace(tzinfo=None)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Cleaning current auctions...")
        cur.execute("TRUNCATE current_auctions")
        conn.commit()

        total = 0

        for realm_name, realm_id in REALMS.items():
            total += import_realm(cur, headers, realm_name, realm_id, now)
            conn.commit()

        total += import_commodities(cur, headers, now)
        conn.commit()

        save_history(cur, now)
        conn.commit()

        print(f"\nDONE - imported {total} auctions")

    except Exception as e:
        conn.rollback()
        print("ERROR:", e)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()