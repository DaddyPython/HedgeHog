"""Order-book recorder for the Polymarket CLOB market websocket channel.

Appends every message (book snapshots, price changes, trades) to daily JSONL
files with a local receive timestamp. This archive is the foundation of
Phase 0: public historical tick data for Polymarket books does not exist, so
we build our own.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets

from .config import CLOB_WS_MARKET, settings

PING_INTERVAL = 10.0
RECONNECT_DELAY = 3.0
MAX_ASSETS_PER_CONN = 100


def _out_path(books_dir: Path) -> Path:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return books_dir / f"books-{day}.jsonl"


async def _record_connection(asset_ids: list[str], books_dir: Path) -> None:
    async with websockets.connect(CLOB_WS_MARKET, ping_interval=None) as ws:
        await ws.send(json.dumps({"assets_ids": asset_ids, "type": "market"}))
        print(f"[recorder] subscribed to {len(asset_ids)} assets")

        async def keepalive() -> None:
            while True:
                await asyncio.sleep(PING_INTERVAL)
                await ws.send("PING")

        ka = asyncio.create_task(keepalive())
        try:
            async for raw in ws:
                recv_ts = time.time()
                if raw == "PONG":
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                events = payload if isinstance(payload, list) else [payload]
                path = _out_path(books_dir)
                with path.open("a") as f:
                    for event in events:
                        f.write(json.dumps({"recv_ts": recv_ts, "event": event}) + "\n")
        finally:
            ka.cancel()


async def record(asset_ids: list[str]) -> None:
    """Record given CLOB token ids forever, reconnecting on drops."""
    settings.ensure_dirs()
    chunks = [
        asset_ids[i : i + MAX_ASSETS_PER_CONN]
        for i in range(0, len(asset_ids), MAX_ASSETS_PER_CONN)
    ]

    async def run_chunk(chunk: list[str]) -> None:
        while True:
            try:
                await _record_connection(chunk, settings.books_dir)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - keep recording through any drop
                print(f"[recorder] connection error ({exc!r}); reconnecting in {RECONNECT_DELAY}s")
                await asyncio.sleep(RECONNECT_DELAY)

    await asyncio.gather(*(run_chunk(c) for c in chunks))
