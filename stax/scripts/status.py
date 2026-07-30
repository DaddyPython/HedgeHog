#!/usr/bin/env python3
"""Show how much Phase 0 data has been collected and whether Gate 0 is assessable."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.config import settings


def count_lines(path: Path) -> int:
    with path.open() as f:
        return sum(1 for _ in f)


def main() -> None:
    book_files = sorted(settings.books_dir.glob("books-*.jsonl"))
    news_files = sorted(settings.news_dir.glob("news-*.jsonl"))

    print("Phase 0 collection status\n")

    if not book_files and not news_files:
        sys.exit("no data yet; start scripts/collect.py and scripts/ingest_news.py")

    print(f"{'day':<12} {'book events':>12} {'news items':>11} {'live news':>10}")
    days = sorted({p.stem.split("-", 1)[1] for p in book_files}
                  | {p.stem.split("-", 1)[1] for p in news_files})
    total_live_news = 0
    for day in days:
        books = settings.books_dir / f"books-{day}.jsonl"
        news = settings.news_dir / f"news-{day}.jsonl"
        n_books = count_lines(books) if books.exists() else 0
        n_news = live = 0
        if news.exists():
            with news.open() as f:
                for line in f:
                    n_news += 1
                    if not json.loads(line).get("backfill"):
                        live += 1
        total_live_news += live
        print(f"{day:<12} {n_books:>12,} {n_news:>11,} {live:>10,}")

    print(f"\ndays with data: {len(days)}   live news items total: {total_live_news:,}")
    print("\nGate 0 needs >=14 days of overlap and >=30 hand-verified matched")
    print("events. Run scripts/measure_lag.py once both columns have depth.")


if __name__ == "__main__":
    main()
