import requests
import base64

import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")


def get_token():
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    r = requests.post(
        "https://oauth.battle.net/token",
        headers={"Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials"}
    )

    return r.json()["access_token"]


def find_archimonde(token):
    index_url = "https://eu.api.blizzard.com/data/wow/connected-realm/index"

    index = requests.get(
        index_url,
        headers={"Authorization": f"Bearer {token}"},
        params={"namespace": "dynamic-eu"}
    ).json()

    for entry in index["connected_realms"]:
        realm_data = requests.get(
            entry["href"],
            headers={"Authorization": f"Bearer {token}"},
            params={"namespace": "dynamic-eu"}
        ).json()

        for r in realm_data.get("realms", []):
            name = r.get("name", {}).get("fr_FR", "").lower()

            if "archimonde" in name:
                print("🔥 ARCHIMONDE FOUND")
                print("ID:", realm_data["id"])
                return realm_data["id"]

    print("❌ Archimonde not found")
    return None


if __name__ == "__main__":
    token = get_token()
    find_archimonde(token)