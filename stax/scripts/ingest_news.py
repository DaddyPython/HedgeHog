#!/usr/bin/env python3
"""Poll news wires and log items with first-seen timestamps. Runs until Ctrl-C."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.config import settings
from stax.news.rss import ingest


def main() -> None:
    print(f"polling every {settings.news_poll_seconds:.0f}s -> {settings.news_dir}")
    try:
        asyncio.run(ingest())
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
