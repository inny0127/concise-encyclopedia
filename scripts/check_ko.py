"""Mechanical checks of Korean translations against the English entries.

Flags: missing keys, numbers in the English text that the Korean lacks, link targets added or dropped,
leftover *italics*, polite endings (~습니다), Latin-only entries.
Usage: python check_ko.py data/ko/translated_haiku [more dirs]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
NUM = re.compile(r"\d[\d,.]*\d|\d")


def numbers(text):
    return {n.rstrip(".,") for n in NUM.findall(LINK.sub(lambda m: m.group(2) or m.group(1), text))}


def main():
    en = {}
    for f in (ROOT / "data" / "condensed").glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            en[e["key"]] = e
    for d in sys.argv[1:]:
        flags, n = [], 0
        for f in sorted((ROOT / d).glob("*.json")):
            group = (ROOT / "data" / "ko" / f"{f.stem}.txt").read_text(encoding="utf-8")
            want = re.findall(r"^=== KEY: (\S+)", group, re.M)
            got = json.loads(f.read_text(encoding="utf-8"))
            have = {e["key"] for e in got}
            flags += [f"{f.stem}: missing {k}" for k in want if k not in have]
            for e in got:
                n += 1
                src = en.get(e["key"])
                if not src:
                    flags.append(f"{e['key']}: unknown key")
                    continue
                k, t = e["key"], e["entry"]
                miss = numbers(src["entry"]) - numbers(t)
                if miss:
                    flags.append(f"{k}: numbers missing {sorted(miss)}")
                a = sorted(m.group(1) for m in LINK.finditer(src["entry"]))
                b = sorted(m.group(1) for m in LINK.finditer(t))
                if a != b:
                    flags.append(f"{k}: links differ, dropped {sorted(set(a) - set(b))}, added {sorted(set(b) - set(a))}")
                if "*" in t:
                    flags.append(f"{k}: italics marks left")
                if re.search(r"습니다|입니다", t):
                    flags.append(f"{k}: polite ending")
                if not re.search(r"[가-힣]", t):
                    flags.append(f"{k}: not Korean")
        print(f"{d}: {n} entries, {len(flags)} flags")
        for x in flags:
            print("  " + x)


if __name__ == "__main__":
    main()
