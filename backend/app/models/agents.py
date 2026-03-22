"""
Agent I/O Schemas
Pydantic models for structured agent inputs and outputs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================
# Orchestrator Agent Schemas
# ============================================================

class OrchestratorInput(BaseModel):
    """Input schema for Orchestrator Agent."""
    user_query: str = Field(..., description="The user's question or request")
    available_agents: List[str] = Field(
        default=["finance_reasoning", "knowledge", "explainability", "alert"],
        description="List of available agent names"
    )
    context_summary: Dict[str, bool] = Field(
        default_factory=dict,
        description="Summary of available context (has_assets, has_liabilities, etc.)"
    )


class AgentTask(BaseModel):
    """Single agent task in execution plan."""
    agent: str = Field(..., description="Agent name to invoke")
    context_required: List[str] = Field(
        default_factory=list,
        description="Context layers this agent needs"
    )


class OrchestratorOutput(BaseModel):
    """Output schema for Orchestrator Agent."""
    execution_plan: List[AgentTask] = Field(
        ..., 
        description="Ordered list of agents to invoke"
    )
    reason: str = Field(..., description="Explanation for the execution plan")


# ============================================================
# Finance Reasoning Agent Schemas
# ============================================================

class FinancialContext(BaseModel):
    """Financial context for Finance Agent."""
    income_summary: Optional[str] = None
    expense_summary: Optional[str] = None
    assets_summary: Optional[str] = None
    liabilities_summary: Optional[str] = None


class FinanceReasoningInput(BaseModel):
    """Input schema for Finance Reasoning Agent."""
    financial_context: FinancialContext
    user_goal: Optional[str] = None


class FinanceMetrics(BaseModel):
    """Calculated financial metrics (privacy-masked)."""
    savings_rate: Optional[str] = Field(None, description="LOW, MEDIUM, or HIGH")
    debt_to_income_ratio: Optional[str] = Field(None, description="LOW, MEDIUM, or HIGH")
    investment_diversification: Optional[str] = Field(None, description="LOW, MODERATE, or HIGH")


class FinanceReasoningOutput(BaseModel):
    """Output schema for Finance Reasoning Agent."""
    metrics: FinanceMetrics = Field(default_factory=FinanceMetrics)
    signals_detected: List[str] = Field(
        default_factory=list,
        description="Financial signals/observations"
    )
    intermediate_reasoning: List[str] = Field(
        default_factory=list,
        description="Step-by-step calculation logic"
    )


# ============================================================
# Knowledge Agent Schemas
# ============================================================

class KnowledgeInput(BaseModel):
    """Input schema for Knowledge Agent."""
    query_topic: str = Field(..., description="Topic to research")
    source: str = Field(default="Firecrawl MCP", description="Knowledge source")


class KnowledgeFact(BaseModel):
    """Single fact from knowledge retrieval."""
    fact: str
    source_type: Optional[str] = None
    confidence: str = Field(default="MEDIUM", description="HIGH, MEDIUM, or LOW")


class KnowledgeOutput(BaseModel):
    """Output schema for Knowledge Agent."""
    facts: List[str] = Field(default_factory=list, description="Retrieved facts")
    source_type: Optional[str] = None
    confidence: str = Field(default="MEDIUM")


# ============================================================
# Explainability Agent Schemas
# ============================================================

class ExplainabilityInput(BaseModel):
    """Input schema for Explainability Agent."""
    finance_output: Optional[Dict[str, Any]] = None
    knowledge_output: Optional[Dict[str, Any]] = None
    confidence_level: str = Field(default="MEDIUM")


class ExplainabilityOutput(BaseModel):
    """Output schema for Explainability Agent."""
    summary: str = Field(..., description="Human-readable summary")
    key_reasons: List[str] = Field(
        default_factory=list,
        description="Key reasons for the recommendation"
    )
    assumptions_used: List[str] = Field(
        default_factory=list,
        description="Assumptions made in the analysis"
    )
    confidence: str = Field(default="MEDIUM")


# ============================================================
# Alert Agent Schemas
# ============================================================

class AlertInput(BaseModel):
    """Input schema for Alert Agent."""
    signals: List[str] = Field(
        default_factory=list,
        description="Financial signals to evaluate"
    )


class AlertItem(BaseModel):
    """Single alert item."""
    type: str = Field(..., description="RISK, OPPORTUNITY, or INFO")
    title: str
    severity: str = Field(..., description="LOW, MEDIUM, or HIGH")
    reason: str


class AlertOutput(BaseModel):
    """Output schema for Alert Agent."""
    alerts: List[AlertItem] = Field(default_factory=list)


# ============================================================
# Common Schemas
# ============================================================

class AgentTrace(BaseModel):
    """Trace of agent execution for explainability."""
    agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_summary: str
    output_summary: str
    reasoning_steps: List[str] = Field(default_factory=list)
    context_accessed: List[str] = Field(default_factory=list)
    confidence: str = Field(default="MEDIUM")
