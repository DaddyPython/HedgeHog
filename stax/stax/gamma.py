"""Market discovery via Polymarket's public Gamma API (read-only, no auth)."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any

import httpx

from .config import GAMMA_BASE


@dataclass
class Market:
    id: str
    question: str
    slug: str
    category: str | None
    end_date: str | None
    volume_24h: float
    liquidity: float
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    outcomes: list[str]
    outcome_prices: list[float]
    clob_token_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _maybe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_list(raw: Any) -> list:
    """Gamma returns some list fields as JSON-encoded strings."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def parse_market(m: dict[str, Any]) -> Market:
    return Market(
        id=str(m.get("id", "")),
        question=m.get("question", ""),
        slug=m.get("slug", ""),
        category=m.get("category"),
        end_date=m.get("endDate"),
        volume_24h=_maybe_float(m.get("volume24hr")) or 0.0,
        liquidity=_maybe_float(m.get("liquidity")) or 0.0,
        best_bid=_maybe_float(m.get("bestBid")),
        best_ask=_maybe_float(m.get("bestAsk")),
        spread=_maybe_float(m.get("spread")),
        outcomes=[str(o) for o in _json_list(m.get("outcomes"))],
        outcome_prices=[
            f for o in _json_list(m.get("outcomePrices")) if (f := _maybe_float(o)) is not None
        ],
        clob_token_ids=[str(t) for t in _json_list(m.get("clobTokenIds"))],
    )


def fetch_active_markets(
    limit: int = 50,
    order: str = "volume24hr",
    client: httpx.Client | None = None,
) -> list[Market]:
    own_client = client is None
    client = client or httpx.Client(timeout=30)
    try:
        resp = client.get(
            f"{GAMMA_BASE}/markets",
            params={
                "active": "true",
                "closed": "false",
                "order": order,
                "ascending": "false",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        markets = [parse_market(m) for m in resp.json()]
        # Markets without CLOB tokens can't be recorded or traded.
        return [m for m in markets if m.clob_token_ids]
    finally:
        if own_client:
            client.close()


def build_watchlist(limit: int = 50) -> list[Market]:
    """Watchlist across liquidity tiers.

    Deliberately mixes headline markets (to confirm they reprice too fast to
    trade) with mid/long-tail markets (where ANALYSIS.md expects any edge to
    live), rather than only taking the top of the volume ranking.
    """
    by_volume = fetch_active_markets(limit=limit * 3)
    top = by_volume[:limit // 2]
    tail = by_volume[limit:limit + (limit - len(top))]
    return top + tail
