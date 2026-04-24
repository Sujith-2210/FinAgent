from app.services.finance_research_adapter import finance_research_adapter


def test_build_personalized_research_brief_uses_mcp_context():
    context_layers = {
        "user_financial_context": {
            "data": {
                "income_profile": {"monthly_income_band": "MEDIUM"},
                "assets_profile": {"net_worth_band": "HIGH"},
                "liabilities_profile": {"debt_intensity": "LOW"},
                "credit_profile": {"credit_score_band": "EXCELLENT"},
            }
        },
        "transactional_signals": {
            "signals": {"savings_rate_band": "HIGH"}
        },
        "user_goals_context": {
            "goals": [{"goal_type": "RETIREMENT"}, {"goal_type": "HOME_PURCHASE"}]
        },
    }

    result = finance_research_adapter.build_personalized_research_brief(
        query="Analyze long-term risk for NVDA",
        context_layers=context_layers,
    )

    assert "personalized_research_brief" in result
    assert result["profile"]["income_band"] == "MEDIUM"
    assert result["profile"]["debt_intensity"] == "LOW"
    assert "RETIREMENT" in result["goal_types"]
    assert len(result["personalized_focus"]) > 0


def test_build_personalized_research_brief_handles_missing_context():
    result = finance_research_adapter.build_personalized_research_brief(
        query="Compare growth and valuation signals",
        context_layers={},
    )

    assert result["profile"]["income_band"] == "UNKNOWN"
    assert result["profile"]["savings_rate_band"] == "UNKNOWN"
    assert result["goal_types"] == []
