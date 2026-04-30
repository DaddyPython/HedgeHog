"""Configuration helpers for HedgeHog applications."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LBankCredentials:
    """Holds API credentials loaded from environment variables."""

    api_key: str
    secret_key: str

    @classmethod
    def from_env(cls) -> "LBankCredentials":
        try:
            api_key = os.environ["LBANK_API_KEY"]
            secret_key = os.environ["LBANK_SECRET_KEY"]
        except KeyError as exc:  # pragma: no cover - env var errors are explicit
            missing = exc.args[0]
            raise RuntimeError(
                f"Missing required environment variable: {missing}. "
                "Set LBANK_API_KEY and LBANK_SECRET_KEY before starting the app."
            ) from exc
        return cls(api_key=api_key, secret_key=secret_key)
