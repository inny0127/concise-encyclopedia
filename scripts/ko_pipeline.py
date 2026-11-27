"""Korean edition pipeline: glossary groups (Opus), merge, translation groups (Sonnet), assemble.

  python ko_pipeline.py gloss-prep   # data/ko/gloss_in/g_NNN.txt, 100 entries each
  python ko_pipeline.py merge        # data/ko/gloss/*.json -> data/ko/glossary_full.json + gloss_conflicts.txt
  python ko_pipeline.py tr-prep      # data/ko/tr_in/t_NNN.txt, 40 entries each, with that group's glossary lines
  python ko_pipeline.py status       # which phase is next and which groups still lack output
  python ko_pipeline.py assemble     # data/ko/translated/*.json (headword fields filled from the glossary)

Glossary agents write data/ko/gloss/g_NNN.json:
  {"heads": {KEY: {"ko", "orig", "ko_sort"}}, "terms": {English term: {"ko", "orig"}}}
Conflict resolution (one Opus agent) writes data/ko/gloss_resolved.json: {term: {"ko", "orig"} or "context"}
("context": the sense depends on the entry, so each entry keeps its own glossary group's form).
Translation agents write data/ko/tr_out/t_NNN.json: [{"key", "entry"}].
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KO = ROOT / "data" / "ko"
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
GLOSS_N, TR_N = 100, 40


def entries():
    out = {}
    for f in (ROOT / "data" / "condensed").glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            out[e["key"]] = e
    persons = {}
    for f in (ROOT / "data" / "sources").glob("*.json"):
        s = json.loads(f.read_text(encoding="utf-8"))
        persons[s["key"]] = (bool(s.get("person")), s["level"])
    keys = sorted(out)
    return [dict(out[k], person=persons.get(k, (False, 5))[0], level=persons.get(k, (False, 5))[1]) for k in keys]


def chunks(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]


def write_lines(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def gloss_prep():
    for i, group in enumerate(chunks(entries(), GLOSS_N)):
        parts = []
        for e in group:
            targets = sorted({m.group(1) for m in LINK.finditer(e["entry"])})
            parts.append(f"=== KEY: {e['key']}\nHEADWORD: {e['headword']}\nPERSON: {'yes' if e['person'] else 'no'}\n"
                         f"LINK TARGETS: {' | '.join(targets)}\nENTRY:\n{e['entry']}\n")
        write_lines(KO / "gloss_in" / f"g_{i:03d}.txt", "\n".join(parts))
    print(f"{i + 1} glossary groups")


def split(group, parts):
    """Split a group whose agent keeps failing (e.g. content filter) into smaller parts g_019a, g_019b, ..."""
    d = KO / ("gloss_in" if group.startswith("g_") else "tr_in")
    src = d / f"{group}.txt"
    blocks = ["=== KEY:" + b for b in src.read_text(encoding="utf-8").split("=== KEY:")[1:]]
    size = -(-len(blocks) // parts)
    for i in range(parts):
        if blocks[i * size:(i + 1) * size]:
            write_lines(d / f"{group}{'abcdefghij'[i]}.txt", "".join(blocks[i * size:(i + 1) * size]))
    (d / "split").mkdir(exist_ok=True)
    src.rename(d / "split" / src.name)
    print(f"{group}: {len(blocks)} entries -> {parts} parts")


def verify():
    """Each glossary file must have heads for exactly its own group's keys, and its terms must come from its own text
    (agents share a scratchpad, so a collision would show up here)."""
    bad = 0
    for f in sorted((KO / "gloss").glob("g_*.json")):
        txt = (KO / "gloss_in" / f"{f.stem}.txt").read_text(encoding="utf-8")
        want = set(re.findall(r"^=== KEY: (\S+)", txt, re.M))
        g = json.loads(f.read_text(encoding="utf-8"))
        terms = list(g.get("terms", {}))
        foreign = sum(1 for t in terms if t not in txt)
        if set(g.get("heads", {})) != want or foreign > 0.1 * len(terms):
            bad += 1
            print(f"{f.stem}: heads {len(g.get('heads', {}))}/{len(want)}, {foreign}/{len(terms)} terms not in its text")
    print(f"verify: {bad} bad files")


def load_gloss():
    heads, local = {}, {}  # local: key -> {term: rec} from that entry's glossary group
    votes = defaultdict(Counter)
    recs = {}
    for f in sorted((KO / "gloss").glob("g_*.json")):
        g = json.loads(f.read_text(encoding="utf-8"))
        group_keys = list(g.get("heads", {}))
        heads.update(g.get("heads", {}))
        for term, rec in g.get("terms", {}).items():
            votes[term][rec["ko"]] += 1
            recs[(term, rec["ko"])] = rec
        for k in group_keys:
            local[k] = g.get("terms", {})
    return heads, local, votes, recs


def merge():
    heads, local, votes, recs = load_gloss()
    resolved_path = KO / "gloss_resolved.json"
    resolved = json.loads(resolved_path.read_text(encoding="utf-8")) if resolved_path.exists() else {}
    full, conflicts = {}, []
    for term, c in votes.items():
        if term in resolved and resolved[term] != "context":
            full[term] = resolved[term]
        elif term in resolved:
            full[term] = "context"
        else:
            ko, _ = c.most_common(1)[0]
            full[term] = recs[(term, ko)]
            if len(c) > 1:
                conflicts.append(f"{term}\t" + " | ".join(f"{k} ({n})" for k, n in c.most_common()))
    (KO / "glossary_full.json").write_text(json.dumps(full, ensure_ascii=False, indent=0), encoding="utf-8")
    unresolved = [c for c in conflicts if c.split("\t")[0] not in resolved]
    (KO / "gloss_conflicts.txt").write_text("\n".join(unresolved) + "\n", encoding="utf-8")
    print(f"{len(heads)} headwords, {len(full)} terms, {len(unresolved)} unresolved conflicts")


def terms_for(e, full, local):
    """Glossary terms that occur in this entry: link targets plus any term found in the text (1-6 word n-grams)."""
    plain = LINK.sub(lambda m: m.group(2) or m.group(1), e["entry"]).replace("*", "")
    words = re.findall(r"[\w'’.-]+", plain)
    found = {m.group(1) for m in LINK.finditer(e["entry"])}
    for n in range(1, 7):
        for i in range(len(words) - n + 1):
            found.add(" ".join(words[i:i + n]).strip(".,"))
    out = {}
    for t in found:
        rec = full.get(t)
        if rec == "context":
            rec = local.get(e["key"], {}).get(t)
        if rec:
            out[t] = rec
    return out


def tr_prep():
    heads, local, _, _ = load_gloss()
    full = json.loads((KO / "glossary_full.json").read_text(encoding="utf-8"))
    for i, group in enumerate(chunks(entries(), TR_N)):
        parts = []
        for e in group:
            h = heads.get(e["key"], {})
            gl = terms_for(e, full, local)
            lines = "\n".join(f"  {t} = {r['ko']}" for t, r in sorted(gl.items()))
            parts.append(f"=== KEY: {e['key']}\nHEADWORD: {e['headword']} = {h.get('ko', '?')}\nLEVEL: {e['level']}\n"
                         f"GLOSSARY:\n{lines}\nENTRY:\n{e['entry']}\n")
        write_lines(KO / "tr_in" / f"t_{i:03d}.txt", "\n".join(parts))
    print(f"{i + 1} translation groups")


def pending(in_dir, out_dir, prefix):
    ins = sorted(p.stem for p in (KO / in_dir).glob(f"{prefix}_*.txt"))  # split parts replace their parent
    return [s for s in ins if not (KO / out_dir / f"{s}.json").exists()], len(ins)


def status():
    g_todo, g_all = pending("gloss_in", "gloss", "g")
    if not g_all:
        print("phase: gloss-prep (run: python scripts/ko_pipeline.py gloss-prep)")
        return
    if g_todo:
        print(f"phase: glossary  {g_all - len(g_todo)}/{g_all} done  todo: {' '.join(g_todo)}")
        return
    if not (KO / "glossary_full.json").exists() or (KO / "gloss_conflicts.txt").stat().st_size > 1 \
            and not (KO / "gloss_resolved.json").exists():
        print("phase: merge/resolve (run merge; if gloss_conflicts.txt is non-empty, one Opus agent writes gloss_resolved.json, then merge again)")
        return
    t_todo, t_all = pending("tr_in", "tr_out", "t")
    if not t_all:
        print("phase: tr-prep (run: python scripts/ko_pipeline.py tr-prep)")
        return
    if t_todo:
        print(f"phase: translation  {t_all - len(t_todo)}/{t_all} done  todo: {' '.join(t_todo)}")
        return
    print("phase: assemble + check + build (all groups translated)")


def assemble():
    heads, _, _, _ = load_gloss()
    out_dir = KO / "translated"
    out_dir.mkdir(exist_ok=True)
    n = 0
    for f in sorted((KO / "tr_out").glob("t_*.json")):
        rows = []
        for e in json.loads(f.read_text(encoding="utf-8")):
            h = heads.get(e["key"])
            if not h:
                print("no headword for", e["key"])
                continue
            rows.append({"key": e["key"], "ko_headword": h["ko"], "orig": h.get("orig", ""),
                         "ko_sort": h.get("ko_sort") or re.sub(r"[\s\W]", "", h["ko"]), "entry": e["entry"]})
        (out_dir / f.name).write_text("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n]\n",
                                      encoding="utf-8")
        n += len(rows)
    print(f"{n} entries assembled")


if __name__ == "__main__":
    if sys.argv[1] == "split":
        split(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    else:
        {"gloss-prep": gloss_prep, "merge": merge, "verify": verify, "tr-prep": tr_prep, "status": status,
         "assemble": assemble}[sys.argv[1]]()
