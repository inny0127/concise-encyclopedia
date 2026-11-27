"""Assemble condensed entries + metadata and compile the book as print PDFs.

The book is split into volumes at letter boundaries of roughly equal length (book/vol1.pdf ...).
Homographs (same headword) are numbered Bar¹, Bar² in a stable order: level, then key.
The last volume ends with an index of every headword with its volume and page; page numbers
come from a first compile of each volume (Typst query on <idx> metadata).

Usage: python build_book.py [--volumes 3] [--light] [--only 2]
  --volumes N   number of volumes (1 builds a single book)
  --light       small images for phone/email viewing (writes book/vol*_light.pdf)
  --only K      rebuild only volume K (the index is skipped unless K is the last volume)
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import typst
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "data" / "sources"
DONE = ROOT / "data" / "condensed"
IMG_IN = ROOT / "data" / "images"
LIGHT = "--light" in sys.argv  # small images for email/phone viewing
IMG_OUT = ROOT / "data" / ("images_light" if LIGHT else "images_print")
BOOK = ROOT / "book"

MONTHS = "January February March April May June July August September October November December".split()
TOKEN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]|\*([^*]+)\*")


IMAGE_CAP = 2000  # roughly one image per page; the policy alone would pick about 6,000
IMAGE_CATEGORIES = {"Geography", "Biology and health sciences", "Arts", "Technology"}
_IMAGE_KEYS = None


def image_eligible(src):
    """Policy: core topics (Level 1-3) always; Level 4 people and visual subjects compete for the rest."""
    if not (src.get("image") and src["image"].get("url")):
        return False
    return src["level"] <= 3 or (src["level"] == 4 and (src.get("person") or src["category"] in IMAGE_CATEGORIES))


def image_keys():
    """Keys of the entries that get an image: all eligible Level 1-3, then Level 4 by pageviews, up to IMAGE_CAP."""
    global _IMAGE_KEYS
    if _IMAGE_KEYS is None:
        views = {}
        for f in (ROOT / "data" / "pageviews").glob("*.json"):
            for title, n in json.loads(f.read_text(encoding="utf-8")).items():
                views[title] = views.get(title, 0) + n
        cands = []
        for f in SOURCES.glob("*.json"):
            src = json.loads(f.read_text(encoding="utf-8"))
            if image_eligible(src):
                cands.append((src["level"] > 3, -views.get(src["title"], 0), src["key"]))
        _IMAGE_KEYS = {k for _, _, k in sorted(cands)[:IMAGE_CAP]}
    return _IMAGE_KEYS


def show_image(src):
    return src["key"] in image_keys()


def fmt_date(d):
    if not d or d["precision"] < 9:
        return None
    y = d["year"]
    year = f"{-y} BC" if y < 0 else str(y)
    if d["precision"] >= 11 and d["month"] and d["day"]:
        return f"{MONTHS[d['month'] - 1]} {d['day']}, {year}"
    if d["precision"] >= 10 and d["month"]:
        return f"{MONTHS[d['month'] - 1]} {year}"
    return year


def life_dates(p):
    if not p:
        return ""
    born, died = fmt_date(p.get("born")), fmt_date(p.get("died"))
    b = f"b. {born}" + (f", {p['birthplace']}" if p.get("birthplace") else "") if born else ""
    d = f"d. {died}" + (f", {p['deathplace']}" if p.get("deathplace") else "") if died else ""
    if b and d:
        return f"({b}—{d})"
    if b and not p.get("died"):
        return f"({b})"
    return f"({d})" if d else ""


def curly(text):
    text = re.sub(r'(^|[\s(\[—–-])"', "\\1\u201c", text)
    text = text.replace('"', "\u201d")
    text = re.sub(r"(^|[\s(\[—–-])'", "\\1\u2018", text)
    return text.replace("'", "\u2019")


def segments(text):
    """Split entry text into typed runs: text / italic / crossref."""
    text = curly(text)
    out, pos = [], 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            out.append({"t": "text", "v": text[pos:m.start()]})
        if m.group(1):
            out.append({"t": "xref", "v": m.group(2) or m.group(1)})
        else:
            out.append({"t": "ital", "v": m.group(3)})
        pos = m.end()
    if pos < len(text):
        out.append({"t": "text", "v": text[pos:]})
    return out


def prep_image(name, key):
    """Normalize to RGB JPEG at print width so Typst never sees odd formats."""
    src = IMG_IN / name
    dst = IMG_OUT / f"{key}.jpg"
    if not dst.exists():
        try:
            im = Image.open(src)
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, "white")
                bg.paste(im, mask=im.split()[-1])
                im = bg
            im = im.convert("RGB")
            if LIGHT:
                im.thumbnail((450, 450))
            im.save(dst, "JPEG", quality=70 if LIGHT else 88)
        except OSError:
            return None
    with Image.open(dst) as im:
        w, h = im.size
    return {"path": f"/data/{IMG_OUT.name}/{key}.jpg", "ratio": h / w}


def sort_letter(sort_key):
    c = unicodedata.normalize("NFKD", sort_key)[:1].upper()
    return c if c.isalpha() else "#"


ROMAN = ["", "I", "II", "III", "IV", "V", "VI"]


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def collect():
    sources = {}
    for p in SOURCES.glob("*.json"):
        src = json.loads(p.read_text(encoding="utf-8"))
        sources[src["key"]] = src
    entries = []
    for f in DONE.glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            src = sources.get(e["key"])
            if not src:
                continue
            paras = [segments(p.strip()) for p in e["entry"].split("\n\n") if p.strip()]
            item = {"head": e["headword"].strip(), "sort": e["sort_key"].lower().strip(), "hom": 0,
                    "level": src["level"], "key": e["key"], "words": len(e["entry"].split()),
                    "dates": life_dates(src.get("person")), "paras": paras, "image": None, "credit": None}
            img = src.get("image")
            if img and img.get("path") and (IMG_IN / img["path"]).exists() and show_image(src):
                item["image"] = prep_image(img["path"], e["key"])
                if item["image"]:
                    item["credit"] = {"artist": img.get("artist") or "Unknown",
                                      "license": img.get("license") or "see Wikimedia Commons"}
            entries.append(item)
    return entries


def number_homographs(entries):
    groups = {}
    for e in entries:
        groups.setdefault(e["head"], []).append(e)
    for same in groups.values():
        if len(same) > 1:
            for i, e in enumerate(sorted(same, key=lambda x: (x["level"], x["key"])), 1):
                e["hom"] = i


def split_volumes(entries, n):
    """Cut at letter boundaries so each volume has about the same amount of text and images."""
    weight = [e["words"] + (90 if e["image"] else 0) for e in entries]
    total, cuts, run = sum(weight), [], 0
    starts = [i for i, e in enumerate(entries) if i == 0 or e["letter"] != entries[i - 1]["letter"]]
    for k in range(1, n):
        target = total * k / n
        best = min(starts, key=lambda i: abs(sum(weight[:i]) - target))
        cuts.append(best)
    bounds = [0] + sorted(set(cuts)) + [len(entries)]
    return [entries[a:b] for a, b in zip(bounds, bounds[1:])]


def compile_volume(name, data, out_pdf):
    (BOOK / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    inputs = {"data": f"{name}.json"}
    typst.compile(str(BOOK / "main.typ"), output=str(out_pdf), root=str(ROOT), sys_inputs=inputs)
    found = json.loads(typst.query(str(BOOK / "main.typ"), "<idx>", field="value", root=str(ROOT), sys_inputs=inputs))
    print("wrote", out_pdf.relative_to(ROOT), flush=True)
    return found


def main():
    n_vol = int(arg("--volumes", 3))
    only = int(arg("--only", 0))
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    entries = collect()
    entries.sort(key=lambda x: (x["sort"], x["head"], x["level"], x["key"]))
    for e in entries:
        e["letter"] = sort_letter(e["sort"])
    number_homographs(entries)
    vols = split_volumes(entries, n_vol)
    print(f"{len(entries)} entries, {sum(1 for e in entries if e['image'])} images, "
          f"{sum(1 for e in entries if e['hom'])} numbered homographs", flush=True)
    suffix = "_light" if LIGHT else ""
    pages = []  # (head, hom, sort, volume, page)
    for i, vol in enumerate(vols, 1):
        first, last = (e["letter"] for e in (vol[0], vol[-1]))
        first = "A" if first == "#" else first  # entries starting with a digit (100 meters) open volume I
        span = first if first == last else f"{first}\u2013{last}"
        credits = sorted(({"head": e["head"], "hom": e["hom"], **e["credit"]} for e in vol if e["credit"]),
                         key=lambda c: c["head"])
        data = {"title": "A Concise Encyclopedia",
                "volume": f"Volume {ROMAN[i]}" if n_vol > 1 else "",
                "span": span if n_vol > 1 else "", "entries": vol, "credits": credits, "index": []}
        name = f"vol{i}{suffix}" if n_vol > 1 else f"book{suffix}"
        print(f"{data['volume'] or 'Book'} {span}: {len(vol)} entries", flush=True)
        last_vol = i == n_vol
        if only and i != only and not (only == n_vol and not last_vol):
            continue
        if only and i != only:  # rebuilding the last volume: earlier volumes are only queried for page numbers
            (BOOK / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            found = json.loads(typst.query(str(BOOK / "main.typ"), "<idx>", field="value", root=str(ROOT),
                                           sys_inputs={"data": f"{name}.json"}))
        else:
            found = compile_volume(name, data, BOOK / f"{name}.pdf")
        pages += [(f["h"], f["n"], f["s"], ROMAN[i] if n_vol > 1 else "", f["p"]) for f in found]
        if last_vol:
            data["index"] = [{"h": h, "n": hn, "v": v, "p": p}
                             for h, hn, srt, v, p in sorted(pages, key=lambda x: (x[2], x[0], x[1]))]
            compile_volume(name, data, BOOK / f"{name}.pdf")


if __name__ == "__main__":
    main()
