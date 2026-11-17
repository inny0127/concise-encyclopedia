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
# Proper names that contain a lowercase we/you/us/our; add more as they turn up.
NAMES_WITH_PRONOUNS = ["Umkhonto we Sizwe", "Yo-Yo", "Tu Fu", "Mwene we Mutapa"]
FORBIDDEN = [(re.compile(p, re.I), why) for p, why in [
    (r"wikipedia|grokipedia", "mentions source"),
    (r"\[\d+\]", "citation marker"),
    (r"^\s*[#\-•]", "markdown heading/bullet"),
    (r"this article", "first/second person"),
    (r"it is (important|worth) (to note|noting)", "filler"),
]]


def words(entry):
    plain = LINK.sub(lambda m: m.group(2) or m.group(1), entry).replace("*", "")
    return len(plain.split())


def italics_balanced(text):
    """Pair each opening * (not after a letter/digit) with the next *. A leftover * right after a
    letter or digit is part of a name (Sagittarius A*, M87*); any other leftover is unbalanced."""
    text = re.sub(r"\[\[[^\]]*\]\]", "", text)
    i = 0
    while (i := text.find("*", i)) != -1:
        if i and text[i - 1].isalnum():
            i += 1  # name asterisk
            continue
        j = text.find("*", i + 1)
        if j == -1:
            return False
        i = j + 1
    return True


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
    # Quoted text and [[links]] are exempt: "Wikipedia" as a topic (a cross-reference, or a quoted
    # name) is fine; only prose that cites the sources is a problem.
    unquoted = re.sub(r"\[\[[^\]]*\]\]", "LINK", re.sub(r"[\"“][^\"”]*[\"”]", "", e["entry"]))
    for rx, why in FORBIDDEN:
        if rx.search(unquoted):
            problems.append(why)
    # Pronouns: lowercase only, outside *titles* and [[links]], so "I Love You" or "Zhong You" pass.
    prose = re.sub(r"\*[^*]*\*|\[\[[^\]]*\]\]", "", unquoted)
    prose = re.sub("|".join(NAMES_WITH_PRONOUNS), "", prose)
    if re.search(r"\b(we|you|your|our|us)\b", prose) and "first/second person" not in problems:
        problems.append("first/second person")
    if "**" in e["entry"]:  # checked on the raw text: *"Heroes"* is an italic title in quotes, not bold
        problems.append("bold markup")
    first = e["entry"].split(". ")[0]
    if inp["is_person"] and re.search(r"\((b|d)\.\s|\((born|died)\s+\w+\s+\d", first):
        problems.append("life dates in opening")
    if not italics_balanced(e["entry"]):
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
    for key in sorted(set(entries) - set(inputs)):
        print(f"UNKNOWN KEY {key} in {entries[key]['_file']} (headword {entries[key].get('headword')!r})")
    for lvl in sorted(lengths):
        xs = sorted(lengths[lvl])
        print(f"level {lvl}: n={len(xs)} words median={xs[len(xs) // 2]} min={xs[0]} max={xs[-1]}")
    for r, c in reasons.most_common():
        print(f"  {c:4d}  {r}")


if __name__ == "__main__":
    main()
