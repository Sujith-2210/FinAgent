import pytest
import time
from hypothesis import given, strategies as st
from app.agents.knowledge import KnowledgeAgent

# Property-Based Testing
@given(st.text(min_size=1, max_size=100))
def test_knowledge_clean_content_property(content):
    """
    Property: _clean_content should never crash and always return string <= max_length
    """
    agent = KnowledgeAgent()
    cleaned = agent._clean_content(content, max_length=50)
    assert isinstance(cleaned, str)
    assert len(cleaned) <= 53 # 50 + "..."

# Performance Testing
@pytest.mark.asyncio
async def test_agent_latency_threshold():
    """
    Ensure agent instantiation and basic processing is fast (< 10ms for non-I/O).
    Real I/O tests belong in a separate benchmark suite.
    """
    start_time = time.time()
    agent = KnowledgeAgent()
    _ = agent.input_schema
    duration = time.time() - start_time
    
    assert duration < 0.01 # 10ms
