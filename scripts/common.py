"""Shared helpers for the Game Shelf GitHub Actions."""
import json
import re
import time
import urllib.error
import urllib.request

UA = {"User-Agent": "GameShelf/2.0 (+github actions)"}
NUMS = {"ii": "2", "iii": "3", "iv": "4", "two": "2", "three": "3", "gta": "grandtheftauto"}
DROP = {"the", "marvels"}


def norm(s):
    """Same matching the page uses: lowercase, drop punctuation and ™, II -> 2, drop 'the'."""
    s = re.sub(r"['’]", "", (s or "").lower())
    words = [NUMS.get(w, w) for w in re.split(r"[^a-z0-9]+", s) if w]
    return "".join(w for w in words if w not in DROP)


def request(url, data=None, headers=None, retries=3):
    body = data.encode("utf-8") if isinstance(data, str) else data
    req = urllib.request.Request(url, data=body, headers={**UA, **(headers or {})})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            detail = e.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"HTTP {e.code} from {url.split('?')[0]}: {detail}")
        except urllib.error.URLError as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError(f"Couldn't reach {url.split('?')[0]}: {e.reason}")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
