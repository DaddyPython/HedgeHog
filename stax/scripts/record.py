#!/usr/bin/env python3
"""Record order books for every asset on the watchlist. Runs until Ctrl-C."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.config import settings
from stax.recorder import record


def main() -> None:
    if not settings.watchlist_path.exists():
        sys.exit(f"no watchlist at {settings.watchlist_path}; run scripts/discover.py first")

    watchlist = json.loads(settings.watchlist_path.read_text())
    asset_ids = [t for m in watchlist for t in m["clob_token_ids"]]
    print(f"recording {len(asset_ids)} assets across {len(watchlist)} markets -> {settings.books_dir}")

    try:
        asyncio.run(record(asset_ids))
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
