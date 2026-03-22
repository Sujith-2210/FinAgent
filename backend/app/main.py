"""
FinAgent FastAPI Application Entry Point
Main application with CORS, WebSocket, and route registration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("⚠️ prometheus_client not installed — /metrics endpoint disabled")

from app.config import get_settings
from app.api.routes import chat, context, dashboard, agents, alerts, feedback, realtime, auth
from app.api.websocket import router as ws_router
from app.mcp.client import MCPClientManager
from app.db.database import init_db
from app.services.realtime_data import get_realtime_service
from app.middleware.rate_limit import RateLimitMiddleware # NEW
from app.core.cache import cache_manager


# Prometheus metrics (only if available)
if PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter('finagent_requests_total', 'Total request count', ['method', 'endpoint', 'status'])
    REQUEST_LATENCY = Histogram('finagent_request_duration_seconds', 'Request latency', ['method', 'endpoint'])

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("🚀 Starting FinAgent Backend...")
    
    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize Redis cache manager used by rate-limiting and caching.
    await cache_manager.connect()
    if cache_manager.is_healthy:
        logger.info("✅ Cache manager connected")
    else:
        logger.warning("⚠️ Cache manager unavailable - rate limiting will fail open")
    
    # Initialize MCP client manager
    mcp_manager = MCPClientManager()
    app.state.mcp_manager = mcp_manager
    logger.info("✅ MCP Client Manager initialized")
    
    # Initialize Real-Time Data Service
    try:
        realtime_service = await get_realtime_service()
        app.state.realtime_service = realtime_service
        logger.info("✅ Real-Time Data Service initialized")
    except Exception as e:
        logger.warning(f"⚠️ Real-Time Data Service initialization failed (Redis may not be running): {e}")
        app.state.realtime_service = None
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down FinAgent Backend...")
    if hasattr(app.state, 'mcp_manager'):
        await app.state.mcp_manager.close()
    if hasattr(app.state, 'realtime_service') and app.state.realtime_service:
        await app.state.realtime_service.disconnect()
    await cache_manager.disconnect()


from fastapi.staticfiles import StaticFiles
import os

# Create FastAPI application
app = FastAPI(
    title="FinAgent API",
    description="Privacy-preserving multi-agent financial intelligence system",
    version="1.0.0",
    lifespan=lifespan
)

# Ensure workspace directory exists
os.makedirs("workspace", exist_ok=True)

# Mount static files for generated artifacts (charts, PDFs)
app.mount("/files", StaticFiles(directory="workspace"), name="files")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Rate Limiting
app.add_middleware(RateLimitMiddleware)


# Include API routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(context.router, prefix="/api/context", tags=["Context"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(realtime.router, prefix="/api/realtime", tags=["Real-Time Data"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# Include WebSocket router
app.include_router(ws_router, tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FinAgent API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "database": "up",
            "mcp_client": "initialized"
        }
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    if PROMETHEUS_AVAILABLE:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    return {"status": "metrics not available", "reason": "prometheus_client not installed"}
