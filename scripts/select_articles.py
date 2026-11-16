"""Build the candidate article list from Wikipedia's Vital Articles project.

Writes data/vital.json: [{title, level, category}], lowest (most vital) level wins.
"""
import json
import time
from pathlib import Path

import requests

API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "ConciseEncyclopedia/0.1 (personal print project; inny050127@gmail.com)"}
OUT = Path(__file__).resolve().parent.parent / "data" / "vital.json"

session = requests.Session()
session.headers.update(HEADERS)


def api(**params):
    params |= {"format": "json", "formatversion": 2}
    for attempt in range(6):
        try:
            r = session.get(API, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2 ** attempt)
    raise RuntimeError(f"API request failed: {params}")


def list_pages(prefix):
    pages, cont = [], {}
    while True:
        data = api(action="query", list="allpages", apnamespace=4, apprefix=prefix,
                   apfilterredir="nonredirects", aplimit=500, **cont)
        pages += [p["title"] for p in data["query"]["allpages"]]
        if "continue" not in data:
            return pages
        cont = data["continue"]


def page_links(title):
    links, cont = [], {}
    while True:
        data = api(action="query", titles=title, prop="links", plnamespace=0, pllimit=500, **cont)
        for page in data["query"]["pages"]:
            links += [l["title"] for l in page.get("links", [])]
        if "continue" not in data:
            return links
        cont = data["continue"]


def main():
    result = {}
    for level in (1, 2, 3, 4, 5):
        prefix = f"Vital articles/Level {level}"
        skip = ("/Archive", "/Talk", "/Removed", "/Article alerts", "/Statistics")
        pages = [p for p in list_pages(prefix) if not any(s in p for s in skip)]
        for page in pages:
            parts = page.split("/")
            category = parts[2] if len(parts) > 2 else "General"
            links = page_links(page)
            for t in links:
                if t not in result:
                    result[t] = {"title": t, "level": level, "category": category}
            print(f"L{level} {page}: {len(links)} links, total {len(result)}", flush=True)
    OUT.write_text(json.dumps(list(result.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT, len(result))


if __name__ == "__main__":
    main()
