#!/usr/bin/env python3
"""Build the market watchlist from the Gamma API and save it to data/."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.config import settings
from stax.gamma import build_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=40, help="watchlist size")
    args = parser.parse_args()

    markets = build_watchlist(limit=args.limit)
    settings.ensure_dirs()
    settings.watchlist_path.write_text(
        json.dumps([m.to_dict() for m in markets], indent=2)
    )

    print(f"wrote {len(markets)} markets -> {settings.watchlist_path}\n")
    for m in markets[:10]:
        spread = f"{m.spread:.3f}" if m.spread is not None else "?"
        print(f"  vol24h ${m.volume_24h:>12,.0f}  spread {spread}  {m.question[:70]}")
    if len(markets) > 10:
        print(f"  ... and {len(markets) - 10} more")


if __name__ == "__main__":
    main()
