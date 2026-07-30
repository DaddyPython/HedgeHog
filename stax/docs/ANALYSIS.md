# Forensic analysis of the "Claude quant bot" post

This document is the honest read of the hypertech Instagram carousel claiming a
Claude-built bot made "$220,000 in 64 days" by trading Polymarket repricing lag.
Conclusion first: **the post is fabricated marketing content, but the strategy it
describes is a real (heavily competed) strategy class.** The numbers are fantasy;
the mechanism is worth testing empirically. STAX is built to test it, not to
assume it.

## 1. Why the post itself is not evidence

**The account is an engagement funnel, not a trader.** Slide 3 is pure
follow-bait ("You won't see this page again. Follow before it disappears").
Accounts with a real money-printing edge do not need Instagram followers; the
edge decays with every additional participant. The incentive structure only
makes sense if the product being sold is the audience.

**The dashboards are AI-generated set dressing.** The screenshots contain
widgets that do not correspond to anything a real trading system would display:
"MIROFISH — BTC FORCE GRAPH", "STRATEGY DNA — TRADE GENOME", "LIQ RISK 0.6/10",
a "VOLATILITY SURFACE / IV MESH" (there are no options on Polymarket binaries,
so there is no implied-vol surface), and BTC/USD 5-minute candles from a
centralized-exchange feed sitting next to Polymarket branding. The text is
subtly garbled in places, which is characteristic of image-model output.

**The two slides contradict each other.** One shows $232,295 all-time PnL,
62,819 trades, 58.0% win rate; the other shows $119,139, 37,681 trades, 47.0%
win rate — yet both show the *identical* 3.92 "AVG R/R". That is a reused
template with the numbers swapped, not two views of one system.

**The claimed statistics are internally impossible.**

- 62,819 trades in 64 days is ~982 trades/day, ~one every 90 seconds around the
  clock. On Polymarket's books, that volume of taker flow in one account would
  be one of the most visible wallets on the platform. The wallet address is
  conveniently truncated ("0x9f5f...605528") so it cannot be checked.
- A 58% win rate with a 3.92 average reward/risk gives per-trade expectancy of
  roughly 0.58 × 3.92 − 0.42 ≈ **+1.85R**. Compounded over ~63,000 trades, that
  is not "+2,140%", it is a number with dozens of digits. The stats were picked
  to look impressive individually and were never checked against each other.
- The "BIGGEST WIN x111 — entry $34 → $4,344" is only possible by buying a
  ~1-cent tail outcome that then resolved (or repriced) near $1. That is a
  lottery ticket, not evidence of a repeatable process — and it contradicts the
  stated strategy of scalping 30–90-second repricing lags, which produces many
  small wins, never a 111x.

**"Claude built it" is the hook, not the mechanism.** The carousel is
calibrated to ride AI hype (slide 3 is literally a photo of the Claude app).
An LLM can absolutely write a trading bot; that says nothing about whether the
bot has an edge.

## 2. The kernel of truth worth extracting

The described logic — *news breaks → prediction-market odds lag → enter during
the lag → exit into the repricing* — is a real strategy class: **event-driven
latency arbitrage on prediction markets.** It has genuinely worked, for a small
number of fast, specialized actors:

- **Sports in-game latency**: bots with low-latency score feeds picking off
  stale quotes in live-game markets. Well documented, and why serious
  market-makers on sports books pull quotes around scoring events.
- **Scheduled macro prints** (CPI, FOMC, NFP): the release time is known to the
  millisecond, the market mapping is unambiguous, and repricing is a race. In
  2026 the top-of-book on these markets reprices in **~1–3 seconds**, not 30–90.
  This lane is occupied by people with parsers wired to the BLS/Fed release
  infrastructure.
- **Breaking, unscheduled news** (resignations, indictments, deaths, geopolitical
  events): this is the only lane where the "30–90 seconds" claim is even
  plausible, because repricing requires *interpretation* — someone has to read
  the headline, figure out which of thousands of long-tail markets it touches,
  and decide the new fair price. Human attention is the bottleneck, and it is
  scarce on low-liquidity markets.

The honest inference: **if any edge is accessible to a small operator in 2026,
it is in lane 3** — automated news→market mapping over the long tail, where an
LLM in the loop is a genuine differentiator rather than a marketing sticker.
The catch is that long-tail markets are thin: being right earns you tens of
dollars per event, not thousands.

## 3. The economics the post ignores

- **This strategy is 100% taker.** Polymarket now charges per-category taker
  fees: `fee = shares × rate × p × (1−p)`, with rates of 0.04 (politics,
  finance, tech), 0.05 (sports, economics, culture, other), 0.07 (crypto);
  geopolitics is fee-free. At p = 0.50 that peaks around 1.0–1.75% of notional.
  Makers pay zero and earn rebates — the fee structure actively subsidizes the
  people on the *other side* of this strategy.
- **Spread is the bigger cost.** Long-tail books routinely show 2–5¢ spreads.
  Crossing a 3¢ spread on a 50¢ contract costs 6% before fees. The edge per
  event must exceed spread + fee + adverse selection.
- **Depth caps the prize.** Top-of-book depth on non-headline markets is often
  a few hundred to a few thousand dollars. Even a perfect signal nets small
  absolute dollars per event, and your own order moves the book. $3,400/day
  (the post's implied run rate) is not extractable from this liquidity profile
  by taking stale quotes.
- **Exiting "before repricing completes" is a second taker trade** paying the
  spread and fee again, into a book that has already moved toward your entry.
  In practice you often hold to resolution on tails, which changes the risk
  profile entirely.

## 4. Legal and platform reality (US)

- The offshore Polymarket exchange (Polygon CLOB, the one with the public bot
  API) **still geoblocks US persons** per the 2022 CFTC settlement. Trading it
  from the US through a VPN violates the terms and the settlement's intent.
- **Polymarket US** (QCX LLC, a CFTC-designated contract market acquired in the
  QCEX deal) opened general US signup in spring 2026 — but access is
  intermediated through a KYC'd FCM account, currently iOS-first, with a
  narrower market catalog and no equivalent public self-custody bot API.
- Practical consequence: **if the operator is a US person, this bot cannot
  legally run against the offshore CLOB.** Non-US operation, or waiting for
  Polymarket's main exchange to onshore (in CFTC discussion as of 2026), are
  the compliant paths. This is a hard gate, not a footnote.

## 5. What we do about it

The correct engineering response to an unverifiable claim is to **measure the
one number everything depends on**: the actual repricing-lag distribution after
news events, per market category, joined against real book depth. That is
Phase 0 in [PLAN.md](PLAN.md). If the measured lag × depth doesn't clear
spread + fees with margin, the strategy is dead on arrival and we will have
proven it with data instead of a screenshot.

Expectation setting: the realistic best case for a small operator is a system
that earns modest, lumpy returns on long-tail news events with strict per-trade
caps — an interesting, measurable machine. The $220k/64-day number should be
treated as fiction unless our own recorder says otherwise.
