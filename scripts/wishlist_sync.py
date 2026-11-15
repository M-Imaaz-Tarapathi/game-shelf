"""Save your Steam wishlist to data/wishlist.json for the site's Wishlist view.

For each game it keeps the name, Steam art, release info and current price
(including any sale). Uses the same STEAM_API_KEY and STEAM_ID secrets as the
playtime sync. The wishlist must be visible: Steam shows it to others when
"Game details" is set to Public in your privacy settings.
"""
import json
import os
import sys
import time
import urllib.parse

from common import load_json, request, save_json
from steam_sync import steam_id64

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "wishlist.json")
CDN = "https://shared.akamai.steamstatic.com/store_item_assets/"
COUNTRY = os.environ.get("STEAM_COUNTRY", "AE")


def get_json(url):
    return json.loads(request(url))


def wishlist(key, sid):
    q = urllib.parse.urlencode({"key": key, "steamid": sid})
    resp = get_json("https://api.steampowered.com/IWishlistService/GetWishlist/v1/?" + q).get("response", {})
    return resp.get("items") or []


def asset_url(assets, name):
    fmt, file = assets.get("asset_url_format"), assets.get(name)
    return CDN + fmt.replace("${FILENAME}", file) if fmt and file else None


def store_items(appids):
    """Name, art, release and price for each app, in batches, via IStoreBrowseService."""
    found = {}
    for i in range(0, len(appids), 40):
        chunk = appids[i:i + 40]
        body = {
            "ids": [{"appid": a} for a in chunk],
            "context": {"language": "english", "country_code": COUNTRY, "steam_realm": 1},
            "data_request": {"include_assets": True, "include_release": True, "include_all_purchase_options": True},
        }
        url = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?" + urllib.parse.urlencode({"input_json": json.dumps(body)})
        try:
            items = get_json(url).get("response", {}).get("store_items", [])
        except RuntimeError as e:
            print(f"Store lookup failed for a batch: {e}")
            continue
        for it in items:
            appid = it.get("appid") or it.get("id")
            if not appid or it.get("success", 1) != 1:
                continue
            assets = it.get("assets") or {}
            rel = it.get("release") or {}
            buy = it.get("best_purchase_option") or ((it.get("purchase_options") or [None])[0]) or {}
            coming = bool(rel.get("is_coming_soon"))
            release = rel.get("coming_soon_display") or rel.get("custom_release_date_message")
            if not release and rel.get("steam_release_date"):
                release = time.strftime("%-d %b %Y", time.gmtime(rel["steam_release_date"]))
            found[appid] = {
                "name": it.get("name"),
                "cover": asset_url(assets, "library_capsule_2x") or asset_url(assets, "library_capsule"),
                "header": asset_url(assets, "header"),
                "coming_soon": coming,
                "release": release,
                "free": bool(it.get("is_free")),
                "price": buy.get("formatted_final_price"),
                "original_price": buy.get("formatted_original_price"),
                "discount": int(buy.get("discount_pct") or 0),
            }
        time.sleep(0.5)
    return found


def appdetails(appid):
    """Fallback for anything the batch lookup missed: one game at a time from the store API."""
    q = urllib.parse.urlencode({"appids": appid, "cc": COUNTRY.lower(), "l": "english"})
    try:
        data = get_json("https://store.steampowered.com/api/appdetails?" + q).get(str(appid), {})
    except RuntimeError as e:
        print(f"App {appid}: {e}")
        return None
    if not data.get("success"):
        return None
    d = data.get("data") or {}
    po = d.get("price_overview") or {}
    rel = d.get("release_date") or {}
    time.sleep(1.2)  # the store API allows roughly 200 calls per 5 minutes
    return {
        "name": d.get("name"),
        "cover": None,
        "header": d.get("header_image"),
        "coming_soon": bool(rel.get("coming_soon")),
        "release": rel.get("date"),
        "free": bool(d.get("is_free")),
        "price": po.get("final_formatted"),
        "original_price": po.get("initial_formatted") or None,
        "discount": int(po.get("discount_percent") or 0),
    }


def main():
    key, raw = os.environ.get("STEAM_API_KEY"), os.environ.get("STEAM_ID")
    if not key or not raw:
        sys.exit("Add STEAM_API_KEY and STEAM_ID in Settings > Secrets and variables > Actions.")
    sid = steam_id64(key, raw)
    items = wishlist(key, sid)
    if not items:
        # Keep what we had rather than wiping the page if Steam hiccups or the wishlist is private.
        if load_json(OUT):
            print("Steam returned an empty wishlist; keeping the last saved one.")
            return
        print("Steam returned no wishlist. If you have one, set 'Game details' to Public in Steam's privacy settings.")
    appids = [w["appid"] for w in items if w.get("appid")]
    info = store_items(appids)
    out = []
    for w in items:
        a = w.get("appid")
        if not a:
            continue
        d = info.get(a) or appdetails(a) or {}
        out.append({
            "appid": a,
            "name": d.get("name") or f"App {a}",
            "priority": w.get("priority"),
            "added": time.strftime("%Y-%m-%d", time.gmtime(w["date_added"])) if w.get("date_added") else None,
            **{k: v for k, v in d.items() if k != "name"},
        })
    out.sort(key=lambda x: (x["priority"] if x.get("priority") not in (None, 0) else 10**6, x.get("added") or ""))
    save_json(OUT, {"source": "steam", "exported": time.strftime("%Y-%m-%d"), "items": out})
    on_sale = sum(1 for x in out if x.get("discount"))
    print(f"Saved {len(out)} wishlist games ({on_sale} on sale).")


if __name__ == "__main__":
    main()
