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
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (compatible; clash-war-tracker/1.0)",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code} from {url}: {body}")
        raise


def fetch_current_members():
    tag = urllib.parse.quote(CLAN_TAG, safe="")
    data = cr_get(f"/clans/{tag}")
    return [{"tag": m["tag"], "name": m.get("name", "")} for m in data.get("memberList", [])]


def fetch_war_log():
    tag = urllib.parse.quote(CLAN_TAG, safe="")
    data = cr_get(f"/clans/{tag}/riverracelog?limit=2")
    wars = []
    for race in data.get("items", []):
        participants = {}
        for standing in race.get("standings", []):
            clan = standing.get("clan", {})
            if clan.get("tag") != CLAN_TAG:
                continue
            for p in clan.get("participants", []):
                participants[p["tag"]] = {
                    "name": p.get("name", ""),
                    "trophies": p.get("fame", 0),
                }
        wars.append({
            "season": f"Season {race.get('seasonId', '?')}",
            "participants": participants,
        })
    return wars


def build_roster(members, wars):
    war1 = wars[0]["participants"] if len(wars) > 0 else {}
    war2 = wars[1]["participants"] if len(wars) > 1 else {}

    roster = []
    for m in members:
        tag = m["tag"]
        p1 = war1.get(tag)
        p2 = war2.get(tag)
        roster.append({
            "name": m["name"] or (p1 or p2 or {}).get("name", ""),
            "tag": tag,
            "trophies1": p1["trophies"] if p1 else None,
            "trophies2": p2["trophies"] if p2 else None,
            "isNew": p1 is None or p2 is None,
        })
    return roster


def main():
    members = fetch_current_members()
    wars = fetch_war_log()
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "season1": wars[0]["season"] if len(wars) > 0 else "War 1",
        "season2": wars[1]["season"] if len(wars) > 1 else "War 2",
        "members": build_roster(members, wars),
    }
    os.makedirs("data", exist_ok=True)
    with open("data/wars.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote data/wars.json with {len(output['members'])} current clan members.")


if __name__ == "__main__":
    main()
