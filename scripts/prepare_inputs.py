"""Build compact condenser inputs: data/condense_input/<key>.json.

Adds cross-reference candidates (outgoing Wikipedia links that are also in the book).
Usage: python prepare_inputs.py [selection.json]   (default: data/vital.json as the book's title set)
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fetch_sources import SOURCES, wp

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "condense_input"
EXCERPT_CHARS = {1: 8000, 2: 8000, 3: 6000, 4: 4000, 5: 3000}


def mentioned(title, text):
    """Keep only candidates the source text actually talks about."""
    base = title.split(" (")[0].lower()
    return base in text


def outgoing_links(title):
    links, cont = [], {}
    while True:
        data = wp(action="query", titles=title, prop="links", plnamespace=0, pllimit="max", **cont)
        if not data:
            return links
        for p in data["query"]["pages"]:
            links += [l["title"] for l in p.get("links", [])]
        if "continue" not in data:
            return links
        cont = data["continue"]


def main(selection_path):
    book_titles = {it["title"] for it in json.loads(Path(selection_path).read_text(encoding="utf-8"))}
    OUT.mkdir(parents=True, exist_ok=True)
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in SOURCES.glob("*.json")]
    todo = [r for r in recs if not (OUT / f"{r['key']}.json").exists() or "--rebuild" in sys.argv]

    def one(r):
        excerpt = r["wiki_fulltext"][:EXCERPT_CHARS[r["level"]]]
        text = (r["wiki_lead"] + " " + excerpt + " " + r["grok_lead"]).lower()
        links = outgoing_links(r["wiki_title"])
        cands = sorted({l for l in links if l in book_titles and l != r["title"] and mentioned(l, text)})
        person = r.get("person")
        inp = {
            "key": r["key"],
            "title": r["title"],
            "level": r["level"],
            "category": r["category"],
            "description": r["description"],
            "is_person": bool(person),
            "wiki_lead": r["wiki_lead"],
            "wiki_excerpt": excerpt,
            "grok_lead": r["grok_lead"],
            "crossref_candidates": cands,
        }
        (OUT / f"{r['key']}.json").write_text(json.dumps(inp, ensure_ascii=False, indent=1), encoding="utf-8")
        return len(cands)

    with ThreadPoolExecutor(4) as ex:
        counts = list(ex.map(one, todo))
    print(f"wrote {len(todo)} inputs; median crossref candidates "
          f"{sorted(counts)[len(counts) // 2] if counts else 0}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else str(ROOT / "data" / "vital.json"))
