"""Phase 0 measurement: join news first-seen times to subsequent book moves.

For every (news item, matched market) pair, find the first meaningful
mid-price move after the news timestamp and report the lag distribution.
This is the number the whole project gates on (docs/PLAN.md, Gate 0).

Honest caveats baked into the method:
- News first-seen time is bounded by the RSS poll interval, so measured lags
  carry that uncertainty; we report it alongside results.
- Keyword matching (mapper.py v0) produces false joins; results should be
  spot-checked by hand before believing them.
- A price move after news is correlation, not proof the news caused it.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from pathlib import Path

from .mapper import candidate_markets


@dataclass
class LagObservation:
    news_key: str
    headline: str
    market_question: str
    asset_id: str
    match_score: float
    news_ts: float
    move_ts: float
    lag_seconds: float
    pre_mid: float
    post_mid: float

    @property
    def move_size(self) -> float:
        return abs(self.post_mid - self.pre_mid)


def load_jsonl(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(paths):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def mid_price_series(book_rows: list[dict], asset_id: str) -> list[tuple[float, float]]:
    """Extract a (recv_ts, mid) series for one asset from recorder output.

    Uses full `book` snapshots (sent at subscribe time) plus incremental
    `price_change` events, which carry best_bid/best_ask per asset directly.
    """
    series: list[tuple[float, float]] = []
    for row in book_rows:
        event = row.get("event", {})
        event_type = event.get("event_type")
        if event_type == "book" and event.get("asset_id") == asset_id:
            bids = event.get("bids") or []
            asks = event.get("asks") or []
            if bids and asks:
                best_bid = max(float(level["price"]) for level in bids)
                best_ask = min(float(level["price"]) for level in asks)
                series.append((row["recv_ts"], (best_bid + best_ask) / 2))
        elif event_type == "price_change":
            for change in event.get("price_changes", []):
                if change.get("asset_id") != asset_id:
                    continue
                bid, ask = change.get("best_bid"), change.get("best_ask")
                if bid is not None and ask is not None:
                    series.append((row["recv_ts"], (float(bid) + float(ask)) / 2))
    return series


def first_move_after(
    series: list[tuple[float, float]], ts: float, min_move: float
) -> tuple[float, float, float] | None:
    """Return (move_ts, pre_mid, post_mid) for the first move >= min_move after ts."""
    pre = [(t, m) for t, m in series if t <= ts]
    if not pre:
        return None
    pre_mid = pre[-1][1]
    for t, mid in series:
        if t > ts and abs(mid - pre_mid) >= min_move:
            return t, pre_mid, mid
    return None


def measure(
    news_rows: list[dict],
    book_rows: list[dict],
    watchlist: list[dict],
    min_move: float = 0.02,
    max_lag_seconds: float = 600.0,
) -> list[LagObservation]:
    observations: list[LagObservation] = []
    series_cache: dict[str, list[tuple[float, float]]] = {}

    for item in news_rows:
        if item.get("backfill"):
            continue
        for score, market in candidate_markets(item["title"], watchlist):
            for asset_id in market.get("clob_token_ids", []):
                if asset_id not in series_cache:
                    series_cache[asset_id] = mid_price_series(book_rows, asset_id)
                hit = first_move_after(series_cache[asset_id], item["first_seen_ts"], min_move)
                if hit is None:
                    continue
                move_ts, pre_mid, post_mid = hit
                lag = move_ts - item["first_seen_ts"]
                if lag <= max_lag_seconds:
                    observations.append(
                        LagObservation(
                            news_key=item["key"],
                            headline=item["title"],
                            market_question=market["question"],
                            asset_id=asset_id,
                            match_score=score,
                            news_ts=item["first_seen_ts"],
                            move_ts=move_ts,
                            lag_seconds=lag,
                            pre_mid=pre_mid,
                            post_mid=post_mid,
                        )
                    )
    return observations


def summarize(observations: list[LagObservation], poll_seconds: float) -> str:
    if not observations:
        return (
            "No matched news->move observations yet. Keep the recorder and news\n"
            "ingest running longer, or loosen --min-move / mapper threshold."
        )
    lags = [o.lag_seconds for o in observations]
    moves = [o.move_size for o in observations]
    lines = [
        f"observations: {len(observations)}",
        f"lag seconds  (±{poll_seconds:.0f}s poll uncertainty): "
        f"median={statistics.median(lags):.1f}  p25={statistics.quantiles(lags, n=4)[0]:.1f}  "
        f"p75={statistics.quantiles(lags, n=4)[2]:.1f}" if len(lags) >= 4
        else f"lags: {[f'{l:.1f}' for l in lags]}",
        f"move size:   median={statistics.median(moves):.3f}",
        "",
        "Gate 0 reminder: exploitable = depth-weighted move minus spread minus",
        "taker fee, over >=30 hand-verified events. This summary is the raw",
        "material, not the verdict.",
    ]
    return "\n".join(lines)
