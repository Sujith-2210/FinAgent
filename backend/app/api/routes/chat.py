"""
Chat API Routes
Handles user chat interactions and multi-agent orchestration.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi import Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from loguru import logger
import uuid
import time

from app.agents.coordinator import AgentCoordinator
from app.auth.dependencies import get_current_user
from app.db.models import User
from app.services.alert_service import alert_service
from app.services.finance_research_adapter import finance_research_adapter
from app.services.user_context_service import UserContextService

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for context")


class AgentContribution(BaseModel):
    """Agent contribution in response."""
    agent: str
    reasoning: List[str]
    confidence: str


class ChatResponse(BaseModel):
    """Chat response with agent reasoning."""
    message: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID for context continuity")
    agents_involved: List[str] = Field(default_factory=list)
    agent_contributions: List[AgentContribution] = Field(default_factory=list)
    metrics_used: dict = Field(default_factory=dict)
    actions: List[dict] = Field(default_factory=list, description="Actions like images or widgets")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Store coordinators per session
_coordinators: dict[str, AgentCoordinator] = {}
_session_last_used: dict[str, float] = {}
_MAX_ACTIVE_SESSIONS = 200
_SESSION_IDLE_TTL_SECONDS = 60 * 60 * 2  # 2 hours


def _evict_stale_or_excess_sessions() -> None:
    """Bound coordinator memory by evicting idle and oldest sessions."""
    now = time.time()

    stale = [
        sid for sid, last_used in _session_last_used.items()
        if now - last_used > _SESSION_IDLE_TTL_SECONDS
    ]
    for sid in stale:
        _coordinators.pop(sid, None)
        _session_last_used.pop(sid, None)

    if len(_coordinators) <= _MAX_ACTIVE_SESSIONS:
        return

    # Evict oldest sessions until we are under the cap.
    for sid, _ in sorted(_session_last_used.items(), key=lambda x: x[1]):
        _coordinators.pop(sid, None)
        _session_last_used.pop(sid, None)
        if len(_coordinators) <= _MAX_ACTIVE_SESSIONS:
            break


def _should_build_external_research_brief(query: str) -> bool:
    query_lower = query.lower()
    trigger_keywords = [
        "earnings",
        "10-k",
        "sec filing",
        "quarterly result",
        "guidance",
        "company analysis",
        "stock research",
        "market news",
    ]
    return any(keyword in query_lower for keyword in trigger_keywords)


def get_coordinator(session_id: str, mcp_manager) -> AgentCoordinator:
    """Get or create a coordinator for a session."""
    _evict_stale_or_excess_sessions()
    if session_id not in _coordinators:
        _coordinators[session_id] = AgentCoordinator(mcp_manager)
    _session_last_used[session_id] = time.time()
    return _coordinators[session_id]


@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Send a chat message and get AI response with reasoning.

    This endpoint orchestrates multiple agents to provide:
    - Personalized financial advice
    - Step-by-step reasoning
    - Privacy-preserved metrics
    """
    logger.info(f"Chat request: {request.message[:50]}...")

    try:
        # Get MCP manager from app state
        mcp_manager = req.app.state.mcp_manager

        # Public session ID for client; internal session ID is namespaced by user ID.
        public_session_id = request.session_id or str(uuid.uuid4())
        internal_session_id = f"{current_user.user_id}:{public_session_id}"

        # Get coordinator for this session
        coordinator = get_coordinator(internal_session_id, mcp_manager)

        # Process the query through multi-agent system
        result = await coordinator.process_query(
            query=request.message,
            session_id=internal_session_id
        )

        # Opportunistically generate sentiment-driven alerts from user market text.
        # This path is intentionally best-effort and should never fail the chat flow.
        sentiment_signal = {"checked": False}
        try:
            sentiment_result = await alert_service.run_sentiment_alert_check(
                user_id=current_user.user_id,
                text=request.message,
            )
            sentiment_signal = {"checked": True, **sentiment_result}
        except Exception as sentiment_error:
            logger.warning(f"Sentiment alert check skipped due to error: {sentiment_error}")
            sentiment_signal = {
                "checked": False,
                "message": "sentiment_check_failed",
            }

        metrics_used = dict(result.get("metrics_used", {}))
        metrics_used["sentiment_signal"] = sentiment_signal

        if _should_build_external_research_brief(request.message):
            try:
                context_service = UserContextService(req.app.state.mcp_manager)
                context = await context_service.get_context_response(user_id=current_user.user_id)
                research = finance_research_adapter.build_personalized_research_brief(
                    query=request.message,
                    context_layers=context.get("layers", {}),
                )
                metrics_used["external_research_brief"] = {
                    "provider": research.get("provider"),
                    "personalized_focus": research.get("personalized_focus", []),
                    "is_finance_agent_available": research.get("is_finance_agent_available", False),
                }
            except Exception as research_error:
                logger.warning(f"External research brief skipped due to error: {research_error}")
                metrics_used["external_research_brief"] = {"status": "skipped"}

        # Format response
        return ChatResponse(
            message=result.get("message", "I couldn't process your request."),
            session_id=public_session_id,
            agents_involved=result.get("agents_involved", []),
            agent_contributions=[
                AgentContribution(
                    agent=c["agent"],
                    reasoning=c["reasoning"],
                    confidence=c["confidence"]
                )
                for c in result.get("agent_contributions", [])
            ],
            metrics_used=metrics_used,
            actions=result.get("actions", []),
            timestamp=result.get("timestamp", datetime.utcnow())
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    session_id: Optional[str] = None,
    limit: int = 50,
):
    """Get chat history for a session."""
    # TODO: Implement chat history retrieval from database
    return {
        "messages": [],
        "session_id": session_id,
        "total": 0
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str, current_user: User = Depends(get_current_user)):
    """Clear a chat session and its coordinator."""
    internal_session_id = f"{current_user.user_id}:{session_id}"
    if internal_session_id in _coordinators:
        del _coordinators[internal_session_id]
        _session_last_used.pop(internal_session_id, None)
        return {"status": "cleared", "session_id": session_id}
    return {"status": "not_found", "session_id": session_id}
