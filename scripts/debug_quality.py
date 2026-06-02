import requests
import json

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

token_res = requests.post(
    "https://oauth.battle.net/token",
    data={"grant_type": "client_credentials"},
    auth=(CLIENT_ID, CLIENT_SECRET)
)

token = token_res.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}

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

auctions = data.get("auctions", [])

# Azeroot
TARGET_ITEM = 236775

count = 0

for auc in auctions:

    item_id = auc["item"]["id"]

    if item_id == TARGET_ITEM:

        print("\n====================")
        print(json.dumps(auc, indent=2))

        count += 1

        if count >= 20:
            break