#!/usr/bin/env python3
"""Serve the terminal-style Phase 0 status dashboard (default port 8080)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stax.dashboard import serve

if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print("\nstopped")
