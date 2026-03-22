"""
Dashboard API Routes
Provides persisted, per-user financial dashboard data.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.services.user_context_service import UserContextService

router = APIRouter()


class NetWorthData(BaseModel):
    """Net worth summary with privacy-masked values."""
    band: str = Field(..., description="Net worth band: LOW, MEDIUM, HIGH")
    trend: str = Field(default="stable", description="Trend: up, down, stable")
    asset_breakdown: dict = Field(default_factory=dict)
    liability_breakdown: dict = Field(default_factory=dict)


class CreditHealthData(BaseModel):
    """Credit health summary."""
    score_band: str = Field(..., description="Credit score band")
    utilization_band: str = Field(..., description="Credit utilization band")
    active_loans: int = Field(default=0)
    on_time_payments: str = Field(default="N/A")


class CashFlowData(BaseModel):
    """Monthly cash flow summary."""
    income_band: str
    expense_band: str
    savings_rate_band: str
    top_expense_categories: List[str] = Field(default_factory=list)


class DashboardData(BaseModel):
    """Complete dashboard data."""
    net_worth: NetWorthData
    credit_health: CreditHealthData
    cash_flow: CashFlowData
    last_updated: Optional[str] = None


def _service(req: Request) -> UserContextService:
    return UserContextService(req.app.state.mcp_manager)


@router.get("/", response_model=DashboardData)
async def get_dashboard_data(req: Request, current_user: User = Depends(get_current_user)):
    """Get persisted dashboard data for the authenticated user."""
    try:
        service = _service(req)
        payload = await service.get_dashboard_response(user_id=current_user.user_id)
        return DashboardData(**payload)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


@router.get("/net-worth")
async def get_net_worth_details(req: Request, current_user: User = Depends(get_current_user)):
    """Get detailed net-worth breakdown from persisted per-user context."""
    try:
        service = _service(req)
        context = await service.get_context_response(user_id=current_user.user_id)
        financial = context.get("layers", {}).get("user_financial_context", {}).get("data", {})
        assets = financial.get("assets_profile", {})
        liabilities = financial.get("liabilities_profile", {})
        return {
            "band": assets.get("net_worth_band", "UNKNOWN"),
            "assets": {
                "types": assets.get("asset_classes", []),
                "diversification": "HIGH" if len(assets.get("asset_classes", [])) >= 4 else "MODERATE",
            },
            "liabilities": {
                "types": liabilities.get("loan_types", []),
                "debt_intensity": liabilities.get("debt_intensity", "LOW"),
            },
        }
    except Exception as e:
        logger.error(f"Net worth error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load net-worth details")


@router.get("/trends")
async def get_financial_trends(
    req: Request,
    period: str = "monthly",
    current_user: User = Depends(get_current_user),
):
    """Get trend summary from persisted snapshot version comparisons."""
    try:
        service = _service(req)
        trends = await service.get_trend_response(user_id=current_user.user_id)
        return {
            "period": period,
            "net_worth_trend": trends["net_worth_trend"],
            "savings_trend": trends["savings_trend"],
            "debt_trend": trends["debt_trend"],
            "last_updated": trends["last_updated"],
        }
    except Exception as e:
        logger.error(f"Trend analysis error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load trends")
