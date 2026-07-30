#!/usr/bin/env python3
"""Long-running Phase 0 collector: record books, refreshing the watchlist daily.

Markets resolve and new ones appear, so a multi-week recording run must not
pin a stale watchlist. This wrapper rebuilds the watchlist every
--refresh-hours, then restarts the recorder subscription with the fresh
asset set. Run alongside scripts/ingest_news.py (or via docker compose).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.config import settings
from stax.gamma import build_watchlist
from stax.recorder import record


async def collect(limit: int, refresh_hours: float) -> None:
    settings.ensure_dirs()
    while True:
        try:
            markets = build_watchlist(limit=limit)
            settings.watchlist_path.write_text(
                json.dumps([m.to_dict() for m in markets], indent=2)
            )
            asset_ids = [t for m in markets for t in m.clob_token_ids]
            print(f"[collect] watchlist refreshed: {len(markets)} markets, "
                  f"{len(asset_ids)} assets; recording for {refresh_hours}h")
        except Exception as exc:  # noqa: BLE001 - Gamma hiccup must not kill a long run
            print(f"[collect] watchlist refresh failed ({exc!r}); retrying in 60s")
            await asyncio.sleep(60)
            continue

        task = asyncio.create_task(record(asset_ids))
        await asyncio.sleep(refresh_hours * 3600)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=40, help="watchlist size")
    parser.add_argument("--refresh-hours", type=float, default=24.0,
                        help="rebuild watchlist and resubscribe this often")
    args = parser.parse_args()
    try:
        asyncio.run(collect(args.limit, args.refresh_hours))
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
