"""
MCP Context Manager
Manages the 7-layer MCP context with versioning, access control, and audit logging.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from loguru import logger

from app.mcp.fi_mcp import FiMCPService
from app.privacy.masking import PrivacyMasker
from app.privacy.access_control import access_controller


class PrivacyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ContextLayer(str, Enum):
    """Available MCP context layers."""
    USER_FINANCIAL_CONTEXT = "user_financial_context"
    TRANSACTIONAL_SIGNALS = "transactional_signals"
    USER_GOALS_CONTEXT = "user_goals_context"
    EXTERNAL_KNOWLEDGE_CONTEXT = "external_knowledge_context"
    AGENT_WORKING_MEMORY = "agent_working_memory"
    EXPLAINABILITY_CONTEXT = "explainability_context"
    ALERT_CONTEXT = "alert_context"


class ContextAccessLog(BaseModel):
    """Log entry for context access."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: str
    layer: str
    operation: str  # "read" or "write"
    context_version: int


class MCPContext(BaseModel):
    """
    Full MCP Context with all 7 layers.

    This is the central data structure that agents interact with.
    """
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    context_version: int = 1
    privacy_level: PrivacyLevel = PrivacyLevel.HIGH

    # Layer 1: User Financial Context (from Fi MCP)
    user_financial_context: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "fi-mcp-dev",
        "last_sync": None,
        "data": {
            # Raw values for internal agent use (NEVER sent to frontend)
            "raw_values": {
                "monthly_income": None,
                "net_worth": None,
                "total_assets": None,
                "total_liabilities": None,
                "credit_score": None,
                "credit_utilization": None,
                "savings_rate": None,
                "monthly_expenses": None,
                "monthly_emi": None,
            },
            "demographics_profile": {
                "age": None,
                "risk_profile": "MODERATE"
            },
            "income_profile": {
                "monthly_income_band": None,
                "income_stability": None
            },
            "assets_profile": {
                "net_worth_band": None,
                "asset_classes": []
            },
            "liabilities_profile": {
                "has_loans": False,
                "debt_intensity": None
            },
            "credit_profile": {
                "credit_score_band": None,
                "credit_utilization_band": None
            }
        }
    })

    # Layer 2: Transactional Signals (derived)
    transactional_signals: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "derived",
        "computed_at": None,
        "signals": {
            "savings_rate_band": None,
            "emi_burden_band": None,
            "spending_volatility": None
        }
    })

    # Layer 3: User Goals Context
    user_goals_context: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "user",
        "goals": []
    })

    # Layer 4: External Knowledge Context (Firecrawl)
    external_knowledge_context: Dict[str, Any] = Field(default_factory=lambda: {
        "source": "firecrawl-mcp",
        "last_updated": None,
        "knowledge_items": []
    })

    # Layer 5: Agent Working Memory (ephemeral)
    agent_working_memory: Dict[str, Any] = Field(default_factory=lambda: {
        "session_id": None,
        "entries": []
    })

    # Layer 6: Explainability & Audit Context
    explainability_context: Dict[str, Any] = Field(default_factory=lambda: {
        "agent_trace": [],
        "confidence_score": None
    })

    # Layer 7: Alert Context
    alert_context: Dict[str, Any] = Field(default_factory=lambda: {
        "active_alerts": []
    })

    # NEW: Access Controls & Consent Flags (Sprint 1)
    access_controls: Dict[str, bool] = Field(default_factory=lambda: {
        "can_call_external_price_api": False,
        "can_access_full_transactions": False
    })

    user_preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "consent_flags": {
            "allow_external_retrieval": False,
            "allow_graph_analysis": False
        },
        "risk_band": "moderate",
        "investment_horizon_months": 12
    })


class ContextManager:
    """
    Manages MCP context lifecycle, access control, and versioning.

    Key responsibilities:
    - Load/sync context from Fi MCP
    - Apply privacy masking
    - Enforce agent access rules
    - Version control and audit logging
    """

    def __init__(self, fi_mcp_service: FiMCPService):
        self.fi_mcp_service = fi_mcp_service
        self.privacy_masker = PrivacyMasker()
        self._context: Optional[MCPContext] = None
        self._access_log: List[ContextAccessLog] = []

    async def initialize_context(self, user_id: Optional[str] = None) -> MCPContext:
        """Initialize a new MCP context."""
        self._context = MCPContext(user_id=user_id)
        logger.info(f"Initialized context: {self._context.context_id}")
        return self._context

    async def sync_from_fi_mcp(self) -> None:
        """Sync context with latest data from Fi MCP."""
        if self._context is None:
            await self.initialize_context()

        logger.info("Syncing context from Fi MCP...")

        try:
            # Fetch all financial data
            financial_data = await self.fi_mcp_service.fetch_all_financial_data()

            # Demographics
            if financial_data.get("user_profile"):
                profile = financial_data["user_profile"]
                self._context.user_financial_context["data"]["demographics_profile"] = {
                    "age": profile.age,
                    "risk_profile": profile.risk_profile
                }

            # Apply privacy masking and update context - Net Worth
            if financial_data.get("net_worth"):
                net_worth = financial_data["net_worth"]

                # Store RAW values for internal agent use
                total_assets = sum(
                    a.value.units if hasattr(a, 'value') and hasattr(a.value, 'units') else getattr(a, 'value_inr', 0)
                    for a in net_worth.assets
                )
                total_liabilities = sum(
                    liability.value.units if hasattr(liability, 'value') and hasattr(liability.value, 'units') else getattr(liability, 'value_inr', 0)
                    for liability in net_worth.liabilities
                )
                self._context.user_financial_context["data"]["raw_values"]["net_worth"] = net_worth.total_net_worth
                self._context.user_financial_context["data"]["raw_values"]["total_assets"] = total_assets
                self._context.user_financial_context["data"]["raw_values"]["total_liabilities"] = total_liabilities

                # Masked bands for API response / frontend
                self._context.user_financial_context["data"]["assets_profile"] = {
                    "net_worth_band": self.privacy_masker.mask_net_worth(net_worth.total_net_worth),
                    "asset_classes": [a.asset_type for a in net_worth.assets]
                }
                self._context.user_financial_context["data"]["liabilities_profile"] = {
                    "has_loans": len(net_worth.liabilities) > 0,
                    "debt_intensity": self.privacy_masker.calculate_debt_intensity(net_worth),
                    "loan_types": [liability.liability_type for liability in net_worth.liabilities]
                }

            # Credit Report
            if financial_data.get("credit_report"):
                credit = financial_data["credit_report"]
                utilization_band = self.privacy_masker.mask_credit_utilization(
                    credit.credit_utilization if credit.credit_utilization else None
                )

                # Store RAW credit data
                self._context.user_financial_context["data"]["raw_values"]["credit_score"] = credit.credit_score
                self._context.user_financial_context["data"]["raw_values"]["credit_utilization"] = credit.credit_utilization

                self._context.user_financial_context["data"]["credit_profile"] = {
                    "credit_score_band": self.privacy_masker.mask_credit_score(credit.credit_score),
                    "credit_utilization_band": utilization_band or "LOW",
                    "active_loans": len(credit.loans)
                }

            # Transactions - Calculate savings rate
            if financial_data.get("transactions"):
                txns = financial_data["transactions"]
                if txns.total_credits > 0:
                    savings_rate = (txns.total_credits - txns.total_debits) / txns.total_credits
                else:
                    savings_rate = 0

                # Store RAW transaction data
                self._context.user_financial_context["data"]["raw_values"]["monthly_income"] = txns.total_credits
                self._context.user_financial_context["data"]["raw_values"]["monthly_expenses"] = txns.total_debits
                self._context.user_financial_context["data"]["raw_values"]["savings_rate"] = savings_rate

                self._context.transactional_signals["signals"] = {
                    "savings_rate_band": self.privacy_masker.mask_savings_rate(savings_rate),
                    "spending_pattern": "MODERATE" if savings_rate > 0.2 else "HIGH",
                    "income_stability": "STABLE"
                }
                self._context.transactional_signals["computed_at"] = datetime.utcnow().isoformat()

            # Update sync timestamp
            self._context.user_financial_context["last_sync"] = datetime.utcnow().isoformat()
            self._context.last_updated = datetime.utcnow()
            self._context.context_version += 1

            logger.info(f"Context synced. Version: {self._context.context_version}")

        except Exception as e:
            logger.error(f"Context sync failed: {e}")
            raise

    def get_context(self) -> Optional[MCPContext]:
        """Get the current context."""
        return self._context

    def get_layer(self, layer: ContextLayer, agent: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific context layer with access logging.

        Args:
            layer: The layer to access
            agent: Name of the agent requesting access

        Returns:
            Layer data if access is allowed, None otherwise
        """
        if self._context is None:
            return None

        if not access_controller.can_read(agent, layer.value):
            logger.warning(f"Access denied: agent={agent} layer={layer.value} op=read")
            return None

        # Log access
        self._access_log.append(ContextAccessLog(
            agent=agent,
            layer=layer.value,
            operation="read",
            context_version=self._context.context_version
        ))

        # Return layer data
        return getattr(self._context, layer.value, None)

    def get_raw_financial_values(self, agent: str) -> Dict[str, Any]:
        """
        Get raw (unmasked) financial values for internal agent processing.

        These values MUST NEVER be included in API responses to the frontend.
        They are used by agents to produce deeply personalized recommendations.

        Args:
            agent: Name of the agent requesting access

        Returns:
            Dict with raw financial values (monthly_income, net_worth, etc.)
        """
        if self._context is None:
            return {}

        if not access_controller.can_read(agent, ContextLayer.USER_FINANCIAL_CONTEXT.value):
            logger.warning(f"Raw access denied: agent={agent}")
            return {}

        # Log raw access for audit trail
        self._access_log.append(ContextAccessLog(
            agent=agent,
            layer="user_financial_context.raw_values",
            operation="read_raw",
            context_version=self._context.context_version
        ))

        return self._context.user_financial_context.get("data", {}).get("raw_values", {})

    def update_layer(
        self,
        layer: ContextLayer,
        agent: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Update a specific context layer with access logging.

        Args:
            layer: The layer to update
            agent: Name of the agent making the update
            data: New data to merge into the layer

        Returns:
            True if update succeeded, False otherwise
        """
        if self._context is None:
            return False

        if not access_controller.can_write(agent, layer.value):
            logger.warning(f"Access denied: agent={agent} layer={layer.value} op=write")
            return False

        # Log access
        self._access_log.append(ContextAccessLog(
            agent=agent,
            layer=layer.value,
            operation="write",
            context_version=self._context.context_version
        ))

        # Update layer
        current_data = getattr(self._context, layer.value, {})
        current_data.update(data)
        setattr(self._context, layer.value, current_data)

        # Increment version
        self._context.context_version += 1
        self._context.last_updated = datetime.utcnow()

        logger.debug(f"Layer {layer.value} updated by {agent}")
        return True

    def get_llm_safe_projection(self) -> Dict[str, Any]:
        """
        Get a privacy-safe projection of context for LLM prompts.

        This is what the LLM sees - no raw values, only bands and summaries.
        """
        if self._context is None:
            return {}

        return {
            "financial_summary": {
                "income": self._context.user_financial_context["data"]["income_profile"].get("monthly_income_band"),
                "savings_rate": self._context.transactional_signals["signals"].get("savings_rate_band"),
                "debt_level": self._context.user_financial_context["data"]["liabilities_profile"].get("debt_intensity"),
                "credit_health": self._context.user_financial_context["data"]["credit_profile"].get("credit_score_band")
            },
            "goals": [g.get("goal_type") for g in self._context.user_goals_context.get("goals", [])],
            "external_rules": [
                item.get("summary")
                for item in self._context.external_knowledge_context.get("knowledge_items", [])
            ],
            "active_alerts": len(self._context.alert_context.get("active_alerts", []))
        }

    def get_access_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent context access log entries."""
        return [
            log.model_dump()
            for log in self._access_log[-limit:]
        ]

    def clear_working_memory(self) -> None:
        """Clear ephemeral working memory (called at session end)."""
        if self._context:
            self._context.agent_working_memory = {
                "session_id": None,
                "entries": []
            }
            logger.info("Working memory cleared")
