"""Fast-poll RSS/Atom ingest with first-seen timestamps.

The published timestamp in a feed is unreliable for latency work; what matters
for Phase 0 is when *we* could first have known. Each new item is logged with
`first_seen_ts`, whose accuracy is bounded by the poll interval — a 15 s poll
means ±15 s on every lag estimate downstream, which is fine for testing a
"30-90 seconds of lag" claim and not fine for millisecond racing (which is
explicitly not the lane we're in; see docs/ANALYSIS.md §2).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone

import feedparser
import httpx

from ..config import DEFAULT_FEEDS, settings


def _item_key(source: str, entry: dict) -> str:
    basis = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(f"{source}:{basis}".encode()).hexdigest()[:16]


async def _poll_feed(
    client: httpx.AsyncClient, source: str, url: str, seen: set[str]
) -> list[dict]:
    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - a dead feed must not stop the others
        print(f"[news] {source}: fetch failed ({exc!r})")
        return []

    parsed = feedparser.parse(resp.content)
    now = time.time()
    fresh = []
    for entry in parsed.entries:
        key = _item_key(source, entry)
        if key in seen:
            continue
        seen.add(key)
        fresh.append(
            {
                "first_seen_ts": now,
                "source": source,
                "key": key,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            }
        )
    return fresh


async def ingest(feeds: dict[str, str] | None = None) -> None:
    """Poll feeds forever, appending new items to daily JSONL files."""
    feeds = feeds or DEFAULT_FEEDS
    settings.ensure_dirs()
    seen: set[str] = set()
    first_pass = True

    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            results = await asyncio.gather(
                *(_poll_feed(client, name, url, seen) for name, url in feeds.items())
            )
            items = [item for batch in results for item in batch]
            if first_pass:
                # Items present on the very first poll have unknown true break
                # times; mark them so lag measurement can exclude them.
                for item in items:
                    item["backfill"] = True
                first_pass = False

            if items:
                day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                path = settings.news_dir / f"news-{day}.jsonl"
                with path.open("a") as f:
                    for item in items:
                        f.write(json.dumps(item) + "\n")
                print(f"[news] +{len(items)} items ({sum(1 for i in items if not i.get('backfill'))} live)")

            await asyncio.sleep(settings.news_poll_seconds)
