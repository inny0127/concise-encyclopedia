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


UNITS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
WORDNUM = re.compile(r"\b(?:(%s)(?:[- ](%s))?|(%s))(?:[- ](hundred|thousand|million))?\b" % (
    "|".join(TENS), "|".join(UNITS[1:10]), "|".join(UNITS)), re.I)
ORDINALS = ("first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
            "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth twentieth").split()
ORDINAL_CENTURY = {w: str(i + 1) for i, w in enumerate(ORDINALS)}
ORDINAL_CENTURY |= {"twenty-" + w: str(20 + i + 1) for i, w in enumerate(ORDINALS[:9])}
for _i, _t in enumerate(TENS[1:], start=3):  # thirty .. ninety: "thirty-second", "forty-fifth"
    ORDINAL_CENTURY |= {f"{_t}-{w}": str(_i * 10 + k + 1) for k, w in enumerate(ORDINALS[:9])}
    ORDINAL_CENTURY[_t[:-1] + "ieth"] = str(_i * 10)


def spelled_numbers(text):
    """Digits for spelled-out numbers ("forty-six" -> 46, "eight hundred" -> 800, "nineteenth" -> 19)."""
    out = set()
    for m in WORDNUM.finditer(text):
        tens, unit, small, scale = (g.lower() if g else None for g in m.groups())
        n = (TENS.index(tens) + 2) * 10 + (UNITS.index(unit) if unit else 0) if tens else UNITS.index(small)
        out.add(str(n))
        if scale:
            out.add(str(n * {"hundred": 100, "thousand": 1000, "million": 1000000}[scale]))
    for w, n in ORDINAL_CENTURY.items():
        if re.search(r"\b" + w + r"\b", text, re.I):
            out.add(n)
    return out


def source_numbers(inp):
    text = " ".join([inp["wiki_lead"], inp["wiki_excerpt"], inp["grok_lead"]])
    raw = NUM.findall(text)
    nums = {norm(n) for n in raw} | spelled_numbers(text)
    # "2.5 × 106" is 2.5 × 10⁶ with the superscript flattened: accept the base 10
    if re.search(r"[×x]\s*10\d", text):
        nums.add("10")
    # "203.062.512" (dots as thousands separators, as in Portuguese or German sources)
    nums |= {n.replace(".", "") for n in raw if re.fullmatch(r"\d{1,3}(\.\d{3}){2,}", n)}
    # "4.325 million" / "6.3 million" -> 4325000 / 6300000
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(thousand|million|billion)", text):
        nums.add(str(round(float(m.group(1)) * {"thousand": 1e3, "million": 1e6, "billion": 1e9}[m.group(2)])))
    # ranges like 1914–18 abbreviate the second year
    nums |= {n[-2:] for n in nums if len(n) == 4}
    return nums


def main():
    inputs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in INP.glob("*.json")}
    flagged, total = 0, 0
    for f in sorted(DONE.glob("*.json")):
        for e in json.loads(f.read_text(encoding="utf-8")):
            inp = inputs.get(e["key"])
            if inp is None:
                print(f"{f.stem:12} UNKNOWN KEY {e['key']}")
                continue
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
