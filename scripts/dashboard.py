import os
import sys
import subprocess

import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2

from dotenv import load_dotenv


# =========================
# ENV
# =========================
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL missing")
    st.stop()


# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="WoW AH Dashboard",
    layout="wide"
)

st.title("📊 WoW AH Dashboard")


# =========================
# DB
# =========================
def get_conn():
    return psycopg2.connect(DATABASE_URL)


# =========================
# LOAD ITEM NAMES
# =========================
@st.cache_data(ttl=3600)
def load_item_names():

    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT item_id, name
        FROM items
    """, conn)

    conn.close()

    return dict(
        zip(
            df["item_id"],
            df["name"]
        )
    )


ITEM_NAMES = load_item_names()


# =========================
# MIDNIGHT RANK SYSTEM
# =========================
def get_item_name(item_id):

    name = ITEM_NAMES.get(
        item_id,
        f"Item {item_id}"
    )

    if pd.isna(name):
        name = f"Item {item_id}"

    if (item_id - 1) in ITEM_NAMES:

        prev_name = ITEM_NAMES[item_id - 1]

        if prev_name == name:
            return f"{name} (R2)"

    if (item_id + 1) in ITEM_NAMES:

        next_name = ITEM_NAMES[item_id + 1]

        if next_name == name:
            return f"{name} (R1)"

    return str(name)


# =========================
# UPDATE BUTTON
# =========================
if st.button("🔄 Update AH Data"):

    with st.spinner("Updating Blizzard AH..."):

        subprocess.run(
            [
                sys.executable,
                "scripts/import_commodities_pg.py"
            ]
        )

    st.cache_data.clear()

    st.success("AH Updated!")


# =========================
# LOAD REALMS
# =========================
@st.cache_data(ttl=300)
def load_realms():

    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT DISTINCT realm
        FROM current_auctions
        WHERE realm IS NOT NULL
        ORDER BY realm
    """, conn)

    conn.close()

    return df["realm"].dropna().tolist()


# =========================
# LOAD ITEMS FOR REALM
# =========================
@st.cache_data(ttl=300)
def load_items_for_realm(realm):

    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT DISTINCT
            item_id
        FROM current_auctions
        WHERE realm = %s
        ORDER BY item_id
    """, conn, params=(realm,))

    conn.close()

    if df.empty:
        return df

    df["display_name"] = df["item_id"].apply(
        get_item_name
    )

    df = df.dropna(
        subset=["display_name"]
    )

    df["display_name"] = df[
        "display_name"
    ].astype(str)

    df = df.sort_values(
        "display_name"
    )

    return df


# =========================
# LOAD CURRENT AUCTIONS
# =========================
@st.cache_data(ttl=300)
def load_item_auctions(item_id, realm):

    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT
            buyout,
            quantity,
            time_left,
            item_id
        FROM current_auctions
        WHERE item_id = %s
        AND realm = %s
        ORDER BY buyout ASC
        LIMIT 5000
    """, conn, params=(item_id, realm))

    conn.close()

    if not df.empty:

        df["buyout_gold"] = (
            df["buyout"] / 10000
        ).round(2)

    return df


# =========================
# LOAD PRICE HISTORY
# =========================
@st.cache_data(ttl=300)
def load_price_history(item_id, realm):

    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT
            avg_price,
            quantity,
            ts
        FROM price_history
        WHERE item_id = %s
        AND realm = %s
        ORDER BY ts ASC
        LIMIT 500
    """, conn, params=(item_id, realm))

    conn.close()

    return df


# =========================
# LOAD CROSS REALM
# =========================
@st.cache_data(ttl=300)
def load_cross_realm(item_id):

    conn = get_conn()

    df = pd.read_sql_query("""
        SELECT
            realm,
            MIN(buyout) / 10000.0 AS lowest_price
        FROM current_auctions
        WHERE item_id = %s
        GROUP BY realm
        ORDER BY lowest_price ASC
    """, conn, params=(item_id,))

    conn.close()

    if not df.empty:
        df["lowest_price"] = df[
            "lowest_price"
        ].round(2)

    return df


# =========================
# SIDEBAR
# =========================
st.sidebar.header("Filters")

realms = load_realms()

if not realms:
    st.warning("No auction data yet. Run the PostgreSQL import first.")
    st.stop()

selected_realm = st.sidebar.selectbox(
    "Realm",
    realms
)

items_df = load_items_for_realm(
    selected_realm
)

if items_df.empty:
    st.warning("No items found for this realm.")
    st.stop()

selected_display = st.sidebar.selectbox(
    "Item",
    items_df["display_name"].tolist()
)

selected_rows = items_df[
    items_df["display_name"] == selected_display
]

if selected_rows.empty:
    st.warning("No item selected.")
    st.stop()

selected_item_id = int(
    selected_rows["item_id"].iloc[0]
)

selected_item = selected_display


# =========================
# LOAD DATA
# =========================
item_df = load_item_auctions(
    selected_item_id,
    selected_realm
)

history = load_price_history(
    selected_item_id,
    selected_realm
)

cross = load_cross_realm(
    selected_item_id
)


# =========================
# HEADER
# =========================
st.header(selected_item)


# =========================
# STATS
# =========================
if not item_df.empty:

    lowest_price = round(
        item_df["buyout_gold"].min(),
        2
    )

    median_price = round(
        item_df["buyout_gold"].median(),
        2
    )

    total_quantity = int(
        item_df["quantity"].sum()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Lowest Price",
        f"{lowest_price:.2f} g"
    )

    col2.metric(
        "Median Price",
        f"{median_price:.2f} g"
    )

    col3.metric(
        "Total Quantity",
        total_quantity
    )


# =========================
# CURRENT AUCTIONS
# =========================
st.subheader("📦 Current Auctions")

if not item_df.empty:

    auction_view = item_df[
        [
            "buyout_gold",
            "quantity",
            "time_left"
        ]
    ].copy()

    auction_view.columns = [
        "Price (g)",
        "Quantity",
        "Time Left"
    ]

    st.dataframe(
        auction_view,
        use_container_width=True,
        height=400
    )

else:

    st.warning("No auctions found.")


# =========================
# PRICE HISTORY
# =========================
st.subheader("📈 Price History")

if not history.empty:

    history["avg_price"] = history[
        "avg_price"
    ].astype(float).round(2)

    history["ts"] = pd.to_datetime(
        history["ts"],
        errors="coerce"
    )

    history = history.dropna(
        subset=["ts"]
    )

    history["time"] = history[
        "ts"
    ].dt.strftime("%d/%m %H:%M")

    fig = px.line(
        history,
        x="time",
        y="avg_price",
        markers=True,
        text="avg_price"
    )

    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="top center",
        hovertemplate=
        "Price: %{y:.2f}g<br>Time: %{x}<extra></extra>"
    )

    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Price (g)",
        height=500
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.warning("No history yet.")


# =========================
# CROSS REALM
# =========================
st.subheader("🌍 Cross Realm Prices")

if not cross.empty:

    cross.columns = [
        "Realm",
        "Lowest Price"
    ]

    st.dataframe(
        cross,
        use_container_width=True
    )

    if len(cross) >= 2:

        cheapest = cross.sort_values(
            "Lowest Price"
        ).iloc[0]

        expensive = cross.sort_values(
            "Lowest Price"
        ).iloc[-1]

        diff = round(
            expensive["Lowest Price"]
            -
            cheapest["Lowest Price"],
            2
        )

        percent = round(
            (
                diff
                /
                cheapest["Lowest Price"]
            ) * 100,
            1
        )

        st.subheader("💰 Arbitrage")

        st.success(
            f"""
Buy on {cheapest['Realm']}
at {cheapest['Lowest Price']:.2f}g

Sell on {expensive['Realm']}
at {expensive['Lowest Price']:.2f}g

Spread:
{diff:.2f}g ({percent:.1f}%)
"""
        )

else:

    st.warning("No cross realm data.")


# =========================
# DEBUG
# =========================
st.subheader("Debug")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Loaded Auctions",
    len(item_df)
)

col2.metric(
    "History Points",
    len(history)
)

col3.metric(
    "Realms",
    len(realms)
)