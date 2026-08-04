import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

API_BASE = "https://proxy.royaleapi.dev/v1"
API_KEY = os.environ["CR_API_KEY"]
CLAN_TAG = os.environ["CLAN_TAG"]

HISTORY_PATH = "data/member_history.json"
DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"
NEW_MEMBER_GRACE_DAYS = 14


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
        wars.append({"participants": participants})
    return wars


def load_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH) as f:
            return json.load(f), False
    return {}, True


def update_history(history, members, now, first_run):
    # On the first run, everyone currently in the clan is grandfathered in as
    # already-established, since we have no real record of when they joined.
    # From here on, a tag appearing for the first time is a genuine new join.
    backfill_date = (now - timedelta(days=NEW_MEMBER_GRACE_DAYS + 1)).strftime(DATE_FMT)
    now_str = now.strftime(DATE_FMT)
    current_tags = {m["tag"] for m in members}

    for tag in current_tags:
        if tag not in history:
            history[tag] = backfill_date if first_run else now_str

    # Drop members who've left the clan so the history file doesn't grow forever.
    for tag in list(history.keys()):
        if tag not in current_tags:
            del history[tag]

    return history


def build_roster(members, wars, history, now):
    war1 = wars[0]["participants"] if len(wars) > 0 else {}
    war2 = wars[1]["participants"] if len(wars) > 1 else {}

    roster = []
    for m in members:
        tag = m["tag"]
        p1 = war1.get(tag)
        p2 = war2.get(tag)
        first_seen = datetime.strptime(history[tag], DATE_FMT).replace(tzinfo=timezone.utc)
        is_new = (now - first_seen) < timedelta(days=NEW_MEMBER_GRACE_DAYS)
        roster.append({
            "name": m["name"] or (p1 or p2 or {}).get("name", ""),
            "tag": tag,
            "trophies1": p1["trophies"] if p1 else 0,
            "trophies2": p2["trophies"] if p2 else 0,
            "isNew": is_new,
        })
    return roster


def main():
    now = datetime.now(timezone.utc)
    members = fetch_current_members()
    wars = fetch_war_log()

    history, first_run = load_history()
    history = update_history(history, members, now, first_run)
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2, sort_keys=True)

    output = {
        "updated": now.strftime(DATE_FMT),
        "season1": "Previous War",
        "season2": "War Before That",
        "members": build_roster(members, wars, history, now),
    }
    with open("data/wars.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote data/wars.json with {len(output['members'])} current clan members.")


if __name__ == "__main__":
    main()
