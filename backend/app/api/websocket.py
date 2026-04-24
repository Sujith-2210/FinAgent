"""
WebSocket Handler for Real-time Chat and Market Data
Provides streaming responses, live agent activity updates, and real-time market data.
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from typing import Dict, List, Optional
import json
from datetime import datetime
import jwt
from loguru import logger
from app.api.routes.chat import get_coordinator
from app.auth.security import decode_access_token

router = APIRouter()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


class WebSocketManager:
    """
    Manages WebSocket connections for real-time bidirectional communication.

    Features:
    - Connect/disconnect management
    - Personal and broadcast messaging
    - Message type routing (price updates, alerts, portfolio updates)
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_subscriptions: Dict[str, List[str]] = {}  # user_id -> [symbols]

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: Unique user identifier
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_subscriptions[user_id] = []
        logger.info(f"🔌 WebSocket connected: {user_id}")

    def disconnect(self, user_id: str):
        """
        Remove a connection.

        Args:
            user_id: User identifier
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_subscriptions:
            del self.user_subscriptions[user_id]
        logger.info(f"🔌 WebSocket disconnected: {user_id}")

    async def send_personal(self, user_id: str, message: dict):
        """
        Send message to specific user.

        Args:
            user_id: Target user ID
            message: JSON-serializable message
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, message: dict, user_ids: Optional[List[str]] = None):
        """
        Broadcast message to users.

        Args:
            message: JSON-serializable message
            user_ids: Target users (None = all connected users)
        """
        target_users = user_ids if user_ids else list(self.active_connections.keys())

        for user_id in target_users:
            await self.send_personal(user_id, message)

    def add_subscription(self, user_id: str, symbol: str):
        """Add stock symbol to user's subscriptions."""
        if user_id in self.user_subscriptions:
            if symbol not in self.user_subscriptions[user_id]:
                self.user_subscriptions[user_id].append(symbol)
                logger.info(f"📊 User {user_id} subscribed to {symbol}")

    def remove_subscription(self, user_id: str, symbol: str):
        """Remove stock symbol from user's subscriptions."""
        if user_id in self.user_subscriptions:
            if symbol in self.user_subscriptions[user_id]:
                self.user_subscriptions[user_id].remove(symbol)
                logger.info(f"📊 User {user_id} unsubscribed from {symbol}")

    def get_subscribers(self, symbol: str) -> List[str]:
        """Get list of users subscribed to a symbol."""
        subscribers = []
        for user_id, symbols in self.user_subscriptions.items():
            if symbol in symbols:
                subscribers.append(user_id)
        return subscribers


# Global WebSocket manager instance
manager = WebSocketManager()


def _resolve_user_id_from_ws_token(token: str | None) -> str | None:
    """Resolve authenticated user ID from a websocket token."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if isinstance(user_id, str) and user_id:
            return user_id
    except jwt.PyJWTError:
        return None
    except Exception:
        return None
    return None


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for real-time chat.

    Message types:
    - user_message: User sends a message
    - agent_update: Agent activity update (streaming)
    - response: Final AI response
    - error: Error message
    """
    user_id = _resolve_user_id_from_ws_token(token)
    if not user_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Unauthorized websocket access",
        )
        return

    internal_session_id = f"{user_id}:{session_id}"
    await manager.connect(websocket, internal_session_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.debug(f"Received: {message}")

            if message.get("type") == "user_message":
                user_text = message.get("content", "")
                if not user_text.strip():
                    await manager.send_personal(internal_session_id, {
                        "type": "error",
                        "message": "Message content cannot be empty."
                    })
                    continue

                # Send acknowledgment
                await manager.send_personal(internal_session_id, {
                    "type": "ack",
                    "message": "Processing your request..."
                })

                await manager.send_personal(internal_session_id, {
                    "type": "agent_update",
                    "agent": "orchestrator",
                    "status": "analyzing",
                    "message": "Analyzing your query..."
                })

                try:
                    mcp_manager = websocket.app.state.mcp_manager
                    coordinator = get_coordinator(internal_session_id, mcp_manager)
                    result = await coordinator.process_query(
                        query=user_text,
                        session_id=internal_session_id,
                    )

                    await manager.send_personal(internal_session_id, {
                        "type": "response",
                        "content": result.get("message", "I couldn't process your request."),
                        "session_id": session_id,
                        "agents_involved": result.get("agents_involved", []),
                        "agent_contributions": result.get("agent_contributions", []),
                        "metrics_used": result.get("metrics_used", {}),
                        "actions": result.get("actions", []),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"WebSocket orchestration error: {e}")
                    await manager.send_personal(internal_session_id, {
                        "type": "error",
                        "message": "I encountered an issue while processing your request."
                    })

            elif message.get("type") == "ping":
                await manager.send_personal(internal_session_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(internal_session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(internal_session_id)


@router.websocket("/ws/market/{user_id}")
async def websocket_market_data(
    websocket: WebSocket,
    user_id: str,
    token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for real-time market data updates.

    Client message types:
    - subscribe: Subscribe to stock updates {"type": "subscribe", "symbol": "HDFCBANK.NS"}
    - unsubscribe: Unsubscribe from stock {"type": "unsubscribe", "symbol": "HDFCBANK.NS"}
    - ping: Keep-alive ping

    Server message types:
    - PRICE_UPDATE: Real-time price update
    - ALERT: Price alert notification
    - PORTFOLIO_UPDATE: Portfolio value update
    - REGIME_CHANGE: Market regime change notification
    """
    token_user_id = _resolve_user_id_from_ws_token(token)
    if not token_user_id or token_user_id != user_id:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Unauthorized websocket access",
        )
        return

    await manager.connect(websocket, user_id)

    try:
        # Send welcome message
        await manager.send_personal(user_id, {
            "type": "connected",
            "message": "Connected to real-time market data stream",
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "subscribe":
                symbol = message.get("symbol")
                if symbol:
                    manager.add_subscription(user_id, symbol)
                    await manager.send_personal(user_id, {
                        "type": "subscribed",
                        "symbol": symbol,
                        "message": f"Subscribed to {symbol}"
                    })

            elif msg_type == "unsubscribe":
                symbol = message.get("symbol")
                if symbol:
                    manager.remove_subscription(user_id, symbol)
                    await manager.send_personal(user_id, {
                        "type": "unsubscribed",
                        "symbol": symbol,
                        "message": f"Unsubscribed from {symbol}"
                    })

            elif msg_type == "ping":
                await manager.send_personal(user_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket market data error: {e}")
        manager.disconnect(user_id)


@router.websocket("/ws/agents")
async def websocket_agents(websocket: WebSocket):
    """
    WebSocket endpoint for real-time agent activity monitoring.

    Broadcasts agent status changes and activity to all connected clients.
    """
    await websocket.accept()

    try:
        while True:
            # This endpoint is for broadcasting agent activity
            # Clients just listen, they don't send messages
            await websocket.receive_text()
            # Handle any client messages if needed
    except WebSocketDisconnect:
        pass


# Helper functions for broadcasting market data

async def broadcast_price_update(symbol: str, price_data: dict):
    """
    Broadcast price update to subscribed users.

    Args:
        symbol: Stock symbol
        price_data: Price data dictionary
    """
    message = {
        "type": "PRICE_UPDATE",
        "symbol": price_data["symbol"],
        "price": price_data["price"],
        "change": price_data["change"],
        "change_percent": price_data["change_percent"],
        "volume": price_data["volume"],
        "timestamp": price_data["timestamp"]
    }

    # Get users subscribed to this symbol
    subscribers = manager.get_subscribers(symbol)

    if subscribers:
        await manager.broadcast(message, user_ids=subscribers)
        logger.debug(f"📊 Broadcasted {symbol} update to {len(subscribers)} users")


async def broadcast_alert(user_id: str, alert_data: dict):
    """
    Send alert to specific user.

    Args:
        user_id: Target user ID
        alert_data: Alert data dictionary
    """
    message = {
        "type": "ALERT",
        "severity": alert_data.get("severity", "MEDIUM"),
        "title": alert_data.get("title", "Alert"),
        "message": alert_data.get("message", ""),
        "action_url": alert_data.get("action_url"),
        "timestamp": alert_data.get("timestamp")
    }

    await manager.send_personal(user_id, message)
    logger.info(f"🔔 Sent alert to {user_id}: {alert_data.get('title')}")


async def broadcast_portfolio_update(user_id: str, portfolio_data: dict):
    """
    Send portfolio update to specific user.

    Args:
        user_id: Target user ID
        portfolio_data: Portfolio data dictionary
    """
    message = {
        "type": "PORTFOLIO_UPDATE",
        "total_value": portfolio_data.get("total_value", 0),
        "change_today": portfolio_data.get("change_today", 0),
        "change_percent": portfolio_data.get("change_percent", 0),
        "timestamp": portfolio_data.get("timestamp")
    }

    await manager.send_personal(user_id, message)
    logger.debug(f"💼 Sent portfolio update to {user_id}")


async def broadcast_regime_change(regime: str, index_symbol: str = "^NSEI"):
    """
    Broadcast market regime change to all connected users.

    Args:
        regime: New market regime (BULL/BEAR/SIDEWAYS)
        index_symbol: Market index symbol
    """
    message = {
        "type": "REGIME_CHANGE",
        "regime": regime,
        "index": index_symbol,
        "message": f"Market regime changed to {regime}",
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast(message)
    logger.info(f"📈 Broadcasted regime change: {regime}")
