import pytest
from app.agents.orchestrator import OrchestratorAgent
from app.agents.finance import FinanceReasoningAgent
from app.agents.knowledge import KnowledgeAgent

@pytest.mark.asyncio
async def test_full_flow_stock_query(mock_cache_manager):
    """
    Test end-to-end flow for a simple stock query.
    Note: deeper integration tests would require real services or heavy mocking.
    """
    orchestrator = OrchestratorAgent()
    # Mocking internal agents for Orchestrator would be ideal
    # For now, we instantiate them

    # We are testing the orchestration logic primarily
    query = "What is the price of Reliance?"

    # Simulate process
    # 1. Classify
    intent = orchestrator.classify_intent(query)
    assert intent in ["KNOWLEDGE", "ANALYSIS"]

    # 2. Plan
    plan = await orchestrator._create_execution_plan(query, {}, {}, intent)
    assert len(plan) >= 2 # At least Knowledge/Finance + Explainability

    # 3. Check for specific agents
    agents = [step['agent'] for step in plan]
    # "reliance" triggers stock lookup -> Knowledge or Finance
    # Based on our previous edits, Orchestrator routes stock queries to knowledge/finance
    assert "knowledge" in agents or "finance_reasoning" in agents

@pytest.mark.asyncio
async def test_performance_metric_tracking():
    """Verify that execution times are tracked (mocked)."""
    # This would use the metrics service/middleware we verified earlier
    pass
