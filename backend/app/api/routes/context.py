"""
Context API Routes
Exposes persisted, per-user MCP context layers.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.privacy.audit_log import audit_logger
from app.services.user_context_service import UserContextService

router = APIRouter()


def _get_context_service(req: Request) -> UserContextService:
    return UserContextService(req.app.state.mcp_manager)


@router.get("/")
async def get_full_context(req: Request, current_user: User = Depends(get_current_user)):
    """
    Get complete persisted context for the authenticated user.
    """
    try:
        service = _get_context_service(req)
        return await service.get_context_response(user_id=current_user.user_id)
    except Exception as e:
        logger.error(f"Context retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve context")


@router.get("/layer/{layer_name}")
async def get_context_layer(layer_name: str, req: Request, current_user: User = Depends(get_current_user)):
    """Get a specific context layer."""
    valid_layers = [
        "user_financial_context",
        "transactional_signals",
        "user_goals_context",
        "external_knowledge_context",
        "agent_working_memory",
        "explainability_context",
        "alert_context",
    ]

    if layer_name not in valid_layers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid layer. Valid layers: {valid_layers}",
        )

    full_context = await get_full_context(req, current_user=current_user)
    layer_data = full_context.get("layers", {}).get(layer_name, {})
    last_updated = (
        full_context.get("layers", {})
        .get("user_financial_context", {})
        .get("last_sync")
    )

    return {
        "layer": layer_name,
        "data": layer_data,
        "last_updated": last_updated,
    }


@router.get("/audit")
async def get_context_audit_log(limit: int = 100, current_user: User = Depends(get_current_user)):
    """Get context access audit log."""
    user_hash = audit_logger.hash_identifier(current_user.user_id)
    entries = [
        entry for entry in audit_logger.export_logs()
        if entry.get("user_id_hash") == user_hash
    ]
    return {
        "entries": list(reversed(entries[-limit:])),
        "total": len(entries),
    }


@router.post("/sync")
async def sync_context(req: Request, current_user: User = Depends(get_current_user)):
    """
    Trigger fresh sync from Fi-MCP and persist new user context snapshot.
    """
    try:
        service = _get_context_service(req)
        snapshot = await service.sync_user_context(user_id=current_user.user_id)
        return {
            "status": "synced",
            "message": "Context sync completed",
            "context_id": snapshot.context_id,
            "new_version": snapshot.version,
            "synced_at": (snapshot.context_data or {}).get("fetched_at"),
        }
    except Exception as e:
        logger.error(f"Context sync error: {e}")
        raise HTTPException(status_code=500, detail="Context sync failed")


@router.get("/fi-money")
async def get_fi_money_data(req: Request, current_user: User = Depends(get_current_user)):
    """
    Get per-user Fi-MCP summary data from persisted context.
    """
    service = _get_context_service(req)
    context = await service.get_context_response(user_id=current_user.user_id)
    layers = context.get("layers", {})
    financial = layers.get("user_financial_context", {}).get("data", {})
    signals = layers.get("transactional_signals", {}).get("signals", {})

    return {
        "source": "fi-mcp-dev",
        "user_id": current_user.user_id,
        "last_sync": layers.get("user_financial_context", {}).get("last_sync"),
        "net_worth": {
            "band": financial.get("assets_profile", {}).get("net_worth_band", "UNKNOWN"),
            "asset_classes": financial.get("assets_profile", {}).get("asset_classes", []),
            "liabilities": financial.get("liabilities_profile", {}).get("loan_types", []),
            "debt_intensity": financial.get("liabilities_profile", {}).get("debt_intensity", "LOW"),
        },
        "credit_report": {
            "score_band": financial.get("credit_profile", {}).get("credit_score_band", "UNKNOWN"),
            "utilization_band": financial.get("credit_profile", {}).get("credit_utilization_band", "UNKNOWN"),
            "active_loans": financial.get("credit_profile", {}).get("active_loans", 0),
        },
        "insights": {
            "income_band": financial.get("income_profile", {}).get("monthly_income_band", "UNKNOWN"),
            "savings_rate_band": signals.get("savings_rate_band", "UNKNOWN"),
            "expense_band": signals.get("expense_band", "UNKNOWN"),
            "top_expense_categories": signals.get("top_expense_categories", []),
        },
    }
