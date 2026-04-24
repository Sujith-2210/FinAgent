"""
AI4Finance sentiment service.
Provides a lightweight FinGPT-compatible sentiment signal with safe fallbacks.
"""

from pathlib import Path
from typing import Any


POSITIVE_KEYWORDS = {
    "beat",
    "growth",
    "surge",
    "rally",
    "bullish",
    "upgrade",
    "profit",
    "strong",
    "outperform",
    "optimistic",
}

NEGATIVE_KEYWORDS = {
    "miss",
    "drop",
    "crash",
    "bearish",
    "downgrade",
    "loss",
    "weak",
    "underperform",
    "risk",
    "uncertain",
}


class AI4FinanceSentimentService:
    """
    Sentiment scoring helper for finance text.
    """

    def __init__(self) -> None:
        root_path = Path(__file__).resolve().parents[3]
        self.fingpt_local_path = root_path / "external" / "ai4finance" / "FinGPT"

    def analyze_text(self, text: str) -> dict[str, Any]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return {
                "score": 0.0,
                "label": "NEUTRAL",
                "provider": "heuristic-fallback",
                "details": "empty_input",
            }

        tokens = [token.lower().strip(".,!?;:()[]{}\"'") for token in cleaned_text.split()]
        tokens = [token for token in tokens if token]

        positive_hits = sum(1 for token in tokens if token in POSITIVE_KEYWORDS)
        negative_hits = sum(1 for token in tokens if token in NEGATIVE_KEYWORDS)
        total_hits = positive_hits + negative_hits

        if total_hits == 0:
            score = 0.0
        else:
            score = (positive_hits - negative_hits) / total_hits

        label = "NEUTRAL"
        if score >= 0.25:
            label = "POSITIVE"
        elif score <= -0.25:
            label = "NEGATIVE"

        provider = "fingpt-local-compatible-heuristic" if self.fingpt_local_path.exists() else "heuristic-fallback"
        return {
            "score": round(score, 4),
            "label": label,
            "provider": provider,
            "details": {
                "positive_hits": positive_hits,
                "negative_hits": negative_hits,
                "total_tokens": len(tokens),
            },
        }


ai4finance_sentiment_service = AI4FinanceSentimentService()
