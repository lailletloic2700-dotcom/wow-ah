import sqlite3

conn = sqlite3.connect("data/ah.db")
cur = conn.cursor()

total_auctions = cur.execute("""
SELECT COUNT(*)
FROM auctions
""").fetchone()[0]

unique_items = cur.execute("""
SELECT COUNT(DISTINCT item_id)
FROM auctions
""").fetchone()[0]

print("Total auctions:", total_auctions)
print("Unique item IDs:", unique_items)

conn.close()