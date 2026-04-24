"""
Tavily Service
Provides real-time web search and data retrieval for financial information.

Tavily is a search API optimized for LLMs and RAG systems, providing:
- Real-time web search
- Stock market data
- Financial news
- Company information
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import httpx
import json


class TavilyService:
    """
    Service for web data retrieval using Tavily API.

    Provides methods to:
    - Search for financial information
    - Get real-time stock data
    - Fetch company news and analysis

    Falls back to None when Tavily unavailable.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 1800  # 30 minutes cache

    async def is_available(self) -> bool:
        """Check if Tavily API is available."""
        return bool(self.api_key)

    async def search(self, query: str, max_results: int = 5, search_depth: str = "basic") -> List[Dict[str, Any]]:
        """
        Search for information using Tavily.

        Args:
            query: Search query
            max_results: Maximum number of results
            search_depth: "basic" or "advanced"

        Returns:
            List of search results with content
        """
        # Check cache first using redis-backed cache manager.
        cache_key = f"tavily:{query}:{search_depth}"
        from app.core.cache import cache_manager

        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            logger.debug(f"Tavily cache hit for: {query}")
            return cached_data

        if not self.api_key:
            logger.info("Tavily API key not configured")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": search_depth,
                        "include_answer": True,
                        "include_raw_content": False
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_search_results(data)

                    # Cache results via Redis
                    await cache_manager.set(cache_key, results, ttl=self._cache_ttl_seconds)

                    logger.info(f"Tavily search returned {len(results)} results")
                    return results
                else:
                    logger.warning(f"Tavily search failed: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []

    async def get_stock_info(self, symbol: str, company_name: str = None) -> Dict[str, Any]:
        """
        Get stock information using Tavily search.

        Args:
            symbol: Stock ticker symbol
            company_name: Company name for better search

        Returns:
            Stock information dictionary
        """
        query = f"{company_name or symbol} stock price current market data"
        results = await self.search(query, max_results=3, search_depth="advanced")

        if not results:
            return {"error": "No stock data found"}

        # Combine relevant information from multiple sources
        stock_info = {
            "symbol": symbol,
            "company": company_name,
            "sources": results,
            "summary": results[0].get("content", "") if results else ""
        }

        return stock_info

    async def get_financial_news(self, topic: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Get financial news articles on a specific topic.

        Args:
            topic: News topic (e.g., "Tesla earnings", "Indian stock market")
            max_results: Maximum number of articles

        Returns:
            List of news articles
        """
        query = f"{topic} financial news latest"
        return await self.search(query, max_results=max_results, search_depth="advanced")

    async def get_historical_data(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for historical financial data and analysis.

        Args:
            query: Historical query (e.g., "worst stock crashes in history")

        Returns:
            List of historical data results
        """
        return await self.search(query, max_results=5, search_depth="advanced")

    def _parse_search_results(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Tavily search response."""
        results = []

        # Extract the answer if available
        answer = raw_data.get("answer")
        if answer:
            results.append({
                "title": "AI-Generated Summary",
                "url": "",
                "content": answer,
                "source": "Tavily AI"
            })

        # Extract organic results
        for item in raw_data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score", 0),
                "source": "Tavily Search"
            })

        return results


# Singleton instance
_tavily_service: Optional[TavilyService] = None


def get_tavily_service(api_key: str = None) -> Optional[TavilyService]:
    """Get or create Tavily service instance."""
    global _tavily_service

    if api_key and _tavily_service is None:
        _tavily_service = TavilyService(api_key)

    return _tavily_service
