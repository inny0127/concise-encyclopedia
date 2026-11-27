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


SCALE_EN = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
SCALE_KO = {"천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12}
VAL_EN = re.compile(r"(\d[\d,]*(?:\.\d+)?)(?:\s*(thousand|million|billion|trillion))?")
VAL_KO = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(천|만|억|조)?")


SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def values(text, ko):
    """Numeric values, with English million/billion and Korean 만/억/조 scaled, so 6 million == 600만.
    A Korean compound such as 4억 5천만 or 6만 5,000 is also summed."""
    text = LINK.sub(lambda m: m.group(2) or m.group(1), text).translate(SUP)
    out = set()
    if ko:
        for run in re.finditer(r"(?:\d[\d,]*(?:\.\d+)?\s*[천만억조]\s*)+(?:\d[\d,]*(?:\.\d+)?)?", text):
            total = 0
            for num, unit in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([천만억조]?)", run.group(0)):
                total += float(num.replace(",", "")) * (SCALE_KO[unit] if unit else 1)
            out.add(round(total, 3))
    for num, unit in (VAL_KO if ko else VAL_EN).findall(text):
        v = float(num.replace(",", ""))
        out.add(round(v, 3))
        if unit:
            out.add(round(v * (SCALE_KO if ko else SCALE_EN)[unit], 3))
    return out


def main():
    en = {}
    for f in (ROOT / "data" / "condensed").glob("*.json"):
        for e in json.loads(f.read_text(encoding="utf-8")):
            en[e["key"]] = e
    for d in sys.argv[1:]:
        flags, n = [], 0
        for f in sorted((ROOT / d).glob("*.json")):
            gpath = ROOT / "data" / "ko" / "tr_in" / f"{f.stem}.txt"
            if not gpath.exists():
                gpath = ROOT / "data" / "ko" / f"{f.stem}.txt"
            group = gpath.read_text(encoding="utf-8")
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
                ko_vals = values(t, True)
                plain = LINK.sub(lambda m: m.group(2) or m.group(1), src["entry"]).translate(SUP)
                # "1.5 to 2 million": the scale word applies to both ends of the range
                plain = re.sub(r"(\d[\d,]*(?:\.\d+)?)(\s*(?:to|–|-|and)\s*\d[\d,]*(?:\.\d+)?\s*(thousand|million|billion|trillion))",
                               r"\1 \3\2", plain)
                miss = set()
                for num, unit in VAL_EN.findall(plain):
                    v = float(num.replace(",", ""))
                    scaled = v * SCALE_EN[unit] if unit else v
                    if round(v, 3) not in ko_vals and round(scaled, 3) not in ko_vals:
                        miss.add(num + (" " + unit if unit else ""))
                if miss:
                    flags.append(f"{k}: numbers missing {sorted(miss)}")
                a = sorted(m.group(1) for m in LINK.finditer(src["entry"]))
                b = sorted(m.group(1) for m in LINK.finditer(t))
                if a != b:
                    flags.append(f"{k}: links differ, dropped {sorted(set(a) - set(b))}, added {sorted(set(b) - set(a))}")
                if re.search(r"\*[^*]*[가-힣][^*]*\*", t):  # italics stay only for Latin-script words and scientific names
                    flags.append(f"{k}: italics on Korean text")
                if re.search(r"습니다|입니다", t):
                    flags.append(f"{k}: polite ending")
                if not re.search(r"[가-힣]", t):
                    flags.append(f"{k}: not Korean")
        print(f"{d}: {n} entries, {len(flags)} flags")
        for x in flags:
            print("  " + x)


if __name__ == "__main__":
    main()
