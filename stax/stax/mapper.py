"""Headline -> market matching.

v0 is deliberately dumb: keyword overlap between the headline and market
questions on the watchlist. It exists so Phase 0 lag measurement has *some*
join key between news and markets. Phase 1 replaces the scoring with an
embedding prefilter plus a latency-budgeted LLM classification, per
docs/PLAN.md — but only if Gate 0 passes.
"""

from __future__ import annotations

import re

STOPWORDS = {
    "will", "the", "a", "an", "of", "in", "on", "to", "by", "be", "is", "at",
    "for", "and", "or", "before", "after", "with", "than", "more", "less",
    "does", "do", "what", "who", "when", "how", "as", "its", "his", "her",
    "this", "that", "from", "into", "over", "under", "2025", "2026",
}


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def match_score(headline: str, question: str) -> float:
    """Jaccard-ish overlap weighted toward the (shorter) headline side."""
    h, q = tokens(headline), tokens(question)
    if not h or not q:
        return 0.0
    return len(h & q) / min(len(h), len(q))


def candidate_markets(
    headline: str,
    watchlist: list[dict],
    min_score: float = 0.34,
    top_n: int = 5,
) -> list[tuple[float, dict]]:
    scored = [
        (score, market)
        for market in watchlist
        if (score := match_score(headline, market["question"])) >= min_score
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[:top_n]
