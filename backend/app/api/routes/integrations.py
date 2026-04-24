"""
Integration routes for optional external finance AI repos.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.services.ai4finance_registry import get_ai4finance_integrations
from app.services.finance_research_adapter import finance_research_adapter
from app.services.user_context_service import UserContextService

router = APIRouter()


@router.get("/ai4finance")
async def get_ai4finance_status():
    """Get AI4Finance repository integration status."""
    return get_ai4finance_integrations()


class PersonalizedResearchRequest(BaseModel):
    query: str = Field(..., min_length=8, description="Financial research query")


@router.post("/personalized-research")
async def run_personalized_research(
    payload: PersonalizedResearchRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Build a context-aware research brief using persisted MCP context layers.
    """
    try:
        context_service = UserContextService(req.app.state.mcp_manager)
        context = await context_service.get_context_response(user_id=current_user.user_id)
        context_layers = context.get("layers", {})

        research = finance_research_adapter.build_personalized_research_brief(
            query=payload.query,
            context_layers=context_layers,
        )

        return {
            "user_id": current_user.user_id,
            "context_version": context.get("context_version"),
            "privacy_level": context.get("privacy_level", "HIGH"),
            "research": research,
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Failed to build personalized research brief: {error}")
