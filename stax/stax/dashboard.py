"""Terminal-style status dashboard for Phase 0 collection.

Zero extra dependencies (stdlib http.server): serves one HTML page and a JSON
status endpoint the page polls every few seconds. Designed to run 24/7 next to
the collectors and be opened from a phone at http://<vps-ip>:8080.

Book archives grow to gigabytes over a multi-week run, so all tallies are
incremental: files are only ever read from their last-seen byte offset, and
live panels parse only the tail of today's file.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import settings

GATE0_DAYS = 14
LIVE_NEWS_REFERENCE = 300   # rough live-headline count expected over the window
STALL_AFTER_SECONDS = 120
TAIL_BYTES = 512 * 1024

PAGE_PATH = Path(__file__).parent / "dashboard_page.html"


class IncrementalLineCounter:
    """Counts newlines per file, reading only bytes appended since last call."""

    def __init__(self) -> None:
        self._state: dict[str, tuple[int, int]] = {}  # path -> (offset, lines)

    def count(self, path: Path) -> int:
        key = str(path)
        size = path.stat().st_size
        offset, lines = self._state.get(key, (0, 0))
        if size < offset:  # file was truncated/rotated; recount
            offset, lines = 0, 0
        if size > offset:
            with path.open("rb") as f:
                f.seek(offset)
                while chunk := f.read(1 << 20):
                    lines += chunk.count(b"\n")
            offset = size
        self._state[key] = (offset, lines)
        return lines


def _tail_lines(path: Path, max_bytes: int = TAIL_BYTES) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(max(0, size - max_bytes))
        data = f.read()
    lines = data.split(b"\n")
    if size > max_bytes:
        lines = lines[1:]  # drop the partial first line
    return [l.decode("utf-8", "replace") for l in lines if l.strip()]


def _first_ts(path: Path) -> float | None:
    try:
        with path.open() as f:
            return json.loads(f.readline())["recv_ts"]
    except Exception:  # noqa: BLE001
        return None


class StatusService:
    def __init__(self) -> None:
        self._books = IncrementalLineCounter()
        self._lock = threading.Lock()
        self._cache: dict | None = None
        self._cache_ts = 0.0
        self._started_ts: float | None = None

    def status(self) -> dict:
        with self._lock:
            if self._cache is not None and time.time() - self._cache_ts < 2.0:
                return self._cache
            try:
                self._cache = self._build()
            except Exception as exc:  # noqa: BLE001 - dashboard must never 500
                self._cache = {"error": repr(exc), "now": time.time()}
            self._cache_ts = time.time()
            return self._cache

    # -- builders ---------------------------------------------------------

    def _build(self) -> dict:
        now = time.time()
        book_files = sorted(settings.books_dir.glob("books-*.jsonl"))
        news_files = sorted(settings.news_dir.glob("news-*.jsonl"))

        if self._started_ts is None and book_files:
            self._started_ts = _first_ts(book_files[0])

        days, totals = self._day_table(book_files, news_files)
        last_book_ts, markets, trades = self._book_tail(book_files)
        last_news_ts, recent_news = self._news_tail(news_files)

        overlap_days = sum(1 for d in days if d["book_events"] and d["news_items"])
        time_component = min(overlap_days / GATE0_DAYS, 1.0)
        news_component = min(totals["live_news"] / LIVE_NEWS_REFERENCE, 1.0)
        readiness = round(100 * (0.7 * time_component + 0.3 * news_component))

        if not book_files:
            phase = "NO DATA — COLLECTORS NOT STARTED"
        elif overlap_days < 1:
            phase = "WARMING UP — DAY 0"
        elif overlap_days < GATE0_DAYS:
            phase = f"COLLECTING — DAY {overlap_days} OF {GATE0_DAYS}"
        else:
            phase = "GATE 0 ASSESSABLE — RUN measure_lag.py"

        data_bytes = sum(p.stat().st_size for p in book_files + news_files)
        disk = shutil.disk_usage(settings.data_dir if settings.data_dir.exists() else Path("."))
        bytes_per_day = data_bytes / max(len(days), 1)
        disk_days_left = disk.free / bytes_per_day if bytes_per_day > 0 else None

        return {
            "now": now,
            "phase": phase,
            "collection": {
                "started_ts": self._started_ts,
                "uptime_seconds": (now - self._started_ts) if self._started_ts else 0,
                "last_book_ts": last_book_ts,
                "last_news_ts": last_news_ts,
                "book_live": bool(last_book_ts and now - last_book_ts < STALL_AFTER_SECONDS),
                "news_live": bool(
                    last_news_ts and now - last_news_ts < STALL_AFTER_SECONDS
                    + settings.news_poll_seconds * 4
                ),
            },
            "days": days,
            "totals": totals,
            "gate0": {
                "days_target": GATE0_DAYS,
                "days_done": overlap_days,
                "live_news_reference": LIVE_NEWS_REFERENCE,
                "readiness_pct": readiness,
                "formula": "0.7 x min(overlap_days/14, 1) + 0.3 x min(live_news/300, 1)",
                "note": "Final Gate 0 verdict needs >=30 hand-verified matched events "
                        "via scripts/measure_lag.py; this gauge tracks collection only.",
            },
            "markets": markets,
            "trades": trades,
            "recent_news": recent_news,
            "disk": {
                "data_bytes": data_bytes,
                "free_bytes": disk.free,
                "est_days_capacity": disk_days_left,
            },
        }

    def _day_table(self, book_files: list[Path], news_files: list[Path]):
        news_by_day: dict[str, tuple[int, int]] = {}
        for path in news_files:  # news files are tiny; full parse is fine
            n = live = 0
            with path.open() as f:
                for line in f:
                    if line.strip():
                        n += 1
                        if not json.loads(line).get("backfill"):
                            live += 1
            news_by_day[path.stem.split("-", 1)[1]] = (n, live)

        books_by_day = {
            p.stem.split("-", 1)[1]: self._books.count(p) for p in book_files
        }
        all_days = sorted(set(books_by_day) | set(news_by_day))
        days = []
        for day in all_days:
            n, live = news_by_day.get(day, (0, 0))
            days.append({
                "day": day,
                "book_events": books_by_day.get(day, 0),
                "news_items": n,
                "live_news": live,
            })
        totals = {
            "book_events": sum(d["book_events"] for d in days),
            "news_items": sum(d["news_items"] for d in days),
            "live_news": sum(d["live_news"] for d in days),
            "days_with_data": len(all_days),
        }
        return days, totals

    def _book_tail(self, book_files: list[Path]):
        if not book_files:
            return None, [], []
        watchlist = {}
        if settings.watchlist_path.exists():
            for m in json.loads(settings.watchlist_path.read_text()):
                for token, outcome in zip(
                    m["clob_token_ids"],
                    m["outcomes"] or [""] * len(m["clob_token_ids"]),
                ):
                    watchlist[token] = {"question": m["question"], "outcome": outcome}

        last_ts = None
        quotes: dict[str, dict] = {}
        trades: list[dict] = []
        for raw in _tail_lines(book_files[-1]):
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            last_ts = row.get("recv_ts", last_ts)
            event = row.get("event", {})
            if event.get("event_type") == "price_change":
                for change in event.get("price_changes", []):
                    asset = change.get("asset_id")
                    if asset in watchlist and change.get("best_bid") is not None:
                        quotes[asset] = {
                            "question": watchlist[asset]["question"],
                            "outcome": watchlist[asset]["outcome"],
                            "bid": float(change["best_bid"]),
                            "ask": float(change["best_ask"]),
                            "ts": row["recv_ts"],
                        }
            elif event.get("event_type") == "last_trade_price":
                asset = event.get("asset_id")
                trades.append({
                    "question": watchlist.get(asset, {}).get("question", asset[:16] + "..."),
                    "price": float(event.get("price", 0)),
                    "size": float(event.get("size", 0)),
                    "side": event.get("side", ""),
                    "ts": row["recv_ts"],
                })

        markets = sorted(quotes.values(), key=lambda q: q["ts"], reverse=True)[:12]
        return last_ts, markets, trades[-8:][::-1]

    def _news_tail(self, news_files: list[Path]):
        if not news_files:
            return None, []
        last_ts = None
        live_items: list[dict] = []
        for raw in _tail_lines(news_files[-1]):
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            last_ts = item.get("first_seen_ts", last_ts)
            if not item.get("backfill"):
                live_items.append({
                    "ts": item["first_seen_ts"],
                    "source": item["source"],
                    "title": item["title"],
                })
        return last_ts, live_items[-10:][::-1]


def serve(port: int | None = None) -> None:
    port = port or int(os.getenv("STAX_DASHBOARD_PORT", "8080"))
    service = StatusService()
    page = PAGE_PATH.read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?")[0] == "/api/status":
                body = json.dumps(service.status()).encode()
                ctype = "application/json"
            elif self.path.split("?")[0] == "/":
                body, ctype = page, "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args) -> None:  # keep container logs quiet
            pass

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[dashboard] serving on http://0.0.0.0:{port}")
    server.serve_forever()
