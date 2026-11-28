"""Mechanical link repair for Korean translations (data/ko/tr_out/*.json), run after all groups are translated.

Links the translator added that the English entry does not have are unwrapped to plain text. A link the translator
dropped is restored when the glossary's Korean form of its target occurs in the text outside other links (first
occurrence only). Remaining mismatches are printed for the fix agent.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KO = ROOT / "data" / "ko"
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def main():
    en = {}
    for f in (ROOT / "data" / "condensed").glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            en[e["key"]] = e["entry"]
    full = json.loads((KO / "glossary_full.json").read_text(encoding="utf-8"))
    fixed_add = fixed_drop = 0
    left = []
    for f in sorted((KO / "tr_out").glob("t_*.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for r in rows:
            want = {m.group(1) for m in LINK.finditer(en.get(r["key"], ""))}
            t = r["entry"]
            def unwrap(m):
                nonlocal fixed_add
                if m.group(1) in want:
                    return m.group(0)
                fixed_add += 1
                return m.group(2) or m.group(1)
            t2 = LINK.sub(unwrap, t)
            have = {m.group(1) for m in LINK.finditer(t2)}
            for target in sorted(want - have):
                rec = full.get(target)
                forms = [rec["ko"]] if isinstance(rec, dict) else []
                forms = [x.strip("『』「」") for x in forms if x] + [x for x in forms if x]
                done = False
                for form in sorted(set(forms), key=len, reverse=True):
                    # first occurrence that is not inside an existing link
                    spans = [(m.start(), m.end()) for m in LINK.finditer(t2)]
                    for m in re.finditer(re.escape(form), t2):
                        if not any(a <= m.start() < b for a, b in spans):
                            t2 = t2[:m.start()] + f"[[{target}|{form}]]" + t2[m.end():]
                            fixed_drop += 1
                            done = True
                            break
                    if done:
                        break
                if not done:
                    left.append(f"{r['key']}\t{target}")
            if t2 != t:
                r["entry"] = t2
                changed = True
        if changed:
            f.write_text("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n]\n", encoding="utf-8")
    (KO / "links_left.txt").write_text("\n".join(left) + "\n", encoding="utf-8")
    print(f"unwrapped {fixed_add} added links, restored {fixed_drop} dropped links, {len(left)} dropped links left "
          f"(data/ko/links_left.txt)")


if __name__ == "__main__":
    main()
