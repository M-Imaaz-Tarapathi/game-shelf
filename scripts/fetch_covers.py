"""Download an official IGDB cover for every game that doesn't have one yet.

Covers are saved as covers/<game id>.jpg. This script never edits data/games.json,
so it can't clash with edits made from the website while it runs.

Needs the TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET repository secrets.
"""
import json
import os
import sys
import time
import urllib.parse

from common import load_json, norm, request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = os.path.join(ROOT, "data", "games.json")
OVERRIDES = os.path.join(ROOT, "data", "overrides.json")
COVERS = os.path.join(ROOT, "covers")
REPORT = os.path.join(ROOT, "data", "covers_report.txt")


def token(cid, secret):
    q = urllib.parse.urlencode({"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"})
    return json.loads(request("https://id.twitch.tv/oauth2/token?" + q, data=""))["access_token"]


def igdb(cid, tok, query):
    time.sleep(0.3)  # IGDB allows 4 requests a second
    headers = {"Client-ID": cid, "Authorization": "Bearer " + tok}
    return json.loads(request("https://api.igdb.com/v4/games", data=query, headers=headers))


def find_cover(cid, tok, title, override):
    fields = "fields name,cover.image_id,version_parent,total_rating_count,first_release_date;"
    if isinstance(override, int) or (isinstance(override, str) and override.isdigit()):
        rows = [r for r in igdb(cid, tok, f"{fields} where id = {int(override)};") if r.get("cover")]
        return (rows[0]["name"], rows[0]["cover"]["image_id"], True) if rows else None
    term = override or title
    rows = [r for r in igdb(cid, tok, f'search "{term.replace(chr(34), "")}"; {fields} limit 15;') if r.get("cover")]
    if not rows:
        return None
    wanted = {norm(title), norm(term)}
    exact = [r for r in rows if norm(r["name"]) in wanted]
    pool = exact or rows
    main = [r for r in pool if not r.get("version_parent")] or pool
    pick = max(main, key=lambda r: r.get("total_rating_count") or 0) if exact else main[0]
    name = pick["name"]
    if exact and len(main) > 1 and pick.get("first_release_date"):
        name += time.strftime(" (%Y)", time.gmtime(pick["first_release_date"]))
    return name, pick["cover"]["image_id"], bool(exact) and len(main) == 1


def main():
    cid, secret = os.environ.get("TWITCH_CLIENT_ID"), os.environ.get("TWITCH_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("Add TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET in Settings > Secrets and variables > Actions.")
    games = (load_json(GAMES, {}) or {}).get("games", [])
    overrides = {k: v for k, v in (load_json(OVERRIDES, {}) or {}).items() if not k.startswith("_")}
    os.makedirs(COVERS, exist_ok=True)
    todo = [g for g in games if not g.get("cover") and not os.path.exists(os.path.join(COVERS, g["id"] + ".jpg"))]
    if not todo:
        print("Every game already has a cover.")
        return
    tok = token(cid, secret)
    got, check, missing = [], [], []
    for g in todo:
        title = g["title"]
        try:
            hit = find_cover(cid, tok, title, overrides.get(title))
        except RuntimeError as e:
            print(f"{title}: {e}")
            missing.append(title)
            continue
        if not hit:
            print(f"{title}: no cover on IGDB")
            missing.append(title)
            continue
        name, image_id, exact = hit
        img = request(f"https://images.igdb.com/igdb/image/upload/t_cover_big_2x/{image_id}.jpg")
        with open(os.path.join(COVERS, g["id"] + ".jpg"), "wb") as f:
            f.write(img)
        got.append(title)
        if not exact:
            check.append(f"{title}  ->  used IGDB's \"{name}\"")
        print(f"{title}: {'ok' if exact else 'check, used ' + repr(name)}")

    lines = [f"Last run: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
             f"Added {len(got)} covers, not found {len(missing)}.", ""]
    if check:
        lines += ["Double-check these (not an exact name match, or several games share the name):"] + ["  " + c for c in check] + [""]
    if missing:
        lines += ["No cover found (add a better name or IGDB id to data/overrides.json, or upload one on the site):"] + ["  " + m for m in missing]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
