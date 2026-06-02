import streamlit as st
import sqlite3
import pandas as pd
import subprocess
import plotly.express as px

DB_PATH = "data/ah.sqlite"
import os

st.write("Current folder:", os.getcwd())
st.write("Files:", os.listdir("."))
st.write("Data exists:", os.path.exists("data"))
st.write("DB exists:", os.path.exists(DB_PATH))


# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="WoW AH Dashboard",
    layout="wide"
)

st.title("📊 WoW AH Dashboard")


# =========================
# UPDATE BUTTON
# =========================
if st.button("🔄 Update AH Data"):

    with st.spinner("Updating Blizzard AH..."):

        subprocess.run(
            ["py", "scripts/import_commodities.py"]
        )

    st.cache_data.clear()

    st.success("AH Updated!")



# =========================
# LOAD REALMS
# =========================
@st.cache_data(ttl=300)
def load_realms():

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT DISTINCT realm
        FROM auctions
        WHERE realm IS NOT NULL
        ORDER BY realm
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    realms = df["realm"].dropna().tolist()

    return realms


# =========================
# LOAD ITEMS FOR REALM
# =========================
@st.cache_data(ttl=300)
def load_items_for_realm(realm):

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT DISTINCT
            a.item_id,
            i.name
        FROM auctions a

        LEFT JOIN items i
        ON a.item_id = i.item_id

        WHERE a.realm = ?
        AND i.name IS NOT NULL
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(realm,)
    )

    conn.close()

    names = []

    for _, row in df.iterrows():

        item_name = str(row["name"])

        item_id = row["item_id"]

        names.append(
            f"{item_name}"
        )

    names = sorted(list(set(names)))

    return names


# =========================
# LOAD AUCTIONS
# =========================
@st.cache_data(ttl=300)
def load_item_auctions(item_name, realm):

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            a.buyout,
            a.quantity,
            a.time_left,
            a.item_id
        FROM auctions a

        LEFT JOIN items i
        ON a.item_id = i.item_id

        WHERE i.name = ?
        AND a.realm = ?

        ORDER BY a.buyout ASC
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(item_name, realm)
    )

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

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            avg_price,
            quantity,
            ts
        FROM price_history
        WHERE item_id = ?
        AND realm = ?
        ORDER BY ts ASC
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(item_id, realm)
    )

    conn.close()

    return df


# =========================
# LOAD CROSS REALM
# =========================
@st.cache_data(ttl=300)
def load_cross_realm(item_name):

    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            a.realm,
            MIN(a.buyout) as lowest_price

        FROM auctions a

        LEFT JOIN items i
        ON a.item_id = i.item_id

        WHERE i.name = ?

        GROUP BY a.realm
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(item_name,)
    )

    conn.close()

    if not df.empty:

        df["lowest_price"] = (
            df["lowest_price"] / 10000
        ).round(2)

    return df


# =========================
# SIDEBAR
# =========================
st.sidebar.header("Filters")

realms = load_realms()

selected_realm = st.sidebar.selectbox(
    "Realm",
    realms
)

items = load_items_for_realm(
    selected_realm
)

selected_item = st.sidebar.selectbox(
    "Item",
    items
)


# =========================
# LOAD ITEM DATA
# =========================
item_df = load_item_auctions(
    selected_item,
    selected_realm
)


# =========================
# GET ITEM ID
# =========================
selected_item_id = None

if not item_df.empty:

    selected_item_id = int(
        item_df["item_id"].iloc[0]
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

if selected_item_id:

    history = load_price_history(
        selected_item_id,
        selected_realm
    )

    if not history.empty:

        history["avg_price"] = history[
            "avg_price"
        ].round(2)

        history["ts"] = pd.to_datetime(
            history["ts"]
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
            textposition="top center"
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

        st.warning(
            "No history yet."
        )


# =========================
# CROSS REALM
# =========================
st.subheader("🌍 Cross Realm Prices")

cross = load_cross_realm(
    selected_item
)

if not cross.empty:

    cross.columns = [
        "Realm",
        "Lowest Price"
    ]

    st.dataframe(
        cross,
        use_container_width=True
    )

    # =========================
    # ARBITRAGE
    # =========================
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

    st.warning(
        "No cross realm data."
    )


# =========================
# DEBUG
# =========================
st.subheader("Debug")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Loaded Auctions",
    len(item_df)
)

if selected_item_id:

    history_count = len(
        load_price_history(
            selected_item_id,
            selected_realm
        )
    )

else:

    history_count = 0

col2.metric(
    "History Points",
    history_count
)

col3.metric(
    "Realms",
    len(realms)
)