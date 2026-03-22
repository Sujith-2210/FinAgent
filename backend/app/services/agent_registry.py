"""
Agent Registry
Central in-memory state for enabling/disabling agents at runtime.
"""

from typing import Dict

_AGENT_TOGGLE_STATE: Dict[str, bool] = {
    "orchestrator": True,
    "finance_reasoning": True,
    "knowledge": True,
    "deep_research": True,
    "graph_reasoning": True,
    "code": True,
    "explainability": True,
    "alert": True,
}


def is_agent_enabled(agent_name: str) -> bool:
    """Return whether an agent is currently enabled."""
    return _AGENT_TOGGLE_STATE.get(agent_name, True)


def set_agent_enabled(agent_name: str, enabled: bool) -> None:
    """Set runtime enabled/disabled state for an agent."""
    _AGENT_TOGGLE_STATE[agent_name] = enabled


def get_agent_toggle_state() -> Dict[str, bool]:
    """Get a copy of current runtime toggle state."""
    return _AGENT_TOGGLE_STATE.copy()
