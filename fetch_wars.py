import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

API_BASE = "https://proxy.royaleapi.dev/v1"
API_KEY = os.environ["CR_API_KEY"]
CLAN_TAG = os.environ["CLAN_TAG"]


def cr_get(path):
    url = API_BASE + path
    key = API_KEY.strip()
    print(f"API key length: {len(key)}, starts with: {key[:6]}...")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} from {url}: {body}")
        raise


def fetch_war_log():
    tag = urllib.parse.quote(CLAN_TAG, safe="")
    data = cr_get(f"/clans/{tag}/riverracelog?limit=2")
    wars = []
    for race in data.get("items", []):
        season_id = race.get("seasonId", "?")
        end_time = race.get("createdDate", "")
        participants = []
        for clan in race.get("standings", []):
            for p in clan.get("clan", {}).get("participants", []):
                participants.append({
                    "name": p.get("name", ""),
                    "tag": p.get("tag", ""),
                    "fame": p.get("fame", 0),
                    "decksUsed": p.get("decksUsed", 0),
                })
        wars.append({
            "season": f"Season {season_id}",
            "endTime": end_time,
            "participants": participants,
        })
    return wars


def main():
    wars = fetch_war_log()
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wars": wars,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/wars.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote data/wars.json with {len(wars)} wars.")


if __name__ == "__main__":
    main()
