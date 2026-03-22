"""
Firecrawl MCP Service
Provides real-time web data retrieval for external knowledge.

Uses the Firecrawl MCP server for:
- Tax regulations and updates
- Financial news and market data  
- Government scheme information
- RBI/SEBI guidelines

The Firecrawl MCP provides these tools:
- firecrawl_search: Search the web for information
- firecrawl_scrape: Scrape content from a URL
- firecrawl_extract: Extract structured data
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import httpx
import json

from app.config import get_settings


class FirecrawlService:
    """
    Service for web data retrieval using Firecrawl MCP.
    
    Provides methods to:
    - Search for financial regulations
    - Scrape specific URLs for content
    - Get real-time market/policy updates
    
    Falls back to built-in knowledge base when Firecrawl unavailable.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.firecrawl_api_key
        self.base_url = "https://api.firecrawl.dev/v0"  # Firecrawl API
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 3600  # 1 hour cache
    
    async def is_available(self) -> bool:
        """Check if Firecrawl API is available."""
        return bool(self.api_key)
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for information using Firecrawl.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results with content
        """
        # Check cache first
        cache_key = f"search:{query}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            cache_age = (datetime.utcnow() - cached["cached_at"]).total_seconds()
            if cache_age < self._cache_ttl_seconds:
                logger.debug(f"Cache hit for: {query}")
                return cached["results"]
        
        if not self.api_key:
            logger.info("Firecrawl API key not configured, using fallback")
            return self._get_fallback_results(query)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "query": query,
                        "limit": max_results,
                        "scrapeOptions": {"formats": ["markdown"]}
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_search_results(data)
                    
                    # Cache results
                    self._cache[cache_key] = {
                        "results": results,
                        "cached_at": datetime.utcnow()
                    }
                    
                    logger.info(f"Firecrawl search returned {len(results)} results")
                    return results
                else:
                    logger.warning(f"Firecrawl search failed: {response.status_code}")
                    return self._get_fallback_results(query)
                    
        except Exception as e:
            logger.error(f"Firecrawl search error: {e}")
            return self._get_fallback_results(query)
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a specific URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraped content with metadata
        """
        if not self.api_key:
            return {"error": "Firecrawl not configured", "content": None}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/scrape",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "url": url,
                        "formats": ["markdown"]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "url": url,
                        "title": data.get("data", {}).get("metadata", {}).get("title", ""),
                        "content": data.get("data", {}).get("markdown", ""),
                        "source": "Firecrawl MCP"
                    }
                else:
                    return {"error": f"Scrape failed: {response.status_code}", "content": None}
                    
        except Exception as e:
            logger.error(f"Firecrawl scrape error: {e}")
            return {"error": str(e), "content": None}
    
    def _parse_search_results(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Firecrawl search response."""
        results = []
        
        data = raw_data.get("data", raw_data.get("web", []))
        if isinstance(data, list):
            for item in data:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("markdown", item.get("description", "")),
                    "source": "Firecrawl MCP"
                })
        
        return results
    
    def _get_fallback_results(self, query: str) -> List[Dict[str, Any]]:
        """
        Get fallback results from built-in knowledge base.
        Used when Firecrawl API is unavailable.
        """
        query_lower = query.lower()
        results = []
        
        # Built-in knowledge base for common Indian financial queries
        knowledge_base = {
            "tax": [
                {
                    "title": "Income Tax Section 80C Deductions",
                    "content": "Section 80C allows deductions up to ₹1.5 lakh per year for investments in PPF, ELSS, NSC, life insurance premiums, and more. Lock-in periods vary by instrument.",
                    "url": "https://incometax.gov.in",
                    "source": "Income Tax Department"
                },
                {
                    "title": "NPS Tax Benefits (Section 80CCD)",
                    "content": "NPS offers additional ₹50,000 deduction under 80CCD(1B), over and above the ₹1.5 lakh limit of 80C. Total tax benefit can be up to ₹2 lakh.",
                    "url": "https://npscra.nsdl.co.in",
                    "source": "PFRDA"
                }
            ],
            "mutual fund": [
                {
                    "title": "Mutual Fund Taxation Rules 2024",
                    "content": "SEBI regulates all mutual funds in India. From July 2024: LTCG (held >24 months) taxed at 12.5%. Short-term gains taxed per income slab. ELSS funds offer tax benefits with 3-year lock-in.",
                    "url": "https://sebi.gov.in",
                    "source": "SEBI"
                }
            ],
            "epf": [
                {
                    "title": "EPF Contribution and Withdrawal Rules",
                    "content": "Employee contributes 12% of basic salary. Employer matches 12% (3.67% EPF + 8.33% EPS). Interest rate ~8.15%. Full withdrawal after 2 months unemployment or age 58.",
                    "url": "https://epfindia.gov.in",
                    "source": "EPFO"
                }
            ],
            "credit": [
                {
                    "title": "Credit Score Guidelines India",
                    "content": "Credit scores range 300-900. Above 750 is excellent. Key factors: payment history (35%), credit utilization (30%), credit age (15%). RBI mandates free annual credit report.",
                    "url": "https://rbi.org.in",
                    "source": "RBI"
                }
            ],
            "retirement": [
                {
                    "title": "National Pension System (NPS)",
                    "content": "NPS offers market-linked returns with flexible asset allocation. Tax benefits under 80CCD. Partial withdrawal allowed after 3 years for specific purposes.",
                    "url": "https://npscra.nsdl.co.in",
                    "source": "PFRDA"
                }
            ],
            "stock": [
                {
                    "title": "Top 5 Stocks to Buy - January 2026 (Demo Data)",
                    "content": "Based on today's market analysis, here are top 5 stocks to consider: 1. Reliance Industries (₹2,850 - Strong diversified portfolio), 2. HDFC Bank (₹1,650 - Leading private sector bank), 3. Infosys (₹1,780 - IT sector leader), 4. TCS (₹3,950 - Consistent performer), 5. ICICI Bank (₹1,100 - Growing retail book). Note: This is demo data for demonstration purposes. Always consult a SEBI-registered advisor before investing.",
                    "url": "https://www.nseindia.com",
                    "source": "NSE India (Demo)"
                },
                {
                    "title": "Nifty 50 Market Overview",
                    "content": "Nifty 50 is trading at 22,500 levels. Key sectors performing well: Banking, IT, and FMCG. Market sentiment is cautiously optimistic. FII inflows have been positive this week.",
                    "url": "https://www.nseindia.com",
                    "source": "NSE India (Demo)"
                }
            ],
            "market": [
                {
                    "title": "Indian Stock Market Overview - January 2026",
                    "content": "Sensex is at 74,000 levels. Nifty 50 at 22,500. Banking sector leads gains. IT stocks showing momentum. Key events to watch: RBI policy, quarterly results season.",
                    "url": "https://www.bseindia.com",
                    "source": "BSE India (Demo)"
                }
            ]
        }
        
        # Search through knowledge base
        for category, items in knowledge_base.items():
            if category in query_lower:
                results.extend(items)
        
        # If no match, return generic financial info
        if not results:
            for _, items in knowledge_base.items():
                results.extend(items[:1])
        
        return results[:5]


# Singleton instance
_firecrawl_service: Optional[FirecrawlService] = None


def get_firecrawl_service() -> FirecrawlService:
    """Get or create Firecrawl service instance."""
    global _firecrawl_service
    if _firecrawl_service is None:
        _firecrawl_service = FirecrawlService()
    return _firecrawl_service
