"""
Trading Analysis Service
Integrates the TradingAgents multi-agent framework into FinAgent.

This service wraps TradingAgents' LangGraph-based pipeline:
  Analysts (market/social/news/fundamentals)
  → Bull/Bear Debate
  → Research Manager
  → Trader Decision
  → Risk Analysis (aggressive/conservative/neutral debate)
  → Final Recommendation

Uses free OpenRouter models for all LLM operations.
"""

import os
import sys
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.config import get_settings


class TradingAnalysisService:
    """
    Wraps TradingAgents framework for stock analysis within FinAgent.

    Provides:
    - Multi-analyst stock research (fundamentals, market, news, social media)
    - Structured bull/bear debate
    - Trader decision synthesis
    - Risk management assessment
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.settings = get_settings()
        self._config = config or self._build_default_config()
        self._graph = None
        self._available = False
        self._init_attempted = False

    def _build_default_config(self) -> Dict[str, Any]:
        """Build TradingAgents config using FinAgent's settings (OpenRouter free models)."""
        return {
            "llm_provider": self.settings.trading_agents_llm_provider,
            "deep_think_llm": self.settings.trading_agents_deep_think_llm,
            "quick_think_llm": self.settings.trading_agents_quick_think_llm,
            "backend_url": "https://openrouter.ai/api/v1",
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
            "max_recur_limit": 100,
            "data_vendors": {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
            },
            "tool_vendors": {},
        }

    def _ensure_env(self):
        """Ensure OpenRouter API key is set in environment for TradingAgents."""
        if self.settings.openrouter_api_key:
            os.environ["OPENROUTER_API_KEY"] = self.settings.openrouter_api_key
        if self.settings.alpha_vantage_api_key:
            os.environ["ALPHA_VANTAGE_API_KEY"] = self.settings.alpha_vantage_api_key

    async def initialize(self) -> bool:
        """Initialize the TradingAgents graph. Returns True if successful."""
        if self._init_attempted:
            return self._available

        self._init_attempted = True
        self._ensure_env()

        try:
            # Add TradingAgents to Python path
            trading_agents_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "TradingAgents"
            )
            if trading_agents_path not in sys.path:
                sys.path.insert(0, trading_agents_path)

            from tradingagents.graph.trading_graph import TradingAgentsGraph

            self._graph = TradingAgentsGraph(config=self._config)
            self._available = True
            logger.info("✅ TradingAgents graph initialized (using OpenRouter free models)")
            return True

        except ImportError as e:
            logger.warning(f"TradingAgents not available (missing dependency): {e}")
            self._available = False
            return False
        except Exception as e:
            logger.error(f"TradingAgents initialization failed: {e}")
            self._available = False
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    async def analyze_stock(
        self,
        ticker: str,
        analysis_date: Optional[str] = None,
        selected_analysts: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run the full TradingAgents pipeline for a stock.

        Pipeline: Analysts → Bull/Bear Debate → Trader → Risk Assessment

        Args:
            ticker: Stock ticker symbol (e.g., "TCS", "AAPL", "RELIANCE")
            analysis_date: Date for analysis (default: today)
            selected_analysts: Analyst types to include (default: all 4)

        Returns:
            Dict with analyst reports, debate summary, trader decision, risk assessment
        """
        if not self._available:
            success = await self.initialize()
            if not success:
                return self._fallback_response(ticker, "TradingAgents not available")

        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        if selected_analysts is None:
            selected_analysts = ["market", "social", "news", "fundamentals"]

        try:
            logger.info(f"🔍 Running TradingAgents analysis for {ticker} on {analysis_date}")
            logger.info(f"   Analysts: {selected_analysts}")
            logger.info(f"   Models: quick={self._config['quick_think_llm']}, deep={self._config['deep_think_llm']}")

            # Run the graph in a thread pool to avoid blocking the event loop
            def _run_graph():
                return self._graph.propagate(
                    company=ticker,
                    curr_date=analysis_date,
                    selected_analysts=selected_analysts
                )

            state, decision = await asyncio.to_thread(_run_graph)

            # Format results
            result = self._format_results(state, decision, ticker, analysis_date)
            logger.info(f"✅ TradingAgents analysis complete for {ticker}: {decision.get('action', 'N/A')}")
            return result

        except Exception as e:
            logger.error(f"TradingAgents analysis failed for {ticker}: {e}")
            return self._fallback_response(ticker, str(e))

    def _format_results(
        self,
        state: Dict[str, Any],
        decision: Dict[str, Any],
        ticker: str,
        analysis_date: str
    ) -> Dict[str, Any]:
        """Format TradingAgents graph state into a structured result."""
        return {
            "source": "trading_agents",
            "ticker": ticker,
            "analysis_date": analysis_date,
            "success": True,

            # Analyst Reports
            "analyst_reports": {
                "market_report": state.get("market_report", ""),
                "sentiment_report": state.get("sentiment_report", ""),
                "news_report": state.get("news_report", ""),
                "fundamentals_report": state.get("fundamentals_report", ""),
            },

            # Debate Summary
            "debate": {
                "bull_arguments": state.get("investment_debate_state", {}).get("bull_history", ""),
                "bear_arguments": state.get("investment_debate_state", {}).get("bear_history", ""),
                "debate_rounds": state.get("investment_debate_state", {}).get("count", 0),
            },

            # Trader Decision
            "trader_decision": decision,

            # Risk Assessment
            "risk_assessment": {
                "risk_debate_state": state.get("risk_debate_state", {}),
            },

            # Final recommendation
            "recommendation": decision.get("action", "HOLD"),
            "confidence": decision.get("confidence", "MEDIUM"),
            "reasoning": decision.get("reasoning", "Analysis complete"),
        }

    def _fallback_response(self, ticker: str, error: str) -> Dict[str, Any]:
        """Return a graceful fallback when TradingAgents isn't available."""
        return {
            "source": "trading_agents_fallback",
            "ticker": ticker,
            "success": False,
            "error": error,
            "analyst_reports": {},
            "debate": {},
            "trader_decision": {},
            "risk_assessment": {},
            "recommendation": "UNABLE_TO_ANALYZE",
            "confidence": "LOW",
            "reasoning": f"TradingAgents analysis unavailable: {error}. "
                        f"Use FinAgent's knowledge agent for stock research instead.",
        }


# Module-level lazy singleton
_trading_service: Optional[TradingAnalysisService] = None


def get_trading_analysis_service() -> TradingAnalysisService:
    """Get or create the TradingAnalysisService singleton."""
    global _trading_service
    if _trading_service is None:
        _trading_service = TradingAnalysisService()
    return _trading_service
