"""Risk caps and kill switch. Caps change only via reviewed config commits."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import settings


class RiskViolation(Exception):
    pass


@dataclass
class RiskState:
    daily_realized_pnl: float = 0.0
    open_positions: dict[str, float] = field(default_factory=dict)  # market_id -> notional


class RiskManager:
    def __init__(self, state: RiskState | None = None) -> None:
        self.state = state or RiskState()

    def check_order(self, market_id: str, notional: float) -> None:
        """Raises RiskViolation unless the order passes every cap."""
        if settings.kill_switch_path.exists():
            raise RiskViolation("KILL_SWITCH file present; all order flow halted")
        if notional > settings.max_trade_notional:
            raise RiskViolation(
                f"notional {notional:.2f} exceeds per-trade cap {settings.max_trade_notional:.2f}"
            )
        exposure = self.state.open_positions.get(market_id, 0.0) + notional
        if exposure > settings.max_market_exposure:
            raise RiskViolation(
                f"market exposure {exposure:.2f} exceeds cap {settings.max_market_exposure:.2f}"
            )
        if (
            market_id not in self.state.open_positions
            and len(self.state.open_positions) >= settings.max_open_positions
        ):
            raise RiskViolation(f"open position count cap {settings.max_open_positions} reached")
        if self.state.daily_realized_pnl <= -settings.max_daily_loss:
            raise RiskViolation(
                f"daily loss limit {settings.max_daily_loss:.2f} reached; done for the day"
            )

    def record_fill(self, market_id: str, notional: float) -> None:
        self.state.open_positions[market_id] = (
            self.state.open_positions.get(market_id, 0.0) + notional
        )

    def record_close(self, market_id: str, realized_pnl: float) -> None:
        self.state.open_positions.pop(market_id, None)
        self.state.daily_realized_pnl += realized_pnl
