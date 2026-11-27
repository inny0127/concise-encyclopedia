"""Convert British spellings to American in condensed entries (style_guide: "Spelling: American").

Only lowercase whole words are changed, so proper names (Globe Theatre, Labour Party, Ministry of
Defence) keep their official spelling. Link targets ([[Target|text]]) and *italic titles* are left
alone; only link display text and plain text change. Headwords listed in HEADWORDS are changed.

Usage: python americanize.py [--dry]
"""
import json
import re
import sys
from pathlib import Path

DONE = Path(__file__).resolve().parent.parent / "data" / "condensed"

BASE = {
    "colour": "color", "favour": "favor", "honour": "honor", "labour": "labor", "behaviour": "behavior",
    "neighbour": "neighbor", "harbour": "harbor", "flavour": "flavor", "humour": "humor", "rumour": "rumor",
    "armour": "armor", "vapour": "vapor", "vigour": "vigor", "rigour": "rigor", "odour": "odor",
    "tumour": "tumor", "savour": "savor", "endeavour": "endeavor", "splendour": "splendor", "parlour": "parlor",
    "centre": "center", "theatre": "theater", "metre": "meter", "litre": "liter", "fibre": "fiber",
    "lustre": "luster", "spectre": "specter", "sombre": "somber", "calibre": "caliber", "manoeuvre": "maneuver",
    "defence": "defense", "offence": "offense", "licence": "license", "pretence": "pretense",
    "travelled": "traveled", "travelling": "traveling", "traveller": "traveler", "travellers": "travelers",
    "cancelled": "canceled", "cancelling": "canceling", "modelled": "modeled", "modelling": "modeling",
    "labelled": "labeled", "labelling": "labeling", "fuelled": "fueled", "signalled": "signaled",
    "channelled": "channeled", "levelled": "leveled", "marvellous": "marvelous", "jewellery": "jewelry",
    "programme": "program", "programmes": "programs", "catalogue": "catalog", "catalogues": "catalogs",
    "catalogued": "cataloged", "aluminium": "aluminum", "sulphur": "sulfur", "mould": "mold", "moulds": "molds",
    "plough": "plow", "ploughs": "plows", "tyre": "tire", "tyres": "tires", "grey": "gray", "greys": "grays",
    "greyish": "grayish", "ageing": "aging", "judgement": "judgment", "cheque": "check", "cheques": "checks",
    "sceptic": "skeptic", "sceptical": "skeptical", "scepticism": "skepticism", "encyclopaedia": "encyclopedia",
    "mediaeval": "medieval", "foetus": "fetus", "oestrogen": "estrogen", "anaemia": "anemia",
    "haemoglobin": "hemoglobin", "oesophagus": "esophagus", "paediatric": "pediatric",
    "practised": "practiced", "practising": "practicing",
    "carcinisation": "carcinization", "centralisation": "centralization", "centralised": "centralized",
    "cephalised": "cephalized", "civilisation": "civilization", "civilisations": "civilizations",
    "criticised": "criticized", "criticise": "criticize", "decolonisation": "decolonization",
    "democratisation": "democratization", "equalisation": "equalization", "industrialisation": "industrialization",
    "iodised": "iodized", "proselytise": "proselytize", "recognise": "recognize", "recognised": "recognized",
    "serialised": "serialized", "standardised": "standardized", "popularised": "popularized",
    "organisation": "organization", "organisations": "organizations", "organised": "organized",
    "realised": "realized", "colonisation": "colonization", "urbanisation": "urbanization",
    "modernisation": "modernization", "specialised": "specialized", "characterised": "characterized",
    "emphasised": "emphasized", "symbolised": "symbolized", "utilised": "utilized", "minimise": "minimize",
    "maximise": "maximize", "analysed": "analyzed", "analyse": "analyze", "paralysed": "paralyzed",
    "catalysed": "catalyzed",
}
# derived forms: colours, coloured, honours, honoured, centres, centred, metres, theatres, ...
WORDS = dict(BASE)
for b, a in BASE.items():
    if b.endswith("our"):  # colours, coloured, honouring, flavourful ...
        for suf in ("s", "ed", "ing", "ful"):
            WORDS.setdefault(b + suf, a + suf)
for b, a in [("centred", "centered"), ("centres", "centers"), ("metres", "meters"), ("litres", "liters"),
             ("theatres", "theaters"), ("fibres", "fibers"), ("spectres", "specters"), ("kilometre", "kilometer"),
             ("kilometres", "kilometers"), ("centimetre", "centimeter"), ("centimetres", "centimeters"),
             ("millimetre", "millimeter"), ("millimetres", "millimeters"), ("defences", "defenses"),
             ("offences", "offenses"), ("licences", "licenses"), ("armoured", "armored"), ("coloured", "colored"),
             ("honoured", "honored"), ("favoured", "favored"), ("favourite", "favorite"), ("favourable", "favorable"),
             ("labourers", "laborers"), ("labourer", "laborer"), ("behavioural", "behavioral"), ("savoury", "savory"),
             ("harbours", "harbors"), ("neighbours", "neighbors")]:
    WORDS[b] = a

HEADWORDS = {}  # filled from the report below when a headword itself needs changing
WORD = re.compile(r"\b[a-z]+\b")
PROTECT = re.compile(r"\[\[[^\]|]+\||\[\[[^\]]+\]\]|\*[^*]+\*")  # link targets, bare links, italic titles


def fix_text(text, changes):
    out, pos = [], 0
    for m in PROTECT.finditer(text):
        out.append(fix_plain(text[pos:m.start()], changes))
        out.append(m.group(0))
        pos = m.end()
    out.append(fix_plain(text[pos:], changes))
    return "".join(out)


def fix_plain(s, changes):
    def rep(m):
        w = m.group(0)
        if re.search(r"British spelling (is|was)\s*$", s[:m.start()]):  # "The British spelling is armour."
            return w
        if w in WORDS:
            changes.append(f"{w}->{WORDS[w]}")
            return WORDS[w]
        return w
    return WORD.sub(rep, s)


def main():
    dry = "--dry" in sys.argv
    total, files = 0, 0
    tally = {}
    for p in sorted(DONE.glob("*.json")):
        data = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        for e in data:
            ch = []
            new = fix_text(e["entry"], ch)
            if e["headword"] in HEADWORDS:
                e["headword"] = HEADWORDS[e["headword"]]
                ch.append("headword")
            if ch:
                for c in ch:
                    tally[c] = tally.get(c, 0) + 1
                total += len(ch)
                e["entry"] = new
                changed = True
        if changed and not dry:
            files += 1
            p.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in data) + "\n]\n", encoding="utf-8")
    print(f"{total} changes in {files} files{' (dry run)' if dry else ''}")
    for c, n in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {n:4} {c}")


if __name__ == "__main__":
    main()
