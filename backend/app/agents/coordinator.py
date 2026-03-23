"""
Agent Coordinator
Manages the multi-agent orchestration flow from user query to final response.

Flow:
1. User Query → Orchestrator (determines which agents to invoke)
2. Orchestrator Plan → Execute agents in order
3. Agent Outputs → Explainability Agent (synthesize response)
4. Final Response → User

Key Responsibilities:
- Initialize and sync MCP context
- Execute orchestrator to get execution plan
- Invoke agents according to plan with proper context
- Aggregate results through explainability agent
- Return structured response with reasoning trace
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.agents.orchestrator import OrchestratorAgent
from app.agents.finance import FinanceReasoningAgent
from app.agents.knowledge import KnowledgeAgent
from app.agents.explainability import ExplainabilityAgent
from app.agents.alert import AlertAgent
from app.agents.research import DeepResearchAgent
from app.agents.graph_reasoning import GraphReasoningAgent
from app.agents.code import CodeAgent
from app.agents.base import AgentResult
from app.mcp.context_manager import ContextManager, ContextLayer
from app.mcp.fi_mcp import FiMCPService
from app.mcp.client import MCPClientManager
from app.mcp.firecrawl import get_firecrawl_service
from app.services.tavily_service import get_tavily_service
from app.services.vector_db import VectorDBService
from app.services.graph_db import GraphDBService
from app.services.rag_service import GraphRAGService
from app.services.sandbox import SandboxService
from app.services.agent_registry import is_agent_enabled
from app.privacy.audit_log import audit_logger
from app.privacy.enhancer import privacy_enhancer


class AgentCoordinator:
    """
    Coordinates multi-agent execution for a user query.
    
    This is the central orchestration engine that:
    - Manages the agent execution flow
    - Handles context access
    - Aggregates results
    - Produces explainable outputs
    """
    
    def __init__(self, mcp_manager: MCPClientManager):
        self.mcp_manager = mcp_manager
        
        # Initialize services
        self.fi_mcp_service = FiMCPService(mcp_manager)
        self.context_manager = ContextManager(self.fi_mcp_service)
        
        # Initialize agents
        self.orchestrator = OrchestratorAgent()
        
        # Create knowledge agent with Firecrawl service for web data
        knowledge_agent = KnowledgeAgent()
        knowledge_agent.set_firecrawl_service(get_firecrawl_service())
        
        
        # Initialize Tavily service for web search
        from app.config import get_settings
        settings = get_settings()
        if settings.tavily_api_key:
            tavily_service = get_tavily_service(settings.tavily_api_key)
            knowledge_agent.set_tavily_service(tavily_service)
            logger.info("Tavily service initialized and injected into knowledge agent")
        else:
            logger.warning("Tavily API key not configured - web search will use Firecrawl only")
        # Initialize Services (Sprint 3: GraphRAG) with graceful degradation.
        self.vector_db = None
        self.graph_db = None
        self.rag_service = None
        try:
            self.vector_db = VectorDBService()
            self.graph_db = GraphDBService()
            self.rag_service = GraphRAGService(self.vector_db, self.graph_db)
            knowledge_agent.set_rag_service(self.rag_service)
        except Exception as e:
            logger.warning(f"GraphRAG initialization failed; continuing without RAG: {e}")
            knowledge_agent.set_rag_service(None)
        
        # Initialize Deep Research Agent (Sprint 2)
        deep_research_agent = DeepResearchAgent()
        deep_research_agent.set_knowledge_agent(knowledge_agent)

        # Initialize Graph Reasoning Agent (Sprint 3)
        graph_reasoning_agent = GraphReasoningAgent()
        if hasattr(self, 'graph_db'):
            graph_reasoning_agent.set_graph_db(self.graph_db)
            
        # Initialize Code Agent (Sprint 4)
        self.sandbox_service = SandboxService()
        code_agent = CodeAgent(self.sandbox_service)
        
        self.agents = {
            "orchestrator": self.orchestrator,
            "finance_reasoning": FinanceReasoningAgent(),
            "knowledge": knowledge_agent,
            "deep_research": deep_research_agent,
            "graph_reasoning": graph_reasoning_agent,
            "code": code_agent,
            "explainability": ExplainabilityAgent(),
            "alert": AlertAgent(),
        }
        
        # Execution state
        self._current_session_id: Optional[str] = None
        self._agent_traces: List[Dict[str, Any]] = []
        self._last_agent_traces: List[Dict[str, Any]] = []
        self._last_final_output: Dict[str, Any] = {}
        self._last_response_timestamp: Optional[datetime] = None
        
        # TradingAgents integration (lazy initialization)
        self._trading_service = None
        self._trading_service_init_attempted = False
    
    async def initialize_session(self, session_id: str):
        """
        Initialize a new session with fresh context.
        """
        self._current_session_id = session_id
        self._agent_traces = []
        
        # Initialize context
        await self.context_manager.initialize_context(session_id)
        # Sync initial data from MCP
        try:
            await self.context_manager.sync_from_fi_mcp()
        except Exception as e:
            logger.warning(f"Initial context sync failed: {e}")
        
        logger.info(f"Session initialized: {session_id}")
    
    async def process_query(
        self, 
        query: str, 
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent system.
        
        Args:
            query: User's natural language query
            session_id: Optional session ID for context continuity
            
        Returns:
            Complete response with message, agents involved, reasoning, and metrics
        """
        start_time = datetime.utcnow()
        
        # Ensure session is initialized
        if session_id and session_id != self._current_session_id:
            await self.initialize_session(session_id)
        elif not self._current_session_id:
            await self.initialize_session(session_id or "default")

        # Meta-queries should explain the previous recommendation without rerunning all agents.
        if self._is_reasoning_trace_query(query):
            return self._build_reasoning_trace_response()
        if self._is_assumptions_query(query):
            return self._build_assumptions_response()
        
        self._agent_traces = []
        
        try:
            # Step 1: Get execution plan from orchestrator
            logger.info("Step 1: Getting execution plan from orchestrator")
            execution_plan = await self._get_execution_plan(query)
            
            # Step 2: Execute agents according to plan
            logger.info(f"Step 2: Executing {len(execution_plan)} agents")
            agent_results = await self._execute_agents(execution_plan, query)
            
            # Step 3: Generate final response through explainability
            logger.info("Step 3: Generating final response")
            final_response = await self._generate_response(query, agent_results)
            
            # Calculate execution time
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            response_timestamp = datetime.utcnow()
            self._last_agent_traces = list(self._agent_traces)
            self._last_final_output = dict(final_response)
            self._last_response_timestamp = response_timestamp
            
            return {
                "message": final_response["summary"],
                "agents_involved": [trace["agent"] for trace in self._agent_traces],
                "agent_contributions": self._format_contributions(),
                "metrics_used": self._get_metrics_used(),
                "reasoning_trace": self._agent_traces,
                "actions": final_response.get("actions", []),
                "execution_time_ms": execution_time_ms,
                "timestamp": response_timestamp
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "message": f"I encountered an issue while processing your request. Please try again.",
                "agents_involved": ["orchestrator"],
                "agent_contributions": [],
                "metrics_used": {},
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def _get_execution_plan(self, query: str) -> List[Dict[str, Any]]:
        """
        Get execution plan from orchestrator agent.
        """
        # Build context summary for orchestrator
        context_summary = self._get_context_summary()
        
        # Run orchestrator
        orchestrator_input = {
            "user_query": query,
            "available_agents": list(self.agents.keys()),
            "context_summary": context_summary
        }
        
        # Log orchestrator invocation to audit trail
        audit_logger.log_agent_invocation(
            agent_name="orchestrator",
            query=query,
            user_id=self._current_session_id or "default",
            context_layers=["user_goals_context"],
            reasoning="Query analysis and execution plan creation",
            epsilon_consumed=0.0
        )
        
        result = await self.orchestrator.run(orchestrator_input)
        
        # Record trace
        self._agent_traces.append({
            "agent": "orchestrator",
            "input_summary": f"Query: {query[:50]}...",
            "output_summary": f"Plan: {len(result.output.get('execution_plan', []))} agents",
            "reasoning_steps": result.reasoning_steps,
            "confidence": result.confidence,
            "execution_time_ms": result.execution_time_ms
        })
        
        return result.output.get("execution_plan", [])
    
    async def _execute_agents(
        self, 
        execution_plan: List[Dict[str, Any]], 
        query: str
    ) -> Dict[str, AgentResult]:
        """
        Execute agents according to the execution plan.
        """
        results = {}
        
        for step in execution_plan:
            agent_name = step["agent"]
            context_required = step.get("context_required", [])
            
            # Skip orchestrator (already executed)
            if agent_name == "orchestrator":
                continue
            
            # Skip explainability (will be executed last)
            if agent_name == "explainability":
                continue

            if not is_agent_enabled(agent_name):
                logger.info(f"Skipping disabled agent: {agent_name}")
                continue
            
            agent = self.agents.get(agent_name)
            
            # Special handling for TradingAgents pipeline
            if agent_name == "trading_analysis":
                trading_result = await self._execute_trading_analysis(step, query)
                if trading_result:
                    results[agent_name] = trading_result
                    self._agent_traces.append({
                        "agent": "trading_analysis",
                        "input_summary": f"Stock: {step.get('input', {}).get('stock_symbol', 'N/A')}",
                        "output_summary": f"Recommendation: {trading_result.output.get('recommendation', 'N/A')}",
                        "reasoning_steps": trading_result.reasoning_steps,
                        "context_accessed": [],
                        "confidence": trading_result.confidence,
                        "execution_time_ms": trading_result.execution_time_ms
                    })
                continue
            
            if not agent:
                logger.warning(f"Unknown agent: {agent_name}")
                continue
            
            # Store current step for access by _build_agent_input
            self._current_step = step
            
            # Build input for agent
            agent_input = await self._build_agent_input(agent_name, query, context_required, results)
            
            # Log agent invocation to audit trail
            reasoning = step.get("reasoning", f"Agent selected for {agent_name} capability")
            audit_logger.log_agent_invocation(
                agent_name=agent_name,
                query=query,
                user_id=self._current_session_id or "default",
                context_layers=context_required,
                reasoning=reasoning,
                epsilon_consumed=0.0  # Will be updated when DP is implemented
            )
            
            # Execute agent
            logger.info(f"Executing agent: {agent_name}")
            result = await agent.run(agent_input)
            results[agent_name] = result
            
            # Record trace
            self._agent_traces.append({
                "agent": agent_name,
                "input_summary": f"Context layers: {context_required}",
                "output_summary": self._summarize_output(result.output),
                "reasoning_steps": result.reasoning_steps,
                "context_accessed": result.context_accessed,
                "confidence": result.confidence,
                "execution_time_ms": result.execution_time_ms
            })
        
        return results
    
    async def _build_agent_input(
        self, 
        agent_name: str, 
        query: str,
        context_required: List[str],
        previous_results: Dict[str, AgentResult]
    ) -> Dict[str, Any]:
        """
        Build input for a specific agent based on context requirements.
        """
        input_data = {"query": query}
        
        if agent_name == "finance_reasoning":
            # Get both masked (for context) and RAW (for personalized calculations) financial data
            financial_layer = self.context_manager.get_layer(
                ContextLayer.USER_FINANCIAL_CONTEXT, 
                agent_name
            )
            signals_layer = self.context_manager.get_layer(
                ContextLayer.TRANSACTIONAL_SIGNALS,
                agent_name
            )
            
            # Get RAW values for deeply personalized agent reasoning
            raw_values = self.context_manager.get_raw_financial_values(agent_name)
            
            input_data["financial_context"] = {
                # Raw values for precise calculations (backend-only, never sent to frontend)
                "monthly_income": raw_values.get("monthly_income"),
                "monthly_expenses": raw_values.get("monthly_expenses"),
                "net_worth": raw_values.get("net_worth"),
                "total_assets": raw_values.get("total_assets"),
                "total_liabilities": raw_values.get("total_liabilities"),
                "credit_score": raw_values.get("credit_score"),
                "credit_utilization": raw_values.get("credit_utilization"),
                "savings_rate": raw_values.get("savings_rate"),
                "monthly_emi": raw_values.get("monthly_emi"),
                # Also keep bands for context-aware responses
                "income_band": financial_layer.get("data", {}).get("income_profile", {}).get("monthly_income_band") if financial_layer else None,
                "expense_pattern": signals_layer.get("signals", {}).get("spending_pattern") if signals_layer else None,
                "net_worth_band": financial_layer.get("data", {}).get("assets_profile", {}).get("net_worth_band") if financial_layer else None,
                "debt_intensity": financial_layer.get("data", {}).get("liabilities_profile", {}).get("debt_intensity") if financial_layer else None,
                "credit_score_band": financial_layer.get("data", {}).get("credit_profile", {}).get("credit_score_band") if financial_layer else None,
                "loan_types": financial_layer.get("data", {}).get("liabilities_profile", {}).get("loan_types", []) if financial_layer else [],
                "asset_classes": financial_layer.get("data", {}).get("assets_profile", {}).get("asset_classes", []) if financial_layer else [],
            }
            
            # Extract demographics
            demographics = financial_layer.get("data", {}).get("demographics_profile", {}) if financial_layer else {}
            input_data["user_age"] = demographics.get("age")
            input_data["risk_profile"] = demographics.get("risk_profile", "MODERATE")
            
            input_data["user_goal"] = self._extract_goal_from_query(query)

            # Carry orchestrator-identified structured inputs to finance agent.
            if hasattr(self, "_current_step") and self._current_step:
                step_input = self._current_step.get("input", {})
                if step_input.get("target_amount"):
                    input_data["target_amount"] = step_input["target_amount"]
                if step_input.get("specific_goal"):
                    input_data["specific_goal"] = step_input["specific_goal"]
            
        elif agent_name == "knowledge":
            input_data["query_topic"] = query
            
        elif agent_name == "alert":
            # Get signals from finance agent if available
            finance_result = previous_results.get("finance_reasoning")
            if finance_result:
                input_data["signals"] = finance_result.output.get("signals_detected", [])
            else:
                input_data["signals"] = []
            
            # Add context for pattern detection
            input_data["context"] = {
                "user_financial_context": self.context_manager.get_layer(
                    ContextLayer.USER_FINANCIAL_CONTEXT,
                    agent_name
                )
            }
        
        elif agent_name == "graph_reasoning":
            input_data["query_topic"] = query
            input_data["analysis_type"] = "network"
            # Pass stock/company info if available from orchestrator
            if hasattr(self, '_current_step') and self._current_step:
                step_input = self._current_step.get("input", {})
                if step_input.get("analysis_type"):
                    input_data["analysis_type"] = step_input["analysis_type"]
        
        elif agent_name == "deep_research":
            input_data["research_topic"] = query
            input_data["focus_areas"] = []
            # Extract focus areas from orchestrator step input if available
            if hasattr(self, '_current_step') and self._current_step:
                step_input = self._current_step.get("input", {})
                if step_input.get("focus_areas"):
                    input_data["focus_areas"] = step_input["focus_areas"]
        
        elif agent_name == "code":
            input_data["query_topic"] = query
            # Pass stock_symbol if it was extracted by orchestrator
            # The symbol comes from the execution plan step's "input" dict
            if hasattr(self, '_current_step') and self._current_step:
                step_input = self._current_step.get("input", {})
                if step_input.get("stock_symbol"):
                    input_data["stock_symbol"] = step_input["stock_symbol"]
                    logger.info(f"Passing stock_symbol to code agent: {step_input['stock_symbol']}")
            
            # Pass historical data from knowledge agent if available (for predictions)
            knowledge_result = previous_results.get("knowledge")
            if knowledge_result and knowledge_result.output:
                historical_data = knowledge_result.output.get("historical_data")
                if historical_data:
                    input_data["historical_data"] = historical_data
                    logger.info(f"Passing historical data to code agent: {historical_data.get('data_points', 0)} data points")
            
        return input_data
    
    async def _generate_response(
        self, 
        query: str,
        agent_results: Dict[str, AgentResult]
    ) -> Dict[str, Any]:
        """
        Generate final response through explainability agent.
        """
        explainability = self.agents["explainability"]
        
        # Get code output if available
        code_agent_result = agent_results.get("code", AgentResult(success=False, output={}))
        code_output = code_agent_result.output
        
        # Build input for explainability - include the original query
        
        # DEBUG: Check what knowledge agent returned
        knowledge_result = agent_results.get("knowledge", AgentResult(success=False, output={}))
        logger.info(f"COORDINATOR DEBUG: knowledge_result.success={knowledge_result.success}, knowledge_result.output={knowledge_result.output}")
        
        explainability_input = {
            "user_query": query,
            "agent_outputs": {
                "finance_reasoning": agent_results.get("finance_reasoning", AgentResult(success=False, output={})).output,
                "knowledge": knowledge_result.output,
                "code": code_output,
                "alert": agent_results.get("alert", AgentResult(success=False, output={})).output,
                "trading_analysis": agent_results.get("trading_analysis", AgentResult(success=False, output={})).output,
                "graph_reasoning": agent_results.get("graph_reasoning", AgentResult(success=False, output={})).output,
                "deep_research": agent_results.get("deep_research", AgentResult(success=False, output={})).output,
                "execution_trace": self._agent_traces,
            },
            "confidence_level": self._aggregate_confidence(agent_results),
            # Include raw financial context for personalized response generation
            "user_financial_context": self.context_manager.get_raw_financial_values("explainability"),
        }
        
        result = await explainability.run(explainability_input)
        
        # Log if images/actions present
        if code_output.get("images"):
            logger.info(f"Processing {len(code_output['images'])} generated chart(s)")
        if result.output.get("actions"):
            logger.info(f"Response includes {len(result.output['actions'])} action(s)")
        
        # Record trace
        self._agent_traces.append({
            "agent": "explainability",
            "input_summary": f"Synthesizing {len(agent_results)} agent outputs",
            "output_summary": result.output.get("summary", "")[:100],
            "reasoning_steps": result.reasoning_steps,
            "confidence": result.confidence,
            "execution_time_ms": result.execution_time_ms
        })
        
        return result.output
    
    def _get_context_summary(self) -> Dict[str, bool]:
        """
        Get a summary of available context for orchestrator.
        """
        context = self.context_manager._context
        if not context:
            return {}
        
        financial = context.user_financial_context.get("data", {})
        
        return {
            "has_assets": bool(financial.get("assets_profile")),
            "has_liabilities": bool(financial.get("liabilities_profile")),
            "has_credit_data": bool(financial.get("credit_profile")),
            "has_goals": bool(context.user_goals_context.get("goals")),
            "has_transactions": bool(context.transactional_signals.get("signals")),
        }
    
    def _extract_goal_from_query(self, query: str) -> Optional[str]:
        """
        Extract financial goal from user query.
        """
        query_lower = query.lower()
        
        goal_keywords = {
            "retirement": "RETIREMENT",
            "retire": "RETIREMENT",
            "emergency": "EMERGENCY_FUND",
            "save": "SAVINGS",
            "saving": "SAVINGS",
            "invest": "INVESTMENT",
            "debt": "DEBT_REDUCTION",
            "loan": "DEBT_REDUCTION",
            "education": "EDUCATION",
            "house": "HOME_PURCHASE",
            "home": "HOME_PURCHASE",
        }
        
        for keyword, goal in goal_keywords.items():
            if keyword in query_lower:
                return goal
        
        return None
    
    def _aggregate_confidence(self, results: Dict[str, AgentResult]) -> str:
        """
        Aggregate confidence levels from multiple agents.
        """
        confidence_values = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        
        if not results:
            return "LOW"
        
        total = sum(
            confidence_values.get(r.confidence, 1) 
            for r in results.values() 
            if r.success
        )
        count = sum(1 for r in results.values() if r.success)
        
        if count == 0:
            return "LOW"
        
        avg = total / count
        
        if avg >= 2.5:
            return "HIGH"
        elif avg >= 1.5:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _format_contributions(self) -> List[Dict[str, Any]]:
        """
        Format agent traces into contributions for API response.
        """
        return [
            {
                "agent": trace["agent"],
                "reasoning": trace["reasoning_steps"],
                "confidence": trace["confidence"]
            }
            for trace in self._agent_traces
        ]
    
    def _get_metrics_used(self) -> Dict[str, Any]:
        """
        Get summary of metrics and context used in processing.
        """
        all_context = set()
        for trace in self._agent_traces:
            all_context.update(trace.get("context_accessed", []))
        
        return {
            "context_layers_accessed": list(all_context),
            "privacy_level": "HIGH",
            "agents_executed": len(self._agent_traces),
            "total_reasoning_steps": sum(
                len(trace.get("reasoning_steps", [])) 
                for trace in self._agent_traces
            )
        }

    def _is_reasoning_trace_query(self, query: str) -> bool:
        """Detect meta-queries asking for agent reasoning trace."""
        q = query.lower()
        trace_keywords = [
            "reasoning trace", "which agents were used", "which agents are used",
            "show the trace", "agent trace", "why for this recommendation",
            "how did you arrive", "show your reasoning"
        ]
        return any(k in q for k in trace_keywords)

    def _is_assumptions_query(self, query: str) -> bool:
        """Detect meta-queries asking assumptions and missing data."""
        q = query.lower()
        assumption_keywords = ["what assumptions", "assumptions are you making", "additional data", "improve this advice", "what data would improve"]
        return any(k in q for k in assumption_keywords)

    def _build_reasoning_trace_response(self) -> Dict[str, Any]:
        """Return a human-readable trace of the most recent recommendation."""
        if not self._last_agent_traces:
            return {
                "message": "I don't have a prior recommendation in this session yet. Ask a finance question first, then I can show the full reasoning trace.",
                "agents_involved": ["orchestrator"],
                "agent_contributions": [],
                "metrics_used": {},
                "reasoning_trace": [],
                "actions": [],
                "execution_time_ms": 0.0,
                "timestamp": datetime.utcnow(),
            }

        lines = []
        for idx, trace in enumerate(self._last_agent_traces, 1):
            reasoning_steps = trace.get("reasoning_steps", []) or []
            why = reasoning_steps[0] if reasoning_steps else trace.get("input_summary", "Contributed to final recommendation")
            lines.append(f"{idx}. {trace.get('agent', 'unknown')}: {why}")

        message = "Reasoning trace for your latest recommendation:\n" + "\n".join(lines)

        return {
            "message": message,
            "agents_involved": [trace.get("agent", "unknown") for trace in self._last_agent_traces],
            "agent_contributions": [
                {
                    "agent": trace.get("agent", "unknown"),
                    "reasoning": trace.get("reasoning_steps", []),
                    "confidence": trace.get("confidence", "MEDIUM"),
                }
                for trace in self._last_agent_traces
            ],
            "metrics_used": {
                "source": "last_recommendation_trace",
                "last_response_timestamp": self._last_response_timestamp.isoformat() if self._last_response_timestamp else None,
            },
            "reasoning_trace": self._last_agent_traces,
            "actions": [],
            "execution_time_ms": 0.0,
            "timestamp": datetime.utcnow(),
        }

    def _build_assumptions_response(self) -> Dict[str, Any]:
        """Return assumptions used in the last recommendation and data that would improve it."""
        assumptions_used = self._last_final_output.get("assumptions_used", []) if self._last_final_output else []
        if not assumptions_used:
            assumptions_used = [
                "Income/expense bands may be inferred from masked context rather than exact values",
                "Debt burden is assessed from available obligations summary",
                "Recommendations prioritize cash-flow safety before aggressive growth",
            ]

        additional_data = [
            "Exact monthly essential expenses (rent, EMIs, insurance, groceries)",
            "Loan-wise details: outstanding, interest rate, tenure, and prepayment penalty",
            "Current portfolio allocation by asset class and instrument",
            "Goal deadlines and required corpus per goal",
            "Risk tolerance and income stability horizon (next 12-24 months)",
        ]

        message = (
            "Assumptions currently used:\n- " + "\n- ".join(assumptions_used[:6]) +
            "\n\nAdditional data that would improve advice quality:\n- " + "\n- ".join(additional_data)
        )

        involved_agents = [trace.get("agent", "unknown") for trace in self._last_agent_traces] if self._last_agent_traces else ["orchestrator"]
        contributions = [
            {
                "agent": "explainability",
                "reasoning": ["Summarized assumptions and listed highest-impact missing inputs"],
                "confidence": "HIGH",
            }
        ]

        return {
            "message": message,
            "agents_involved": involved_agents,
            "agent_contributions": contributions,
            "metrics_used": {
                "source": "last_recommendation_assumptions",
                "assumptions_count": len(assumptions_used),
            },
            "reasoning_trace": self._last_agent_traces,
            "actions": [],
            "execution_time_ms": 0.0,
            "timestamp": datetime.utcnow(),
        }
    
    def _summarize_output(self, output: Dict[str, Any]) -> str:
        """
        Create a brief summary of agent output.
        """
        if "metrics" in output:
            return f"Metrics: {output['metrics']}"
        if "facts" in output:
            return f"Retrieved {len(output['facts'])} facts"
        if "alerts" in output:
            return f"Generated {len(output['alerts'])} alerts"
        if "summary" in output:
            return output["summary"][:100]
        return str(output)[:100]

    async def _execute_trading_analysis(
        self, 
        step: Dict[str, Any], 
        query: str
    ) -> Optional[AgentResult]:
        """
        Execute the TradingAgents pipeline for stock analysis.
        
        This runs the full multi-agent flow:
        Analysts → Bull/Bear Debate → Trader Decision → Risk Assessment
        
        Returns an AgentResult with the trading analysis output.
        """
        from datetime import datetime
        start_time = datetime.utcnow()
        
        stock_symbol = step.get("input", {}).get("stock_symbol", "")
        if not stock_symbol:
            logger.warning("Trading analysis requested but no stock symbol provided")
            return None
        
        # Lazy initialization of TradingAnalysisService
        if not self._trading_service_init_attempted:
            self._trading_service_init_attempted = True
            try:
                from app.services.trading_analysis_service import get_trading_analysis_service
                self._trading_service = get_trading_analysis_service()
                await self._trading_service.initialize()
            except Exception as e:
                logger.warning(f"TradingAnalysisService initialization failed: {e}")
                self._trading_service = None
        
        if self._trading_service is None or not self._trading_service.is_available:
            logger.info(f"TradingAgents not available - skipping trading analysis for {stock_symbol}")
            return AgentResult(
                success=False,
                output={
                    "error": "TradingAgents pipeline not available",
                    "recommendation": "UNABLE_TO_ANALYZE",
                    "reasoning": "TradingAgents dependencies not installed. Using standard analysis agents."
                },
                reasoning_steps=["TradingAgents unavailable"],
                confidence="LOW",
                execution_time_ms=0
            )
        
        try:
            logger.info(f"🔍 Running TradingAgents pipeline for {stock_symbol}")
            result = await self._trading_service.analyze_stock(
                ticker=stock_symbol,
                analysis_date=datetime.now().strftime("%Y-%m-%d")
            )
            
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return AgentResult(
                success=result.get("success", False),
                output=result,
                reasoning_steps=[
                    f"Ran TradingAgents analysis for {stock_symbol}",
                    f"Recommendation: {result.get('recommendation', 'N/A')}",
                    f"Confidence: {result.get('confidence', 'N/A')}",
                ],
                confidence=result.get("confidence", "MEDIUM"),
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            logger.error(f"TradingAgents analysis failed for {stock_symbol}: {e}")
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            return AgentResult(
                success=False,
                output={"error": str(e), "recommendation": "UNABLE_TO_ANALYZE"},
                reasoning_steps=[f"TradingAgents failed: {e}"],
                confidence="LOW",
                execution_time_ms=execution_time_ms
            )
