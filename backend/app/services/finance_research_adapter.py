"""
Context-aware finance research adapter.
Builds personalized research prompts from MCP context with optional external repo support.
"""

from pathlib import Path
from typing import Any


class FinanceResearchAdapter:
    def __init__(self) -> None:
        root_path = Path(__file__).resolve().parents[3]
        self.finance_agent_path = root_path / "external" / "community" / "finance-agent"

    def is_finance_agent_available(self) -> bool:
        return self.finance_agent_path.exists()

    def build_personalized_research_brief(
        self,
        *,
        query: str,
        context_layers: dict[str, Any],
    ) -> dict[str, Any]:
        financial = context_layers.get("user_financial_context", {}).get("data", {})
        signals = context_layers.get("transactional_signals", {}).get("signals", {})
        goals = context_layers.get("user_goals_context", {}).get("goals", [])

        profile = {
            "income_band": financial.get("income_profile", {}).get("monthly_income_band", "UNKNOWN"),
            "net_worth_band": financial.get("assets_profile", {}).get("net_worth_band", "UNKNOWN"),
            "debt_intensity": financial.get("liabilities_profile", {}).get("debt_intensity", "UNKNOWN"),
            "credit_score_band": financial.get("credit_profile", {}).get("credit_score_band", "UNKNOWN"),
            "savings_rate_band": signals.get("savings_rate_band", "UNKNOWN"),
        }

        goal_types = [g.get("goal_type", "UNKNOWN") for g in goals][:5]
        personalized_focus = self._derive_focus(profile=profile, goal_types=goal_types)
        provider = "finance-agent-local" if self.is_finance_agent_available() else "internal-fallback"

        brief = (
            "You are a financial research copilot. Build an evidence-based answer using earnings calls, "
            "SEC filings, and relevant market news. Personalize recommendations using this user context "
            f"(income={profile['income_band']}, net_worth={profile['net_worth_band']}, debt={profile['debt_intensity']}, "
            f"credit={profile['credit_score_band']}, savings={profile['savings_rate_band']}). "
            f"User goals: {', '.join(goal_types) if goal_types else 'not specified'}. "
            f"Research focus: {', '.join(personalized_focus)}. "
            f"User query: {query}"
        )

        return {
            "provider": provider,
            "query": query,
            "personalized_research_brief": brief,
            "profile": profile,
            "goal_types": goal_types,
            "personalized_focus": personalized_focus,
            "is_finance_agent_available": self.is_finance_agent_available(),
        }

    def _derive_focus(self, *, profile: dict[str, str], goal_types: list[str]) -> list[str]:
        focus: list[str] = ["valuation drivers", "forward guidance quality"]

        if profile.get("debt_intensity") == "HIGH":
            focus.append("balance-sheet risk and debt servicing")
        if profile.get("savings_rate_band") == "LOW":
            focus.append("cash-flow resilience and downside protection")
        if "RETIREMENT" in goal_types:
            focus.append("long-term stability and dividend durability")
        if "HOME_PURCHASE" in goal_types:
            focus.append("capital preservation and drawdown risk")

        return focus[:5]


finance_research_adapter = FinanceResearchAdapter()
