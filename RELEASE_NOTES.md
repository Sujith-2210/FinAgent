# Release Notes

## FinAgent - MCP Personalization Integration Release

This release finalizes the project direction: context-aware, agentic AI for personalized finance using MCP.

## Highlights

- Added optional integration framework for:
  - AI4Finance repositories (FinGPT, FinRAG, FinRobot, FinRL)
  - Community `finance-agent` repository
- Added integration status API:
  - `GET /api/integrations/ai4finance`
- Added personalized research API:
  - `POST /api/integrations/personalized-research`

## Personalization & Agentic Improvements

- Introduced MCP-aware research adapter:
  - `backend/app/services/finance_research_adapter.py`
- Wired personalized research brief into chat and knowledge workflows:
  - chat metrics include external research metadata
  - knowledge agent consumes personalized focus derived from MCP context
- Added sentiment-driven alerting flow:
  - manual endpoint: `POST /api/alerts/sentiment-check`
  - automatic chat-triggered sentiment checks

## Frontend UX Improvements

- Chat timeline now surfaces:
  - sentiment check events
  - context-aware research brief events
- Chat message cards display sentiment signal badges
- Alerts page shows AI4Finance source tag for AI-generated alerts

## Reliability & DevEx

- Hardened CI behavior and aligned env variable usage
- Added root `pytest.ini` to scope collection and avoid unrelated suites
- Added bootstrap script for integrations:
  - `scripts/bootstrap_ai4finance.sh`
- Added smoke tests for personalization adapter:
  - `backend/app/tests/test_finance_research_adapter.py`

## Important Notes

- Integrations are optional and fail-safe; core project works without cloning external repos
- Knowledge and personalization logic uses MCP context bands/goals to preserve privacy-aware behavior
- Some heavyweight backend suites may still depend on local package versions/tools
