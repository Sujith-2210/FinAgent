"""
Evaluation Framework for FinAgent
Implements 50-query test suite and evaluation metrics.
Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time
import json
from enum import Enum
from loguru import logger
import numpy as np
from scipy import stats


class QueryCategory(Enum):
    """Categories for query classification."""
    PREDICTION = "prediction"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    RESEARCH = "research"
    GRAPH = "graph"
    PERSONAL = "personal"
    TAX = "tax"
    INSURANCE = "insurance"
    RETIREMENT = "retirement"
    EMERGENCY = "emergency"


@dataclass
class QueryTestCase:
    """A single test case in the evaluation suite."""
    query: str
    category: QueryCategory
    expected_agents: List[str]
    expected_keywords: List[str]
    max_latency_ms: float = 3000
    expected_confidence: str = "MEDIUM"


@dataclass
class EvaluationResult:
    """Result of evaluating a single query."""
    query: str
    passed: bool
    agents_used: List[str]
    latency_ms: float
    keywords_found: List[str]
    confidence: str
    errors: List[str] = field(default_factory=list)


@dataclass
class EvaluationSummary:
    """Summary of evaluation run."""
    total_queries: int
    passed: int
    failed: int
    pass_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    agent_coverage: Dict[str, int]
    category_pass_rates: Dict[str, float]
    timestamp: str


class QueryEvaluation:
    """
    Evaluation framework for testing agent responses.
    Implements Requirements 7.1-7.6.
    """
    
    def __init__(self):
        self.test_suite = self._create_test_suite()
        self.results: List[EvaluationResult] = []
        
    def _create_test_suite(self) -> List[QueryTestCase]:
        """
        Create 50-query test suite covering all agent capabilities.
        10 queries per major category (5 categories = 50 queries).
        Validates: Requirement 7.1
        """
        return [
            # === PREDICTION (10 queries) ===
            QueryTestCase(
                query="Predict HDFC Bank stock for next 30 days",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["prediction", "HDFC", "forecast"]
            ),
            QueryTestCase(
                query="What will be Reliance Industries price next month?",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["Reliance", "price", "prediction"]
            ),
            QueryTestCase(
                query="Forecast TCS stock using LSTM model",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["TCS", "LSTM", "forecast"]
            ),
            QueryTestCase(
                query="Predict Infosys share price for next 2 weeks",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["Infosys", "prediction"]
            ),
            QueryTestCase(
                query="Use Prophet to forecast Nifty 50 for 60 days",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["Prophet", "Nifty", "forecast"]
            ),
            QueryTestCase(
                query="What will Bitcoin price be next week?",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["Bitcoin", "price", "prediction"]
            ),
            QueryTestCase(
                query="Predict gold prices for next quarter",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["gold", "prediction"]
            ),
            QueryTestCase(
                query="Forecast Axis Bank share for 14 days",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["Axis", "forecast"]
            ),
            QueryTestCase(
                query="What will ICICI Bank stock be worth in a month?",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["ICICI", "prediction"]
            ),
            QueryTestCase(
                query="Predict Maruti Suzuki price movement",
                category=QueryCategory.PREDICTION,
                expected_agents=["code"],
                expected_keywords=["Maruti", "prediction"]
            ),
            
            # === ANALYSIS (10 queries) ===
            QueryTestCase(
                query="Analyze my portfolio performance",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["portfolio", "analysis", "performance"]
            ),
            QueryTestCase(
                query="What is my debt-to-income ratio?",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["debt", "income", "ratio"]
            ),
            QueryTestCase(
                query="Calculate my Sharpe ratio",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["Sharpe", "ratio"]
            ),
            QueryTestCase(
                query="How diversified is my investment portfolio?",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["diversified", "portfolio"]
            ),
            QueryTestCase(
                query="Analyze my savings rate",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["savings", "rate", "analysis"]
            ),
            QueryTestCase(
                query="What is my current net worth?",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["net worth"]
            ),
            QueryTestCase(
                query="Calculate my monthly expenses breakdown",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["expenses", "breakdown"]
            ),
            QueryTestCase(
                query="Show me my investment returns this year",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["investment", "returns"]
            ),
            QueryTestCase(
                query="Analyze my cash flow for the last 3 months",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["cash flow", "analysis"]
            ),
            QueryTestCase(
                query="What percentage of my income goes to EMIs?",
                category=QueryCategory.ANALYSIS,
                expected_agents=["finance"],
                expected_keywords=["EMI", "income", "percentage"]
            ),
            
            # === PLANNING (10 queries) ===
            QueryTestCase(
                query="How can I retire with 5 crores?",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["retire", "5 crores", "plan"]
            ),
            QueryTestCase(
                query="Plan my child's education fund for 20 lakhs",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["education", "fund", "plan"]
            ),
            QueryTestCase(
                query="How much should I save monthly for retirement?",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["save", "monthly", "retirement"]
            ),
            QueryTestCase(
                query="Create a financial plan for buying a house",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["house", "plan", "financial"]
            ),
            QueryTestCase(
                query="I want to save 1 lakh for vacation in 6 months",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["save", "lakh", "vacation"]
            ),
            QueryTestCase(
                query="Plan my emergency fund with 6 months expenses",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["emergency fund", "6 months"]
            ),
            QueryTestCase(
                query="How to become financially independent by 45?",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["financially independent", "45"]
            ),
            QueryTestCase(
                query="Create SIP plan to reach 2 crores in 15 years",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["SIP", "crores", "years"]
            ),
            QueryTestCase(
                query="Plan my daughter's wedding fund for 50 lakhs",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["wedding", "fund", "lakhs"]
            ),
            QueryTestCase(
                query="How much life insurance do I need?",
                category=QueryCategory.PLANNING,
                expected_agents=["finance"],
                expected_keywords=["life insurance", "need"]
            ),
            
            # === RESEARCH (10 queries) ===
            QueryTestCase(
                query="What are the best ELSS funds for tax saving?",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["ELSS", "tax saving"]
            ),
            QueryTestCase(
                query="Explain Section 80C deductions",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["80C", "deduction"]
            ),
            QueryTestCase(
                query="What is the current EPF interest rate?",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["EPF", "interest rate"]
            ),
            QueryTestCase(
                query="Tell me about NPS tax benefits",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["NPS", "tax", "benefits"]
            ),
            QueryTestCase(
                query="What are the latest RBI interest rate changes?",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["RBI", "interest rate"]
            ),
            QueryTestCase(
                query="Explain capital gains tax on mutual funds",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["capital gains", "mutual funds", "tax"]
            ),
            QueryTestCase(
                query="What is the difference between term and whole life insurance?",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["term", "whole life", "insurance"]
            ),
            QueryTestCase(
                query="How does PPF work?",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["PPF", "work"]
            ),
            QueryTestCase(
                query="What are the trending stocks in India today?",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["trending", "stocks", "India"]
            ),
            QueryTestCase(
                query="Explain the new income tax regime",
                category=QueryCategory.RESEARCH,
                expected_agents=["knowledge"],
                expected_keywords=["income tax", "regime"]
            ),
            
            # === PERSONAL (10 queries) ===
            QueryTestCase(
                query="Can I afford a 50 lakh house with my income?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["afford", "house", "income"]
            ),
            QueryTestCase(
                query="Should I prepay my home loan or invest in mutual funds?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["prepay", "home loan", "mutual funds"]
            ),
            QueryTestCase(
                query="How much can I spend on a car?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["spend", "car"]
            ),
            QueryTestCase(
                query="Am I saving enough for my age?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["saving", "enough", "age"]
            ),
            QueryTestCase(
                query="Should I switch to new tax regime?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["switch", "tax regime"]
            ),
            QueryTestCase(
                query="Is my credit score good enough for a loan?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["credit score", "loan"]
            ),
            QueryTestCase(
                query="Should I increase my SIP amount?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["increase", "SIP"]
            ),
            QueryTestCase(
                query="Can I take a 6 month sabbatical financially?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["sabbatical", "financially"]
            ),
            QueryTestCase(
                query="What should be my ideal asset allocation?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["asset allocation", "ideal"]
            ),
            QueryTestCase(
                query="How much should I budget for my wedding?",
                category=QueryCategory.PERSONAL,
                expected_agents=["finance"],
                expected_keywords=["budget", "wedding"]
            ),
        ]
    
    def evaluate(
        self, 
        query: str, 
        response: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Evaluate a single query response.
        Validates: Requirement 7.2
        
        Args:
            query: The user query
            response: The agent response containing agents_used, latency, etc.
            
        Returns:
            EvaluationResult with pass/fail status
        """
        # Find matching test case
        test_case = None
        for tc in self.test_suite:
            if tc.query == query:
                test_case = tc
                break
        
        errors = []
        agents_used = response.get("agents_used", [])
        latency_ms = response.get("latency_ms", 0)
        keywords_found = []
        confidence = response.get("confidence", "MEDIUM")
        response_text = response.get("response", "").lower()
        
        # Check keywords in response
        if test_case:
            for keyword in test_case.expected_keywords:
                if keyword.lower() in response_text:
                    keywords_found.append(keyword)
        
        # Evaluate pass/fail criteria
        passed = True
        
        # Check latency
        max_latency = test_case.max_latency_ms if test_case else 3000
        if latency_ms > max_latency:
            passed = False
            errors.append(f"Latency {latency_ms}ms exceeds max {max_latency}ms")
        
        # Check if expected agents were used
        if test_case:
            for expected in test_case.expected_agents:
                if expected not in agents_used:
                    # This is a warning, not a failure
                    logger.warning(f"Expected agent '{expected}' not in {agents_used}")
        
        # Check if any keywords were found
        if test_case and len(keywords_found) == 0:
            passed = False
            errors.append(f"No expected keywords found: {test_case.expected_keywords}")
        
        result = EvaluationResult(
            query=query,
            passed=passed,
            agents_used=agents_used,
            latency_ms=latency_ms,
            keywords_found=keywords_found,
            confidence=confidence,
            errors=errors
        )
        
        self.results.append(result)
        return result
    
    def run_full_evaluation(
        self, 
        agent_function: callable
    ) -> EvaluationSummary:
        """
        Run evaluation on all 50 test queries.
        
        Args:
            agent_function: Async function that takes query and returns response
            
        Returns:
            EvaluationSummary with pass rate and metrics
        """
        import asyncio
        
        self.results = []
        latencies = []
        agent_counts = {}
        category_results = {}
        
        for test_case in self.test_suite:
            start = time.time()
            
            try:
                # Run query
                response = asyncio.run(agent_function(test_case.query))
                latency_ms = (time.time() - start) * 1000
                response["latency_ms"] = latency_ms
                
            except Exception as e:
                response = {
                    "response": f"Error: {str(e)}",
                    "agents_used": [],
                    "latency_ms": (time.time() - start) * 1000,
                    "confidence": "LOW"
                }
            
            result = self.evaluate(test_case.query, response)
            latencies.append(result.latency_ms)
            
            # Track agent usage
            for agent in result.agents_used:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
            
            # Track category results
            cat = test_case.category.value
            if cat not in category_results:
                category_results[cat] = []
            category_results[cat].append(result.passed)
        
        # Calculate summary
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        category_pass_rates = {
            cat: sum(results) / len(results) if results else 0
            for cat, results in category_results.items()
        }
        
        return EvaluationSummary(
            total_queries=len(self.results),
            passed=passed,
            failed=failed,
            pass_rate=passed / len(self.results) if self.results else 0,
            avg_latency_ms=np.mean(latencies) if latencies else 0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0,
            agent_coverage=agent_counts,
            category_pass_rates=category_pass_rates,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def compare_with_benchmark(
        self,
        our_results: EvaluationSummary,
        benchmark_name: str = "baseline"
    ) -> Dict[str, Any]:
        """
        Compare results against benchmarks (Mint, ET Money).
        Validates: Requirement 7.3
        """
        # Simulated benchmark data
        benchmarks = {
            "Mint": {"pass_rate": 0.65, "avg_latency_ms": 2500},
            "ET Money": {"pass_rate": 0.70, "avg_latency_ms": 2200},
            "baseline": {"pass_rate": 0.30, "avg_latency_ms": 4000}
        }
        
        benchmark = benchmarks.get(benchmark_name, benchmarks["baseline"])
        
        return {
            "our_pass_rate": our_results.pass_rate,
            "benchmark_pass_rate": benchmark["pass_rate"],
            "pass_rate_improvement": our_results.pass_rate - benchmark["pass_rate"],
            "our_avg_latency_ms": our_results.avg_latency_ms,
            "benchmark_avg_latency_ms": benchmark["avg_latency_ms"],
            "latency_improvement": benchmark["avg_latency_ms"] - our_results.avg_latency_ms
        }
    
    def ab_test(
        self,
        group_a_results: List[EvaluationResult],
        group_b_results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        Perform A/B test with statistical significance.
        Validates: Requirement 7.4
        """
        a_scores = [1 if r.passed else 0 for r in group_a_results]
        b_scores = [1 if r.passed else 0 for r in group_b_results]
        
        # Calculate pass rates
        a_pass_rate = sum(a_scores) / len(a_scores) if a_scores else 0
        b_pass_rate = sum(b_scores) / len(b_scores) if b_scores else 0
        
        # Statistical significance (t-test)
        if len(a_scores) >= 2 and len(b_scores) >= 2:
            t_stat, p_value = stats.ttest_ind(a_scores, b_scores)
        else:
            t_stat, p_value = 0, 1.0
        
        return {
            "group_a_pass_rate": a_pass_rate,
            "group_b_pass_rate": b_pass_rate,
            "difference": b_pass_rate - a_pass_rate,
            "t_statistic": t_stat,
            "p_value": p_value,
            "is_significant": p_value < 0.05
        }


# Singleton instance
query_evaluator = QueryEvaluation()
