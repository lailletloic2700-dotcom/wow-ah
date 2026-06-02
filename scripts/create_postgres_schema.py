import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL missing")

engine = create_engine(DATABASE_URL)

schema = """
CREATE TABLE IF NOT EXISTS realms (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    connected_realm_id INTEGER
);

CREATE TABLE IF NOT EXISTS items (
    item_id INTEGER PRIMARY KEY,
    name TEXT,
    expansion_id INTEGER,
    icon_id INTEGER
);

CREATE TABLE IF NOT EXISTS current_auctions (
    auction_id BIGINT PRIMARY KEY,
    item_id INTEGER NOT NULL,
    realm TEXT NOT NULL,
    buyout BIGINT NOT NULL,
    quantity INTEGER NOT NULL,
    time_left TEXT,
    quality INTEGER DEFAULT 1,
    ts TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL,
    item_name TEXT,
    realm TEXT NOT NULL,
    quality INTEGER DEFAULT 1,
    avg_price NUMERIC(14, 4),
    quantity INTEGER,
    ts TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_current_item_realm
ON current_auctions(item_id, realm, quality, buyout);

CREATE INDEX IF NOT EXISTS idx_history_item_realm_ts
ON price_history(item_id, realm, quality, ts);

CREATE INDEX IF NOT EXISTS idx_items_name
ON items(name);
"""

with engine.begin() as conn:
    conn.execute(text(schema))

print("PostgreSQL schema created.")