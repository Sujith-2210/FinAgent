# FinAgent — Context-Aware Agentic AI for Personalized Finance using MCP

**A multi-agent AI financial advisor that leverages MCP (Model Context Protocol) to deliver personalized, data-driven financial insights while preserving user privacy.**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)
![MCP](https://img.shields.io/badge/MCP-Fi%20Money-blueviolet.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🎯 Overview

FinAgent connects to your financial data via the **Fi Money MCP Server** and uses a **multi-agent architecture** to provide truly personalized financial advice. Instead of generic responses, every recommendation is grounded in your actual financial data — net worth, credit score, income, expenses, asset allocation, and liabilities.

### Key Highlights
- 🏦 **MCP-Powered Data Pipeline** — Connects to Fi Money MCP for real financial data (net worth, credit report, transactions, user profile)
- 🤖 **6 Specialized AI Agents** — Each agent handles a specific domain (finance, knowledge, explainability, alerts, code, orchestration)
- 🔒 **Privacy-First Architecture** — Raw data stays internal; frontend displays only masked bands (LOW/MEDIUM/HIGH)
- 📊 **Real-Time Stock Analysis** — Alpha Vantage API integration with LSTM/Linear Regression predictions and chart generation
- 🎤 **Voice Interface** — Web Speech API for hands-free interaction
- 🌐 **Multi-language Support** — English, Hindi, Tamil, Telugu, Marathi

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                   │
│  Chat UI │ Dashboard │ Context │ Settings │ Agents │ Alerts      │
└───────────────────────────────┬──────────────────────────────────┘
                                │ REST API + WebSocket
┌───────────────────────────────▼──────────────────────────────────┐
│                     FastAPI Backend                               │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                   Orchestrator Agent                          │ │
│  │  • Intent Classification (PLANNING/KNOWLEDGE/ANALYSIS/ALERT) │ │
│  │  • Entity Extraction (amounts, stocks, goals)                │ │
│  │  • Agent Routing & Coordination                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│         ▼              ▼              ▼              ▼           │
│  ┌───────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Finance   │ │ Knowledge   │ │  Code    │ │ Explainability │  │
│  │ Reasoning │ │ Agent       │ │  Agent   │ │ Agent          │  │
│  │           │ │             │ │          │ │                │  │
│  │• Savings  │ │• Firecrawl  │ │• LSTM    │ │• LLM Prompts   │  │
│  │• DTI      │ │• Alpha      │ │• Prophet │ │• Financial     │  │
│  │• House    │ │  Vantage    │ │• Charts  │ │  Snapshot      │  │
│  │• Tax      │ │• Web Search │ │• Code    │ │• Personalized  │  │
│  │• Retire   │ │• RAG        │ │  Sandbox │ │  Advice        │  │
│  └───────────┘ └─────────────┘ └──────────┘ └────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    Privacy Layer                              │ │
│  │  • Differential Privacy (ε=0.5)  • Access Control per Agent  │ │
│  │  • Value Masking (₹→Bands)       • Audit Logging             │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                          ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │               MCP Context Manager                             │ │
│  │  fetch_net_worth() │ fetch_credit_report()                    │ │
│  │  fetch_transactions() │ fetch_user_profile()                  │ │
│  └──────────────────────────────┬───────────────────────────────┘ │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────┐
│                    Fi Money MCP Server (Go)                       │
│         fi-mcp-dev — Test data for development                   │
│  Net Worth │ Credit Report │ Transactions │ User Profile          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Details

| Agent | Role | Data Sources |
|-------|------|-------------|
| **Orchestrator** | Routes queries, extracts entities (amounts, stocks, goals), classifies intent | User query |
| **Finance Reasoning** | Savings rate, DTI, house affordability, tax optimization, Monte Carlo, portfolio rebalancing | MCP: income, expenses, net worth, credit score, assets, liabilities |
| **Code** | LSTM/Prophet stock predictions, chart generation, code sandbox execution | Yahoo Finance, Alpha Vantage |
| **Knowledge** | External facts via Firecrawl, real-time stock data, RAG knowledge base | Firecrawl MCP, Alpha Vantage API, GraphRAG |
| **Explainability** | Generates personalized LLM responses with full financial snapshot context | All agent outputs + MCP financial data |
| **Alert** | Proactive notifications for spending spikes, market movements, goal progress | Transaction patterns, market data |

---

## 📁 Project Structure

```
FinAgent/
├── backend/                     # FastAPI Backend
│   ├── app/
│   │   ├── agents/             # 6 specialized agents
│   │   │   ├── coordinator.py  # Agent orchestration
│   │   │   ├── finance.py      # Financial calculations
│   │   │   ├── explainability.py # LLM response generation
│   │   │   └── ...
│   │   ├── api/routes/         # REST API endpoints
│   │   ├── auth/               # JWT authentication
│   │   ├── mcp/                # MCP client & context manager
│   │   │   ├── fi_mcp.py       # Fi Money MCP service
│   │   │   └── context_manager.py
│   │   ├── privacy/            # Privacy layer & masking
│   │   ├── services/           # User context, RAG, real-time data
│   │   └── llm/                # LLM controller (Gemini/MLX/OpenRouter)
│   └── requirements.txt
│
├── frontend/                    # React + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── pages/              # 8 pages (Chat, Dashboard, Context, Settings, ...)
│   │   ├── components/         # Reusable UI components
│   │   └── context/            # Auth & I18n contexts
│   └── package.json
│
├── fi-mcp-dev/                  # Fi MCP Server (Go) — test financial data
│
├── .github/workflows/           # CI/CD pipeline
│   └── ci.yml
│
└── .env                         # Environment configuration (not committed)
```

---

## 🛠 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Redis** (for caching & rate limiting)
- **Go 1.21+** (optional, for fi-mcp-dev server)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/Sujith-2210/FinAgent.git
cd FinAgent

# Backend
cd backend
python -m venv venv
source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API keys (GOOGLE_API_KEY, ALPHA_VANTAGE_KEY, etc.)
```

### 2. Start Services

```bash
# Terminal 1: Start Redis
redis-server &

# Terminal 2: Start Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 3: Start Frontend
cd frontend
npm install
npm run dev

# Terminal 4 (Optional): Start Fi MCP Server
cd fi-mcp-dev
go run main.go
```

### 3. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## 🔗 API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check with component status |
| `/api/auth/register` | POST | No | User registration |
| `/api/auth/login` | POST | No | JWT token login |
| `/api/chat/` | POST | Yes | AI advisor chat (multi-agent) |
| `/api/dashboard/` | GET | Yes | Financial dashboard overview |
| `/api/dashboard/net-worth` | GET | Yes | Net worth breakdown |
| `/api/dashboard/trends` | GET | Yes | Financial trends analysis |
| `/api/context/` | GET | Yes | Full MCP context layers |
| `/api/context/sync` | POST | Yes | Trigger fresh MCP data sync |
| `/api/context/fi-money` | GET | Yes | Fi MCP data summary |
| `/api/agents/status` | GET | Yes | Agent operational status |
| `/api/alerts/` | GET | Yes | Active financial alerts |
| `/api/realtime/` | GET | Yes | Real-time market data |

---

## 🔒 Privacy Architecture

FinAgent uses a **dual-layer privacy approach**:

| Layer | What it Does | Example |
|-------|-------------|---------|
| **Frontend Display** | Shows only privacy-masked bands | Net Worth: `MEDIUM`, Credit Score: `EXCELLENT` |
| **Backend Agents** | Use actual raw values for personalized calculations | Income: ₹75,000, DTI: 7.1%, Savings Rate: 66.7% |

This ensures the **user sees privacy-preserving labels** while **agents compute precise recommendations** using real data from the MCP server.

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
# LLM Configuration
LLM_PROVIDER=gemini                      # gemini, openrouter, or mlx
GOOGLE_API_KEY=your_gemini_api_key

# External APIs
ALPHA_VANTAGE_API_KEY=your_av_key
TAVILY_API_KEY=your_tavily_key

# MCP Server
FI_MCP_URL=http://localhost:8080/mcp/stream
FI_MCP_PHONE=2222222222

# Security
JWT_SECRET_KEY=your_secret_key

# Redis
REDIS_URL=redis://localhost:6379
```

---

## 📊 Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, SQLAlchemy (async), Pydantic, Redis, JWT Auth |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **LLM** | Google Gemini API, OpenRouter (free models), MLX (local) |
| **MCP** | Fi Money MCP Server (Go), Model Context Protocol |
| **Data** | Alpha Vantage, Yahoo Finance, Firecrawl, Tavily |
| **Testing** | Pytest, Hypothesis (property-based testing) |
| **CI/CD** | GitHub Actions (lint, test, build) |
| **Monitoring** | Prometheus, Grafana |

---

## 🌐 Internationalization

| Language | Code |
|----------|------|
| 🇺🇸 English | `en` |
| 🇮🇳 Hindi | `hi` |
| 🇮🇳 Tamil | `ta` |
| 🇮🇳 Telugu | `te` |
| 🇮🇳 Marathi | `mr` |

---

## 📝 License

MIT License

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and ensure CI checks pass before submitting a PR.

---

**Built with ❤️ as a Final Year Project — Context-Aware Agentic AI for Personalized Finance using MCP**
