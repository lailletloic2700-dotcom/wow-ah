import sqlite3

conn = sqlite3.connect("data/ah.db")
cur = conn.cursor()

print()

total_auctions = cur.execute("""
SELECT COUNT(*)
FROM auctions
""").fetchone()[0]

print("TOTAL AUCTIONS:")
print(total_auctions)

print()

unique_items = cur.execute("""
SELECT COUNT(DISTINCT item_id)
FROM auctions
""").fetchone()[0]

print("UNIQUE ITEM IDS:")
print(unique_items)

print()

named_items = cur.execute("""
SELECT COUNT(*)
FROM items
WHERE name IS NOT NULL
AND name != ''
""").fetchone()[0]

print("ITEMS WITH NAMES:")
print(named_items)

print()

missing_names = cur.execute("""
SELECT COUNT(*)
FROM items
WHERE name IS NULL
OR name = ''
""").fetchone()[0]

print("ITEMS WITHOUT NAMES:")
print(missing_names)

conn.close()