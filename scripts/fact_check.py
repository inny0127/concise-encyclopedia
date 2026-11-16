"""Cheap hallucination screen: every number in an entry should appear in its sources.

Prints entries whose numbers (years, counts, measurements) are absent from the
Wikipedia lead/excerpt and Grokipedia lead given to the condenser.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INP = ROOT / "data" / "condense_input"
DONE = ROOT / "data" / "condensed"
NUM = re.compile(r"\d[\d,.]*\d|\d")

sys.stdout.reconfigure(encoding="utf-8")


def norm(n):
    return n.replace(",", "").rstrip(".")


def source_numbers(inp):
    text = " ".join([inp["wiki_lead"], inp["wiki_excerpt"], inp["grok_lead"]])
    nums = {norm(n) for n in NUM.findall(text)}
    # ranges like 1914–18 abbreviate the second year
    nums |= {n[-2:] for n in nums if len(n) == 4}
    return nums


def main():
    inputs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in INP.glob("*.json")}
    flagged, total = 0, 0
    for f in sorted(DONE.glob("*.json")):
        for e in json.loads(f.read_text(encoding="utf-8")):
            inp = inputs[e["key"]]
            have = source_numbers(inp)
            text = re.sub(r"\[\[[^\]|]+\|?", "", e["entry"])
            missing = sorted({norm(n) for n in NUM.findall(text)} - have,
                             key=lambda n: (len(n), n))
            missing = [n for n in missing if not (len(n) == 1)]  # single digits are usually counts in words
            total += 1
            if missing:
                flagged += 1
                print(f"{f.stem:12s} L{inp['level']} {e['headword'][:34]:34s} {missing}")
    print(f"\n{flagged}/{total} entries contain numbers not found in their sources")


if __name__ == "__main__":
    main()
