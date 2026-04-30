"""Matrix-themed Hedge Hog Flask web application."""
from dotenv import load_dotenv
import os

# Load .env before anything else
load_dotenv()

api_key = os.getenv("LBANK_API_KEY")
secret_key = os.getenv("LBANK_SECRET_KEY")

if not api_key or not secret_key:
    raise ValueError("❌ Missing required environment variable(s).")



from __future__ import annotations

import logging
from typing import Dict

from flask import Flask, Response, jsonify, render_template, request

from hedgehog.config import LBankCredentials
from hedgehog.lbank_client import LBankClient, LBankError, OrderRequest
from hedgehog.logging_stream import LogStreamer

app = Flask(__name__)
streamer = LogStreamer()
streamer.attach_to_root()

logger = logging.getLogger(__name__)


def _client() -> LBankClient:
    creds = LBankCredentials.from_env()
    return LBankClient(api_key=creds.api_key, secret_key=creds.secret_key)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/symbols")
def symbols() -> Response:
    try:
        client = _client()
        data = client.get_top_perpetual_pairs()
        symbols = [ticker["symbol"].replace("/", "-") for ticker in data]
        return jsonify({"symbols": symbols, "raw": data})
    except Exception as exc:  # pragma: no cover - simple error propagation
        logger.exception("Failed to load symbols")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/execute", methods=["POST"])
def execute_trade() -> Response:
    payload: Dict[str, str] = request.json or {}
    symbol = payload.get("symbol", "")
    size = float(payload.get("size", 1))
    tp = float(payload.get("takeProfit", 1.11))
    sl = float(payload.get("stopLoss", 0.9))
    request_obj = OrderRequest(
        symbol=symbol.replace("-", "/"),
        side="both",
        size=size,
        take_profit=tp,
        stop_loss=sl,
    )
    try:
        client = _client()
        result = client.create_dual_orders(request_obj)
        return jsonify(result)
    except LBankError as exc:
        logger.exception("LBANK returned an error")
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Unexpected error executing trade")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/cancel", methods=["POST"])
def cancel() -> Response:
    payload: Dict[str, str] = request.json or {}
    symbol = payload.get("symbol", "")
    try:
        client = _client()
        result = client.cancel_all(symbol.replace("-", "/"))
        return jsonify(result)
    except LBankError as exc:
        logger.exception("LBANK returned an error on cancel")
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Unexpected error cancelling trades")
        return jsonify({"error": str(exc)}), 500


@app.route("/logs")
def logs() -> Response:
    return Response(streamer.stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
