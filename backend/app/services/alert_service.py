"""
Alert Service
Handles generation, persistence, and management of financial alerts.
"""

from sqlalchemy import desc, select, update
from typing import Any, Dict, List
import uuid

from app.db.models import Alert, ContextSnapshot
from app.db.database import async_session_maker
from app.services.ai4finance_sentiment_service import ai4finance_sentiment_service

class AlertService:
    """
    Service for managing alerts.
    """
    
    async def get_active_alerts(self, user_id: str, limit: int = 50) -> List[Alert]:
        """Get active alerts for a specific user."""
        async with async_session_maker() as session:
            query = select(Alert).where(
                Alert.status == "ACTIVE",
                Alert.user_id == user_id,
            )
            result = await session.execute(query.order_by(Alert.created_at.desc()).limit(limit))
            return result.scalars().all()

    async def create_alert(
        self,
        title: str,
        description: str,
        severity: str,
        alert_type: str,
        triggered_by: str,
        user_id: str,
        context: dict | None = None,
    ) -> Alert:
        """Create a new alert."""
        async with async_session_maker() as session:
            alert = Alert(
                alert_id=str(uuid.uuid4()),
                user_id=user_id,
                title=title,
                description=description,
                severity=severity,
                alert_type=alert_type,
                triggered_by=triggered_by,
                context_snapshot=context or {},
                status="ACTIVE"
            )
            session.add(alert)
            await session.commit()
            return alert

    async def dismiss_alert(self, alert_id: str, user_id: str) -> bool:
        """Dismiss a user's alert."""
        async with async_session_maker() as session:
            query = update(Alert).where(
                Alert.alert_id == alert_id,
                Alert.user_id == user_id,
            )
            result = await session.execute(query.values(status="DISMISSED"))
            await session.commit()
            return result.rowcount > 0

    async def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """Acknowledge a user's alert."""
        async with async_session_maker() as session:
            query = update(Alert).where(
                Alert.alert_id == alert_id,
                Alert.user_id == user_id,
            )
            result = await session.execute(query.values(status="ACKNOWLEDGED"))
            await session.commit()
            return result.rowcount > 0

    async def _get_latest_context_snapshot(self, user_id: str) -> ContextSnapshot | None:
        """Fetch latest persisted context snapshot for a user."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(ContextSnapshot)
                .where(ContextSnapshot.user_id == user_id)
                .order_by(desc(ContextSnapshot.version))
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _active_alert_exists(self, user_id: str, title: str, triggered_by: str) -> bool:
        """Check if an equivalent active alert already exists to avoid duplicates."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Alert).where(
                    Alert.user_id == user_id,
                    Alert.status == "ACTIVE",
                    Alert.title == title,
                    Alert.triggered_by == triggered_by,
                )
            )
            return result.scalar_one_or_none() is not None

    async def run_proactive_check(self, user_id: str) -> Dict[str, int]:
        """
        Run proactive checks using the user's persisted context snapshot.
        """
        snapshot = await self._get_latest_context_snapshot(user_id=user_id)
        if snapshot is None:
            return {"evaluated_rules": 0, "created_alerts": 0}

        layers = (snapshot.context_data or {}).get("layers", {})
        financial = layers.get("user_financial_context", {}).get("data", {})
        signals = layers.get("transactional_signals", {}).get("signals", {})

        savings_band = str(signals.get("savings_rate_band", "UNKNOWN")).upper()
        debt_intensity = str(
            financial.get("liabilities_profile", {}).get("debt_intensity", "LOW")
        ).upper()

        created_alerts = 0
        evaluated_rules = 0

        async def create_if_missing(
            *,
            title: str,
            description: str,
            severity: str,
            alert_type: str,
            triggered_by: str,
            context: Dict[str, Any],
        ) -> None:
            nonlocal created_alerts
            exists = await self._active_alert_exists(
                user_id=user_id,
                title=title,
                triggered_by=triggered_by,
            )
            if exists:
                return

            await self.create_alert(
                title=title,
                description=description,
                severity=severity,
                alert_type=alert_type,
                triggered_by=triggered_by,
                user_id=user_id,
                context=context,
            )
            created_alerts += 1

        evaluated_rules += 1
        if savings_band == "LOW":
            await create_if_missing(
                title="Low Savings Rate Detected",
                description="Your current savings-rate band is LOW. Consider reducing discretionary spending.",
                severity="MEDIUM",
                alert_type="RISK",
                triggered_by="context_signal_monitor",
                context={
                    "savings_rate_band": savings_band,
                    "snapshot_version": snapshot.version,
                },
            )

        evaluated_rules += 1
        if debt_intensity == "HIGH":
            await create_if_missing(
                title="High Debt Intensity",
                description="Debt intensity is HIGH in your latest profile. Prioritize repayment planning.",
                severity="HIGH",
                alert_type="RISK",
                triggered_by="context_signal_monitor",
                context={
                    "debt_intensity": debt_intensity,
                    "snapshot_version": snapshot.version,
                },
            )

        evaluated_rules += 1
        if savings_band == "HIGH" and debt_intensity == "LOW":
            await create_if_missing(
                title="Investment Opportunity Window",
                description="Strong savings with low debt intensity detected. You may evaluate long-term investments.",
                severity="LOW",
                alert_type="OPPORTUNITY",
                triggered_by="context_signal_monitor",
                context={
                    "savings_rate_band": savings_band,
                    "debt_intensity": debt_intensity,
                    "snapshot_version": snapshot.version,
                },
            )

        return {"evaluated_rules": evaluated_rules, "created_alerts": created_alerts}

    async def run_sentiment_alert_check(self, user_id: str, text: str) -> Dict[str, Any]:
        """
        Analyze a finance text sentiment and create an alert when signal is strong.
        """
        result = ai4finance_sentiment_service.analyze_text(text=text)
        score = float(result.get("score", 0.0))
        label = str(result.get("label", "NEUTRAL")).upper()

        if label == "NEUTRAL":
            return {
                "created_alert": False,
                "sentiment": result,
                "message": "Sentiment is neutral. No alert generated.",
            }

        severity = "MEDIUM" if abs(score) < 0.6 else "HIGH"
        is_negative_sentiment = label == "NEGATIVE"
        title = "Negative Market Sentiment Signal" if is_negative_sentiment else "Positive Market Sentiment Signal"
        description = (
            "Market commentary appears risk-heavy. Consider conservative positioning."
            if is_negative_sentiment
            else "Market commentary appears constructive. Review opportunity allocation."
        )
        alert_type = "RISK" if is_negative_sentiment else "OPPORTUNITY"

        exists = await self._active_alert_exists(
            user_id=user_id,
            title=title,
            triggered_by="ai4finance_fingpt_sentiment",
        )
        if exists:
            return {
                "created_alert": False,
                "sentiment": result,
                "message": "Equivalent sentiment alert already active.",
            }

        await self.create_alert(
            title=title,
            description=description,
            severity=severity,
            alert_type=alert_type,
            triggered_by="ai4finance_fingpt_sentiment",
            user_id=user_id,
            context={"sentiment": result},
        )

        return {
            "created_alert": True,
            "sentiment": result,
            "message": "Sentiment alert created.",
        }

# Singleton
alert_service = AlertService()
