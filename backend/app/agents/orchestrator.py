"""
Orchestrator Agent
Routes queries to specialized agents and manages execution flow.
"""

from typing import Dict, Any, List
from loguru import logger

from app.agents.base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent - The central coordinator.
    
    Responsibilities:
    - Understand user intent
    - Decide which agents to invoke
    - Determine execution order
    - Specify what context each agent needs
    
    Rules:
    - Does NOT perform calculations
    - Does NOT generate user-facing advice
    - Does NOT access raw financial values
    """
    
    def __init__(self):
        super().__init__()
        self.name = "orchestrator"
        self.description = "Routes queries to specialized agents and manages execution flow"
        self.read_layers = {"user_goals_context"}
        self.write_layers = {"agent_working_memory"}
        
        self.system_prompt = """You are the Orchestrator Agent in a multi-agent financial intelligence system.

Your task is to:
- Understand the user's intent
- Decide which specialized agents are required
- Determine execution order
- Specify what context each agent must read

Rules:
- Do NOT perform financial calculations
- Do NOT generate user-facing advice
- Do NOT access raw financial values
- Output must be structured JSON only
- Minimize the number of agents invoked

Available agents:
- finance_reasoning: For financial calculations, metrics, risk analysis
- knowledge: For external facts, tax rules, regulations
- explainability: For converting outputs to human-readable explanations
- alert: For generating proactive alerts based on financial signals"""
        
        # Stock symbol mapping for common queries (expanded for better coverage)
        self.stock_symbol_map = {
            # US Stocks
            "tesla": "TSLA",
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "amazon": "AMZN",
            "meta": "META",
            "facebook": "META",
            "netflix": "NFLX",
            "nvidia": "NVDA",
            "intel": "INTC",
            "amd": "AMD",
            "ibm": "IBM",
            "oracle": "ORCL",
            "salesforce": "CRM",
            "adobe": "ADBE",
            "cisco": "CSCO",
            "paypal": "PYPL",
            "visa": "V",
            "mastercard": "MA",
            "jpmorgan": "JPM",
            "jp morgan": "JPM",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "goldman sachs": "GS",
            "morgan stanley": "MS",
            "walmart": "WMT",
            "target": "TGT",
            "costco": "COST",
            "home depot": "HD",
            "nike": "NKE",
            "starbucks": "SBUX",
            "mcdonald": "MCD",
            "coca cola": "KO",
            "pepsi": "PEP",
            "procter": "PG",
            "johnson": "JNJ",
            "pfizer": "PFE",
            "moderna": "MRNA",
            "boeing": "BA",
            "lockheed": "LMT",
            "exxon": "XOM",
            "chevron": "CVX",
            "conocophillips": "COP",
            
            # Indian Stocks (with .NS suffix for NSE)
            "reliance": "RELIANCE.NS",
            "ril": "RELIANCE.NS",
            "tcs": "TCS.NS",
            "tata consultancy": "TCS.NS",
            "infosys": "INFY.NS",
            "infy": "INFY.NS",
            "hdfc": "HDFCBANK.NS",
            "hdfcbank": "HDFCBANK.NS",
            "hdfc bank": "HDFCBANK.NS",
            "icici": "ICICIBANK.NS",
            "icicibank": "ICICIBANK.NS",
            "icici bank": "ICICIBANK.NS",
            "sbi": "SBIN.NS",
            "state bank": "SBIN.NS",
            "state bank of india": "SBIN.NS",
            "wipro": "WIPRO.NS",
            "bharti": "BHARTIARTL.NS",
            "airtel": "BHARTIARTL.NS",
            "bharti airtel": "BHARTIARTL.NS",
            "itc": "ITC.NS",
            "axis": "AXISBANK.NS",
            "axis bank": "AXISBANK.NS",
            "bajaj": "BAJFINANCE.NS",
            "bajaj finance": "BAJFINANCE.NS",
            "bajaj finserv": "BAJAJFINSV.NS",
            "maruti": "MARUTI.NS",
            "maruti suzuki": "MARUTI.NS",
            "mahindra": "M&M.NS",
            "m&m": "M&M.NS",
            "tata motors": "TATAMOTORS.NS",
            "tata steel": "TATASTEEL.NS",
            "tata power": "TATAPOWER.NS",
            "adani": "ADANIENT.NS",
            "adani enterprises": "ADANIENT.NS",
            "adani ports": "ADANIPORTS.NS",
            "adani green": "ADANIGREEN.NS",
            "larsen": "LT.NS",
            "l&t": "LT.NS",
            "larsen & toubro": "LT.NS",
            "ultratech": "ULTRACEMCO.NS",
            "ultratech cement": "ULTRACEMCO.NS",
            "asian paints": "ASIANPAINT.NS",
            "nestle": "NESTLEIND.NS",
            "nestle india": "NESTLEIND.NS",
            "hindustan unilever": "HINDUNILVR.NS",
            "hul": "HINDUNILVR.NS",
            "britannia": "BRITANNIA.NS",
            "dabur": "DABUR.NS",
            "godrej": "GODREJCP.NS",
            "godrej consumer": "GODREJCP.NS",
            "sun pharma": "SUNPHARMA.NS",
            "dr reddy": "DRREDDY.NS",
            "cipla": "CIPLA.NS",
            "divi": "DIVISLAB.NS",
            "divis lab": "DIVISLAB.NS",
            "kotak": "KOTAKBANK.NS",
            "kotak bank": "KOTAKBANK.NS",
            "indusind": "INDUSINDBK.NS",
            "indusind bank": "INDUSINDBK.NS",
            "yes bank": "YESBANK.NS",
            "bandhan": "BANDHANBNK.NS",
            "bandhan bank": "BANDHANBNK.NS",
            "power grid": "POWERGRID.NS",
            "ntpc": "NTPC.NS",
            "coal india": "COALINDIA.NS",
            "ongc": "ONGC.NS",
            "oil india": "OIL.NS",
            "ioc": "IOC.NS",
            "indian oil": "IOC.NS",
            "bpcl": "BPCL.NS",
            "bharat petroleum": "BPCL.NS",
            "hpcl": "HINDALCO.NS",
            "hindalco": "HINDALCO.NS",
            "vedanta": "VEDL.NS",
            "jsw steel": "JSWSTEEL.NS",
            "jsw": "JSWSTEEL.NS",
            "tech mahindra": "TECHM.NS",
            "hcl": "HCLTECH.NS",
            "hcl tech": "HCLTECH.NS",
            "mindtree": "MINDTREE.NS",
            "mphasis": "MPHASIS.NS",
            "persistent": "PERSISTENT.NS",
        }

    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_query": {"type": "string"},
                "available_agents": {"type": "array", "items": {"type": "string"}},
                "context_summary": {"type": "object"}
            },
            "required": ["user_query"]
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "execution_plan": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "agent": {"type": "string"},
                            "context_required": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "reason": {"type": "string"}
            },
            "required": ["execution_plan", "reason"]
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user query and create execution plan.
        """
        user_query = input_data.get("user_query", "")
        context_summary = input_data.get("context_summary", {})
        
        self.add_reasoning_step("Analyzing user query intent")
        
        # Extract entities using enhanced method
        parsed_entities = self.extract_entities(user_query)
        if parsed_entities:
            self.add_reasoning_step(f"Extracted entities: {parsed_entities}")
        
        # Classify intent
        intent = self.classify_intent(user_query, parsed_entities)
        self.add_reasoning_step(f"Classified intent: {intent}")
        
        # Determine which agents are needed based on query analysis
        execution_plan = await self._create_execution_plan(user_query, context_summary, parsed_entities, intent)
        
        self.add_reasoning_step(f"Created execution plan with {len(execution_plan)} agents")
        
        return {
            "execution_plan": execution_plan,
            "intent": intent,
            "reason": self._generate_reason(user_query, execution_plan),
            "parsed_entities": parsed_entities  # Pass entities to coordinator
        }
    
    async def _create_execution_plan(
        self, 
        query: str, 
        context: Dict[str, Any],
        parsed_entities: Dict[str, Any] = None,
        intent: str = None
    ) -> List[Dict[str, Any]]:
        """
        Create an execution plan based on query analysis.
        
        Uses intent classification and entity extraction for improved agent selection.
        """
        plan = []
        query_lower = query.lower()
        parsed_entities = parsed_entities or {}
        intent = intent or "KNOWLEDGE"  # Default intent

        self.add_reasoning_step(f"Building execution plan for intent: {intent}")

        planning_guard_keywords = [
            "afford", "emi", "down payment", "home loan", "loan eligibility",
            "credit score", "risk factor"
        ]
        home_guard_keywords = ["house", "home", "property", "purchase", "buy"]
        is_home_affordability_query = (
            any(kw in query_lower for kw in home_guard_keywords)
            and any(kw in query_lower for kw in planning_guard_keywords)
        ) or parsed_entities.get("goal") == "HOME_PURCHASE"
        alert_query_keywords = ["alert", "alert check", "proactive alert", "trigger alert", "trigger a proactive alert check"]
        is_alert_check_query = any(kw in query_lower for kw in alert_query_keywords)

        # Personal income-shock planning queries should not trigger graph reasoning on "impact".
        personal_context_keywords = [" my ", " me ", " i ", "myself", "my context"]
        income_terms = ["income", "salary", "pay"]
        income_drop_terms = ["drop", "drops", "decrease", "decreases", "cut", "cuts", "fall", "falls", "reduce", "reduces"]
        rebalance_terms = ["rebalance", "re-balance", "reallocate", "reprioritize", "re-prioritize", "impacted first", "which goals"]
        padded_query = f" {query_lower} "
        has_personal_context = any(kw in padded_query for kw in personal_context_keywords)
        has_income_context = any(kw in query_lower for kw in income_terms)
        has_income_drop_signal = any(kw in query_lower for kw in income_drop_terms) or "%" in query_lower
        has_rebalance_signal = any(kw in query_lower for kw in rebalance_terms)
        is_personal_income_rebalance_query = (
            has_personal_context and has_income_context and has_income_drop_signal and has_rebalance_signal
        )
        
        # 0. DISCOVERY queries (e.g., "top stocks", "trending stocks", "best performing")
        # These require external knowledge/search, NOT code analysis on specific symbols
        discovery_keywords = ["top", "trending", "best", "worst", "list of", "recommend", "hot", "gainer", "loser"]
        is_discovery = any(kw in query_lower for kw in discovery_keywords) and ("stock" in query_lower or "market" in query_lower)
        
        if is_discovery and not parsed_entities.get("stock_symbol"):
            self.add_reasoning_step("Discovery/Trending query detected - invoking Knowledge_Agent for market data")
            plan.append({
                "agent": "knowledge",
                "input": {
                    "query_topic": query
                },
                "context_required": ["external_knowledge_context"]
            })
            # Skip code agent for discovery queries unless explicitly requested later
            # This prevents CodeAgent from trying to "analyze" an unknown symbol

        # CRITICAL FIX: Ensure Graph_Reasoning_Agent is invoked for GRAPH_QUERY intent
        if intent == "GRAPH_QUERY":
            if is_personal_income_rebalance_query:
                self.add_reasoning_step("Graph intent overridden for personal income-rebalance planning query")
            else:
                self.add_reasoning_step("Graph/Network analysis required - invoking Graph_Reasoning_Agent")
                plan.append({
                    "agent": "graph_reasoning",
                    "input": {
                        "query_topic": query,
                        "analysis_type": "network"
                    },
                    "context_required": ["external_knowledge_context"]
                })
        
        # Also check for explicit graph keywords as fallback
        graph_keywords = ["impact", "affect", "connection", "network", "relationship", 
                         "upstream", "downstream", "supply chain", "supplier", "controversy", "esg"]
        if not any(p["agent"] == "graph_reasoning" for p in plan):
            if any(keyword in query_lower for keyword in graph_keywords):
                if is_personal_income_rebalance_query:
                    self.add_reasoning_step("Graph-keyword fallback skipped for personal income-rebalance planning query")
                else:
                    self.add_reasoning_step("Graph keywords detected - invoking Graph_Reasoning_Agent")
                    plan.append({
                        "agent": "graph_reasoning",
                        "input": {
                            "query_topic": query,
                            "analysis_type": "network"
                        },
                        "context_required": ["external_knowledge_context"]
                    })
        
        # 2. Deep Research Agent - for comprehensive multi-source research
        # CRITICAL FIX: Ensure Deep_Research_Agent is invoked for RESEARCH intent
        if intent == "RESEARCH":
            self.add_reasoning_step("Multi-source research required - invoking Deep_Research_Agent")
            plan.append({
                "agent": "deep_research",
                "input": {
                    "research_topic": query,
                    "focus_areas": []
                },
                "context_required": ["external_knowledge_context"]
            })
        
        # Also check for explicit research keywords as fallback
        research_keywords = ["report", "deep dive", "comprehensive", "research", "compare", "comparison"]
        if not any(p["agent"] == "deep_research" for p in plan):
            if any(kw in query_lower for kw in research_keywords) and len(query_lower.split()) > 5:
                self.add_reasoning_step("Research keywords detected - invoking Deep_Research_Agent")
                plan.append({
                    "agent": "deep_research",
                    "input": {
                        "research_topic": query,
                        "focus_areas": []
                    },
                    "context_required": ["external_knowledge_context"]
                })
        
        # 2.5. Stock Trading Analysis - for buy/sell/hold recommendations using TradingAgents
        stock_trading_keywords = [
            "should i buy", "should i sell", "should i hold",
            "buy or sell", "good investment", "worth buying", "worth investing",
            "entry point", "exit point", "bullish", "bearish",
            "trading recommendation", "investment recommendation",
            "bull case", "bear case", "risk assessment",
        ]
        has_stock_symbol = bool(parsed_entities.get("stock_symbol"))
        has_trading_intent = intent == "STOCK_TRADING" or any(kw in query_lower for kw in stock_trading_keywords)
        
        if has_trading_intent and has_stock_symbol and not is_discovery:
            self.add_reasoning_step(f"Stock trading analysis detected for {parsed_entities.get('stock_symbol')} - invoking TradingAgents pipeline")
            plan.append({
                "agent": "trading_analysis",
                "input": {
                    "stock_symbol": parsed_entities["stock_symbol"],
                    "query_topic": query
                },
                "context_required": ["external_knowledge_context"]
            })
        
        # 3. Code Agent - for predictions, analysis, and visualizations
        if intent in ["PREDICTION", "ANALYSIS"] and not is_home_affordability_query:
            self.add_reasoning_step(f"{intent} detected - invoking Code_Agent")
            agent_input = {"query_topic": query}
            
            # Add parsed stock symbol if available
            if parsed_entities.get("stock_symbol"):
                agent_input["stock_symbol"] = parsed_entities["stock_symbol"]
                self.add_reasoning_step(f"Resolved stock symbol: {parsed_entities['stock_symbol']}")
            
            plan.append({
                "agent": "code",
                "input": agent_input,
                "context_required": ["agent_working_memory"]
            })
        
        # Also check for explicit code keywords as fallback
        code_keywords = ["plot", "graph", "calculate", "analyze data", "compute", 
                        "chart", "math", "volatility", "trend", "predict", "forecast"]
        if not any(p["agent"] == "code" for p in plan):
            if any(keyword in query_lower for keyword in code_keywords):
                if is_home_affordability_query or intent in ["PLANNING", "PERSONAL"]:
                    self.add_reasoning_step("Code-agent fallback skipped for personal planning/affordability query")
                else:
                    self.add_reasoning_step("Analysis/Plotting keywords detected - invoking Code_Agent")
                    agent_input = {"query_topic": query}
                    if parsed_entities.get("stock_symbol"):
                        agent_input["stock_symbol"] = parsed_entities["stock_symbol"]
                    
                    plan.append({
                        "agent": "code",
                        "input": agent_input,
                        "context_required": ["agent_working_memory"]
                    })
        
        # 4. Finance Agent - for financial planning and personal queries
        if intent in ["PLANNING", "PERSONAL"]:
            self.add_reasoning_step(f"{intent} detected - invoking Finance_Agent")
            finance_input = {}
            
            # Add parsed entities for more specific analysis
            if parsed_entities.get("amount"):
                finance_input["target_amount"] = parsed_entities["amount"]
                self.add_reasoning_step(f"Target amount: {parsed_entities['amount']}")
            if parsed_entities.get("goal"):
                finance_input["specific_goal"] = parsed_entities["goal"]
            
            plan.append({
                "agent": "finance_reasoning",
                "input": finance_input,
                "context_required": ["user_financial_context", "transactional_signals"]
            })

            # Pass extracted age if available
            if parsed_entities.get("age"):
                plan[-1]["input"]["user_age"] = parsed_entities["age"]
                self.add_reasoning_step(f"Passed user age: {parsed_entities['age']}")
        
        # Also check for financial keywords as fallback
        financial_keywords = [
            "invest", "save", "saving", "savings", "spend", "budget", "retire", "retirement",
            "loan", "debt", "income", "expense", "net worth", "portfolio", "money", "finance",
            "credit", "emi", "mutual fund", "stock", "epf", "sip", "balance", "rate", "ratio",
            "asset", "liability", "worth", "health", "status", "financial", "afford"
        ]
        
        is_code_active = any(p["agent"] == "code" for p in plan)
        has_financial_kw = any(kw in query_lower for kw in financial_keywords)
        personal_keywords = ["my", "me", "i", "we", "our", "portfolio", "afford", "budget", "account", "transaction"]
        has_personal_context = any(kw in query_lower for kw in personal_keywords)
        
        should_add_finance = False
        if has_financial_kw and not any(p["agent"] == "finance_reasoning" for p in plan):
            if not is_code_active:
                should_add_finance = True
            elif has_personal_context:
                should_add_finance = True
                self.add_reasoning_step("Personal financial context detected alongside analysis")

        if should_add_finance:
            self.add_reasoning_step("Financial keywords detected - invoking Finance_Agent")
            finance_input = {}
            
            if parsed_entities.get("amount"):
                finance_input["target_amount"] = parsed_entities["amount"]
            if parsed_entities.get("goal"):
                finance_input["specific_goal"] = parsed_entities["goal"]
            
            plan.append({
                "agent": "finance_reasoning",
                "input": finance_input,
                "context_required": ["user_financial_context", "transactional_signals"]
            })

            # Pass extracted age if available
            if parsed_entities.get("age"):
                plan[-1]["input"]["user_age"] = parsed_entities["age"]
                self.add_reasoning_step(f"Passed user age: {parsed_entities['age']}")

        # Proactive alert check flow should run finance first, then alert synthesis.
        if is_alert_check_query and not any(p["agent"] == "finance_reasoning" for p in plan):
            self.add_reasoning_step("Alert-check query detected - adding Finance_Agent for signal generation")
            plan.append({
                "agent": "finance_reasoning",
                "input": {},
                "context_required": ["user_financial_context", "transactional_signals"]
            })
        if is_alert_check_query and not any(p["agent"] == "alert" for p in plan):
            self.add_reasoning_step("Alert-check query detected - invoking Alert_Agent")
            plan.append({
                "agent": "alert",
                "input": {},
                "context_required": ["transactional_signals", "user_financial_context"]
            })
        
        # 5. Knowledge Agent - for factual queries and external information
        if intent == "KNOWLEDGE":
            self.add_reasoning_step("Knowledge query detected - invoking Knowledge_Agent")
            plan.append({
                "agent": "knowledge",
                "input": {
                    "query_topic": query
                },
                "context_required": ["external_knowledge_context"]
            })
        
        # Also check for knowledge keywords as fallback
        knowledge_keywords = [
            "tax", "rule", "regulation", "law", "80c", "section", "deduction",
            "sebi", "rbi", "intraday", "margin",
            "current price", "stock price", "price of", "price today", "latest price",
            "market price", "trading at", "worth today", "value today",
            "what is", "what's", "tell me about", "news",
            "worst", "best", "top", "who", "which", "history", "historical"
        ]
        
        if not any(p["agent"] == "knowledge" for p in plan):
            if any(kw in query_lower for kw in knowledge_keywords):
                # Avoid pulling knowledge agent for personal-planning prompts that happen to start with "what is/what's".
                personal_context_keywords = [" my ", " me ", " i ", "myself", "my context"]
                has_personal_context = any(kw in f" {query_lower} " for kw in personal_context_keywords)
                explicit_external_keywords = [
                    "tax", "regulation", "law", "rbi", "sebi", "news",
                    "current price", "price today", "market price", "historical", "history"
                ]
                has_explicit_external_need = any(kw in query_lower for kw in explicit_external_keywords)

                if is_alert_check_query:
                    self.add_reasoning_step("Knowledge-agent fallback skipped for alert-check query")
                elif intent in ["PLANNING", "PERSONAL"] and has_personal_context and not has_explicit_external_need:
                    self.add_reasoning_step("Knowledge-agent fallback skipped for personal planning query")
                else:
                    self.add_reasoning_step("Knowledge keywords detected - invoking Knowledge_Agent")
                    plan.append({
                        "agent": "knowledge",
                        "input": {
                            "query_topic": query
                        },
                        "context_required": ["external_knowledge_context"]
                    })
        
        # 6. Validate execution plan completeness
        # Ensure we have at least one agent besides explainability
        if not plan:
            self.add_reasoning_step("No specific agents selected - defaulting to Knowledge_Agent")
            plan.append({
                "agent": "knowledge",
                "input": {
                    "query_topic": query
                },
                "context_required": ["external_knowledge_context"]
            })
        
        # 7. Always add Explainability at the end for synthesis
        self.add_reasoning_step("Adding Explainability_Agent for response synthesis")
        plan.append({
            "agent": "explainability",
            "context_required": ["agent_working_memory"]
        })
        
        # Validate plan completeness
        self._validate_execution_plan(plan, intent, parsed_entities)
        
        return plan
    
    def _validate_execution_plan(
        self, 
        plan: List[Dict[str, Any]], 
        intent: str, 
        entities: Dict[str, Any]
    ) -> None:
        """
        Validate that the execution plan is complete for the given intent.
        
        Ensures all required agents are included based on intent and entities.
        """
        agent_names = [p["agent"] for p in plan]
        
        # Check intent-specific requirements
        if intent == "GRAPH_QUERY" and "graph_reasoning" not in agent_names:
            self.add_reasoning_step("WARNING: GRAPH_QUERY intent but graph_reasoning agent not in plan")
        
        if intent == "RESEARCH" and "deep_research" not in agent_names:
            self.add_reasoning_step("WARNING: RESEARCH intent but deep_research agent not in plan")
        
        if intent == "PREDICTION" and "code" not in agent_names:
            self.add_reasoning_step("WARNING: PREDICTION intent but code agent not in plan")
        
        if intent == "PLANNING" and "finance_reasoning" not in agent_names:
            self.add_reasoning_step("WARNING: PLANNING intent but finance_reasoning agent not in plan")
        
        # Check entity-specific requirements
        if entities.get("stocks") and "code" not in agent_names and "knowledge" not in agent_names:
            self.add_reasoning_step("WARNING: Stock entities present but no analysis agent in plan")
        
        if entities.get("goals") and "finance_reasoning" not in agent_names:
            self.add_reasoning_step("WARNING: Goal entities present but finance_reasoning agent not in plan")
        
        # Ensure explainability is always last
        if "explainability" in agent_names and agent_names[-1] != "explainability":
            self.add_reasoning_step("WARNING: Explainability agent should be last in execution plan")
    
    def _generate_reason(self, query: str, plan: List[Dict[str, Any]]) -> str:
        """Generate explanation for the execution plan."""
        agents = [p["agent"] for p in plan]
        
        if len(agents) == 1:
            return f"Query requires {agents[0]} agent for analysis"
        else:
            return f"Query requires {', '.join(agents[:-1])} and {agents[-1]} for comprehensive analysis"

    def classify_intent(self, query: str, entities: Dict[str, Any] = None) -> str:
        """
        Classify query intent to determine primary analysis type.
        
        Intent categories:
        - PREDICTION: Stock price forecasting, trend prediction
        - ANALYSIS: Data analysis, visualization, calculations
        - PLANNING: Financial goal planning, budgeting
        - RESEARCH: Multi-source research, comparisons, deep dives
        - GRAPH_QUERY: Relationship analysis, network queries
        - KNOWLEDGE: Factual queries, definitions, regulations
        - PERSONAL: Personal financial status queries
        
        Args:
            query: User query string
            entities: Optional extracted entities for context
            
        Returns:
            Intent classification string
        """
        query_lower = query.lower()
        entities = entities or {}

        # Personal affordability/EMI queries must be treated as PLANNING, even with future dates.
        planning_override_keywords = [
            "afford", "emi", "down payment", "home loan", "loan eligibility",
            "credit score", "can i buy", "can i purchase", "risk factor"
        ]
        home_goal_keywords = ["house", "home", "property", "purchase", "buy"]
        personal_context_keywords = ["my", "me", "i ", "current context", "my context"]
        has_home_goal = any(kw in query_lower for kw in home_goal_keywords) or (
            entities.get("goal") == "HOME_PURCHASE"
        )
        has_planning_override = any(kw in query_lower for kw in planning_override_keywords)
        has_personal_context = any(kw in query_lower for kw in personal_context_keywords)

        if has_home_goal and (has_planning_override or has_personal_context):
            return "PLANNING"

        # Personal coaching/weakness queries should not be forced into prediction by "next N days".
        personal_pronouns = [" my ", " me ", " i ", "mine", "myself"]
        personal_finance_keywords = [
            "financial", "savings", "debt", "cash flow", "budget", "expense", "income",
            "net worth", "portfolio", "risk", "weakness"
        ]
        coaching_keywords = [
            "biggest weakness", "weakness", "what should i do", "improve",
            "next 30 days", "next 60 days", "next 90 days", "action plan"
        ]
        padded_query = f" {query_lower} "
        has_personal_pronoun = any(kw in padded_query for kw in personal_pronouns)
        has_personal_finance_signal = any(kw in query_lower for kw in personal_finance_keywords)
        has_coaching_signal = any(kw in query_lower for kw in coaching_keywords)

        if has_personal_pronoun and has_personal_finance_signal and has_coaching_signal:
            return "PERSONAL"

        # Personal income-shock goal-prioritization should be treated as PLANNING.
        income_terms = ["income", "salary", "pay"]
        income_drop_terms = ["drop", "drops", "decrease", "decreases", "cut", "cuts", "fall", "falls", "reduce", "reduces"]
        rebalance_terms = ["rebalance", "re-balance", "reallocate", "reprioritize", "re-prioritize", "impacted first", "which goals"]
        has_income_context = any(term in query_lower for term in income_terms)
        has_income_drop_signal = any(term in query_lower for term in income_drop_terms) or "%" in query_lower
        has_rebalance_signal = any(term in query_lower for term in rebalance_terms)

        if has_personal_pronoun and has_income_context and has_income_drop_signal and has_rebalance_signal:
            return "PLANNING"

        # Debt payoff strategy queries are planning, not prediction/analysis.
        debt_terms = ["debt", "emi", "loan", "liability", "liabilities", "credit card"]
        debt_planning_terms = ["payoff", "priority", "order", "timeline", "snowball", "avalanche", "debt intensity"]
        has_debt_context = any(term in query_lower for term in debt_terms)
        has_debt_planning_signal = any(term in query_lower for term in debt_planning_terms)
        if has_debt_context and has_debt_planning_signal:
            return "PLANNING"

        # Asset-allocation suitability queries should use personal planning logic.
        allocation_terms = ["asset allocation", "allocation range", "risk profile", "current liabilities", "suitable allocation"]
        if any(term in query_lower for term in allocation_terms):
            return "PLANNING"

        # Proactive alert checks are personal monitoring tasks.
        alert_terms = ["alert", "alert check", "proactive alert", "trigger alert", "trigger a proactive alert check"]
        if any(term in query_lower for term in alert_terms):
            return "PERSONAL"
        
        # 1. GRAPH_QUERY - Relationship and network analysis
        graph_keywords = [
            "impact", "affect", "connection", "network", "relationship",
            "upstream", "downstream", "supply chain", "supplier", "dependency",
            "controversy", "esg", "connected", "related to", "influence"
        ]
        if any(keyword in query_lower for keyword in graph_keywords):
            return "GRAPH_QUERY"
        
        # 1.5. STOCK_TRADING - Buy/sell/hold decision queries with specific stock
        stock_trading_keywords = [
            "should i buy", "should i sell", "should i hold",
            "buy or sell", "good investment", "worth buying", "worth investing",
            "entry point", "exit point", "bullish", "bearish",
            "trading recommendation", "investment recommendation",
        ]
        if any(kw in query_lower for kw in stock_trading_keywords):
            return "STOCK_TRADING"
        
        # 2. PREDICTION - Forecasting and predictions
        prediction_keywords = [
            "predict", "forecast", "future", "will be", "going to",
            "next month", "next year", "tomorrow", "trend", "projection",
            "estimate", "expected price", "expected return", "anticipate"
        ]
        # Also check if dates are in the future
        has_future_date = False
        if entities.get("dates"):
            for date_info in entities["dates"]:
                if "next" in date_info.get("original", "").lower():
                    has_future_date = True
                    break
        
        if any(keyword in query_lower for keyword in prediction_keywords) or has_future_date:
            return "PREDICTION"
        
        # 3. RESEARCH - Multi-source research and comparisons
        research_keywords = [
            "report", "deep dive", "comprehensive", "research", "compare",
            "comparison", "versus", "vs", "difference between", "which is better",
            "best", "worst", "top", "analyze", "analysis of", "study"
        ]
        # Research queries are typically longer and more complex
        is_complex = len(query_lower.split()) > 5
        has_research_keyword = any(kw in query_lower for kw in research_keywords)
        
        if has_research_keyword and is_complex:
            return "RESEARCH"
        
        # 4. ANALYSIS - Data analysis, calculations, visualizations
        analysis_keywords = [
            "plot", "graph", "chart", "calculate", "compute", "analyze data",
            "show me", "visualize", "volatility", "correlation", "performance",
            "returns", "growth", "decline", "statistics", "metrics"
        ]
        if any(keyword in query_lower for keyword in analysis_keywords):
            return "ANALYSIS"
        
        # 5. PLANNING - Financial goal planning
        planning_keywords = [
            "plan", "goal", "save for", "invest for", "afford", "budget",
            "retirement", "emergency fund", "house", "education", "wedding",
            "how much", "how long", "when can i", "strategy", "allocation", "payoff", "liabilities"
        ]
        has_goal = entities.get("goal") or entities.get("goals")
        has_amount = entities.get("amount") or entities.get("amounts")
        
        if any(keyword in query_lower for keyword in planning_keywords) or (has_goal and has_amount):
            return "PLANNING"
        
        # 6. KNOWLEDGE - Factual queries, definitions, regulations (check before PERSONAL)
        knowledge_keywords = [
            "what is", "what are", "tell me about", "explain", "definition",
            "meaning", "tax", "rule", "regulation", "law", "sebi", "rbi",
            "how does", "why", "current price", "price of", "news about"
        ]
        if any(keyword in query_lower for keyword in knowledge_keywords):
            return "KNOWLEDGE"
        
        # 7. PERSONAL - Personal financial status queries (check after KNOWLEDGE)
        personal_keywords = [
            "my portfolio", "my savings", "my income",
            "my net worth", "my credit", "my transactions", "my balance"
        ]
        personal_attributes = ["age", "income", "savings", "networth", "credit_score"]
        has_personal_attr = entities.get("personal_attribute") in personal_attributes
        has_personal_pronoun = any(kw in query_lower for kw in personal_keywords)
        
        if has_personal_attr or has_personal_pronoun:
            return "PERSONAL"
        
        # Default: If query has stock symbols, likely ANALYSIS, otherwise KNOWLEDGE
        if entities.get("stocks") or entities.get("stock_symbol"):
            return "ANALYSIS"
        
        return "KNOWLEDGE"
    
    def extract_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract financial entities from query with comprehensive pattern matching.
        
        Extracts:
        - Stock symbols (with company name mapping)
        - Financial amounts (supporting Indian formats: ₹, cr, lakh)
        - Dates (relative and absolute)
        - Financial goals
        
        Returns:
            Dictionary with extracted entities: stocks, amounts, dates, goals
        """
        import re
        from datetime import datetime, timedelta
        
        entities = {}
        query_lower = query.lower()
        stock_context_keywords = [
            "stock", "stocks", "share", "shares", "ticker", "market", "price", "trading",
            "nse", "bse", "nasdaq", "nyse", "sensex", "nifty", "forecast", "prediction"
        ]
        has_stock_context = any(kw in query_lower for kw in stock_context_keywords)
        ambiguous_company_names = {"target"}
        
        # 1. Extract stock symbols (multiple stocks possible)
        stocks_found = []
        for company_name, ticker in self.stock_symbol_map.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(company_name) + r'\b'
            if re.search(pattern, query_lower):
                # Avoid false positives like "emergency fund target" matching Target (TGT)
                if company_name in ambiguous_company_names and not has_stock_context:
                    continue
                stocks_found.append({
                    "symbol": ticker,
                    "company_name": company_name.title()
                })
        
        if stocks_found:
            entities["stocks"] = stocks_found
            # For backward compatibility, keep single stock_symbol
            entities["stock_symbol"] = stocks_found[0]["symbol"]
            entities["company_name"] = stocks_found[0]["company_name"]
        
        # 2. Extract amounts (Indian currency format with comprehensive patterns)
        amounts_found = []
        
        # Pattern 1: Crores (10cr, 5 crore, 10 crores, 5.5cr)
        crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)\b'
        for match in re.finditer(crore_pattern, query_lower):
            value = float(match.group(1))
            amounts_found.append({
                "value": value * 10000000,
                "formatted": f"₹{value * 10000000:,.0f}",
                "display": f"₹{value} crore" if value == 1 else f"₹{value} crores"
            })
        
        # Pattern 2: Lakhs (10L, 5 lakh, 10 lakhs, 5.5L)
        lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:l|lakh|lakhs)\b'
        for match in re.finditer(lakh_pattern, query_lower):
            value = float(match.group(1))
            amounts_found.append({
                "value": value * 100000,
                "formatted": f"₹{value * 100000:,.0f}",
                "display": f"₹{value} lakh" if value == 1 else f"₹{value} lakhs"
            })
        
        # Pattern 3: Thousands (10k, 5000, 10 thousand)
        thousand_pattern = r'(\d+(?:\.\d+)?)\s*(?:k|thousand|thousands)\b'
        for match in re.finditer(thousand_pattern, query_lower):
            value = float(match.group(1))
            amounts_found.append({
                "value": value * 1000,
                "formatted": f"₹{value * 1000:,.0f}",
                "display": f"₹{value}k"
            })
        
        # Pattern 4: Direct rupee amounts (₹50000, Rs 50000, Rs. 50,000)
        rupee_pattern = r'(?:₹|rs\.?|inr)\s*(\d+(?:,\d+)*(?:\.\d+)?)'
        for match in re.finditer(rupee_pattern, query_lower):
            value = float(match.group(1).replace(',', ''))
            amounts_found.append({
                "value": value,
                "formatted": f"₹{value:,.0f}",
                "display": f"₹{value:,.0f}"
            })
        
        # Pattern 5: Plain numbers with context (e.g., "invest 50000")
        # Only if no other amount patterns matched
        if not amounts_found:
            context_pattern = r'(?:invest|save|spend|earn|income|salary|worth|value|price|cost|budget)\s+(?:of\s+)?(\d+(?:,\d+)*(?:\.\d+)?)'
            for match in re.finditer(context_pattern, query_lower):
                value = float(match.group(1).replace(',', ''))
                # Only consider if value is reasonable (> 100)
                if value > 100:
                    amounts_found.append({
                        "value": value,
                        "formatted": f"₹{value:,.0f}",
                        "display": f"₹{value:,.0f}"
                    })
        
        if amounts_found:
            entities["amounts"] = amounts_found
            # For backward compatibility, keep single amount
            entities["amount"] = amounts_found[0]["value"]
            entities["amount_formatted"] = amounts_found[0]["formatted"]
        
        # 3. Extract dates (relative and absolute)
        dates_found = []
        
        # Relative dates
        relative_patterns = {
            r'\b(?:next|coming)\s+(\d+)\s+(?:day|days)\b': lambda d: datetime.now() + timedelta(days=int(d)),
            r'\b(?:next|coming)\s+(\d+)\s+(?:week|weeks)\b': lambda d: datetime.now() + timedelta(weeks=int(d)),
            r'\b(?:next|coming)\s+(\d+)\s+(?:month|months)\b': lambda d: datetime.now() + timedelta(days=int(d)*30),
            r'\b(?:next|coming)\s+(\d+)\s+(?:year|years)\b': lambda d: datetime.now() + timedelta(days=int(d)*365),
            r'\bnext\s+(?:month|week|year)\b': lambda d: datetime.now() + timedelta(days=30),
            r'\blast\s+(\d+)\s+(?:day|days)\b': lambda d: datetime.now() - timedelta(days=int(d)),
            r'\blast\s+(\d+)\s+(?:month|months)\b': lambda d: datetime.now() - timedelta(days=int(d)*30),
            r'\blast\s+(?:month|week|year)\b': lambda d: datetime.now() - timedelta(days=30),
        }
        
        for pattern, date_func in relative_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                try:
                    if match.groups():
                        date_obj = date_func(match.group(1))
                    else:
                        date_obj = date_func(None)
                    dates_found.append({
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "type": "relative",
                        "original": match.group(0)
                    })
                except:
                    pass
        
        # Absolute dates (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)
        absolute_patterns = [
            r'\b(\d{4})-(\d{2})-(\d{2})\b',  # YYYY-MM-DD
            r'\b(\d{2})/(\d{2})/(\d{4})\b',  # DD/MM/YYYY
            r'\b(\d{2})-(\d{2})-(\d{4})\b',  # DD-MM-YYYY
        ]
        
        for pattern in absolute_patterns:
            for match in re.finditer(pattern, query):
                dates_found.append({
                    "date": match.group(0),
                    "type": "absolute",
                    "original": match.group(0)
                })
        
        if dates_found:
            entities["dates"] = dates_found
        
        # 4. Extract financial goals
        goal_keywords = {
            "house": "HOME_PURCHASE",
            "home": "HOME_PURCHASE",
            "property": "HOME_PURCHASE",
            "real estate": "HOME_PURCHASE",
            "retire": "RETIREMENT",
            "retirement": "RETIREMENT",
            "pension": "RETIREMENT",
            "emergency": "EMERGENCY_FUND",
            "emergency fund": "EMERGENCY_FUND",
            "education": "EDUCATION",
            "college": "EDUCATION",
            "study": "EDUCATION",
            "loan": "DEBT_MANAGEMENT",
            "debt": "DEBT_MANAGEMENT",
            "emi": "DEBT_MANAGEMENT",
            "credit card": "DEBT_MANAGEMENT",
            "wedding": "WEDDING",
            "marriage": "WEDDING",
            "vacation": "VACATION",
            "travel": "VACATION",
            "car": "VEHICLE_PURCHASE",
            "vehicle": "VEHICLE_PURCHASE",
            "bike": "VEHICLE_PURCHASE",
        }
        
        goals_found = []
        for keyword, goal_type in goal_keywords.items():
            if keyword in query_lower:
                goals_found.append({
                    "type": goal_type,
                    "keyword": keyword
                })
        
        if goals_found:
            entities["goals"] = goals_found
            # For backward compatibility
            entities["goal"] = goals_found[0]["type"]
            
        # 5. Extract Age
        # Patterns: "age 25", "at 25", "25 years old", "age of 25", "i am 25"
        age_patterns = [
            r'\bage\s+(\d{2})\b',
            r'\b(\d{2})\s+years\s+old\b',
            r'\bat\s+(\d{2})\b',
            r'\bage\s+of\s+(\d{2})\b',
            r'\bi\s+am\s+(\d{2})\b'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                age = int(match.group(1))
                # Validate reasonable working age
                if 18 <= age <= 100:
                    entities["age"] = age
                    break
        
        return entities
    
    def _parse_query_entities(self, query: str) -> Dict[str, Any]:
        """
        Legacy method - calls extract_entities for backward compatibility.
        """
        return self.extract_entities(query)
