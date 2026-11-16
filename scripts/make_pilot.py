"""Pick a stratified 200-article pilot sample from data/vital.json."""
import json
import random
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
N_CORE, N_EXTENDED = 150, 50

items = json.loads((DATA / "vital.json").read_text(encoding="utf-8"))
rng = random.Random(42)


def stratified(pool, n):
    by_cat = defaultdict(list)
    for it in pool:
        by_cat[it["category"]].append(it)
    picks = []
    for cat, xs in by_cat.items():
        k = max(1, round(n * len(xs) / len(pool)))
        picks += rng.sample(xs, min(k, len(xs)))
    rng.shuffle(picks)
    return picks[:n]


core = [it for it in items if it["level"] <= 4]
extended = [it for it in items if it["level"] == 5]
pilot = stratified(core, N_CORE) + stratified(extended, N_EXTENDED)
(DATA / "pilot_titles.json").write_text(json.dumps(pilot, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(pilot), "pilot articles")
