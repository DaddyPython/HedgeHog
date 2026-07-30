"""Order construction and (guarded) submission.

Dry-run is the default and the only mode implemented until Gates 0-2 pass
(docs/PLAN.md). Live submission requires ALL of:
  1. STAX_LIVE_TRADING set to the exact acknowledgement phrase,
  2. py-clob-client installed and a funded wallet configured,
  3. every RiskManager check passing,
  4. no KILL_SWITCH file.

Order policy: marketable-limit only, price-capped at the pre-news quote plus
allowed slippage, one shot per signal, no chasing.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, asdict

from .config import settings
from .risk import RiskManager


@dataclass
class OrderIntent:
    market_id: str
    asset_id: str
    side: str            # "BUY" or "SELL"
    limit_price: float   # pre-news quote +/- slippage cap; never a naked market order
    size_shares: float
    signal_id: str
    created_ts: float

    @property
    def notional(self) -> float:
        return self.limit_price * self.size_shares


def build_intent(
    market_id: str,
    asset_id: str,
    side: str,
    pre_news_price: float,
    max_slippage: float,
    size_shares: float,
    signal_id: str | None = None,
) -> OrderIntent:
    if side not in ("BUY", "SELL"):
        raise ValueError(f"invalid side {side!r}")
    limit = pre_news_price + max_slippage if side == "BUY" else pre_news_price - max_slippage
    limit = min(max(limit, 0.001), 0.999)
    return OrderIntent(
        market_id=market_id,
        asset_id=asset_id,
        side=side,
        limit_price=round(limit, 3),
        size_shares=size_shares,
        signal_id=signal_id or uuid.uuid4().hex[:12],
        created_ts=time.time(),
    )


def submit(intent: OrderIntent, risk: RiskManager) -> dict:
    """Risk-check the intent, then dry-run log it (or, one day, submit it)."""
    risk.check_order(intent.market_id, intent.notional)

    if not settings.live_trading_enabled:
        record = {"mode": "dry_run", **asdict(intent)}
        print(f"[executor] DRY RUN {intent.side} {intent.size_shares} @ {intent.limit_price} "
              f"(asset {intent.asset_id[:12]}..., signal {intent.signal_id})")
        return record

    # Live path: intentionally unimplemented until Gates 0-2 pass. Wiring
    # py-clob-client here before the strategy is proven would invert the
    # entire point of the plan.
    raise NotImplementedError(
        "Live submission is gated on Phase 0-2 results; see docs/PLAN.md. "
        "Remove this guard only via a reviewed commit that cites the gate data."
    )
