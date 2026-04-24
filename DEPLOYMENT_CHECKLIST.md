# FinAgent Deployment Checklist

This checklist is for deploying FinAgent as a context-aware, agentic AI for personalized finance using MCP.

## 1) Environment Readiness

- Python 3.11+ installed for backend
- Node.js 20+ installed for frontend
- Redis running and reachable by backend (`REDIS_URL`)
- Fi MCP dev server available (or production MCP endpoint configured)
- Optional external integrations cloned:
  - `external/ai4finance/*`
  - `external/community/finance-agent`

## 2) Configuration

- Backend env file prepared (`backend/.env`)
- Required vars set:
  - `JWT_SECRET_KEY`
  - `REDIS_URL`
  - `FI_MCP_URL`
- Optional vars set if used:
  - `TAVILY_API_KEY`
  - `ALPHA_VANTAGE_API_KEY`
  - LLM provider keys (`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, etc.)

## 3) Backend Verification

```bash
cd backend
PYTHONPATH=. python -m py_compile app/main.py
PYTHONPATH=. pytest app/tests/test_sandbox_service.py -q
PYTHONPATH=. pytest app/tests/test_finance_research_adapter.py -q
```

## 4) Frontend Verification

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```

## 5) Runtime Functional Checks

- Login works (`/api/auth/login`)
- Chat request works (`/api/chat/`)
- Context sync works (`/api/context/sync`)
- Alerts load (`/api/alerts/`)
- Integrations status loads (`/api/integrations/ai4finance`)
- Personalized research endpoint works (`/api/integrations/personalized-research`)

## 6) Personalized MCP Behavior Checks

- Ask a finance research query in chat
- Confirm timeline shows:
  - `Sentiment Checked` or `Sentiment Alert Generated`
  - `Context-Aware Research Brief`
- Confirm alerts page shows AI4Finance-tagged alerts for `ai4finance_*` triggers

## 7) Optional Container/K8s Path

- Validate `docker-compose.yml` dependencies (Redis/Neo4j etc.)
- Review `k8s/deployment.yaml` and replace placeholder secrets
- Deploy backend, then frontend, then run runtime checks above

## 8) Release Gate

Ship only when all are true:

- Frontend lint/build passes
- Backend smoke tests pass
- Auth/chat/context/alerts integrations are healthy
- MCP-personalized research and sentiment signal paths are visible in UI
