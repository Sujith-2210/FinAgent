"""
Agents API Routes
Provides visibility into multi-agent system status and activity.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from loguru import logger
from app.privacy.audit_log import audit_logger
from app.services.agent_registry import get_agent_toggle_state, set_agent_enabled

router = APIRouter()


class AgentInfo(BaseModel):
    """Agent information model."""
    name: str
    description: str
    status: str = Field(default="idle", description="idle, active, disabled")
    last_invoked: Optional[datetime] = None
    read_layers: List[str] = Field(default_factory=list)
    write_layers: List[str] = Field(default_factory=list)


class AgentActivity(BaseModel):
    """Recent agent activity."""
    agent: str
    action: str
    timestamp: datetime
    context_accessed: List[str] = Field(default_factory=list)
    reasoning_steps: List[str] = Field(default_factory=list)


@router.get("/status")
async def get_agents_status():
    """Get status of all agents in the system."""
    toggle_state = get_agent_toggle_state()
    logs = audit_logger.export_logs()
    last_invoked_by_agent: dict[str, datetime] = {}
    for log in logs:
        ts = log.get("timestamp")
        agent = log.get("agent_name")
        if not agent or not ts:
            continue
        try:
            parsed = datetime.fromisoformat(ts)
            if agent not in last_invoked_by_agent or parsed > last_invoked_by_agent[agent]:
                last_invoked_by_agent[agent] = parsed
        except Exception:
            continue

    agents = [
        AgentInfo(
            name="orchestrator",
            description="Routes queries to specialized agents and manages execution flow",
            status="active" if toggle_state["orchestrator"] else "disabled",
            last_invoked=last_invoked_by_agent.get("orchestrator"),
            read_layers=["user_goals_context"],
            write_layers=["agent_working_memory"]
        ),
        AgentInfo(
            name="finance_reasoning",
            description="Performs financial calculations and analysis",
            status="idle" if toggle_state["finance_reasoning"] else "disabled",
            last_invoked=last_invoked_by_agent.get("finance_reasoning"),
            read_layers=["user_financial_context", "transactional_signals", "user_goals_context"],
            write_layers=["agent_working_memory", "explainability_context"]
        ),
        AgentInfo(
            name="knowledge",
            description="Retrieves external facts and regulations via Firecrawl MCP",
            status="idle" if toggle_state["knowledge"] else "disabled",
            last_invoked=last_invoked_by_agent.get("knowledge"),
            read_layers=["external_knowledge_context"],
            write_layers=["external_knowledge_context"]
        ),
        AgentInfo(
            name="explainability",
            description="Converts agent outputs to human-readable explanations",
            status="idle" if toggle_state["explainability"] else "disabled",
            last_invoked=last_invoked_by_agent.get("explainability"),
            read_layers=["agent_working_memory", "explainability_context"],
            write_layers=["explainability_context"]
        ),
        AgentInfo(
            name="alert",
            description="Monitors financial signals and generates proactive alerts",
            status="idle" if toggle_state["alert"] else "disabled",
            last_invoked=last_invoked_by_agent.get("alert"),
            read_layers=["transactional_signals", "user_financial_context"],
            write_layers=["alert_context"]
        )
    ]

    return {
        "agents": [agent.model_dump() for agent in agents],
        "total": len(agents),
        "active_count": sum(1 for a in agents if a.status in {"active", "idle"})
    }


@router.get("/activity")
async def get_agent_activity(limit: int = 20):
    """Get recent agent activity log."""
    logs = list(reversed(audit_logger.export_logs()[-limit:]))
    activities = [
        AgentActivity(
            agent=log.get("agent_name", "unknown"),
            action="invoke",
            timestamp=datetime.fromisoformat(log.get("timestamp")),
            context_accessed=log.get("context_layers_accessed", []),
            reasoning_steps=[log.get("reasoning", "")]
        ).model_dump()
        for log in logs
        if log.get("timestamp")
    ]
    return {
        "activities": activities,
        "total": len(audit_logger.export_logs())
    }


@router.get("/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent."""
    valid_agents = ["orchestrator", "finance_reasoning", "knowledge", "explainability", "alert"]

    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found. Valid agents: {valid_agents}"
        )

    toggle_state = get_agent_toggle_state()
    logs = [log for log in audit_logger.export_logs() if log.get("agent_name") == agent_name]
    last_reasoning = [log.get("reasoning", "") for log in logs[-5:]]

    return {
        "name": agent_name,
        "status": "idle" if toggle_state.get(agent_name, True) else "disabled",
        "invocation_count": len(logs),
        "avg_response_time_ms": 0,
        "last_reasoning_trace": last_reasoning
    }


@router.post("/{agent_name}/toggle")
async def toggle_agent(agent_name: str, enabled: bool = True):
    """Enable or disable an agent."""
    valid_agents = ["finance_reasoning", "knowledge", "explainability", "alert"]

    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail="Cannot toggle this agent. Orchestrator cannot be disabled."
        )

    set_agent_enabled(agent_name, enabled)
    logger.info(f"Agent toggle updated: {agent_name} enabled={enabled}")

    return {
        "agent": agent_name,
        "enabled": enabled,
        "message": f"Agent {agent_name} {'enabled' if enabled else 'disabled'}"
    }
