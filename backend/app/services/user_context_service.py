"""
User Context Service
Builds and persists per-user financial context snapshots and dashboard projections.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import statistics
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select

from app.db.database import async_session_maker
from app.db.models import ContextSnapshot, UserGoal
from app.mcp.fi_mcp import FiMCPService
from app.privacy.masking import PrivacyMasker


@dataclass
class DashboardProjection:
    net_worth: Dict[str, Any]
    credit_health: Dict[str, Any]
    cash_flow: Dict[str, Any]
    last_updated: str | None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "net_worth": self.net_worth,
            "credit_health": self.credit_health,
            "cash_flow": self.cash_flow,
            "last_updated": self.last_updated,
        }


class UserContextService:
    """Service layer for persisted user context snapshots."""

    def __init__(self, mcp_manager):
        self.fi_service = FiMCPService(mcp_manager)
        self.masker = PrivacyMasker()

    async def get_latest_snapshot(self, user_id: str) -> Optional[ContextSnapshot]:
        """Return latest persisted context snapshot for user."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(ContextSnapshot)
                .where(ContextSnapshot.user_id == user_id)
                .order_by(desc(ContextSnapshot.version))
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_or_sync_snapshot(self, user_id: str, session_id: Optional[str] = None) -> ContextSnapshot:
        """Return latest snapshot; if none exists, sync from Fi-MCP and persist one."""
        latest = await self.get_latest_snapshot(user_id)
        if latest:
            return latest
        return await self.sync_user_context(user_id=user_id, session_id=session_id)

    async def sync_user_context(self, user_id: str, session_id: Optional[str] = None) -> ContextSnapshot:
        """Fetch fresh data from Fi-MCP, build masked layers, and persist a snapshot."""
        data = await self.fi_service.fetch_all_financial_data(session_id=session_id)
        goals = await self._get_user_goals(user_id)

        latest = await self.get_latest_snapshot(user_id)
        context_id = latest.context_id if latest else str(uuid.uuid4())
        new_version = (latest.version + 1) if latest else 1

        layers = self._build_layers(data=data, goals=goals)
        snapshot_payload = {
            "privacy_level": "HIGH",
            "layers": layers,
            "fetched_at": data.get("fetched_at"),
        }

        snapshot = ContextSnapshot(
            context_id=context_id,
            user_id=user_id,
            version=new_version,
            context_data=snapshot_payload,
        )

        async with async_session_maker() as session:
            session.add(snapshot)
            await session.commit()
            await session.refresh(snapshot)

        return snapshot

    async def get_context_response(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Build API response payload for /api/context from latest persisted snapshot."""
        snapshot = await self.get_or_sync_snapshot(user_id=user_id, session_id=session_id)
        payload = snapshot.context_data or {}
        return {
            "context_id": snapshot.context_id,
            "context_version": snapshot.version,
            "privacy_level": payload.get("privacy_level", "HIGH"),
            "layers": payload.get("layers", {}),
        }

    async def get_dashboard_response(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Build dashboard response from persisted snapshot + previous trend."""
        snapshot = await self.get_or_sync_snapshot(user_id=user_id, session_id=session_id)
        previous = await self._get_previous_snapshot(user_id=user_id, version=snapshot.version)

        current_payload = snapshot.context_data or {}
        current_layers = current_payload.get("layers", {})

        current_nw_band = (
            current_layers.get("user_financial_context", {})
            .get("data", {})
            .get("assets_profile", {})
            .get("net_worth_band", "UNKNOWN")
        )
        previous_nw_band = "UNKNOWN"
        if previous:
            previous_nw_band = (
                (previous.context_data or {})
                .get("layers", {})
                .get("user_financial_context", {})
                .get("data", {})
                .get("assets_profile", {})
                .get("net_worth_band", "UNKNOWN")
            )

        projection = self._build_dashboard_projection(current_layers, current_nw_band, previous_nw_band)
        return projection.to_dict()

    async def get_trend_response(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, str]:
        """Build trend response by comparing latest snapshot with previous version."""
        snapshot = await self.get_or_sync_snapshot(user_id=user_id, session_id=session_id)
        previous = await self._get_previous_snapshot(user_id=user_id, version=snapshot.version)

        current_layers = (snapshot.context_data or {}).get("layers", {})
        previous_layers = (previous.context_data or {}).get("layers", {}) if previous else {}

        current_nw = (
            current_layers.get("user_financial_context", {})
            .get("data", {})
            .get("assets_profile", {})
            .get("net_worth_band", "UNKNOWN")
        )
        previous_nw = (
            previous_layers.get("user_financial_context", {})
            .get("data", {})
            .get("assets_profile", {})
            .get("net_worth_band", "UNKNOWN")
        )

        current_savings = (
            current_layers.get("transactional_signals", {})
            .get("signals", {})
            .get("savings_rate_band", "UNKNOWN")
        )
        previous_savings = (
            previous_layers.get("transactional_signals", {})
            .get("signals", {})
            .get("savings_rate_band", "UNKNOWN")
        )

        current_debt = (
            current_layers.get("user_financial_context", {})
            .get("data", {})
            .get("liabilities_profile", {})
            .get("debt_intensity", "UNKNOWN")
        )
        previous_debt = (
            previous_layers.get("user_financial_context", {})
            .get("data", {})
            .get("liabilities_profile", {})
            .get("debt_intensity", "UNKNOWN")
        )

        return {
            "net_worth_trend": self._trend_from_bands(previous_nw, current_nw),
            "savings_trend": self._progress_from_bands(previous_savings, current_savings),
            "debt_trend": self._debt_trend(previous_debt, current_debt),
            "last_updated": current_layers.get("user_financial_context", {}).get("last_sync"),
        }

    async def _get_previous_snapshot(self, user_id: str, version: int) -> Optional[ContextSnapshot]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(ContextSnapshot)
                .where(
                    ContextSnapshot.user_id == user_id,
                    ContextSnapshot.version < version,
                )
                .order_by(desc(ContextSnapshot.version))
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _get_user_goals(self, user_id: str) -> List[Dict[str, Any]]:
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserGoal)
                .where(UserGoal.user_id == user_id, UserGoal.is_active.is_(True))
                .order_by(UserGoal.created_at.desc())
            )
            goals = result.scalars().all()

        return [
            {
                "goal_id": g.goal_id,
                "goal_type": g.goal_type,
                "target_horizon": g.target_horizon,
                "priority": g.priority,
                "description": g.description,
            }
            for g in goals
        ]

    def _build_layers(self, data: Dict[str, Any], goals: List[Dict[str, Any]]) -> Dict[str, Any]:
        net_worth = data.get("net_worth")
        credit = data.get("credit_report")
        transactions = data.get("transactions")
        user_profile = data.get("user_profile")

        total_credits = float(transactions.total_credits if transactions else 0)
        total_debits = float(transactions.total_debits if transactions else 0)
        income_est = total_credits / 3 if total_credits > 0 else 0
        expense_est = total_debits / 3 if total_debits > 0 else 0
        savings_rate = (income_est - expense_est) / income_est if income_est > 0 else 0

        net_worth_band = self.masker.mask_net_worth(net_worth.total_net_worth if net_worth else 0) or "UNKNOWN"
        debt_intensity = self.masker.calculate_debt_intensity(net_worth) or "LOW"
        credit_score_band = self.masker.mask_credit_score(credit.credit_score if credit else 0) or "UNKNOWN"
        credit_util_band = self.masker.mask_credit_utilization(credit.credit_utilization if credit else 0) or "UNKNOWN"
        income_band = self.masker.mask_income(income_est) or "UNKNOWN"
        savings_band = self.masker.mask_savings_rate(savings_rate) or "UNKNOWN"
        expense_band = self._mask_expense(expense_est)

        asset_classes = [a.asset_type for a in net_worth.assets] if net_worth else []
        loan_types = [l.liability_type for l in net_worth.liabilities] if net_worth else []
        top_expense_categories = self._top_expense_categories(transactions.transactions if transactions else [])
        spending_volatility = self._spending_volatility(transactions.transactions if transactions else [])
        emi_burden = self._derive_emi_burden(debt_intensity)

        return {
            "user_financial_context": {
                "source": "fi-mcp-dev",
                "last_sync": data.get("fetched_at"),
                "data": {
                    "demographics_profile": {
                        "age": user_profile.age if user_profile else None,
                        "risk_profile": user_profile.risk_profile if user_profile else "MODERATE",
                    },
                    "income_profile": {
                        "monthly_income_band": income_band,
                        "income_stability": self.masker.determine_income_stability(
                            transactions.transactions if transactions else []
                        ) or "UNKNOWN",
                    },
                    "assets_profile": {
                        "net_worth_band": net_worth_band,
                        "asset_classes": asset_classes,
                    },
                    "liabilities_profile": {
                        "has_loans": bool(loan_types),
                        "debt_intensity": debt_intensity,
                        "loan_types": loan_types,
                    },
                    "credit_profile": {
                        "credit_score_band": credit_score_band,
                        "credit_utilization_band": credit_util_band,
                        "active_loans": len(credit.loans) if credit and credit.loans else 0,
                        "on_time_payments": "N/A",
                    },
                },
            },
            "transactional_signals": {
                "source": "derived",
                "computed_at": datetime.utcnow().isoformat(),
                "signals": {
                    "savings_rate_band": savings_band,
                    "expense_band": expense_band,
                    "emi_burden_band": emi_burden,
                    "spending_volatility": spending_volatility,
                    "top_expense_categories": top_expense_categories,
                },
            },
            "user_goals_context": {
                "source": "db",
                "goals": goals,
            },
            "external_knowledge_context": {
                "source": "firecrawl-mcp",
                "knowledge_items": [],
            },
            "agent_working_memory": {
                "entries": [],
            },
            "explainability_context": {
                "agent_trace": [],
            },
            "alert_context": {
                "active_alerts": [],
            },
        }

    def _build_dashboard_projection(
        self,
        layers: Dict[str, Any],
        current_nw_band: str,
        previous_nw_band: str,
    ) -> DashboardProjection:
        financial_data = layers.get("user_financial_context", {}).get("data", {})
        transaction_signals = layers.get("transactional_signals", {}).get("signals", {})

        assets_profile = financial_data.get("assets_profile", {})
        liabilities_profile = financial_data.get("liabilities_profile", {})
        credit_profile = financial_data.get("credit_profile", {})
        income_profile = financial_data.get("income_profile", {})

        asset_classes = [str(a).upper() for a in assets_profile.get("asset_classes", [])]
        net_worth = {
            "band": current_nw_band,
            "trend": self._trend_from_bands(previous_nw_band, current_nw_band),
            "asset_breakdown": {
                "mutual_funds": "present" if any("MUTUAL" in a for a in asset_classes) else "absent",
                "epf": "present" if any("EPF" in a for a in asset_classes) else "absent",
                "stocks": "present" if any("SECURITIES" in a or "STOCK" in a for a in asset_classes) else "absent",
                "bank_balance": "present" if any("SAVINGS" in a or "BANK" in a for a in asset_classes) else "absent",
            },
            "liability_breakdown": {
                "loans": "present" if liabilities_profile.get("has_loans") else "none",
                "intensity": liabilities_profile.get("debt_intensity", "LOW"),
            },
        }

        credit_health = {
            "score_band": credit_profile.get("credit_score_band", "UNKNOWN"),
            "utilization_band": credit_profile.get("credit_utilization_band", "UNKNOWN"),
            "active_loans": credit_profile.get("active_loans", 0),
            "on_time_payments": credit_profile.get("on_time_payments", "N/A"),
        }

        cash_flow = {
            "income_band": income_profile.get("monthly_income_band", "UNKNOWN"),
            "expense_band": transaction_signals.get("expense_band", "UNKNOWN"),
            "savings_rate_band": transaction_signals.get("savings_rate_band", "UNKNOWN"),
            "top_expense_categories": transaction_signals.get("top_expense_categories", ["Uncategorized"]),
        }

        return DashboardProjection(
            net_worth=net_worth,
            credit_health=credit_health,
            cash_flow=cash_flow,
            last_updated=layers.get("user_financial_context", {}).get("last_sync"),
        )

    def _mask_expense(self, monthly_expense_inr: float) -> str:
        if monthly_expense_inr < 30000:
            return "LOW"
        if monthly_expense_inr <= 100000:
            return "MEDIUM"
        return "HIGH"

    def _top_expense_categories(self, transactions: List[Any]) -> List[str]:
        category_totals: Dict[str, float] = {}
        for txn in transactions:
            if getattr(txn, "type", "").upper() != "DEBIT":
                continue
            category = getattr(txn, "category", "Uncategorized") or "Uncategorized"
            amount = float(getattr(txn, "amount", 0) or 0)
            category_totals[category] = category_totals.get(category, 0.0) + amount

        if not category_totals:
            return ["Uncategorized"]

        return [
            c for c, _ in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        ]

    def _spending_volatility(self, transactions: List[Any]) -> str:
        debits = [
            float(getattr(txn, "amount", 0) or 0)
            for txn in transactions
            if getattr(txn, "type", "").upper() == "DEBIT"
        ]
        if len(debits) < 2:
            return "LOW"

        mean_val = statistics.mean(debits)
        if mean_val <= 0:
            return "LOW"
        cv = statistics.pstdev(debits) / mean_val
        if cv > 0.70:
            return "HIGH"
        if cv > 0.35:
            return "MEDIUM"
        return "LOW"

    def _derive_emi_burden(self, debt_intensity: str) -> str:
        if debt_intensity == "HIGH":
            return "HIGH"
        if debt_intensity == "MEDIUM":
            return "MEDIUM"
        return "LOW"

    def _trend_from_bands(self, previous_band: str, current_band: str) -> str:
        order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        previous = order.get(str(previous_band).upper(), 0)
        current = order.get(str(current_band).upper(), 0)
        if current > previous:
            return "up"
        if current < previous:
            return "down"
        return "stable"

    def _progress_from_bands(self, previous_band: str, current_band: str) -> str:
        order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        previous = order.get(str(previous_band).upper(), 0)
        current = order.get(str(current_band).upper(), 0)
        if current > previous:
            return "improving"
        if current < previous:
            return "worsening"
        return "stable"

    def _debt_trend(self, previous_band: str, current_band: str) -> str:
        order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        previous = order.get(str(previous_band).upper(), 0)
        current = order.get(str(current_band).upper(), 0)
        if current < previous:
            return "decreasing"
        if current > previous:
            return "increasing"
        return "stable"
