"""Download images only for entries the book will show (build_book.show_image), resumable.

fetch_sources.py records image metadata only; this fills in image["path"] in each source file.
Thumbnails are requested at a standard Wikimedia width (960 px): non-standard widths are
rendered on demand and heavily rate-limited. An image that keeps failing is skipped and
retried on the next run.

Usage: python fetch_images.py
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_book import show_image  # noqa: E402
from fetch_sources import IMAGE_WIDTH, SOURCES, session  # noqa: E402

IMAGES = SOURCES.parent / "images"
MAX_WAIT = 120  # skip an image whose Retry-After is longer than this; the next run retries it


def download(url, key):
    url = re.sub(r"/\d+px-", f"/{IMAGE_WIDTH}px-", url)  # older records asked for 900 px
    ext = ".png" if url.lower().split("?")[0].endswith(".png") else ".jpg"
    path = IMAGES / f"{key}{ext}"
    if path.exists():
        return path.name
    for attempt in range(5):
        try:
            r = session.get(url, timeout=60)
        except Exception:
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            path.write_bytes(r.content)
            return path.name
        if r.status_code == 404:
            return None
        wait = int(r.headers["retry-after"]) if r.headers.get("retry-after", "").isdigit() else 2 ** attempt
        if wait > MAX_WAIT:
            return None
        time.sleep(wait + 1)
    return None


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    todo = []
    for f in sorted(SOURCES.glob("*.json")):
        src = json.loads(f.read_text(encoding="utf-8"))
        img = src.get("image")
        if img and img.get("url") and show_image(src) and not (img.get("path") and (IMAGES / img["path"]).exists()):
            todo.append((f, src))
    print(f"{len(todo)} images to download", flush=True)

    def one(item):
        f, src = item
        name = download(src["image"]["url"], src["key"])
        if name:
            src["image"]["path"] = name
            f.write_text(json.dumps(src, ensure_ascii=False, indent=1), encoding="utf-8")
        return name

    ok = 0
    with ThreadPoolExecutor(2) as ex:
        for i, name in enumerate(ex.map(one, todo), 1):
            ok += bool(name)
            if i % 100 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}, {ok} saved", flush=True)
    print(f"done: {ok} saved, {len(todo) - ok} skipped (rerun to retry)")


if __name__ == "__main__":
    main()
