import sqlite3
import pandas as pd

conn = sqlite3.connect("data/ah.db")

tables = [
    "items",
    "auctions",
    "ah_prices",
    "price_history",
]

for table in tables:
    print(f"\n=== {table.upper()} ===")

    try:
        cols = pd.read_sql_query(
            f"PRAGMA table_info({table});",
            conn
        )

        print("\nCOLUMNS:")
        print(cols[["name", "type"]])

        preview = pd.read_sql_query(
            f"SELECT * FROM {table} LIMIT 5;",
            conn
        )

        print("\nPREVIEW:")
        print(preview)

    except Exception as e:
        print("ERROR:", e)

conn.close()