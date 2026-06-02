import sqlite3

conn = sqlite3.connect("data/ah.db")
cur = conn.cursor()

print("Creating indexes...")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_auctions_item
ON auctions(item_id)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_auctions_realm
ON auctions(realm)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_history_item
ON price_history(item_id)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_history_realm
ON price_history(realm)
""")

conn.commit()
conn.close()

print("DONE")