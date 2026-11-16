"""Check condensed entries against the style guide's mechanical rules.

Writes data/failed.json (keys + reasons) and prints a summary.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / "data" / "condense_input"
DONE = ROOT / "data" / "condensed"

HARD_MAX = {1: 600, 2: 600, 3: 330, 4: 180, 5: 110}
SOFT_MIN = {1: 250, 2: 250, 3: 150, 4: 70, 5: 35}
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
FORBIDDEN = [(re.compile(p, re.I), why) for p, why in [
    (r"wikipedia|grokipedia", "mentions source"),
    (r"\[\d+\]", "citation marker"),
    (r"^\s*[#\-•]", "markdown heading/bullet"),
    (r"this article|\bwe\b|\byou\b", "first/second person"),
    (r"\*\*", "bold markup"),
    (r"it is (important|worth) (to note|noting)", "filler"),
]]


def words(entry):
    plain = LINK.sub(lambda m: m.group(2) or m.group(1), entry).replace("*", "")
    return len(plain.split())


def check(e, inp):
    problems = []
    if not all(isinstance(e.get(k), str) and e[k].strip() for k in ("headword", "sort_key", "entry")):
        return ["missing field"]
    n, lvl = words(e["entry"]), inp["level"]
    if n > HARD_MAX[lvl]:
        problems.append(f"too long ({n} > {HARD_MAX[lvl]})")
    if n < SOFT_MIN[lvl]:
        problems.append(f"too short ({n} < {SOFT_MIN[lvl]})")
    cands = set(inp["crossref_candidates"])
    bad = [t for t, _ in LINK.findall(e["entry"]) if t not in cands]
    if bad:
        problems.append(f"invalid crossrefs {bad[:3]}")
    if len(LINK.findall(e["entry"])) > 8:
        problems.append("more than 8 crossrefs")
    unquoted = re.sub(r"[\"“][^\"”]*[\"”]", "", e["entry"])
    for rx, why in FORBIDDEN:
        if rx.search(unquoted):
            problems.append(why)
    first = e["entry"].split(". ")[0]
    if inp["is_person"] and re.search(r"\((b|d)\.\s|\((born|died)\s+\w+\s+\d", first):
        problems.append("life dates in opening")
    if e["entry"].count("*") % 2:
        problems.append("unbalanced italics")
    return problems


def main():
    inputs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in INP.glob("*.json")}
    entries, broken_files = {}, []
    for f in DONE.glob("*.json"):
        try:
            for e in json.loads(f.read_text(encoding="utf-8")):
                entries[e.get("key")] = e | {"_file": f.name}
        except (json.JSONDecodeError, TypeError) as ex:
            broken_files.append(f"{f.name}: {ex}")

    failed, reasons, lengths = {}, Counter(), {}
    for key, inp in inputs.items():
        e = entries.get(key)
        problems = ["not written"] if e is None else check(e, inp)
        if e:
            lengths.setdefault(inp["level"], []).append(words(e["entry"]))
        if problems:
            failed[key] = problems
            reasons.update(p.split(" (")[0].split(" [")[0] for p in problems)

    (ROOT / "data" / "failed.json").write_text(json.dumps(failed, indent=1), encoding="utf-8")
    print(f"{len(entries)} entries written / {len(inputs)} inputs; {len(failed)} failing")
    for f in broken_files:
        print("BROKEN FILE", f)
    for lvl in sorted(lengths):
        xs = sorted(lengths[lvl])
        print(f"level {lvl}: n={len(xs)} words median={xs[len(xs) // 2]} min={xs[0]} max={xs[-1]}")
    for r, c in reasons.most_common():
        print(f"  {c:4d}  {r}")


if __name__ == "__main__":
    main()
