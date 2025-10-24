"""Utilities for streaming application logs to connected clients."""
from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from queue import Queue, SimpleQueue
from threading import Lock
from typing import Iterable


@dataclass
class LogEntry:
    level: str
    message: str

    def as_sse(self) -> str:
        payload = json.dumps({"level": self.level, "message": self.message})
        return f"event: log\ndata: {payload}\n\n"


class QueueLogHandler(logging.Handler):
    """A logging handler that pushes log messages into a queue."""

    def __init__(self, queue: Queue[LogEntry]):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - passive
        message = self.format(record)
        entry = LogEntry(level=record.levelname.lower(), message=message)
        self.queue.put(entry)


class LogStreamer:
    """Centralised log fan-out for SSE and in-memory consumers."""

    def __init__(self) -> None:
        self._queue: "Queue[LogEntry]" = SimpleQueue()
        self._handler = QueueLogHandler(self._queue)
        self._handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self._lock = Lock()
        self._is_attached = False

    @property
    def handler(self) -> logging.Handler:
        return self._handler

    def attach_to_root(self) -> None:
        with self._lock:
            if self._is_attached:
                return
            logging.getLogger().addHandler(self._handler)
            logging.getLogger().setLevel(logging.INFO)
            self._is_attached = True

    def stream(self) -> Iterable[str]:  # pragma: no cover - generator for SSE
        self.attach_to_root()
        while True:
            entry = self._queue.get()
            yield entry.as_sse()
