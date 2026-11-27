"""Build the Korean edition (or a pilot of it) from translated entries.

Translated files are JSON arrays of {"key", "ko_headword", "orig", "ko_sort", "entry"} (style_guide_ko.md).
Entries sort in 가나다 order by ko_sort; letter dividers use the initial consonant (ㄲ under ㄱ, ...).
Life dates are written the Korean way, without places (Wikidata places are English).

Usage: python build_book_ko.py --src data/ko/translated --out book/ko.pdf [--light]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_book as bb  # noqa: E402

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
MERGE = {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}


def initial(s):
    c = s[:1]
    if "가" <= c <= "힣":
        ch = CHO[(ord(c) - 0xAC00) // 588]
        return MERGE.get(ch, ch)
    return "#"


def ko_date(d):
    if not d or d["precision"] < 9:
        return None
    y = d["year"]
    out = f"기원전 {-y}년" if y < 0 else f"{y}년"
    if d["precision"] >= 10 and d.get("month"):
        out += f" {d['month']}월"
        if d["precision"] >= 11 and d.get("day"):
            out += f" {d['day']}일"
    return out


def ko_life(p):
    if not p:
        return ""
    b, d = ko_date(p.get("born")), ko_date(p.get("died"))
    if b and d:
        return f"({b} ~ {d})"
    if b and not p.get("died"):
        return f"({b} ~ )"
    return f"(~ {d})" if d else ""


def main():
    src_dir = bb.ROOT / bb.arg("--src", "data/ko/translated")
    out_pdf = bb.ROOT / bb.arg("--out", "book/ko.pdf")
    bb.IMG_OUT.mkdir(parents=True, exist_ok=True)
    sources = {}
    for p in bb.SOURCES.glob("*.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        sources[s["key"]] = s
    entries = []
    for f in sorted(src_dir.glob("*.json")):
        for e in json.loads(f.read_text(encoding="utf-8")):
            src = sources[e["key"]]
            paras = [bb.segments(x.strip()) for x in e["entry"].split("\n\n") if x.strip()]
            item = {"head": e["ko_headword"].strip(), "orig": (e.get("orig") or "").strip(),
                    "sort": e["ko_sort"].strip(), "hom": 0, "level": src["level"], "key": e["key"],
                    "dates": ko_life(src.get("person")), "paras": paras, "image": None}
            img = src.get("image")
            if img and img.get("path") and (bb.IMG_IN / img["path"]).exists() and bb.show_image(src):
                item["image"] = bb.prep_image(img["path"], e["key"])
            entries.append(item)
    entries.sort(key=lambda x: (x["sort"], x["level"], x["key"]))
    for e in entries:
        e["letter"] = initial(e["sort"])
    bb.number_homographs(entries)
    data = {"entries": entries, "credits": [], "index": []}
    (bb.BOOK / "ko.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    bb.typst.compile(str(bb.BOOK / "main_ko.typ"), output=str(out_pdf), root=str(bb.ROOT),
                     font_paths=[str(bb.ROOT / "fonts")], sys_inputs={"data": "ko.json"})
    print(f"{len(entries)} entries, {sum(1 for e in entries if e['image'])} images -> {out_pdf.relative_to(bb.ROOT)}")


if __name__ == "__main__":
    main()
