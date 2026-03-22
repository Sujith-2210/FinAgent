"""
Real-Time Data API Routes
Endpoints for real-time market data and alerts.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

router = APIRouter()


class PriceRequest(BaseModel):
    """Request model for price data"""
    symbol: str


class AlertRequest(BaseModel):
    """Request model for creating price alerts"""
    user_id: str
    symbol: str
    threshold_type: str  # "ABOVE" | "BELOW" | "CHANGE_PERCENT"
    threshold_value: float


@router.get("/price/{symbol}")
async def get_stock_price(symbol: str, request: Request):
    """
    Get latest price for a stock symbol.
    
    Args:
        symbol: Stock symbol (e.g., HDFCBANK.NS, TSLA)
        
    Returns:
        Price data with latency < 2s
    """
    realtime_service = request.app.state.realtime_service
    
    if not realtime_service:
        raise HTTPException(
            status_code=503,
            detail="Real-time data service not available (Redis may not be running)"
        )
    
    try:
        price_data = await realtime_service.get_latest_price(symbol)
        
        if not price_data:
            raise HTTPException(
                status_code=404,
                detail=f"Price data not available for symbol: {symbol}"
            )
        
        return price_data
        
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/{index_symbol}")
async def get_market_regime(index_symbol: str, request: Request):
    """
    Get current market regime for an index.
    
    Args:
        index_symbol: Market index symbol (e.g., ^NSEI for NIFTY 50)
        
    Returns:
        Market regime: BULL | BEAR | SIDEWAYS
    """
    realtime_service = request.app.state.realtime_service
    
    if not realtime_service:
        raise HTTPException(
            status_code=503,
            detail="Real-time data service not available"
        )
    
    try:
        regime = await realtime_service.get_market_regime(index_symbol)
        
        return {
            "index": index_symbol,
            "regime": regime
        }
        
    except Exception as e:
        logger.error(f"Error detecting regime for {index_symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts")
async def create_alert(alert: AlertRequest, request: Request):
    """
    Create a price alert.
    
    Args:
        alert: Alert configuration
        
    Returns:
        Alert ID
    """
    realtime_service = request.app.state.realtime_service
    
    if not realtime_service:
        raise HTTPException(
            status_code=503,
            detail="Real-time data service not available"
        )
    
    try:
        alert_id = await realtime_service.create_price_alert(
            user_id=alert.user_id,
            symbol=alert.symbol,
            threshold_type=alert.threshold_type,
            threshold_value=alert.threshold_value
        )
        
        return {
            "alert_id": alert_id,
            "message": "Alert created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, request: Request):
    """
    Delete a price alert.
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        Success status
    """
    realtime_service = request.app.state.realtime_service
    
    if not realtime_service:
        raise HTTPException(
            status_code=503,
            detail="Real-time data service not available"
        )
    
    try:
        success = await realtime_service.remove_price_alert(alert_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Alert not found: {alert_id}"
            )
        
        return {
            "message": "Alert deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/user/{user_id}")
async def get_user_alerts(user_id: str, request: Request):
    """
    Get all alerts for a user.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of user's alerts
    """
    realtime_service = request.app.state.realtime_service
    
    if not realtime_service:
        raise HTTPException(
            status_code=503,
            detail="Real-time data service not available"
        )
    
    try:
        alerts = await realtime_service.get_user_alerts(user_id)
        
        return {
            "user_id": user_id,
            "alerts": [
                {
                    "alert_id": alert.alert_id,
                    "symbol": alert.symbol,
                    "threshold_type": alert.threshold_type,
                    "threshold_value": alert.threshold_value,
                    "triggered": alert.triggered,
                    "created_at": alert.created_at
                }
                for alert in alerts
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching alerts for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
