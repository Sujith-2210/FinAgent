"""
Context Access Control
Defines and enforces agent access rules for MCP context layers.
"""

from typing import Dict, List, Set
from enum import Enum
from pydantic import BaseModel, Field
from loguru import logger


class AccessPermission(str, Enum):
    """Access permission types."""
    READ = "read"
    WRITE = "write"


class AgentAccessRules(BaseModel):
    """Access rules for a single agent."""
    agent_name: str
    read_layers: Set[str] = Field(default_factory=set)
    write_layers: Set[str] = Field(default_factory=set)


# Define access rules for each agent
# This is the single source of truth for context access control

AGENT_ACCESS_RULES: Dict[str, AgentAccessRules] = {
    "orchestrator": AgentAccessRules(
        agent_name="orchestrator",
        read_layers={"user_goals_context"},
        write_layers={"agent_working_memory"}
    ),
    "finance_reasoning": AgentAccessRules(
        agent_name="finance_reasoning",
        read_layers={
            "user_financial_context",
            "transactional_signals",
            "user_goals_context"
        },
        write_layers={
            "agent_working_memory",
            "explainability_context"
        }
    ),
    "knowledge": AgentAccessRules(
        agent_name="knowledge",
        read_layers={"external_knowledge_context"},
        write_layers={"external_knowledge_context"}
    ),
    "deep_research": AgentAccessRules(
        agent_name="deep_research",
        read_layers={"external_knowledge_context"},
        write_layers={"external_knowledge_context"}
    ),
    "graph_reasoning": AgentAccessRules(
        agent_name="graph_reasoning",
        read_layers={"external_knowledge_context", "agent_working_memory"},
        write_layers={"agent_working_memory"}
    ),
    "code": AgentAccessRules(
        agent_name="code",
        read_layers={"agent_working_memory"},
        write_layers={"agent_working_memory"}
    ),
    "explainability": AgentAccessRules(
        agent_name="explainability",
        read_layers={
            "agent_working_memory",
            "explainability_context"
        },
        write_layers={"explainability_context"}
    ),
    "alert": AgentAccessRules(
        agent_name="alert",
        read_layers={
            "transactional_signals",
            "user_financial_context"
        },
        write_layers={"alert_context"}
    )
}


class AccessController:
    """
    Enforces access control rules for context layers.

    Key responsibilities:
    - Check if an agent can read a layer
    - Check if an agent can write to a layer
    - Log access violations
    """

    def __init__(self):
        self.rules = AGENT_ACCESS_RULES
        self._violations: List[Dict] = []

    def can_read(self, agent: str, layer: str) -> bool:
        """
        Check if an agent can read a context layer.

        Args:
            agent: Name of the agent
            layer: Name of the context layer

        Returns:
            True if access is allowed, False otherwise
        """
        if agent not in self.rules:
            logger.warning(f"Unknown agent: {agent}")
            return False

        allowed = layer in self.rules[agent].read_layers

        if not allowed:
            self._log_violation(agent, layer, "read")

        return allowed

    def can_write(self, agent: str, layer: str) -> bool:
        """
        Check if an agent can write to a context layer.

        Args:
            agent: Name of the agent
            layer: Name of the context layer

        Returns:
            True if access is allowed, False otherwise
        """
        if agent not in self.rules:
            logger.warning(f"Unknown agent: {agent}")
            return False

        allowed = layer in self.rules[agent].write_layers

        if not allowed:
            self._log_violation(agent, layer, "write")

        return allowed

    def get_readable_layers(self, agent: str) -> Set[str]:
        """Get all layers an agent can read."""
        if agent not in self.rules:
            return set()
        return self.rules[agent].read_layers

    def get_writable_layers(self, agent: str) -> Set[str]:
        """Get all layers an agent can write to."""
        if agent not in self.rules:
            return set()
        return self.rules[agent].write_layers

    def get_agent_permissions(self, agent: str) -> Dict[str, List[str]]:
        """Get complete permission summary for an agent."""
        if agent not in self.rules:
            return {"read": [], "write": []}

        return {
            "read": list(self.rules[agent].read_layers),
            "write": list(self.rules[agent].write_layers)
        }

    def _log_violation(self, agent: str, layer: str, operation: str):
        """Log an access violation."""
        violation = {
            "agent": agent,
            "layer": layer,
            "operation": operation
        }
        self._violations.append(violation)
        logger.warning(f"Access violation: {agent} attempted {operation} on {layer}")

    def get_violations(self) -> List[Dict]:
        """Get all recorded violations."""
        return self._violations.copy()

    def clear_violations(self):
        """Clear the violations log."""
        self._violations.clear()


# Singleton instance
access_controller = AccessController()
