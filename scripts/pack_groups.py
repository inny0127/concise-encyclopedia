"""Pack condenser inputs into per-model group files for agents.

Level 1-3 -> sonnet groups of 10; level 4-5 -> haiku groups of 25.
Packs only titles in data/selection.json and skips articles that already have a condensed entry.
Writes data/groups/<model>_<n>.json (a JSON array of inputs).
"""
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_sources import key_for  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / "data" / "condense_input"
DONE = ROOT / "data" / "condensed"
GROUPS = ROOT / "data" / "groups"

done = set()
for f in DONE.glob("*.json"):
    for e in json.loads(f.read_text(encoding="utf-8")):
        done.add(e["key"])

inputs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(INP.glob("*.json"))]
book = {key_for(it["title"]) for it in json.loads((ROOT / "data" / "selection.json").read_text(encoding="utf-8"))}
inputs = [i for i in inputs if i["key"] in book and i["key"] not in done]
GROUPS.mkdir(parents=True, exist_ok=True)
for old in GROUPS.glob("*"):
    old.unlink()

def as_text(items):
    """Line-wrapped plain text so agent file readers never truncate long lines."""
    wrap = lambda s: "\n".join(textwrap.fill(p, 160) for p in s.split("\n") if p.strip())
    out = []
    for i in items:
        out += [f"=== KEY: {i['key']}",
                f"TITLE: {i['title']} | LEVEL: {i['level']} | CATEGORY: {i['category']} | "
                f"IS_PERSON: {i['is_person']} | DESCRIPTION: {i['description']}",
                "CROSSREF_CANDIDATES: " + textwrap.fill(" ; ".join(i["crossref_candidates"]), 160),
                "--- WIKIPEDIA LEAD", wrap(i["wiki_lead"]),
                "--- WIKIPEDIA EXCERPT", wrap(i["wiki_excerpt"]),
                "--- GROKIPEDIA LEAD", wrap(i["grok_lead"]) or "(none)", ""]
    return "\n".join(out)


plan = {"sonnet": ([i for i in inputs if i["level"] <= 3], 10),
        "haiku": ([i for i in inputs if i["level"] >= 4], 25)}
for model, (items, size) in plan.items():
    # Number new groups after finished ones so data/condensed/<group>.json never gets overwritten.
    start = 1 + max((int(f.stem.split("_")[1]) for f in DONE.glob(f"{model}_*.json")), default=-1)
    for n in range(0, len(items), size):
        path = GROUPS / f"{model}_{start + n // size:03d}.json"
        path.write_text(json.dumps(items[n:n + size], ensure_ascii=False, indent=1), encoding="utf-8")
        path.with_suffix(".txt").write_text(as_text(items[n:n + size]), encoding="utf-8")
    print(model, len(items), "entries in", -(-len(items) // size), "groups")
