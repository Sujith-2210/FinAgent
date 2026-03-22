#!/bin/bash
# Quick restart script for FinAgent backend

cd /Users/sujith/Documents/FinAgent/New/backend

echo "🚀 Starting FinAgent Backend with Improvements..."
echo ""
echo "Looking for:"
echo "  ✓ Tavily service initialization"
echo "  ✓ Entity extraction features"
echo "  ✓ Enhanced finance calculations"
echo ""

source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
