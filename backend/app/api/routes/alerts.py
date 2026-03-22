"""
Alerts API Routes
Handles proactive financial alerts and insights.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.services.alert_service import alert_service

router = APIRouter()


class AlertType(str, Enum):
    RISK = "RISK"
    OPPORTUNITY = "OPPORTUNITY"
    INFO = "INFO"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISMISSED = "DISMISSED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


class AlertResponse(BaseModel):
    """Financial alert model for API response."""
    alert_id: str
    alert_type: str = Field(..., alias="type")
    severity: str
    title: str
    description: str
    triggered_by: str
    status: str
    created_at: datetime
    context_snapshot: dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True


@router.get("/", response_model=dict)
async def get_alerts(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """
    Get active alerts for the authenticated user.
    """
    alerts = await alert_service.get_active_alerts(user_id=current_user.user_id, limit=limit)
    
    return {
        "alerts": [AlertResponse.model_validate(a).model_dump(by_alias=True) for a in alerts],
        "total": len(alerts),
        "unread": len(alerts),
    }


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, current_user: User = Depends(get_current_user)):
    """Dismiss an alert."""
    success = await alert_service.dismiss_alert(alert_id=alert_id, user_id=current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    return {
        "alert_id": alert_id,
        "status": "DISMISSED",
        "message": "Alert dismissed"
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, current_user: User = Depends(get_current_user)):
    """Acknowledge an alert without dismissing it."""
    success = await alert_service.acknowledge_alert(alert_id=alert_id, user_id=current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    return {
        "alert_id": alert_id,
        "status": "ACKNOWLEDGED",
        "message": "Alert acknowledged"
    }


@router.post("/trigger-check")
async def trigger_check(current_user: User = Depends(get_current_user)):
    """
    Manually trigger proactive alert checks for the authenticated user.
    """
    result = await alert_service.run_proactive_check(user_id=current_user.user_id)
    return {
        "message": "Proactive check completed",
        **result,
    }
