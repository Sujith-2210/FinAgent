"""
AI4Finance integration registry.
Tracks optional external repositories and local availability.
"""

from pathlib import Path
from typing import Any


AI4FINANCE_REPOSITORIES = [
    {
        "id": "fingpt",
        "name": "FinGPT",
        "source": "ai4finance-foundation",
        "repo_url": "https://github.com/AI4Finance-Foundation/FinGPT",
        "use_case": "finance_llm_and_sentiment",
        "local_dir": "external/ai4finance/FinGPT",
        "integration_status": "planned_optional",
    },
    {
        "id": "finrag",
        "name": "FinRAG",
        "source": "ai4finance-foundation",
        "repo_url": "https://github.com/AI4Finance-Foundation/FinRAG",
        "use_case": "financial_rag_pipeline",
        "local_dir": "external/ai4finance/FinRAG",
        "integration_status": "planned_optional",
    },
    {
        "id": "finrobot",
        "name": "FinRobot",
        "source": "ai4finance-foundation",
        "repo_url": "https://github.com/AI4Finance-Foundation/FinRobot",
        "use_case": "agentic_financial_analysts",
        "local_dir": "external/ai4finance/FinRobot",
        "integration_status": "planned_optional",
    },
    {
        "id": "finrl",
        "name": "FinRL",
        "source": "ai4finance-foundation",
        "repo_url": "https://github.com/AI4Finance-Foundation/FinRL",
        "use_case": "portfolio_and_trading_rl_research",
        "local_dir": "external/ai4finance/FinRL",
        "integration_status": "research_optional",
    },
    {
        "id": "finance_agent",
        "name": "finance-agent",
        "source": "community",
        "repo_url": "https://github.com/kamathhrishi/finance-agent.git",
        "use_case": "earnings_calls_sec_filings_news_rag",
        "local_dir": "external/community/finance-agent",
        "integration_status": "planned_optional",
    },
]


def get_ai4finance_integrations() -> dict[str, Any]:
    root_path = Path(__file__).resolve().parents[3]
    integrations: list[dict[str, Any]] = []

    for repository in AI4FINANCE_REPOSITORIES:
        local_path = root_path / repository["local_dir"]
        integrations.append(
            {
                **repository,
                "is_local_clone_available": local_path.exists(),
                "local_path": str(local_path),
            }
        )

    return {"integrations": integrations, "total": len(integrations)}
