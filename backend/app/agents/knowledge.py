"""
Knowledge Agent
Retrieves external facts and regulations via Firecrawl MCP.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import httpx

from app.agents.base import BaseAgent
from app.config import get_settings


class KnowledgeAgent(BaseAgent):
    """
    Knowledge Agent - External fact retrieval.
    
    Responsibilities:
    - Retrieve relevant factual information from web/MCP
    - Summarize rules and regulations
    - Provide source-grounded insights
    
    Rules:
    - Use only MCP-provided documents
    - Do NOT infer personalized advice
    - Do NOT calculate financial outcomes
    - Clearly separate facts from interpretations
    """
    
    def __init__(self, firecrawl_service=None):
        super().__init__()
        self.name = "knowledge"
        self.description = "Retrieves external facts and regulations via Firecrawl MCP"
        self.read_layers = {"external_knowledge_context"}
        self.write_layers = {"external_knowledge_context"}
        self._firecrawl_service = firecrawl_service
        self._tavily_service = None  # Will be injected by coordinator
        self._rag_service = None

        
        self.system_prompt = """You are a Knowledge Agent.

Your task is to:
- Retrieve relevant factual information
- Summarize rules and regulations
- Provide source-grounded insights

Rules:
- Use only MCP-provided documents
- Do NOT infer personalized advice
- Do NOT calculate financial outcomes
- Clearly separate facts from interpretations
- Output must be structured JSON"""
        
        # Fallback knowledge base for common queries
        self._fallback_kb = self._initialize_fallback_kb()
    
    def set_firecrawl_service(self, service):
        """Set the Firecrawl service for web data retrieval."""
        self._firecrawl_service = service

    def set_rag_service(self, service):
        """Set the GraphRAG service."""
        self._rag_service = service
    
    def set_tavily_service(self, service):
        """Set the Tavily service for web search."""
        self._tavily_service = service
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_topic": {"type": "string"},
                "query": {"type": "string"},
                "source": {"type": "string"}
            },
            "required": ["query_topic"]
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "facts": {"type": "array", "items": {"type": "string"}},
                "source_type": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "object"}},
                "confidence": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]}
            },
            "required": ["facts"]
        }
    
    def _initialize_fallback_kb(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize fallback knowledge base for when Firecrawl is unavailable."""
        return {
            "tax": [
                {
                    "topic": "Section 80C",
                    "facts": [
                        "Section 80C allows deductions up to ₹1.5 lakh per year",
                        "Eligible investments include PPF, ELSS, NSC, life insurance premiums",
                        "Lock-in periods vary: ELSS (3 years), PPF (15 years)"
                    ],
                    "source": "Income Tax Act, 1961"
                },
                {
                    "topic": "Section 80CCD",
                    "facts": [
                        "NPS offers additional ₹50,000 deduction under 80CCD(1B)",
                        "This is over and above the ₹1.5 lakh limit of 80C",
                        "Total tax benefit with NPS can be up to ₹2 lakh"
                    ],
                    "source": "Income Tax Act, 1961"
                }
            ],
            "mutual fund": [
                {
                    "topic": "Mutual Fund Taxation",
                    "facts": [
                        "SEBI regulates all mutual funds in India",
                        "Equity funds: LTCG above ₹1 lakh taxed at 10%",
                        "Debt funds: Taxed as per income slab from FY 2023-24",
                        "ELSS funds offer tax benefits with 3-year lock-in"
                    ],
                    "source": "SEBI Regulations"
                }
            ],
            "epf": [
                {
                    "topic": "EPF Rules",
                    "facts": [
                        "Employee contributes 12% of basic salary to EPF",
                        "Employer matches 12% (3.67% EPF + 8.33% EPS)",
                        "Current interest rate approximately 8.15%",
                        "Full withdrawal after 2 months unemployment or age 58"
                    ],
                    "source": "EPFO Guidelines"
                }
            ],
            "retirement": [
                {
                    "topic": "NPS",
                    "facts": [
                        "National Pension System offers market-linked returns",
                        "Flexible allocation: equity, corporate bonds, govt securities",
                        "Partial withdrawal allowed after 3 years",
                        "Additional ₹50,000 tax benefit under 80CCD(1B)"
                    ],
                    "source": "PFRDA Guidelines"
                }
            ],
            "credit": [
                {
                    "topic": "Credit Score",
                    "facts": [
                        "Credit scores in India range from 300-900",
                        "Score above 750 is considered excellent",
                        "Key factors: payment history, utilization, credit age",
                        "RBI mandates free credit report once a year"
                    ],
                    "source": "RBI Guidelines"
                }
            ],
            "trending": [
                {
                    "topic": "Trending Stocks India",
                    "facts": [
                        "Top gainers today: Reliance Industries (+2.1%), HDFC Bank (+1.8%), Infosys (+1.5%)",
                        "Nifty 50 is trading at 22,450 levels with positive momentum",
                        "Banking sector leading gains with 2-3% upside",
                        "IT sector showing recovery after recent correction",
                        "Auto stocks: Maruti, Tata Motors gaining on strong sales data"
                    ],
                    "source": "Market Analysis (Demo Data - Real-time data requires market API)"
                }
            ],
            "top stocks": [
                {
                    "topic": "Top Stocks to Consider",
                    "facts": [
                        "Large Cap: Reliance Industries, TCS, HDFC Bank, Infosys, ICICI Bank",
                        "Mid Cap: Dixon Technologies, Polycab, Indian Hotels, Persistent Systems",
                        "High Dividend: Coal India (8%+), ONGC (5%+), Power Grid (4%+)",
                        "Growth Stocks: Dmart, Titan, Asian Paints, Pidilite Industries",
                        "Value Picks: SBI, Axis Bank, Tech Mahindra (at attractive valuations)"
                    ],
                    "source": "Market Analysis (Demo Data)"
                }
            ],
            "best stocks": [
                {
                    "topic": "Best Performing Stocks",
                    "facts": [
                        "YTD Top Performers: Adani Ports (+45%), Trent (+38%), Mahindra & Mahindra (+32%)",
                        "Best in IT: TCS, Infosys, HCL Tech showing consistent growth",
                        "Best in Banking: HDFC Bank, ICICI Bank, Kotak Bank with strong NII growth",
                        "Best in FMCG: Nestle India, Hindustan Unilever maintaining market leadership",
                        "Best in Pharma: Sun Pharma, Dr Reddy's benefiting from US generics market"
                    ],
                    "source": "Market Analysis (Demo Data)"
                }
            ],
            "market": [
                {
                    "topic": "Market Overview",
                    "facts": [
                        "Nifty 50 trading near all-time highs at 22,400-22,500 range",
                        "Sensex at 73,500+ levels with FII inflows supporting rally",
                        "Bank Nifty showing strength above 48,000 levels",
                        "India VIX (volatility index) at comfortable 12-14 range",
                        "Rupee stable at 83-83.50 against USD"
                    ],
                    "source": "Market Analysis (Demo Data)"
                }
            ],
            "sebi": [
                {
                    "topic": "SEBI Regulations",
                    "facts": [
                        "SEBI (Securities and Exchange Board of India) regulates the securities market",
                        "SEBI mandates T+1 settlement cycle for equity trades since January 2023",
                        "Minimum lot size for F&O trading increased to ₹5-10 lakh notional value",
                        "SEBI requires brokers to collect margins upfront under new peak margin norms",
                        "Listed companies must have minimum 25% public shareholding",
                        "SEBI circular on ESG disclosures mandatory for top 1000 listed companies"
                    ],
                    "source": "SEBI Regulations 2024-25"
                },
                {
                    "topic": "SEBI Investor Protection",
                    "facts": [
                        "SEBI Investor Protection Fund covers up to ₹25 lakh per investor per broker default",
                        "KYC is mandatory for all securities market participants",
                        "SEBI mandates risk disclosure requirement for derivatives trading",
                        "Investor complaints can be filed through SCORES (SEBI Complaints Redressal System)"
                    ],
                    "source": "SEBI Guidelines"
                }
            ],
            "controversy": [
                {
                    "topic": "Stock Controversy Detection",
                    "facts": [
                        "ESG (Environmental, Social, Governance) scores help identify controversial stocks",
                        "SEBI mandates Business Responsibility and Sustainability Reporting (BRSR) for top 1000 companies",
                        "Corporate governance lapses include related-party transactions, board independence issues",
                        "Regulatory actions, SEBI investigations, and NCLT proceedings are red flags",
                        "Check for promoter pledge levels — high pledge ratios indicate corporate stress"
                    ],
                    "source": "Corporate Governance Analysis"
                }
            ],
            "intraday": [
                {
                    "topic": "Intraday Trading Rules India",
                    "facts": [
                        "Intraday trading requires a demat and trading account with a SEBI-registered broker",
                        "SEBI mandates brokers to collect VaR + ELM margins for intraday positions",
                        "Intraday positions are auto-squared off before market close (typically 3:15 PM IST)",
                        "STT on intraday equity is 0.025% on sell side only (reduced from 0.05% in Budget 2024)",
                        "Profits from intraday trading are classified as speculative business income for tax purposes",
                        "SEBI circular restricts leveraged intraday exposure; maximum leverage varies by broker",
                        "Pattern Day Trader rules don't apply in India — no minimum balance requirement"
                    ],
                    "source": "SEBI Trading Regulations 2024-25"
                }
            ],
            "tax regime": [
                {
                    "topic": "Old vs New Tax Regime India",
                    "facts": [
                        "New Tax Regime (default from FY 2023-24): No deductions except ₹50,000 standard deduction",
                        "New regime slabs: ₹0-3L (0%), ₹3-7L (5%), ₹7-10L (10%), ₹10-12L (15%), ₹12-15L (20%), ₹15L+ (30%)",
                        "Old regime allows deductions: 80C (₹1.5L), 80D (₹25-50K), HRA, LTA, etc.",
                        "Old regime slabs: ₹0-2.5L (0%), ₹2.5-5L (5%), ₹5-10L (20%), ₹10L+ (30%)",
                        "New regime beneficial if total deductions are less than ₹3.75 lakh",
                        "Salaried individuals can switch between regimes each year; business owners cannot switch back to old after choosing new",
                        "Rebate under Section 87A: No tax up to ₹7 lakh income under new regime"
                    ],
                    "source": "Income Tax Act (Finance Act 2024)"
                }
            ],
            "tax saving": [
                {
                    "topic": "Tax Saving Schemes 2024",
                    "facts": [
                        "ELSS (Equity Linked Savings Scheme): 80C deduction, 3-year lock-in, equity market returns",
                        "PPF (Public Provident Fund): 80C deduction, 15-year lock-in, ~7.1% interest, EEE status",
                        "NPS: Additional ₹50,000 deduction under 80CCD(1B), market-linked returns",
                        "Life Insurance Premiums: 80C deduction, term plans recommended for pure protection",
                        "SSY (Sukanya Samriddhi Yojana): 80C deduction, 8.2% interest, for girl child",
                        "Home Loan: 80C for principal (₹1.5L), Section 24 for interest (₹2L for self-occupied)",
                        "Health Insurance (80D): ₹25,000 for self/family, ₹50,000 for senior citizen parents"
                    ],
                    "source": "Income Tax Act 2024-25"
                }
            ],
            "rbi": [
                {
                    "topic": "RBI Policies",
                    "facts": [
                        "RBI repo rate at 6.50% (as of early 2024), influencing lending rates across banks",
                        "RBI mandates minimum CRR of 4.5% and SLR of 18% for commercial banks",
                        "Inflation targeting framework: RBI targets 4% CPI inflation with ±2% band",
                        "Digital rupee (e₹) pilot launched for wholesale and retail segments",
                        "UPI transaction limit increased to ₹5 lakh for certain categories",
                        "RBI guidelines on personal loan securitization tightened in November 2023"
                    ],
                    "source": "RBI Monetary Policy 2024"
                }
            ],
            "insurance": [
                {
                    "topic": "Insurance in India",
                    "facts": [
                        "Term insurance recommended: ₹1 crore cover available at ₹8,000-15,000/year for age 25-30",
                        "Health insurance: ₹5 lakh cover minimum recommended, super top-up for additional coverage",
                        "Section 80D allows deduction up to ₹25,000 for health insurance premium",
                        "LIC policies: Traditional plans offer lower returns (~5-6%) vs mutual funds",
                        "IRDAI mandates standard products: Saral Jeevan Bima, Arogya Sanjeevani",
                        "Motor insurance: Third-party mandatory, comprehensive recommended"
                    ],
                    "source": "IRDAI Regulations"
                }
            ],
            "gold": [
                {
                    "topic": "Gold Investment India",
                    "facts": [
                        "Sovereign Gold Bonds (SGBs): 2.5% annual interest + gold price appreciation, 8-year tenure",
                        "Gold ETFs: No making charges, stored digitally, traded on exchanges",
                        "Digital Gold: Available through apps, minimum ₹1 investment",
                        "Physical gold: Making charges 8-25%, storage risk, no income generation",
                        "Gold LTCG tax: 12.5% after 3 years (for bonds and ETFs from FY 2024-25)",
                        "Ideal portfolio allocation for gold: 5-15% for diversification"
                    ],
                    "source": "Investment Analysis"
                }
            ],
            "real estate": [
                {
                    "topic": "Real Estate Investment India",
                    "facts": [
                        "RERA (Real Estate Regulation Act) protects homebuyers; all projects must be RERA registered",
                        "Home loan interest deduction up to ₹2 lakh under Section 24 for self-occupied property",
                        "Stamp duty typically 5-7% of property value, varies by state",
                        "REITs (Real Estate Investment Trusts) allow fractional real estate investment from ₹10,000-15,000",
                        "Circle rate or guidance value is minimum registration value set by state government",
                        "GST on under-construction property: 5% without ITC, 1% for affordable housing"
                    ],
                    "source": "RERA & Tax Regulations"
                }
            ],
            "fd": [
                {
                    "topic": "Fixed Deposit Rates",
                    "facts": [
                        "SBI FD rates: 6.5-7.1% for general, 7.0-7.6% for senior citizens (2024)",
                        "Tax-saving FD: 5-year lock-in, 80C deduction up to ₹1.5 lakh",
                        "Interest is fully taxable; TDS deducted at 10% if interest exceeds ₹40,000/year",
                        "Post Office Term Deposits: Government-backed, slightly higher rates than banks",
                        "Corporate FDs offer 1-2% higher rates but carry more credit risk",
                        "Premature withdrawal penalty: typically 0.5-1% reduction in applicable rate"
                    ],
                    "source": "Banking Regulations 2024"
                }
            ],
            "ppf": [
                {
                    "topic": "PPF (Public Provident Fund)",
                    "facts": [
                        "PPF interest rate: 7.1% per annum (Q1 FY 2024-25), compounded annually",
                        "Tenure: 15 years, extendable in blocks of 5 years",
                        "Minimum deposit: ₹500/year, Maximum: ₹1.5 lakh/year",
                        "EEE (Exempt-Exempt-Exempt) status: Contribution, interest, and maturity all tax-free",
                        "Partial withdrawal allowed from 7th year onwards (up to 50% of balance)",
                        "Loan facility available from 3rd to 6th year at 1% above PPF interest rate",
                        "PPF account can be opened at post office or any nationalized bank"
                    ],
                    "source": "PPF Act & Government Notifications"
                }
            ],
            "sip": [
                {
                    "topic": "SIP (Systematic Investment Plan)",
                    "facts": [
                        "SIP allows investing as low as ₹100-500 per month in mutual funds",
                        "Rupee cost averaging reduces impact of market volatility over time",
                        "SIP in Nifty 50 index fund has delivered ~12-15% CAGR over 10+ years",
                        "Step-up SIP: Increase SIP amount annually by 10-15% for wealth acceleration",
                        "SIP date doesn't significantly impact long-term returns",
                        "Equity SIP should be held for minimum 5-7 years for optimal returns"
                    ],
                    "source": "AMFI & Mutual Fund Analysis"
                }
            ]
        }
    
    def _clean_content(self, content: str, max_length: int = 500) -> str:
        """
        Clean and truncate web content to prevent raw HTML dumps.
        
        - Removes markdown links and images
        - Filters out navigation/menu content
        - Truncates to max_length characters
        """
        if not content:
            return ""
        
        import re
        
        # Remove markdown links [text](url) -> text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        
        # Remove markdown images ![alt](url)
        content = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', content)
        
        # Remove URLs
        content = re.sub(r'https?://\S+', '', content)
        
        # Remove lines that look like navigation (short lines with lots of pipes or bullets)
        lines = content.split('\n')
        filtered_lines = []
        for line in lines:
            line = line.strip()
            # Skip short lines, menu items, navigation
            if len(line) < 20:
                continue
            # Skip lines with too many special characters (likely navigation)
            if line.count('|') > 2 or line.count('-') > 10:
                continue
            # Skip lines that are just headers or menu items
            if line.startswith('#') and len(line) < 50:
                continue
            filtered_lines.append(line)
        
        content = ' '.join(filtered_lines)
        
        # Collapse multiple spaces
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Truncate to max length
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content
    
    def _check_freshness(self, content: str) -> bool:
        """
        Check if content appears recent (2024-2026).
        Simple heuristic based on year mentions.
        """
        import re
        years = re.findall(r'202[0-9]', content)
        if not years: return True # Assume okay if no date
        
        # If explicitly mentions old years without new ones, flag it
        latest_year = max([int(y) for y in years])
        if latest_year < 2024:
            return False
        return True
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve relevant knowledge based on query topic.
        
        Uses Firecrawl MCP if available, falls back to built-in knowledge.
        """
        query_topic = input_data.get("query_topic", "") or input_data.get("query", "")
        query_lower = query_topic.lower()
        
        # NEW: Enforce Indian context for regulatory/tax queries if not specified
        if any(w in query_lower for w in ["tax", "law", "regulation", "rule", "limit", "deduction"]) and "india" not in query_lower:
            query_topic += " in India"
            self.add_reasoning_step(" appended 'in India' to query for locality context")
            
        self.record_context_access("external_knowledge_context")
        self.add_reasoning_step(f"Searching knowledge base for: {query_topic}")
        
        self.record_context_access("external_knowledge_context")
        self.add_reasoning_step(f"Searching knowledge base for: {query_topic}")
        
        # 1. Try GraphRAG (Hybrid) first
        if self._rag_service:
             try:
                 self.add_reasoning_step("Searching internal Knowledge Base (GraphRAG)")
                 # Query GraphRAG
                 search_result = await self._rag_service.hybrid_search(query_topic)
                 
                 docs = search_result.get("documents", [])
                 graph_facts = search_result.get("graph_context", [])
                 
                 if docs or graph_facts:
                     self.add_reasoning_step(f"Found {len(docs)} docs and {len(graph_facts)} graph relations")
                     
                     combined_facts = docs + [f"Graph Relation: {f}" for f in graph_facts]
                     
                     return {
                         "facts": combined_facts,
                         "source_type": "Internal Documents & Graph (Hybrid)",
                         "sources": [{"title": "Internal KB", "type": "hybrid"}],
                         "confidence": "HIGH"
                     }
             except Exception as e:
                 logger.warning(f"GraphRAG search failed: {e}")

        # 2. Try Alpha Vantage API FIRST for stock queries (before Firecrawl)
        # This ensures stock queries get reliable, structured data
        stock_keywords = ["price", "stock", "trading", "worth", "value", "hdfc", "reliance", "tcs", "infosys", "tesla", "tsla", "aapl", "googl", "msft", "amzn", "ibm"]
        if any(kw in query_lower for kw in stock_keywords):
            try:
                self.add_reasoning_step("Stock query detected, fetching from Alpha Vantage API")
                
                # Check cache for stock query
                from app.core.cache import cache_manager
                cache_key_av = f"alpha_vantage:{query_lower}"
                time_series_cache_key = f"alpha_vantage:ts:{query_lower}"
                
                cached_av = await cache_manager.get(cache_key_av)
                if cached_av:
                    self.add_reasoning_step("Retrieved stock data from cache")
                    return cached_av

                # Stock symbol mapping
                stock_map = {
                    "hdfc": "HDFCBANK.BSE",
                    "hdfc bank": "HDFCBANK.BSE",
                    "reliance": "RELIANCE.BSE", 
                    "tcs": "TCS.BSE",
                    "infosys": "INFY",
                    "icici": "ICICIBANK.BSE",
                    "tesla": "TSLA",
                    "apple": "AAPL",
                    "google": "GOOGL",
                    "microsoft": "MSFT",
                    "amazon": "AMZN",
                    "ibm": "IBM"
                }
                
                symbol = None
                company_key = None
                for company, ticker in stock_map.items():
                    if company in query_lower:
                        symbol = ticker
                        company_key = company
                        break
                
                if symbol:
                    api_key = get_settings().alpha_vantage_api_key
                    if not api_key:
                        self.add_reasoning_step("Alpha Vantage API key is not configured; skipping live stock fetch")
                        raise RuntimeError("ALPHA_VANTAGE_API_KEY not configured")
                    
                    # Fetch GLOBAL_QUOTE (current price)
                    quote_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        quote_response = await client.get(quote_url)
                        quote_data = quote_response.json()
                    
                    # Fetch TIME_SERIES_DAILY (historical data for predictions)
                    # We utilize a separate cache key for historical data as it is heavy
                    timeseries_data = await cache_manager.get(time_series_cache_key)
                    if not timeseries_data:
                        timeseries_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={api_key}"
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            timeseries_response = await client.get(timeseries_url)
                            timeseries_data = timeseries_response.json()
                        await cache_manager.set(time_series_cache_key, timeseries_data, ttl=3600) # Cache for 1 hour
                    
                    current_price = None
                    facts = []
                    
                    if "Global Quote" in quote_data and quote_data["Global Quote"]:
                        quote = quote_data["Global Quote"]
                        current_price = float(quote.get("05. price", 0))
                        
                        if current_price > 0:
                            company_name = stock_map.get(company_key, symbol).replace(".BSE", "").replace(".NS", "")
                            previous_close = float(quote.get("08. previous close", 0))
                            high = float(quote.get("03. high", 0))
                            low = float(quote.get("04. low", 0))
                            change_percent = quote.get("10. change percent", "N/A")
                            currency = "₹" if ".BSE" in symbol or ".NS" in symbol else "$"
                            
                            facts.append(f"{company_name} ({symbol}) is currently trading at {currency}{current_price:,.2f}")
                            facts.append(f"Previous close: {currency}{previous_close:,.2f}" if previous_close > 0 else "Previous close: Not available")
                            facts.append(f"Day's range: {currency}{low:,.2f} - {currency}{high:,.2f}" if low > 0 and high > 0 else "Day's range: Not available")
                            facts.append(f"Change: {change_percent}" if change_percent != "N/A" else "Change: Not available")
                    
                    # Process historical time series
                    historical_data = {}
                    if "Time Series (Daily)" in timeseries_data:
                        time_series = timeseries_data["Time Series (Daily)"]
                        historical_data = {
                            "symbol": symbol,
                            "data": time_series,
                            "data_points": len(time_series)
                        }
                        facts.append(f"Historical data available: {len(time_series)} days of trading data")
                        self.add_reasoning_step(f"Retrieved {len(time_series)} days of historical data for {symbol}")
                    
                    if facts and current_price and current_price > 0:
                        self.add_reasoning_step(f"Successfully fetched stock data for {symbol}: {currency}{current_price:,.2f}")
                        
                        result = {
                            "facts": facts,
                            "source_type": "Alpha Vantage (Real-time stock data)",
                            "sources": [{"title": f"{company_name} Stock Data", "type": "financial_data", "provider": "Alpha Vantage"}],
                            "confidence": "HIGH"
                        }
                        
                        if historical_data:
                            result["historical_data"] = historical_data
                        
                        # Cache the successful result
                        await cache_manager.set(cache_key_av, result, ttl=300) # Cache for 5 mins
                        
                        return result
                    
                    logger.warning(f"Alpha Vantage returned no valid data for {symbol}")
                
            except Exception as e:
                logger.warning(f"Alpha Vantage lookup failed: {e}")
                self.add_reasoning_step(f"Alpha Vantage failed, falling back to Firecrawl")

        # 3. Try Firecrawl MCP for non-stock queries (or if Alpha Vantage failed)
        if self._firecrawl_service:
            try:
                self.add_reasoning_step("Attempting Firecrawl MCP search")
                
                from app.core.cache import cache_manager
                cache_key_fc = f"firecrawl:{query_topic}"
                cached_fc = await cache_manager.get(cache_key_fc)
                
                if cached_fc:
                    self.add_reasoning_step("Retrieved Firecrawl results from cache")
                    return cached_fc
                
                results = await self._firecrawl_service.search(query_topic)
                
                if results and len(results) > 0:
                    # Clean and truncate content to prevent raw HTML dumps
                    facts = []
                    for r in results[:5]:
                        content = r.get("content", r.get("title", ""))
                        clean = self._clean_content(content)
                        if clean:
                            # Freshness check
                            if not self._check_freshness(clean):
                                clean += " [WARNING: Content may be outdated (pre-2024 references detected)]"
                            facts.append(clean)
                    
                    self.add_reasoning_step(f"Retrieved {len(facts)} cleaned results from Firecrawl MCP")
                    
                    result = {
                        "facts": facts,
                        "source_type": "Firecrawl MCP (Real-time web data)",
                        "sources": [{"title": r.get("title", ""), "url": r.get("url", "")} for r in results[:3]],
                        "confidence": "HIGH"
                    }
                    
                    # Cache successful result
                    await cache_manager.set(cache_key_fc, result, ttl=3600) # Cache for 1 hour
                    
                    return result
            except Exception as e:
                logger.warning(f"Firecrawl search failed, using fallback: {e}")
                self.add_reasoning_step("Firecrawl unavailable, using fallback knowledge")
        
        # Fallback to built-in knowledge base
        self.add_reasoning_step("No exact match, performing broader search")
        relevant_facts = []
        source_type = None
        
        for category, items in self._fallback_kb.items():
            if category in query_lower:
                for item in items:
                    if any(kw in query_lower for kw in item["topic"].lower().split()):
                        relevant_facts.extend(item["facts"])
                        source_type = item["source"]
                        self.add_reasoning_step(f"Found relevant facts for {item['topic']}")
        
        # If no specific match, try broader search
        if not relevant_facts:
            for category, items in self._fallback_kb.items():
                for item in items:
                    query_words = set(query_lower.split())
                    topic_words = set(item["topic"].lower().split())
                    if query_words & topic_words:
                        relevant_facts.extend(item["facts"])
                        source_type = item["source"]
        
        # Determine confidence
        if relevant_facts:
            confidence = "HIGH" if len(relevant_facts) >= 3 else "MEDIUM"
        else:
            confidence = "LOW"
            relevant_facts = ["No specific information found for this query"]
            source_type = "Knowledge base"
        
        self.add_reasoning_step(f"Retrieved {len(relevant_facts)} facts with {confidence} confidence")
        
        return {
            "facts": relevant_facts,
            "source_type": source_type or "Various financial regulations",
            "sources": [],
            "confidence": confidence
        }
