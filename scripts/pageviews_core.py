"""Pageviews for Level 1-4 titles (select_final.py only fetched Level 5), used to rank images.

Streams two daily dump files (never throttled) into data/pageviews_core/<YYYYMMDD>.json.
Usage: python pageviews_core.py
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import select_final  # noqa: E402

select_final.CACHE = select_final.DATA / "pageviews_core"


def main():
    items = json.loads((select_final.DATA / "vital.json").read_text(encoding="utf-8"))
    titles = [it["title"] for it in items if it["level"] <= 4]
    newest = date.today() - timedelta(days=2)
    days = [newest, newest - timedelta(days=14)]
    with ProcessPoolExecutor(2) as ex:
        list(ex.map(select_final.day_views, days, [titles] * len(days)))


if __name__ == "__main__":
    main()
