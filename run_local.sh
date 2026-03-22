#!/bin/bash

# Configuration
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend
export FI_MCP_SERVER_URL="http://localhost:8080/mcp/sse"
export REDIS_URL="redis://localhost:6379"

# Helper function for cleanup
cleanup() {
    echo "Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Trap cleanup signals
trap cleanup SIGINT SIGTERM

# Check for port conflicts
check_port() {
    local port=$1
    local name=$2
    if lsof -i :$port -t >/dev/null; then
        echo "⚠️  Port $port ($name) is already in use."
        pid=$(lsof -i :$port -t)
        echo "   Process PID: $pid"
        echo "   Please stop this process or run: kill $pid"
        exit 1
    fi
}

echo "🚀 Starting FinAgent Local Environment..."

# Check ports
check_port 8000 "Backend"
check_port 8080 "MCP Server"

# 1. Start Redis (assuming it's installed and running, or start if needed)
# For local dev, we often expect redis-server to be running.
# If you want to force start it:
# redis-server &

# 2. Start Fi MCP Server (Go)
echo "📦 Starting Fi MCP Server (Port 8080)..."
if ! command -v go &> /dev/null; then
    echo "❌ Error: Go is not installed or not in PATH."
    echo "   Please install Go (https://go.dev/dl/) to run the MCP server."
    echo "   The backend will start but won't be able to connect to the MCP server."
else
    cd fi-mcp-dev
    go run main.go &
    MCP_PID=$!
    cd ..
fi

# Wait for MCP to be ready
echo "Waiting for MCP server..."
sleep 5

# 3. Start Backend (Python/FastAPI)
echo "🐍 Starting Backend Server (Port 8000)..."
cd backend
# Use the virtual environment python if available
if [ -d "venv" ]; then
    venv/bin/uvicorn app.main:app --reload --port 8000
else
    uvicorn app.main:app --reload --port 8000
fi

# Keep script running
wait
