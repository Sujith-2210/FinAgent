
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.services.feedback_service import FeedbackService

router = APIRouter()
feedback_service = FeedbackService()

class FeedbackRequest(BaseModel):
    query_id: str
    rating: int  # 1 for positive, -1 for negative
    agent_name: str
    comment: Optional[str] = None
    original_query: Optional[str] = None

@router.post("/")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback for an agent response.
    """
    try:
        await feedback_service.log_feedback(feedback.model_dump())
        return {"status": "success", "message": "Feedback received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_feedback():
    """Get recent feedback (for admin/debug)."""
    return await feedback_service.get_recent_feedback()
