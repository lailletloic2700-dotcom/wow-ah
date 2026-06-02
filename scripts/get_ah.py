import requests
import base64

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

REALM_ID = 1302


def get_token():
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    r = requests.post(
        "https://oauth.battle.net/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    return r.json()["access_token"]


def get_auctions(token):
    url = f"https://eu.api.blizzard.com/data/wow/connected-realm/{REALM_ID}/auctions"

    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "namespace": "dynamic-eu",
            "locale": "fr_FR"
        }
    )

    data = r.json()

    print("Total auctions:", len(data.get("auctions", [])))
    print("Sample:", data.get("auctions", [])[:3])


if __name__ == "__main__":
    token = get_token()
    get_auctions(token)