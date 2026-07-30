#!/usr/bin/env python3
"""Join recorded news and books; print the repricing-lag distribution (Gate 0 input)."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.config import settings
from stax.lag import load_jsonl, measure, summarize


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-move", type=float, default=0.02,
                        help="minimum mid move (price units) to count as a reprice")
    parser.add_argument("--max-lag", type=float, default=600.0,
                        help="ignore moves later than this many seconds after news")
    args = parser.parse_args()

    if not settings.watchlist_path.exists():
        sys.exit("no watchlist; run scripts/discover.py first")
    watchlist = json.loads(settings.watchlist_path.read_text())
    news_rows = load_jsonl(list(settings.news_dir.glob("news-*.jsonl")))
    book_rows = load_jsonl(list(settings.books_dir.glob("books-*.jsonl")))

    if not news_rows or not book_rows:
        sys.exit(
            f"need both news ({len(news_rows)} rows) and books ({len(book_rows)} rows); "
            "run scripts/record.py and scripts/ingest_news.py concurrently first"
        )

    observations = measure(news_rows, book_rows, watchlist,
                           min_move=args.min_move, max_lag_seconds=args.max_lag)
    print(summarize(observations, poll_seconds=settings.news_poll_seconds))

    if observations:
        out = settings.data_dir / "lag_observations.jsonl"
        with out.open("w") as f:
            for o in observations:
                f.write(json.dumps(o.__dict__) + "\n")
        print(f"\nwrote {len(observations)} observations -> {out} (spot-check by hand)")


if __name__ == "__main__":
    main()
