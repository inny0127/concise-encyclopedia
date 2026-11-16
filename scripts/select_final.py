"""Pick the book's titles: all Level 1-4 plus the top Level 5 articles by pageviews.

Level 5 slots are split across categories in proportion to category size (largest remainder),
and filled within each category by user pageviews summed over sample days in the last month.

Pageviews come from the daily dump files on dumps.wikimedia.org (about 700 MB each, streamed,
nothing large is stored), not the action API, which throttles shared IPs. Per-day totals for
vital titles are cached in data/pageviews/<YYYYMMDD>.json, so reruns are instant.

Usage: python select_final.py [--total 15000] [--days 8]
Writes data/selection.json: [{title, level, category}] in the same shape as vital.json.
"""
import argparse
import bz2
import json
import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
CACHE = DATA / "pageviews"
DUMP = "https://dumps.wikimedia.org/other/pageview_complete/{d:%Y}/{d:%Y-%m}/pageviews-{d:%Y%m%d}-user.bz2"
# Wikimedia asks for a contact in the User-Agent; set CE_CONTACT to add one.
_contact = os.environ.get("CE_CONTACT")
UA = "ConciseEncyclopedia/0.1 (personal print project" + (f"; {_contact})" if _contact else ")")


def day_views(day, titles):
    """{title: views} for one day. Dump lines: project title page_id access daily_total hourly."""
    path = CACHE / f"{day:%Y%m%d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    wanted = {t.replace(" ", "_") for t in titles}
    views = defaultdict(int)
    with requests.get(DUMP.format(d=day), headers={"User-Agent": UA}, stream=True, timeout=120) as r:
        r.raise_for_status()
        r.raw.decode_content = True
        for line in bz2.open(r.raw):
            if line.startswith(b"en.wikipedia "):
                parts = line.split(b" ", 5)
                title = parts[1].decode("utf-8", "replace")
                if title in wanted:
                    views[title.replace("_", " ")] += int(parts[4])
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(views, ensure_ascii=False), encoding="utf-8")
    print(f"  {day}: {len(views)} titles with views", flush=True)
    return views


def pageviews(titles, n_days):
    """Total views over n_days sample days spread across the 30 days before the dumps' lag."""
    newest = date.today() - timedelta(days=2)
    days = [newest - timedelta(days=round(i * 30 / n_days)) for i in range(n_days)]
    total = defaultdict(int)
    with ProcessPoolExecutor(min(4, os.cpu_count() or 1)) as ex:
        for views in ex.map(day_views, days, [titles] * n_days):
            for t, v in views.items():
                total[t] += v
    return total


def allocate(sizes, n):
    """Split n slots across categories in proportion to size (largest remainder)."""
    total = sum(sizes.values())
    exact = {c: n * s / total for c, s in sizes.items()}
    quota = {c: int(x) for c, x in exact.items()}
    for c in sorted(exact, key=lambda c: exact[c] - quota[c], reverse=True)[: n - sum(quota.values())]:
        quota[c] += 1
    return quota


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=15000)
    ap.add_argument("--days", type=int, default=8)
    args = ap.parse_args()

    items = json.loads((DATA / "vital.json").read_text(encoding="utf-8"))
    core = [it for it in items if it["level"] <= 4]
    extended = [it for it in items if it["level"] == 5]

    cache = pageviews([it["title"] for it in extended], args.days)

    by_cat = defaultdict(list)
    for it in extended:
        by_cat[it["category"]].append(it)
    quota = allocate({c: len(xs) for c, xs in by_cat.items()}, args.total - len(core))

    picked = []
    for cat, xs in sorted(by_cat.items()):
        xs.sort(key=lambda it: (-cache.get(it["title"], 0), it["title"]))
        top = xs[: quota[cat]]
        picked += top
        print(f"  {cat:32} {len(top):5} of {len(xs):5}  (cutoff {cache.get(top[-1]['title'], 0):,} views)")

    selection = core + picked
    (DATA / "selection.json").write_text(json.dumps(selection, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote data/selection.json: {len(core)} core + {len(picked)} Level 5 = {len(selection)}")


if __name__ == "__main__":
    main()
