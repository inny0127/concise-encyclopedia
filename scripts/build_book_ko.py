"""Build the Korean edition (or a pilot of it) from translated entries.

Translated files are JSON arrays of {"key", "ko_headword", "orig", "ko_sort", "entry"} (style_guide_ko.md).
Entries sort in 가나다 order by ko_sort; letter dividers use the initial consonant (ㄲ under ㄱ, ...).
Life dates are written the Korean way, without places (Wikidata places are English).

Usage: python build_book_ko.py [--src data/ko/translated] [--volumes 3] [--name ko] [--out book/ko.pdf] [--light] [--pilot]
"""
import json
import subprocess
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


def collect(src_dir):
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
                    "words": len(e["entry"].split()), "dates": ko_life(src.get("person")), "paras": paras,
                    "image": None, "credit": None}
            img = src.get("image")
            if img and img.get("path") and (bb.IMG_IN / img["path"]).exists() and bb.show_image(src):
                item["image"] = bb.prep_image(img["path"], e["key"])
                if item["image"]:
                    item["credit"] = {"artist": img.get("artist") or "작자 미상",
                                      "license": img.get("license") or "위키미디어 공용 참조"}
            entries.append(item)
    entries.sort(key=lambda x: (x["sort"], x["level"], x["key"]))
    for e in entries:
        e["letter"] = initial(e["sort"])
    bb.number_homographs(entries)
    return entries


def compile_volume(name, data, out_pdf, pdf=True):
    (bb.BOOK / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    kw = dict(root=str(bb.ROOT), font_paths=[str(bb.ROOT / "fonts")], sys_inputs={"data": f"{name}.json"})
    typ = str(bb.BOOK / "main_ko.typ")
    if pdf:
        bb.typst.compile(typ, output=str(out_pdf), **kw)
        print("wrote", out_pdf.relative_to(bb.ROOT), flush=True)
        if data["index"]:
            return None
    found = json.loads(bb.typst.query(typ, "<idx>", field="value", **kw))
    (bb.BOOK / f"{name}_pages.json").write_text(json.dumps(found, ensure_ascii=False), encoding="utf-8")
    return found


def main():
    """--volumes N splits at initial-consonant boundaries, one process per volume (as in build_book.py);
    the last volume carries the index of all headwords. --pilot marks the title page as a pilot."""
    n_vol = int(bb.arg("--volumes", 1))
    only = int(bb.arg("--only", 0))
    if n_vol > 1 and not only:
        for i in range(1, n_vol + 1):
            subprocess.run([sys.executable, __file__, *sys.argv[1:], "--only", str(i)], check=True)
        return
    src_dir = bb.ROOT / bb.arg("--src", "data/ko/translated")
    bb.IMG_OUT.mkdir(parents=True, exist_ok=True)
    entries = collect(src_dir)
    vols = bb.split_volumes(entries, n_vol) if n_vol > 1 else [entries]
    print(f"{len(entries)} entries, {sum(1 for e in entries if e['image'])} images, "
          f"{sum(1 for e in entries if e['hom'])} numbered homographs", flush=True)
    suffix = "_light" if bb.LIGHT else ""
    base = bb.arg("--name", "ko")
    pages = []
    for i, vol in enumerate(vols, 1):
        first, last = (e["letter"] for e in (vol[0], vol[-1]))
        first = "ㄱ" if first == "#" else first
        span = first if first == last else f"{first}\u2013{last}"
        credits = sorted(({"head": e["head"], "hom": e["hom"], **e["credit"]} for e in vol if e["credit"]),
                         key=lambda c: c["head"])
        data = {"volume": f"제{i}권" if n_vol > 1 else "", "span": span if n_vol > 1 else "",
                "pilot": "--pilot" in sys.argv, "entries": vol, "credits": credits, "index": []}
        name = f"{base}_vol{i}{suffix}" if n_vol > 1 else f"{base}{suffix}"
        out_pdf = bb.ROOT / bb.arg("--out", f"book/{name}.pdf") if n_vol == 1 else bb.BOOK / f"{name}.pdf"
        print(f"{data['volume'] or 'Book'} {span}: {len(vol)} entries", flush=True)
        last_vol = i == n_vol
        if only and i != only and not (only == n_vol and not last_vol):
            continue
        if n_vol == 1:
            compile_volume(name, data, out_pdf)
            return
        if only and i != only:
            saved = bb.BOOK / f"{name}_pages.json"
            if not saved.exists():
                sys.exit(f"{saved.name} missing: build volume {i} first")
            found = json.loads(saved.read_text(encoding="utf-8"))
        else:
            found = compile_volume(name, data, out_pdf, pdf=not last_vol)
        pages += [(f["h"], f["n"], f["s"], str(i), f["p"]) for f in found]
        if last_vol:
            data["index"] = [{"h": h, "n": hn, "v": v, "p": p}
                             for h, hn, srt, v, p in sorted(pages, key=lambda x: (x[2], x[0], x[1]))]
            compile_volume(name, data, out_pdf)


if __name__ == "__main__":
    main()
