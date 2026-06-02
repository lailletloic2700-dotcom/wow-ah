import sqlite3
import pandas as pd
import requests

DB_PATH = "data/ah.db"
ITEM_CACHE = {}


# =========================
# INIT DB (SAFE + CLEAN)
# =========================
def init_db(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY,
        item_level INTEGER
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        item_id INTEGER PRIMARY KEY
    )
    """)

    conn.commit()


# =========================
# FAVORITES
# =========================
def load_favorites(conn):
    try:
        rows = conn.execute("SELECT item_id FROM favorites").fetchall()
        return set(int(r[0]) for r in rows)
    except:
        return set()


# =========================
# LOAD DATA
# =========================
def load_data(conn):
    df = pd.read_sql_query("SELECT * FROM auctions", conn)

    if "item_id" not in df.columns:
        raise Exception("Missing item_id in auctions table")

    df["item_id"] = df["item_id"].astype(int)

    df["buyout_gold"] = df["buyout"] / 10000
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    df = df.dropna(subset=["item_id", "buyout_gold", "ts"])
    df = df[df["buyout_gold"] > 0]

    # remove extreme outliers
    df = df[df["buyout_gold"] < df["buyout_gold"].quantile(0.99)]

    return df


# =========================
# ITEM LEVEL (CACHE + API SAFE)
# =========================
def get_item_level(item_id, token, conn):
    item_id = int(item_id)

    if item_id in ITEM_CACHE:
        return ITEM_CACHE[item_id]

    cur = conn.cursor()

    cur.execute(
        "SELECT item_level FROM items WHERE item_id=?",
        (item_id,)
    )
    row = cur.fetchone()

    if row:
        ITEM_CACHE[item_id] = int(row[0])
        return int(row[0])

    try:
        url = f"https://eu.api.blizzard.com/data/wow/item/{item_id}"

        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"namespace": "static-eu"},
            timeout=10
        )

        data = r.json()
        ilvl = int(data.get("level", 0))

    except:
        ilvl = 0

    cur.execute(
        "INSERT OR REPLACE INTO items (item_id, item_level) VALUES (?, ?)",
        (item_id, ilvl)
    )
    conn.commit()

    ITEM_CACHE[item_id] = ilvl
    return ilvl


# =========================
# FILTER EXPANSION
# =========================
def filter_current_expansion(df, token, conn):
    print("[INFO] Filtering items...")

    if df.empty:
        return df

    valid_items = set()

    for item_id in df["item_id"].unique():
        ilvl = get_item_level(item_id, token, conn)

        # simple safe filter (à améliorer plus tard)
        if ilvl >= 1:
            valid_items.add(item_id)

    return df[df["item_id"].isin(valid_items)]


# =========================
# STATS
# =========================
def compute_stats(df):
    if df.empty:
        return pd.DataFrame(columns=["item_id", "avg", "median", "count"])

    stats = (
        df.groupby("item_id")["buyout_gold"]
        .agg(["mean", "median", "count"])
        .reset_index()
    )

    stats.columns = ["item_id", "avg", "median", "count"]
    stats["item_id"] = stats["item_id"].astype(int)

    return stats


# =========================
# OPPORTUNITIES
# =========================
def detect_opportunities(df, stats):
    if df.empty or stats.empty:
        return pd.DataFrame(), pd.DataFrame()

    df["item_id"] = df["item_id"].astype(int)
    stats["item_id"] = stats["item_id"].astype(int)

    merged = df.merge(stats, on="item_id", how="inner")

    merged["baseline"] = merged["median"]
    merged["diff_pct"] = (
        (merged["buyout_gold"] - merged["baseline"])
        / merged["baseline"]
    )

    buy = merged[merged["diff_pct"] < -0.40].sort_values("diff_pct")
    sell = merged[merged["diff_pct"] > 0.40].sort_values("diff_pct", ascending=False)

    return buy, sell


# =========================
# CRASH DETECTION
# =========================
def detect_crash(df):
    if df.empty:
        return pd.DataFrame()

    latest = df["ts"].max()

    recent = df[df["ts"] == latest]
    prev = df[df["ts"] != latest]

    if recent.empty or prev.empty:
        return pd.DataFrame()

    prev_avg = prev.groupby("item_id")["buyout_gold"].mean().reset_index()
    prev_avg["item_id"] = prev_avg["item_id"].astype(int)

    merged = recent.merge(prev_avg, on="item_id", how="inner", suffixes=("_now", "_prev"))

    merged["crash_pct"] = (
        (merged["buyout_gold_now"] - merged["buyout_gold_prev"])
        / merged["buyout_gold_prev"]
    )

    return merged[merged["crash_pct"] < -0.30]


# =========================
# MAIN
# =========================
def main():
    token = "TON_TOKEN_ICI"

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    df = load_data(conn)
    print(f"[INFO] RAW ITEMS: {df['item_id'].nunique()}")

    df = filter_current_expansion(df, token, conn)
    print(f"[INFO] FILTERED ITEMS: {df['item_id'].nunique()}")

    favorites = load_favorites(conn)
    fav_df = df[df["item_id"].isin(favorites)]

    stats = compute_stats(df)

    buy, sell = detect_opportunities(df, stats)
    crash = detect_crash(df)

    print("\n🔥 BUY OPPORTUNITIES")
    print(buy[["item_id", "buyout_gold", "baseline", "diff_pct"]].head(10))

    print("\n💰 SELL OPPORTUNITIES")
    print(sell[["item_id", "buyout_gold", "baseline", "diff_pct"]].head(10))

    print("\n⚠️ CRASH")
    print(crash.head(10))

    print("\n⭐ FAVORITES SAMPLE")
    print(fav_df.head(10))

    print("\n📊 DEBUG")
    print("ROWS:", len(df))
    print("ITEMS:", df["item_id"].nunique())
    print(df["buyout_gold"].describe())

    conn.close()


if __name__ == "__main__":
    main()