# STAX

Event-driven latency measurement (and, if the data ever justifies it, trading)
for Polymarket prediction markets.

STAX started from a viral Instagram post claiming a Claude-built bot made
$220,000 in 64 days by trading Polymarket repricing lag. That post is
fabricated — see [docs/ANALYSIS.md](docs/ANALYSIS.md) for the forensic
breakdown — but the strategy class it describes (news breaks → odds lag →
enter during the lag) is real and testable. STAX tests it instead of assuming
it: [docs/PLAN.md](docs/PLAN.md) is the phased plan, and **Phase 0 (shipped
here) is pure measurement** — no keys, no orders, no risk.

## What's in the box

| Piece | Purpose |
| --- | --- |
| `stax/gamma.py` | Market discovery via the public Gamma API |
| `stax/recorder.py` | CLOB websocket order-book recorder → timestamped JSONL |
| `stax/news/rss.py` | Fast-poll RSS/Atom ingest with first-seen timestamps |
| `stax/mapper.py` | Headline → market matching (keyword v0, LLM hook later) |
| `stax/lag.py` | Joins news to book moves; outputs the repricing-lag distribution |
| `stax/executor.py` | Order construction — **dry-run by default, hard-guarded** |
| `stax/risk.py` | Per-trade / daily caps and a kill-switch file |
| `scripts/` | CLI entry points for each of the above |

## Quickstart (Phase 0, read-only)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Pick a watchlist of active markets (writes data/watchlist.json)
python scripts/discover.py --limit 40

# 2. Record their order books (runs until Ctrl-C, writes data/books/*.jsonl)
python scripts/record.py

# 3. In a second terminal: poll news wires (writes data/news/*.jsonl)
python scripts/ingest_news.py

# 4. After hours/days of overlap, measure repricing lag
python scripts/measure_lag.py
```

## Running Phase 0 continuously (recommended)

Gate 0 needs ~2 weeks of overlapping book + news data. On any always-on box
with Docker:

```bash
docker compose up -d --build   # recorder (daily watchlist refresh) + news ingest
python3 scripts/status.py      # check collection progress any time
docker compose logs -f         # watch the collectors
```

Data lands in `./data/` on the host. `scripts/collect.py` rebuilds the
watchlist every 24 h so resolved markets rotate out; the news poller runs
independently. Both restart automatically on failure.

## What this is not

- Not a money printer. The honest prior is that liquid markets reprice in
  seconds and any residual edge is small and in the long tail.
- Not legal for US persons to run against the offshore CLOB (see
  ANALYSIS.md §4). Phase 0 recording of public market data is read-only;
  anything past Phase 2 requires a permitted jurisdiction.
- Not connected to the HedgeHog/LBANK perp project this repo neighbors —
  different venue, different risk, kept fully separate.

## Configuration

Copy `.env.example` to `.env`. Phase 0 needs nothing. Live trading (Phase 3)
additionally requires `STAX_LIVE_TRADING=I_UNDERSTAND_THE_RISKS`, a funded
Polygon wallet key, and passing every gate in docs/PLAN.md first.
