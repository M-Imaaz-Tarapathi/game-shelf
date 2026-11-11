"""Save your Steam library and playtime to data/steam.json for the site's Steam review.

Needs the STEAM_API_KEY and STEAM_ID repository secrets. STEAM_ID can be your
profile link, custom URL name, or 17-digit SteamID64.
"""
import json
import os
import re
import sys
import time
import urllib.parse

from common import request, save_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "steam.json")


def steam_id64(key, raw):
    sid = raw.strip().rstrip("/")
    m = re.search(r"steamcommunity\.com/(id|profiles)/([^/]+)", sid)
    if m:
        sid = m.group(2)
    if re.fullmatch(r"\d{17}", sid):
        return sid
    q = urllib.parse.urlencode({"key": key, "vanityurl": sid})
    resp = json.loads(request("https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/?" + q)).get("response", {})
    if resp.get("success") != 1:
        sys.exit(f"Couldn't find a Steam profile at '{sid}'. Check the STEAM_ID secret.")
    return resp["steamid"]


def main():
    key, raw = os.environ.get("STEAM_API_KEY"), os.environ.get("STEAM_ID")
    if not key or not raw:
        sys.exit("Add STEAM_API_KEY and STEAM_ID in Settings > Secrets and variables > Actions.")
    sid = steam_id64(key, raw)
    q = urllib.parse.urlencode({"key": key, "steamid": sid, "include_appinfo": 1,
                                "include_played_free_games": 1, "format": "json"})
    games = json.loads(request("https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?" + q)).get("response", {}).get("games")
    if not games:
        sys.exit("Steam returned no games. Set 'Game details' to Public in your Steam privacy settings.")
    out = [{
        "name": g.get("name") or f"App {g['appid']}",
        "appid": g["appid"],
        "hours": round(g.get("playtime_forever", 0) / 60, 1),
        "last_played": time.strftime("%Y-%m-%d", time.gmtime(g["rtime_last_played"])) if g.get("rtime_last_played") else None,
    } for g in games]
    out.sort(key=lambda g: (-g["hours"], g["name"]))
    save_json(OUT, {"source": "steam", "exported": time.strftime("%Y-%m-%d"), "games": out})
    print(f"Saved {len(out)} Steam games.")


if __name__ == "__main__":
    main()
