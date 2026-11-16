"""Fetch source material for each article into data/sources/<key>.json (resumable).

Usage: python fetch_sources.py data/pilot_titles.json
"""
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
IMAGES = ROOT / "data" / "images"
WP_API = "https://en.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
# Wikimedia asks for a contact in the User-Agent; set CE_CONTACT to add one.
_contact = os.environ.get("CE_CONTACT")
UA = "ConciseEncyclopedia/0.1 (personal print project" + (f"; {_contact})" if _contact else ")")
FULLTEXT_CHARS = 12000
IMAGE_WIDTH = 900

session = requests.Session()
session.headers.update({"User-Agent": UA})


def get(url, params=None, as_json=True):
    """GET with retries. None only for a real 404; persistent failure raises, so a throttled
    request never gets cached as an empty field."""
    for attempt in range(10):
        wait = 2 ** min(attempt, 6)
        try:
            r = session.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json() if as_json else r
            if r.status_code == 404:
                return None
            if r.headers.get("retry-after", "").isdigit():
                wait = int(r.headers["retry-after"]) + 1
        except requests.RequestException:
            pass
        time.sleep(wait)
    raise RuntimeError(f"request kept failing: {url} {params or ''}"[:300])


def wp(**params):
    return get(WP_API, params | {"format": "json", "formatversion": 2})


def key_for(title):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")[:60]
    return f"{slug}_{hashlib.md5(title.encode()).hexdigest()[:6]}"


def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


# ---------- Wikipedia ----------

def wiki_batch(titles):
    """Lead extract, description, page image and Wikidata id for up to 20 titles."""
    data = wp(action="query", titles="|".join(titles), redirects=1,
              prop="extracts|description|pageimages|pageprops",
              exintro=1, explaintext=1, exlimit=20, piprop="name", ppprop="wikibase_item")
    out = {}
    if not data:
        return out
    q = data["query"]
    back = {t: t for t in titles}
    for n in q.get("normalized", []):
        back[n["to"]] = n["from"]
    for r in q.get("redirects", []):
        back[r["to"]] = back.get(r["from"], r["from"])
    for p in q["pages"]:
        if p.get("missing"):
            continue
        orig = back.get(p["title"], p["title"])
        out[orig] = {
            "wiki_title": p["title"],
            "description": p.get("description", ""),
            "wiki_lead": p.get("extract", ""),
            "image_file": p.get("pageimage"),
            "wikidata": p.get("pageprops", {}).get("wikibase_item"),
        }
    return out


def wiki_fulltext(title):
    data = wp(action="query", titles=title, prop="extracts", explaintext=1, exsectionformat="plain")
    if not data:
        return ""
    text = data["query"]["pages"][0].get("extract", "")
    text = re.split(r"\n(See also|References|Notes|Further reading|External links|Bibliography)\n", text)[0]
    return text[:FULLTEXT_CHARS]


# ---------- Wikidata (life dates for people) ----------

def wd_time(claims, prop):
    for c in claims.get(prop, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and "time" in v:
            t, prec = v["time"], v.get("precision", 11)
            year = int(t[:t.index("-", 1)])
            m, d = t[t.index("-", 1) + 1:].split("-")[:2]
            return {"year": year, "month": int(m) if prec >= 10 else 0,
                    "day": int(d[:2]) if prec >= 11 else 0, "precision": prec}
    return None


def wd_item(claims, prop):
    for c in claims.get(prop, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, dict) and "id" in v:
            return v["id"]
    return None


def wikidata_people(qids):
    people, place_ids = {}, set()
    for batch in chunks(qids, 50):
        data = get(WD_API, {"action": "wbgetentities", "ids": "|".join(batch), "props": "claims", "format": "json"})
        for qid, ent in (data or {}).get("entities", {}).items():
            claims = ent.get("claims", {})
            if wd_item(claims, "P31") != "Q5":
                continue
            rec = {"born": wd_time(claims, "P569"), "died": wd_time(claims, "P570"),
                   "birthplace": wd_item(claims, "P19"), "deathplace": wd_item(claims, "P20")}
            place_ids |= {rec["birthplace"], rec["deathplace"]} - {None}
            people[qid] = rec
    labels = {}
    for batch in chunks(sorted(place_ids), 50):
        data = get(WD_API, {"action": "wbgetentities", "ids": "|".join(batch), "props": "labels",
                            "languages": "en", "format": "json"})
        for qid, ent in (data or {}).get("entities", {}).items():
            labels[qid] = ent.get("labels", {}).get("en", {}).get("value")
    for rec in people.values():
        rec["birthplace"] = labels.get(rec["birthplace"])
        rec["deathplace"] = labels.get(rec["deathplace"])
    return people


# ---------- Images ----------

def image_info(files):
    info = {}
    for batch in chunks(files, 50):
        data = wp(action="query", titles="|".join("File:" + f for f in batch), prop="imageinfo",
                  iiprop="url|extmetadata|mime", iiurlwidth=IMAGE_WIDTH)
        for p in (data or {}).get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [None])[0]
            if not ii:
                continue
            meta = ii.get("extmetadata", {})
            clean = lambda k: BeautifulSoup(meta.get(k, {}).get("value", ""), "lxml").get_text(" ", strip=True)
            info[p["title"].removeprefix("File:").replace(" ", "_")] = {
                "url": ii.get("thumburl") or ii.get("url"),
                "artist": clean("Artist")[:120],
                "license": clean("LicenseShortName"),
            }
    return info


def download_image(url, key):
    ext = ".png" if url.lower().endswith(".png") else ".jpg"
    path = IMAGES / f"{key}{ext}"
    if not path.exists():
        r = get(url, as_json=False)
        if r is None:
            return None
        path.write_bytes(r.content)
    return path.name


# ---------- Grokipedia ----------

def grokipedia_lead(title):
    r = get("https://grokipedia.com/page/" + quote(title.replace(" ", "_")), as_json=False)
    if r is None:
        return ""
    soup = BeautifulSoup(r.text, "lxml")
    art = soup.find("article")
    if not art or not art.find("h1"):
        return ""
    for t in art.find_all(["script", "style", "button", "svg", "nav", "aside", "dl"]):
        t.decompose()
    for c in art.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    h2 = art.find("h2")
    parts = []
    for s in art.find("h1").find_all_next(string=True):
        if h2 is not None and (s.parent is h2 or h2 in s.parents):
            break
        parts.append(s.strip())
    text = " ".join(p for p in parts if p)
    text = re.sub(r"^.*?Fact-checked by Grok[^A-Z]*?ago\s*", "", text)
    text = re.sub(r"\s*\[\d+\]", "", text)
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    return text.strip()


# ---------- main ----------

def main(list_path):
    SOURCES.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    items = json.loads(Path(list_path).read_text(encoding="utf-8"))
    todo = [it for it in items if not (SOURCES / f"{key_for(it['title'])}.json").exists()]
    print(f"{len(items)} articles, {len(todo)} to fetch", flush=True)

    for batch in chunks(todo, 20):
        wiki = {}
        for sub in chunks([it["title"] for it in batch], 20):
            wiki |= wiki_batch(sub)
        qids = [w["wikidata"] for w in wiki.values() if w.get("wikidata")]
        people = wikidata_people(qids)
        imgs = image_info([w["image_file"] for w in wiki.values() if w.get("image_file")])

        def one(it):
            try:
                return fetch_one(it)
            except RuntimeError as e:  # leave uncached; the next run retries it
                return it["title"], f"error ({e})"

        def fetch_one(it):
            w = wiki.get(it["title"])
            if not w:
                return it["title"], "missing"
            key = key_for(it["title"])
            rec = it | w
            rec["key"] = key
            rec["wiki_fulltext"] = wiki_fulltext(w["wiki_title"])
            rec["person"] = people.get(w.get("wikidata"))
            rec["grok_lead"] = grokipedia_lead(w["wiki_title"])
            img = imgs.get((w.get("image_file") or "").replace(" ", "_"))
            if img and img["url"]:
                rec["image"] = img | {"path": download_image(img["url"], key)}
            (SOURCES / f"{key}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            return it["title"], "ok"

        with ThreadPoolExecutor(4) as ex:
            for title, status in ex.map(one, batch):
                if status != "ok":
                    print("  ", status, title, flush=True)
        done = sum(1 for _ in SOURCES.glob("*.json"))
        print(f"fetched batch; {done} cached", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
