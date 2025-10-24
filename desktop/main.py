"""Tkinter implementation of the Hedge Hog Matrix console."""
from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import ttk

from hedgehog.config import LBankCredentials
from hedgehog.lbank_client import LBankClient, LBankError, OrderRequest
from hedgehog.logging_stream import LogStreamer

logger = logging.getLogger(__name__)
streamer = LogStreamer()
streamer.attach_to_root()


class HedgeHogApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Hedge Hog :: Matrix Desktop Terminal")
        self.configure(bg="#000000")
        self.geometry("720x640")
        self.resizable(False, False)
        self._client = LBankClient(**LBankCredentials.from_env().__dict__)

        self.symbol_var = tk.StringVar()
        self.size_var = tk.DoubleVar(value=1)
        self.tp_var = tk.DoubleVar(value=111)
        self.sl_var = tk.DoubleVar(value=90)

        self._build_ui()
        threading.Thread(target=self._load_symbols, daemon=True).start()
        threading.Thread(target=self._consume_logs, daemon=True).start()

    def _build_ui(self) -> None:
        title = tk.Label(
            self,
            text="🐗 Hedge Hog // Matrix Terminal",
            fg="#00ff41",
            bg="#000000",
            font=("Share Tech Mono", 18),
        )
        title.pack(pady=10)

        form = tk.Frame(self, bg="#000000")
        form.pack(fill=tk.X, padx=20)

        ttk.Label(form, text="Symbol", foreground="#00ff41", background="#000000").grid(
            row=0, column=0, sticky="w"
        )
        self.symbol_box = ttk.Combobox(form, textvariable=self.symbol_var, width=40)
        self.symbol_box.grid(row=1, column=0, sticky="ew", pady=6)

        ttk.Label(form, text="Size", foreground="#00ff41", background="#000000").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(form, textvariable=self.size_var).grid(row=3, column=0, sticky="ew", pady=6)

        ttk.Label(form, text="Take Profit %", foreground="#00ff41", background="#000000").grid(
            row=4, column=0, sticky="w"
        )
        ttk.Scale(form, from_=101, to=150, orient=tk.HORIZONTAL, variable=self.tp_var).grid(
            row=5, column=0, sticky="ew", pady=6
        )

        ttk.Label(form, text="Stop Loss %", foreground="#00ff41", background="#000000").grid(
            row=6, column=0, sticky="w"
        )
        ttk.Scale(form, from_=50, to=99, orient=tk.HORIZONTAL, variable=self.sl_var).grid(
            row=7, column=0, sticky="ew", pady=6
        )

        execute_btn = ttk.Button(form, text="EXECUTE", command=self._execute)
        execute_btn.grid(row=8, column=0, sticky="ew", pady=10)
        cancel_btn = ttk.Button(form, text="STOP ALL", command=self._cancel)
        cancel_btn.grid(row=9, column=0, sticky="ew", pady=4)

        self.log_box = tk.Text(self, bg="#010a02", fg="#00ff41", state=tk.DISABLED)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    def _load_symbols(self) -> None:
        try:
            data = self._client.get_top_perpetual_pairs()
            symbols = [ticker["symbol"].replace("/", "-") for ticker in data]
            self.symbol_box["values"] = symbols
            if symbols:
                self.symbol_var.set(symbols[0])
            logger.info("Loaded %d symbols", len(symbols))
        except Exception as exc:
            logger.exception("Symbol load failed: %s", exc)

    def _execute(self) -> None:
        symbol = self.symbol_var.get().replace("-", "/")
        request = OrderRequest(
            symbol=symbol,
            side="both",
            size=float(self.size_var.get()),
            take_profit=float(self.tp_var.get()) / 100,
            stop_loss=float(self.sl_var.get()) / 100,
        )
        threading.Thread(target=self._execute_async, args=(request,), daemon=True).start()

    def _execute_async(self, request: OrderRequest) -> None:
        try:
            response = self._client.create_dual_orders(request)
            logger.info("Desktop order response: %s", response)
        except LBankError as exc:
            logger.error("Order failed: %s", exc)

    def _cancel(self) -> None:
        symbol = self.symbol_var.get().replace("-", "/")
        threading.Thread(target=self._cancel_async, args=(symbol,), daemon=True).start()

    def _cancel_async(self, symbol: str) -> None:
        try:
            response = self._client.cancel_all(symbol)
            logger.info("Cancel response: %s", response)
        except LBankError as exc:
            logger.error("Cancel failed: %s", exc)

    def _consume_logs(self) -> None:
        for event in streamer.stream():
            entry = event.partition("data: ")[2].strip()
            if not entry:
                continue
            self.log_box.configure(state=tk.NORMAL)
            self.log_box.insert(tk.END, entry + "\n")
            self.log_box.configure(state=tk.DISABLED)
            self.log_box.see(tk.END)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = HedgeHogApp()
    app.mainloop()


if __name__ == "__main__":
    main()
