"""Assemble condensed entries + metadata into book/entries.json and compile the PDF.

Usage: python build_book.py [--out book/pilot.pdf]
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


def show_image(src):
    """Image policy: core topics always, people and level-4 visual subjects when available."""
    if src["level"] <= 3:
        return True
    if src["level"] == 4 and (src.get("person") or src["category"] in
                              {"Geography", "Biology and health sciences", "Arts", "Technology"}):
        return True
    return False


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


def main():
    out_pdf = BOOK / "pilot.pdf"
    if "--out" in sys.argv:
        out_pdf = ROOT / sys.argv[sys.argv.index("--out") + 1]
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    sources = {json.loads(p.read_text(encoding="utf-8"))["key"]: json.loads(p.read_text(encoding="utf-8"))
               for p in SOURCES.glob("*.json")}
    entries, credits = [], []
    for f in DONE.glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            src = sources.get(e["key"])
            if not src:
                continue
            paras = [segments(p.strip()) for p in e["entry"].split("\n\n") if p.strip()]
            item = {"head": e["headword"].strip(), "sort": e["sort_key"].lower().strip(),
                    "dates": life_dates(src.get("person")), "paras": paras, "image": None}
            img = src.get("image")
            if img and img.get("path") and show_image(src):
                item["image"] = prep_image(img["path"], e["key"])
                if item["image"]:
                    credits.append({"head": item["head"], "artist": img.get("artist") or "Unknown",
                                    "license": img.get("license") or "see Wikimedia Commons"})
            entries.append(item)
    entries.sort(key=lambda x: (x["sort"], x["head"]))
    for e in entries:
        e["letter"] = sort_letter(e["sort"])
    credits.sort(key=lambda c: c["head"])
    (BOOK / "entries.json").write_text(json.dumps({"entries": entries, "credits": credits},
                                                  ensure_ascii=False), encoding="utf-8")
    print(f"{len(entries)} entries, {sum(1 for e in entries if e['image'])} images")
    typst.compile(str(BOOK / "main.typ"), output=str(out_pdf), root=str(ROOT))
    print("wrote", out_pdf)


if __name__ == "__main__":
    main()
