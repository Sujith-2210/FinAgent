# FinAgent Backend

Privacy-preserving multi-agent financial intelligence system backend.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run the server
uvicorn app.main:app --reload --port 8000
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Configuration settings
│   ├── api/                 # API routes
│   ├── mcp/                 # MCP client integration
│   ├── agents/              # Multi-agent system
│   ├── llm/                 # Local LLM controller
│   ├── privacy/             # Privacy masking
│   ├── models/              # Pydantic schemas
│   └── db/                  # Database layer
├── tests/
├── requirements.txt
└── .env.example
```

## API Endpoints

- `POST /api/chat` - Send chat message
- `GET /api/context` - Get MCP context
- `GET /api/dashboard` - Get dashboard data
- `GET /api/agents/status` - Get agent status
- `GET /api/alerts` - Get active alerts
- `WebSocket /ws/chat` - Real-time chat
