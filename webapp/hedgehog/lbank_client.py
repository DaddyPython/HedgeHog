@@ -1,183 +1,11 @@
"""Thin client for interacting with the LBANK REST and WebSocket APIs."""
from __future__ import annotations
import os
import ccxt

import hashlib
import hmac
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
exchange = ccxt.lbank({
    'apiKey': os.getenv("LBANK_API_KEY"),
    'secret': os.getenv("LBANK_API_SECRET"),
})

import requests
import websocket
print("Testing connection...")
print(exchange.fetch_balance())

LBANK_REST_BASE = "https://api.lbkex.com"
LBANK_WS_URL = "wss://www.lbkex.net/ws/V2/"

logger = logging.getLogger(__name__)


class LBankError(RuntimeError):
    """Raised when LBANK returns an error response."""


@dataclass
class OrderRequest:
    symbol: str
    side: str
    size: float
    take_profit: float
    stop_loss: float


class LBankClient:
    """Blocking LBANK API client supporting REST and WebSocket features."""

    def __init__(self, api_key: str, secret_key: str, session: Optional[requests.Session] = None) -> None:
        self.api_key = api_key
        self.secret_key = secret_key.encode()
        self.session = session or requests.Session()
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_listeners: List["LogListener"] = []

    # ------------------------------------------------------------------
    # REST helpers
    # ------------------------------------------------------------------
    def _sign(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload["api_key"] = self.api_key
        payload["timestamp"] = int(time.time() * 1000)
        sorted_items = sorted(payload.items())
        query = "&".join(f"{k}={v}" for k, v in sorted_items)
        signature = hmac.new(self.secret_key, query.encode(), hashlib.sha256).hexdigest()
        payload["sign"] = signature
        return payload

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        signed = self._sign(payload)
        url = f"{LBANK_REST_BASE}{endpoint}"
        logger.info("POST %s payload=%s", endpoint, payload)
        response = self.session.post(url, data=signed, timeout=10)
        if response.status_code != 200:
            logger.error("HTTP error %s: %s", response.status_code, response.text)
            raise LBankError(f"HTTP {response.status_code}: {response.text}")
        data = response.json()
        if str(data.get("result")) != "true":
            logger.error("LBANK error: %s", data)
            raise LBankError(str(data))
        logger.info("POST %s success: %s", endpoint, data)
        return data

    def get_top_perpetual_pairs(self) -> List[Dict[str, Any]]:
        url = f"{LBANK_REST_BASE}/v2/ticker/24hr.do"
        logger.info("Fetching symbol tickers from %s", url)
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        tickers = [ticker for ticker in data.get("data", []) if ticker.get("symbol", "").endswith("/USDT")]
        logger.info("Fetched %d tickers", len(tickers))
        return sorted(tickers, key=lambda t: float(t.get("change", 0.0)), reverse=True)

    def create_dual_orders(self, request: OrderRequest) -> Dict[str, Any]:
        logger.info("Creating dual orders for %s size=%s", request.symbol, request.size)
        base_payload = {
            "symbol": request.symbol,
            "type": "market",
            "price": 0,
            "amount": request.size,
        }
        long_payload = {
            **base_payload,
            "side": "buy",
            "profit_price": request.take_profit,
            "loss_price": request.stop_loss,
        }
        short_payload = {
            **base_payload,
            "side": "sell",
            "profit_price": request.take_profit,
            "loss_price": request.stop_loss,
        }
        long_resp = self._post("/v2/supplement/create_order.do", long_payload)
        short_resp = self._post("/v2/supplement/create_order.do", short_payload)
        return {"long": long_resp, "short": short_resp}

    def cancel_all(self, symbol: str) -> Dict[str, Any]:
        logger.info("Cancelling all positions for %s", symbol)
        payload = {"symbol": symbol}
        return self._post("/v2/supplement/cancel_order_by_symbol.do", payload)

    def get_account_info(self) -> Dict[str, Any]:
        logger.info("Fetching account info")
        return self._post("/v2/supplement/user_info_account.do", {})

    # ------------------------------------------------------------------
    # WebSocket support
    # ------------------------------------------------------------------
    def add_listener(self, listener: "LogListener") -> None:
        self._ws_listeners.append(listener)

    def connect_ws(self) -> None:
        if self._ws is not None:
            return

        def on_message(_: websocket.WebSocketApp, message: str) -> None:
            logger.info("WS message: %s", message)
            for listener in self._ws_listeners:
                listener.on_message(message)

        def on_error(_: websocket.WebSocketApp, error: Any) -> None:
            logger.error("WS error: %s", error)
            for listener in self._ws_listeners:
                listener.on_error(error)

        def on_close(_: websocket.WebSocketApp, status_code: int, msg: str) -> None:
            logger.warning("WS closed (%s): %s", status_code, msg)
            for listener in self._ws_listeners:
                listener.on_close(status_code, msg)

        def on_open(ws: websocket.WebSocketApp) -> None:
            logger.info("WS connection established")
            auth_payload = json.dumps(
                {
                    "action": "login",
                    "args": {
                        "api_key": self.api_key,
                        "timestamp": int(time.time() * 1000),
                    },
                }
            )
            ws.send(auth_payload)

        self._ws = websocket.WebSocketApp(
            LBANK_WS_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        self._ws_thread = threading.Thread(target=self._ws.run_forever, name="LBANK-WS", daemon=True)
        self._ws_thread.start()

    def close(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None
        if self._ws_thread is not None:
            self._ws_thread.join(timeout=1)
            self._ws_thread = None


class LogListener:
    """Receives messages from the websocket for logging/display purposes."""

    def on_message(self, message: str) -> None:  # pragma: no cover - callback
        pass

    def on_error(self, error: Any) -> None:  # pragma: no cover - callback
        pass

    def on_close(self, status_code: int, message: str) -> None:  # pragma: no cover - callback
        pass
