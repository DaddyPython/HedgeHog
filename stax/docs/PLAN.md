# STAX build plan

Goal: determine empirically whether post-news repricing lag on Polymarket is
exploitable after spread, fees, and depth — and if it is, trade it live with
strict caps. Each phase has a **gate**; we do not advance past a failed gate.

## Phase 0 — Measure the lag (implemented in this repo)

Everything depends on one number the Instagram post asserts and never proves:
how long stale quotes actually survive after news breaks, and how much depth is
available at the stale price.

Components (all shipped, all read-only, no keys required):

1. **Market discovery** (`stax/gamma.py`, `scripts/discover.py`) — pull active
   markets from the Gamma API with volume, liquidity, spread, and outcome token
   IDs; select a watchlist across liquidity tiers.
2. **Order book recorder** (`stax/recorder.py`, `scripts/record.py`) —
   subscribe to the CLOB market websocket channel and append every book
   snapshot / price change / trade to timestamped JSONL. This builds the tick
   archive that does not exist publicly.
3. **News ingest** (`stax/news/rss.py`, `scripts/ingest_news.py`) — fast-poll
   RSS/Atom wires (Reuters, AP, BBC, governor feeds are pluggable) and log each
   item with its **first-seen timestamp**. First-seen time is our proxy for
   "news broke"; the poll interval bounds its accuracy.
4. **Lag measurement** (`stax/lag.py`, `scripts/measure_lag.py`) — join news
   timestamps to subsequent book moves on related markets; output the
   distribution of (a) time-to-first-reprice, (b) magnitude, (c) depth
   available at the pre-news quote.

**Gate 0:** across ≥2 weeks of recording and ≥30 matched news events, the
median exploitable move (depth-weighted, minus spread and taker fee) must be
positive. If not, the project stops here with a data-backed post-mortem —
which is itself a useful artifact.

## Phase 1 — Signal engine

Only if Gate 0 passes.

1. **Scheduled-event playbooks**: for known releases (CPI, FOMC, jobs, court
   rulings with announced dates), pre-map release → market → direction rule.
   No LLM in the hot path; a parser wired to the release source.
2. **Breaking-news mapper** (`stax/mapper.py` grows up): headline → candidate
   markets via keyword/embedding prefilter over the watchlist, then a
   fast LLM call (Claude Haiku-class, strict ~1–2 s budget) to answer only:
   *does this headline move market X, which direction, and how confidently?*
   The LLM never sizes positions and never invents markets — it classifies
   against the prefiltered candidate list.
3. **Shadow mode**: signals are logged against the recorder stream, never sent
   to the exchange. Measure hypothetical entry price vs. price 30 s / 5 min /
   1 h later.

**Gate 1:** shadow-mode expectancy positive after simulated spread + fee +
one-tick adverse slippage, over ≥4 weeks and ≥50 signals.

## Phase 2 — Execution (dry-run first)

1. **Guarded executor** (`stax/executor.py`): wraps `py-clob-client` (note the
   v2 migration — protocol-set fees at match time, pUSD collateral, new order
   type). Defaults to dry-run; refuses live orders unless
   `STAX_LIVE_TRADING=I_UNDERSTAND_THE_RISKS` is set *and* risk checks pass.
2. **Order policy**: marketable-limit only (never naked market orders), price
   cap = pre-news quote + configured slippage, IOC-style semantics, one shot
   per signal — no chasing.
3. **Risk layer** (`stax/risk.py`): hard caps on per-trade notional, per-market
   exposure, daily loss, and open position count; global kill switch file.

**Gate 2:** dry-run execution against live books for ≥2 weeks reproduces
shadow-mode results within tolerance (i.e., our fill assumptions were honest).

## Phase 3 — Live, tiny

- Initial caps: $10–25 per trade, $100 daily loss limit, geopolitics and
  politics categories first (lowest/zero taker fees).
- Compare every live fill to the dry-run prediction; any systematic slippage
  gap goes back to Phase 2.
- Review in fixed 4-week windows against Gate 1 expectancy. Scale caps only
  after two consecutive positive windows; halve them after any negative one.

## Hard constraints (read before running anything live)

- **Jurisdiction**: the offshore CLOB is off-limits to US persons (2022 CFTC
  settlement; geoblocking is active). Polymarket US is intermediated (FCM,
  KYC, no equivalent bot API). See ANALYSIS.md §4. Phase 3 requires operating
  from a permitted jurisdiction — this is the operator's responsibility and a
  blocker, not a nuance.
- **Capital**: only money that can go to zero. The honest prior from
  ANALYSIS.md is that headline markets are already efficient within seconds
  and residual edge lives (small) in the long tail.
- **No martingale, no averaging down, no removing caps in code.** Caps change
  only by editing config in a reviewed commit.

## What STAX deliberately does not do

- No candlestick/chart "technical analysis" — the post's dashboards are set
  dressing and the strategy doesn't use them.
- No crypto perp trading (that's the neighboring HedgeHog project, different
  venue, different risk).
- No claims of expected profit until our own recorder produces the number.
