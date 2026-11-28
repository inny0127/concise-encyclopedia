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
SCALE_KO = {"백": 1e2, "천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12}
# native Korean numerals (열세 살, 세 얼간이): 1-99
_U = [("", 0), ("한", 1), ("두", 2), ("세", 3), ("네", 4), ("다섯", 5), ("여섯", 6), ("일곱", 7), ("여덟", 8), ("아홉", 9)]
_T = [("", 0), ("열", 10), ("스물", 20), ("스무", 20), ("서른", 30), ("마흔", 40), ("쉰", 50), ("예순", 60), ("일흔", 70), ("여든", 80), ("아흔", 90)]
NATIVE = {t + u: tv + uv for t, tv in _T for u, uv in _U if len(t + u) >= 2 or (t + u) in ("열",)}
VAL_EN = re.compile(r"(\d[\d,]*(?:\.\d+)?)(?:\s*(thousand|million|billion|trillion))?")
VAL_KO = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(천|만|억|조)?")


SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def values(text, ko):
    """Numeric values, with English million/billion and Korean 만/억/조 scaled, so 6 million == 600만.
    A Korean compound such as 4억 5천만 or 6만 5,000 is also summed."""
    text = LINK.sub(lambda m: m.group(2) or m.group(1), text).translate(SUP)
    out = set()
    if ko:
        # 2억 5천만, 6만 5,000, 45.4억: each number takes the product of the unit letters after it (천만 = 1e7)
        for run in re.finditer(r"(?:\d[\d,]*(?:\.\d+)?\s*[백천만억조]+\s*)+(?:\d[\d,]*(?:\.\d+)?)?", text):
            total = 0
            for num, units in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([백천만억조]*)", run.group(0)):
                mult = 1
                for u in units:
                    mult *= SCALE_KO[u]
                part = float(num.replace(",", "")) * mult
                out.add(round(part, 3))
                total += part
            out.add(round(total, 3))
        for word, v in NATIVE.items():
            if word in text:
                out.add(float(v))
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
                if any(re.search(r"[가-힣]", m) for m in re.findall(r"\*([^*\n]+)\*", t)):  # italics only for Latin-script words
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
