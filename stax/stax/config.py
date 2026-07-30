from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_WS_MARKET = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

LIVE_TRADING_PHRASE = "I_UNDERSTAND_THE_RISKS"

DEFAULT_FEEDS = {
    # Fast general wires. Extend per docs/PLAN.md Phase 1 with category-specific
    # sources (BLS releases, court calendars, sports feeds) as playbooks mature.
    "reuters_top": "https://feeds.reuters.com/reuters/topNews",
    "ap_top": "https://rsshub.app/apnews/topics/apf-topnews",
    "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "nyt_world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
}


@dataclass
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("STAX_DATA_DIR", "data"))
    )
    news_poll_seconds: float = field(
        default_factory=lambda: float(os.getenv("STAX_NEWS_POLL_SECONDS", "15"))
    )
    live_trading_enabled: bool = field(
        default_factory=lambda: os.getenv("STAX_LIVE_TRADING") == LIVE_TRADING_PHRASE
    )
    max_trade_notional: float = field(
        default_factory=lambda: float(os.getenv("STAX_MAX_TRADE_NOTIONAL", "25"))
    )
    max_market_exposure: float = field(
        default_factory=lambda: float(os.getenv("STAX_MAX_MARKET_EXPOSURE", "50"))
    )
    max_daily_loss: float = field(
        default_factory=lambda: float(os.getenv("STAX_MAX_DAILY_LOSS", "100"))
    )
    max_open_positions: int = field(
        default_factory=lambda: int(os.getenv("STAX_MAX_OPEN_POSITIONS", "5"))
    )

    @property
    def books_dir(self) -> Path:
        return self.data_dir / "books"

    @property
    def news_dir(self) -> Path:
        return self.data_dir / "news"

    @property
    def watchlist_path(self) -> Path:
        return self.data_dir / "watchlist.json"

    @property
    def kill_switch_path(self) -> Path:
        # Presence of this file halts all order flow immediately.
        return Path("KILL_SWITCH")

    def ensure_dirs(self) -> None:
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.news_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
