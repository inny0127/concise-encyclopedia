"""Build compact condenser inputs: data/condense_input/<key>.json.

Adds cross-reference candidates (outgoing Wikipedia links that are also in the book).
Usage: python prepare_inputs.py [selection.json]   (default: data/vital.json as the book's title set)
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fetch_sources import SOURCES, wp

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "condense_input"
REDIRECTS = ROOT / "data" / "redirects.json"
EXCERPT_CHARS = {1: 8000, 2: 8000, 3: 6000, 4: 4000, 5: 3000}


def mentioned(title, text):
    """Keep only candidates the source text actually talks about."""
    base = title.split(" (")[0].lower()
    return base in text


LINK = re.compile(r"\[\[([^\[\]|#]+)(?:#[^\[\]|]*)?(?:\|[^\[\]]*)?\]\]")


def body_links(titles):
    """{title: set of link targets} parsed from wikitext, 50 articles per request.

    Wikitext holds the article's own links but not navbox links, which are never "mentioned"
    in the text anyway. prop=links would cost ~2 requests per article (~1,000 links each)."""
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        data = wp(action="query", titles="|".join(batch), prop="revisions", rvprop="content", rvslots="main")
        for page in (data or {}).get("query", {}).get("pages", []):
            rev = (page.get("revisions") or [{}])[0]
            text = rev.get("slots", {}).get("main", {}).get("content", "")
            targets = set()
            for m in LINK.finditer(text):
                t = m.group(1).strip().replace("_", " ")
                if t and ":" not in t[:1]:
                    targets.add(t[0].upper() + t[1:])
            out[page["title"]] = targets
        print(f"  links: {min(i + 50, len(titles))}/{len(titles)}", flush=True)
    return out


def redirect_map(book_titles):
    """{redirect title: book title} for every redirect pointing at a book title (cached).
    Wikitext often links through redirects ([[oil]] for Petroleum)."""
    if REDIRECTS.exists():
        return json.loads(REDIRECTS.read_text(encoding="utf-8"))
    out, titles = {}, sorted(book_titles)
    for i in range(0, len(titles), 50):
        cont = {}
        while True:
            data = wp(action="query", titles="|".join(titles[i:i + 50]), prop="redirects",
                      rdprop="title", rdnamespace=0, rdlimit="max", **cont)
            for page in (data or {}).get("query", {}).get("pages", []):
                for r in page.get("redirects", []):
                    out[r["title"]] = page["title"]
            if not data or "continue" not in data:
                break
            cont = data["continue"]
        if i % 2500 == 0:
            print(f"  redirects: {i}/{len(titles)}", flush=True)
    REDIRECTS.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    return out


def main(selection_path):
    book_titles = {it["title"] for it in json.loads(Path(selection_path).read_text(encoding="utf-8"))}
    OUT.mkdir(parents=True, exist_ok=True)
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in SOURCES.glob("*.json")]
    todo = [r for r in recs if not (OUT / f"{r['key']}.json").exists() or "--rebuild" in sys.argv]

    redirects = redirect_map(book_titles)
    links = {t: {redirects.get(l, l) for l in ls}
             for t, ls in body_links(sorted({r["wiki_title"] for r in todo})).items()}

    def one(r):
        excerpt = r["wiki_fulltext"][:EXCERPT_CHARS[r["level"]]]
        text = (r["wiki_lead"] + " " + excerpt + " " + r["grok_lead"]).lower()
        cands = sorted({l for l in links.get(r["wiki_title"], ()) if l in book_titles and l != r["title"] and mentioned(l, text)})
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
