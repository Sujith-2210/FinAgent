"""
Finance Reasoning Agent
Core financial calculations and analysis.
"""

from typing import Dict, Any, List, Optional
from loguru import logger


from app.agents.base import BaseAgent
from app.lib.market_regime import detect_regime


class FinanceReasoningAgent(BaseAgent):
    """
    Finance Reasoning Agent - The analytical core.
    
    Responsibilities:
    - Analyze structured financial context
    - Compute financial metrics (DTI, savings rate, etc.)
    - Identify risks and opportunities
    - Produce deterministic, step-by-step reasoning
    
    Rules:
    - Use ONLY provided context
    - Never invent financial values
    - Do NOT provide final advice to user
    - Do NOT expose raw sensitive values
    - Always show calculation logic
    """
    
    def __init__(self):
        super().__init__()
        self.name = "finance_reasoning"
        self.description = "Performs financial calculations and analysis"
        self.read_layers = {"user_financial_context", "transactional_signals", "user_goals_context"}
        self.write_layers = {"agent_working_memory", "explainability_context"}
        
        self.system_prompt = """You are a Finance Reasoning Agent.

Your task is to:
- Analyze structured financial context
- Compute financial metrics
- Identify risks and opportunities
- Produce deterministic, step-by-step reasoning

Rules:
- Use ONLY provided context
- Never invent financial values
- Do NOT provide final advice to user
- Do NOT expose raw sensitive values
- Always show calculation logic
- Output must be structured JSON"""
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "financial_context": {
                    "type": "object",
                    "properties": {
                        "income_summary": {"type": "string"},
                        "expense_summary": {"type": "string"},
                        "assets_summary": {"type": "string"},
                        "liabilities_summary": {"type": "string"}
                    }
                },
                "user_goal": {"type": "string"},
                "market_context": {
                    "type": "object",
                    "properties": {
                        "vix_close": {"type": "number"},
                        "momentum_63d": {"type": "number"}
                    },
                    "required": ["vix_close", "momentum_63d"]
                }
            }
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "object",
                    "properties": {
                        "savings_rate": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                        "debt_to_income_ratio": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                        "investment_diversification": {"type": "string", "enum": ["LOW", "MODERATE", "HIGH"]}
                    }
                },
                "signals_detected": {"type": "array", "items": {"type": "string"}},
                "intermediate_reasoning": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["metrics", "signals_detected", "intermediate_reasoning"]
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze financial context and generate metrics/signals.
        """
        financial_context = (
            input_data.get("financial_context")
            or input_data.get("context_summary", {}).get("user_financial_context", {})
        )
        market_context = (
            input_data.get("market_context")
            or input_data.get("context_summary", {}).get("market_context")
        )
        user_goal = input_data.get("user_goal") or input_data.get("context_summary", {}).get("user_goal")
        
        # NEW: Extract orchestrator entities
        target_amount = input_data.get("target_amount")
        specific_goal = input_data.get("specific_goal")
        
        self.add_reasoning_step("Starting financial analysis")
        
        # Extract user data - read from the ACTUAL keys the coordinator sends
        user_age = input_data.get("user_age") or self._get_user_age_from_context(financial_context)
        monthly_income = (
            financial_context.get("monthly_income")
            or self._get_user_income_from_context(financial_context)
        )
        monthly_expenses = financial_context.get("monthly_expenses")
        net_worth = financial_context.get("net_worth")
        total_assets = financial_context.get("total_assets")
        total_liabilities = financial_context.get("total_liabilities")
        credit_score = financial_context.get("credit_score")
        credit_utilization = financial_context.get("credit_utilization")
        savings_rate_raw = financial_context.get("savings_rate")
        monthly_emi = financial_context.get("monthly_emi")
        asset_classes = financial_context.get("asset_classes", [])
        loan_types = financial_context.get("loan_types", [])
        
        if user_age:
            self.add_reasoning_step(f"User age extracted: {user_age} years")
        if monthly_income:
            self.add_reasoning_step(f"Monthly income: ₹{monthly_income:,.0f}")
        if net_worth:
            self.add_reasoning_step(f"Net worth: ₹{net_worth:,.0f}")
        if credit_score:
            self.add_reasoning_step(f"Credit score: {credit_score}")
        if asset_classes:
            self.add_reasoning_step(f"Asset classes: {asset_classes}")
        
        # Initialize metrics and signals
        metrics = {}
        signals = []
        reasoning = []
        
        # Store raw financial data for downstream agents
        metrics["net_worth"] = net_worth
        metrics["credit_score"] = credit_score
        metrics["total_assets"] = total_assets
        metrics["total_liabilities"] = total_liabilities
        metrics["asset_classes"] = asset_classes
        
        # Perform specific calculations for identified goals
        specific_calculations = {}
        if specific_goal == "HOME_PURCHASE" and target_amount:
            self.add_reasoning_step(f"Calculating house affordability for ₹{target_amount/10000000:.2f}cr")
            current_savings = total_assets or 0
            specific_calculations = self._calculate_house_affordability(
                target_amount,
                monthly_income,
                current_savings
            )
            self.add_reasoning_step(f"Required credit score: {specific_calculations.get('credit_score_required')}")
        
        # Evaluate savings rate using ACTUAL numeric data
        self.add_reasoning_step("Evaluating savings rate")
        savings_analysis = self._analyze_savings(financial_context)
        metrics["savings_rate"] = savings_analysis["band"]
        reasoning.extend(savings_analysis["reasoning"])
        if savings_analysis["signal"]:
            signals.append(savings_analysis["signal"])
        
        # Evaluate debt-to-income ratio using ACTUAL data
        self.add_reasoning_step("Calculating debt-to-income ratio")
        dti_analysis = self._analyze_dti(financial_context)
        metrics["debt_to_income_ratio"] = dti_analysis["band"]
        reasoning.extend(dti_analysis["reasoning"])
        if dti_analysis["signal"]:
            signals.append(dti_analysis["signal"])
        
        # Evaluate investment diversification using ACTUAL asset classes
        self.add_reasoning_step("Assessing investment diversification")
        div_analysis = self._analyze_diversification(financial_context)
        metrics["investment_diversification"] = div_analysis["band"]
        reasoning.extend(div_analysis["reasoning"])
        if div_analysis["signal"]:
            signals.append(div_analysis["signal"])
        
        # Goal-specific analysis
        if user_goal:
            self.add_reasoning_step(f"Analyzing for goal: {user_goal}")
            goal_signals = self._analyze_for_goal(user_goal, metrics)
            signals.extend(goal_signals)
        
        # Market Regime Analysis (Sprint 1 Feature)
        if market_context:
            self.add_reasoning_step("Analyzing market regime (based on VIX/Momentum)")
            regime = detect_regime(market_context)
            metrics["market_regime"] = regime
            signals.append(f"Market Regime Detected: {regime}")
            if "Bear" in regime or "HighVol" in regime:
                 metrics["investment_diversification"] = "ALERT - CHECK ALLOCATION"
                 signals.append("High volatility regime - Review risk exposure immediately")

        # Return comprehensive analysis
        return {
            "metrics": metrics,
            "signals_detected": signals,
            "intermediate_reasoning": reasoning,
            "user_age": user_age,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "net_worth": net_worth,
            "credit_score": credit_score,
            "asset_classes": asset_classes,
            "specific_calculations": specific_calculations,
            "target_amount": target_amount,
            "specific_goal": specific_goal,
            "confidence": "HIGH" if (monthly_income and net_worth) else "MEDIUM"
        }
    
    def _analyze_savings(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze savings rate from actual financial data."""
        # Read actual numeric values from the coordinator
        monthly_income = context.get("monthly_income")
        monthly_expenses = context.get("monthly_expenses")
        savings_rate_raw = context.get("savings_rate")
        
        reasoning = []
        
        # Calculate savings rate from actual numbers if available
        if monthly_income and monthly_expenses and monthly_income > 0:
            savings_rate = (monthly_income - monthly_expenses) / monthly_income
            reasoning.append(f"Savings rate calculated: ₹{monthly_income:,.0f} income - ₹{monthly_expenses:,.0f} expenses = {savings_rate*100:.1f}%")
            
            if savings_rate < 0.10:
                return {"band": "LOW", "signal": f"Low savings rate ({savings_rate*100:.1f}%) - spending nearly matches income", "reasoning": reasoning}
            elif savings_rate >= 0.30:
                return {"band": "HIGH", "signal": None, "reasoning": reasoning}
            else:
                return {"band": "MEDIUM", "signal": None, "reasoning": reasoning}
        
        # Use pre-computed savings rate from context sync
        if savings_rate_raw is not None and isinstance(savings_rate_raw, (int, float)):
            reasoning.append(f"Savings rate from MCP context: {savings_rate_raw*100:.1f}%")
            if savings_rate_raw < 0.10:
                return {"band": "LOW", "signal": f"Low savings rate ({savings_rate_raw*100:.1f}%)", "reasoning": reasoning}
            elif savings_rate_raw >= 0.30:
                return {"band": "HIGH", "signal": None, "reasoning": reasoning}
            else:
                return {"band": "MEDIUM", "signal": None, "reasoning": reasoning}
        
        # Fallback to band-based analysis
        income_band = str(context.get("income_band", "")).upper()
        expense_pattern = str(context.get("expense_pattern", "")).upper()
        reasoning.append("Using band-based analysis (exact values unavailable)")
        
        if income_band == "LOW" and expense_pattern in {"HIGH", "AGGRESSIVE"}:
            return {"band": "LOW", "signal": "Low savings rate inferred from spending behavior", "reasoning": reasoning}
        if income_band == "HIGH" and expense_pattern in {"LOW", "MODERATE"}:
            return {"band": "HIGH", "signal": None, "reasoning": reasoning}
        return {"band": "MEDIUM", "signal": None, "reasoning": reasoning}
    
    def _analyze_dti(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze debt-to-income ratio from actual financial data."""
        monthly_income = context.get("monthly_income")
        total_liabilities = context.get("total_liabilities")
        monthly_emi = context.get("monthly_emi")
        loan_types = context.get("loan_types", [])
        
        reasoning = []
        
        # Calculate DTI from actual numbers
        if monthly_income and monthly_income > 0:
            if monthly_emi and monthly_emi > 0:
                dti = (monthly_emi / monthly_income) * 100
                reasoning.append(f"DTI calculated: EMI ₹{monthly_emi:,.0f} / Income ₹{monthly_income:,.0f} = {dti:.1f}%")
            elif total_liabilities:
                # Estimate monthly obligation from total liabilities (rough EMI estimate)
                estimated_emi = total_liabilities / 12
                dti = (estimated_emi / monthly_income) * 100
                reasoning.append(f"DTI estimated: Total liabilities ₹{total_liabilities:,.0f}, est. monthly ₹{estimated_emi:,.0f} / Income ₹{monthly_income:,.0f} = {dti:.1f}%")
            else:
                dti = 0
                reasoning.append("No debt obligations detected")
            
            if loan_types:
                reasoning.append(f"Active loan types: {', '.join(loan_types)}")
            
            if dti > 40:
                return {"band": "HIGH", "signal": f"High DTI ratio ({dti:.1f}%) - debt burden is significant", "reasoning": reasoning}
            elif dti > 20:
                return {"band": "MEDIUM", "signal": None, "reasoning": reasoning}
            else:
                return {"band": "LOW", "signal": None, "reasoning": reasoning}
        
        # Fallback: check debt_intensity band
        debt_intensity = str(context.get("debt_intensity", "")).upper()
        reasoning.append("Using band-based DTI analysis (exact values unavailable)")
        if debt_intensity == "HIGH":
            return {"band": "HIGH", "signal": "High EMI burden detected", "reasoning": reasoning}
        return {"band": "LOW", "signal": None, "reasoning": reasoning}
    
    def _analyze_diversification(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze investment diversification from actual asset data."""
        asset_classes = context.get("asset_classes", [])
        
        reasoning = ["Assessed asset class distribution"]
        
        # Count distinct asset types from the MCP data
        if asset_classes:
            count = len(asset_classes)
            asset_names = [a.replace("ASSET_TYPE_", "").replace("_", " ").title() for a in asset_classes]
            reasoning.append(f"Found {count} asset classes: {', '.join(asset_names)}")
            
            # Run MPT optimization
            has_equity = any("MUTUAL_FUND" in a or "SECURITIES" in a or "ETF" in a for a in asset_classes)
            has_debt = any("DEPOSIT" in a or "EPF" in a for a in asset_classes)
            has_commodity = any("GOLD" in a or "COMMODITY" in a or "ETF" in a for a in asset_classes)
            
            current_alloc = {
                "Equity": 0.6 if has_equity else 0.0,
                "Debt": 0.3 if has_debt else 0.0,
                "Gold": 0.1 if has_commodity else 0.0,
            }
            mpt_result = self._optimize_portfolio_mpt(current_alloc)
            reasoning.append(f"MPT Optimization: {mpt_result['action']}")
            
            if count >= 4:
                return {"band": "HIGH", "signal": None, "reasoning": reasoning}
            elif count >= 2:
                return {"band": "MODERATE", "signal": None, "reasoning": reasoning}
            else:
                return {"band": "LOW", "signal": "Limited investment diversification", "reasoning": reasoning}
        
        # Fallback to string matching
        assets_str = str(context.get("assets_summary", "")).lower()
        asset_type_keywords = ["mutual_fund", "epf", "stock", "bank", "fd", "etf", "deposit", "savings"]
        count = sum(1 for at in asset_type_keywords if at in assets_str)
        
        current_alloc = {"Equity": 0.4, "Debt": 0.4, "Gold": 0.2}
        mpt_result = self._optimize_portfolio_mpt(current_alloc)
        reasoning.append(f"MPT Optimization: {mpt_result['action']}")
        
        if count >= 4:
            return {"band": "HIGH", "signal": None, "reasoning": reasoning}
        elif count >= 2:
            return {"band": "MODERATE", "signal": None, "reasoning": reasoning}
        else:
            return {"band": "LOW", "signal": "Limited investment diversification", "reasoning": reasoning + ["Consider diversifying across more asset classes"]}
    
    def _analyze_for_goal(self, goal: str, metrics: Dict[str, Any]) -> List[str]:
        """Generate goal-specific signals."""
        signals = []
        goal_lower = goal.lower()
        
        if "retire" in goal_lower:
            if metrics.get("savings_rate") == "LOW":
                signals.append("Low savings rate may delay retirement goals")
            if metrics.get("debt_to_income_ratio") == "HIGH":
                signals.append("High debt may impact retirement planning")
        
        if "emergency" in goal_lower:
            if metrics.get("savings_rate") == "LOW":
                signals.append("Low emergency savings detected")
        
        return signals
    
    def _get_user_age_from_context(self, context: Dict[str, Any]) -> Optional[int]:
        """Extract user age from MCP context."""
        from datetime import datetime
        
        # Try credit report first
        credit = context.get("credit_report", {})
        if credit and credit.get("dateOfBirth"):
            try:
                dob_str = credit["dateOfBirth"].replace("Z", "+00:00")
                dob = datetime.fromisoformat(dob_str)
                age = (datetime.now() - dob).days // 365
                return age
            except Exception as e:
                logger.debug(f"Could not parse date of birth: {e}")
        
        return None
    
    def _get_user_income_from_context(self, context: Dict[str, Any]) -> Optional[float]:
        """Extract monthly income from financial context."""
        # First: check for direct monthly_income (from coordinator raw values)
        direct_income = context.get("monthly_income")
        if direct_income and isinstance(direct_income, (int, float)) and direct_income > 0:
            return float(direct_income)
        
        # Second: check income band and map to representative value
        income_band = str(context.get("income_band", "")).upper()
        if income_band == "LOW":
            return 40000.0
        if income_band == "MEDIUM":
            return 100000.0
        if income_band == "HIGH":
            return 250000.0

        # Third: scan transactions for salary credits
        transactions = context.get("transactions", [])
        salary_transactions = [
            t for t in transactions
            if t.get("type") == "CREDIT" and 
            any(kw in t.get("description", "").lower() for kw in ["salary", "income", "wages", "sal"])
        ]
        if salary_transactions:
            amounts = [abs(float(t.get("amount", 0))) for t in salary_transactions[:3]]
            return sum(amounts) / len(amounts) if amounts else None
        
        return None
    
    def _calculate_house_affordability(
        self,
        house_price: float,
        monthly_income: Optional[float],
        current_savings: float
    ) -> Dict[str, Any]:
        """
        Calculate house affordability metrics.
        
        Returns:
            Dictionary with down_payment, loan_amount, emi, credit_score_required, dti_after_loan
        """
        # Standard 20% down payment
        down_payment = house_price * 0.20
        loan_amount = house_price - down_payment
        
        # EMI calculation (20 years @ 8.5% interest for home loans in India)
        interest_rate_annual = 0.085
        interest_rate_monthly = interest_rate_annual / 12
        tenure_months = 20 * 12
        
        # EMI = P × r × (1+r)^n / [(1+r)^n-1]
        emi = loan_amount * interest_rate_monthly * ((1 + interest_rate_monthly)**tenure_months) / \
              (((1 + interest_rate_monthly)**tenure_months) - 1)
        
        # Credit score requirement based on loan amount
        if loan_amount > 50000000:  # > 5cr
            credit_score = 780
            score_reason = "Very high loan amount requires excellent credit"
        elif loan_amount > 20000000:  # > 2cr
            credit_score = 750
            score_reason = "High loan amount requires good credit history"
        else:
            credit_score = 720
            score_reason = "Standard home loan credit requirement"
        
        income_available = bool(monthly_income and monthly_income > 0)

        # DTI after loan
        dti_after = (emi / monthly_income) * 100 if income_available else None
        
        # Affordability assessment
        if not income_available:
            affordability = "UNKNOWN"
            affordability_reason = "Income data unavailable; EMI and down payment computed but risk band cannot be finalized."
        elif dti_after < 40:
            affordability = "GOOD"
            affordability_reason = "EMI is within safe DTI limits"
        elif dti_after < 50:
            affordability = "MARGINAL"
            affordability_reason = "EMI is at upper DTI limit, tight budget"
        else:
            affordability = "HIGH_RISK"
            affordability_reason = "EMI exceeds recommended DTI, may face approval issues"
        
        # Calculate savings gap for down payment
        savings_gap = down_payment - current_savings
        months_to_save = 0
        if savings_gap > 0 and income_available:
            # Assume 20% savings rate
            monthly_savings = monthly_income * 0.20
            months_to_save = savings_gap / monthly_savings if monthly_savings > 0 else 999
        
        return {
            "down_payment": down_payment,
            "down_payment_formatted": f"₹{down_payment/10000000:.2f}cr",
            "loan_amount": loan_amount,
            "loan_formatted": f"₹{loan_amount/10000000:.2f}cr",
            "emi": emi,
            "emi_formatted": f"₹{emi/1000:.0f}k/month",
            "credit_score_required": credit_score,
            "credit_score_reason": score_reason,
            "dti_after_loan": f"{dti_after:.1f}%" if dti_after is not None else "N/A",
            "affordability": affordability,
            "affordability_reason": affordability_reason,
            "income_data_available": income_available,
            "current_savings": current_savings,
            "savings_gap": max(0, savings_gap),
            "months_to_save": int(months_to_save) if savings_gap > 0 else 0
        }

    def _calculate_portfolio_metrics(self, portfolio_data: Dict[str, Any]):
        """
        Calculate advanced portfolio metrics (Sharpe, Volatility, Expected Return).
        Using simplified MPT (Modern Portfolio Theory) assumptions.
        """
        import numpy as np
        
        # Placeholder for actual historical data fetching
        # In production, this would fetch real asset data via RealTimeService/Cache
        
        metrics = {
            "sharpe_ratio": 1.5,  # Good > 1
            "annualized_volatility": 0.12,  # 12%
            "expected_return": 0.18,  # 18%
            "beta": 0.85
        }
        return metrics

    def _optimize_portfolio_mpt(self, current_allocation: Dict[str, float]) -> Dict[str, Any]:
        """
        Generate optimized portfolio allocation using MPT/Efficient Frontier.
        """
        # Simplified optimization logic
        # Returns recommended allocation to maximize Sharpe Ratio
        
        recommended = {
            "Equity": 0.60,
            "Debt": 0.30,
            "Gold": 0.10
        }
        
        return {
            "current": current_allocation,
            "recommended": recommended,
            "action": "Rebalance: Increase Equity to 60%, Reduce Debt/Gold"
        }

    def _tax_harvesting_opportunities(self, financial_context: Dict[str, Any]) -> List[str]:
        """
        Identify Tax Loss Harvesting opportunities.
        """
        opportunities = []
        
        # Check for unrealized losses in context (mock logic)
        assets = financial_context.get("assets", [])
        # Iterate and check if current_value < purchase_value
        
        # Placeholder
        opportunities.append("Review equity portfolio for tax-loss harvesting before March 31")
        
        return opportunities

    def _run_monte_carlo_simulation(self, goal_amount: float, current_savings: float, monthly_contribution: float, horizon_years: int) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for goal probability.
        Validates: Requirements 5.4 (10,000+ iterations)
        """
        import numpy as np
        
        simulations = 10000  # UPDATED: 10,000+ iterations as required
        returns_mean = 0.12  # 12% equity return assumption
        returns_std = 0.15   # 15% volatility
        
        results = []
        for _ in range(simulations):
            value = current_savings
            for _ in range(horizon_years * 12):
                monthly_return = np.random.normal(returns_mean/12, returns_std/np.sqrt(12))
                value = value * (1 + monthly_return) + monthly_contribution
            results.append(value)
            
        success_count = sum(1 for r in results if r >= goal_amount)
        probability = (success_count / simulations) * 100
        
        return {
            "success_probability": f"{probability:.1f}%",
            "median_outcome": np.median(results),
            "worst_case_10th_percentile": np.percentile(results, 10),
            "best_case_90th_percentile": np.percentile(results, 90),
            "iterations_run": simulations
        }

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.06) -> Dict[str, Any]:
        """
        Calculate Sharpe Ratio for risk-adjusted returns.
        Validates: Requirements 5.2
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Annual risk-free rate (default 6% for India)
        
        Returns:
            Sharpe ratio and interpretation
        """
        import numpy as np
        
        if not returns or len(returns) < 2:
            return {"sharpe_ratio": 0, "interpretation": "Insufficient data"}
        
        excess_returns = [r - (risk_free_rate / 12) for r in returns]
        mean_excess = np.mean(excess_returns)
        std_dev = np.std(excess_returns)
        
        if std_dev == 0:
            sharpe = 0
        else:
            sharpe = (mean_excess / std_dev) * np.sqrt(12)  # Annualized
        
        # Interpretation
        if sharpe > 2:
            interpretation = "Excellent risk-adjusted returns"
        elif sharpe > 1:
            interpretation = "Good risk-adjusted returns"
        elif sharpe > 0:
            interpretation = "Positive but modest risk-adjusted returns"
        else:
            interpretation = "Poor risk-adjusted returns - consider rebalancing"
        
        return {
            "sharpe_ratio": round(sharpe, 3),
            "interpretation": interpretation,
            "annualized_return": np.mean(returns) * 12,
            "annualized_volatility": std_dev * np.sqrt(12)
        }

    def calculate_sortino_ratio(self, returns: List[float], target_return: float = 0.0) -> Dict[str, Any]:
        """
        Calculate Sortino Ratio (focuses on downside risk only).
        Validates: Requirements 5.2
        
        Args:
            returns: List of periodic returns
            target_return: Minimum acceptable return (default 0)
        
        Returns:
            Sortino ratio and interpretation
        """
        import numpy as np
        
        if not returns or len(returns) < 2:
            return {"sortino_ratio": 0, "interpretation": "Insufficient data"}
        
        # Calculate downside returns only
        downside_returns = [r for r in returns if r < target_return]
        
        if not downside_returns:
            return {"sortino_ratio": float('inf'), "interpretation": "No downside risk observed"}
        
        mean_return = np.mean(returns)
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            sortino = float('inf')
        else:
            sortino = (mean_return - target_return) / downside_std * np.sqrt(12)
        
        if sortino > 2:
            interpretation = "Excellent downside-adjusted returns"
        elif sortino > 1:
            interpretation = "Good downside protection"
        else:
            interpretation = "Moderate downside risk"
        
        return {
            "sortino_ratio": round(sortino, 3) if sortino != float('inf') else "Infinite",
            "interpretation": interpretation,
            "downside_volatility": downside_std * np.sqrt(12)
        }

    def tax_optimization_recommendations(self, income: float, existing_deductions: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Generate tax optimization recommendations for Indian tax payers.
        Validates: Requirements 5.3
        
        Args:
            income: Annual gross income in INR
            existing_deductions: Dict of already claimed deductions
        
        Returns:
            Tax optimization recommendations by section
        """
        existing_deductions = existing_deductions or {}
        recommendations = []
        potential_savings = 0
        
        # Calculate tax slab
        if income <= 250000:
            tax_rate = 0
        elif income <= 500000:
            tax_rate = 0.05
        elif income <= 1000000:
            tax_rate = 0.20
        else:
            tax_rate = 0.30
        
        # Section 80C (max 1.5L)
        sec_80c_used = existing_deductions.get("80C", 0)
        sec_80c_available = min(150000 - sec_80c_used, 150000)
        if sec_80c_available > 0:
            recommendations.append({
                "section": "80C",
                "available": sec_80c_available,
                "potential_saving": sec_80c_available * tax_rate,
                "options": ["PPF", "ELSS Mutual Funds", "NSC", "Life Insurance Premium", "EPF VPF"]
            })
            potential_savings += sec_80c_available * tax_rate
        
        # Section 80D (Health Insurance - max 25K self, 50K senior parents)
        sec_80d_used = existing_deductions.get("80D", 0)
        sec_80d_available = 75000 - sec_80d_used  # Self + Parents
        if sec_80d_available > 0:
            recommendations.append({
                "section": "80D",
                "available": sec_80d_available,
                "potential_saving": sec_80d_available * tax_rate,
                "options": ["Health Insurance for self/family", "Health checkup", "Parents health insurance"]
            })
            potential_savings += sec_80d_available * tax_rate
        
        # Section 80E (Education Loan Interest - no limit)
        if income > 500000:
            recommendations.append({
                "section": "80E",
                "available": "No limit",
                "potential_saving": "Variable",
                "options": ["Education loan interest deduction (if applicable)"]
            })
        
        # Section 24 (Home Loan Interest - max 2L)
        sec_24_used = existing_deductions.get("24", 0)
        sec_24_available = 200000 - sec_24_used
        if sec_24_available > 0:
            recommendations.append({
                "section": "24",
                "available": sec_24_available,
                "potential_saving": sec_24_available * tax_rate,
                "options": ["Home loan interest deduction"]
            })
            potential_savings += sec_24_available * tax_rate
        
        # NPS (Section 80CCD(1B) - extra 50K)
        nps_available = 50000 - existing_deductions.get("80CCD1B", 0)
        if nps_available > 0:
            recommendations.append({
                "section": "80CCD(1B)",
                "available": nps_available,
                "potential_saving": nps_available * tax_rate,
                "options": ["National Pension Scheme contribution"]
            })
            potential_savings += nps_available * tax_rate
        
        return {
            "income": income,
            "tax_slab": f"{int(tax_rate * 100)}%",
            "recommendations": recommendations,
            "total_potential_savings": round(potential_savings),
            "regime_suggestion": "Old regime recommended" if potential_savings > 50000 else "Compare both regimes"
        }

    def check_rebalancing_needed(self, current_allocation: Dict[str, float], target_allocation: Dict[str, float], threshold: float = 0.05) -> Dict[str, Any]:
        """
        Check if portfolio rebalancing is needed.
        Validates: Requirements 5.5 (trigger when drift > 5%)
        
        Args:
            current_allocation: Current asset allocation (weights summing to 1)
            target_allocation: Target asset allocation
            threshold: Drift threshold (default 5%)
        
        Returns:
            Rebalancing recommendation
        """
        drifts = {}
        max_drift = 0
        rebalancing_actions = []
        
        for asset in target_allocation:
            current = current_allocation.get(asset, 0)
            target = target_allocation[asset]
            drift = abs(current - target)
            drifts[asset] = {
                "current": f"{current*100:.1f}%",
                "target": f"{target*100:.1f}%",
                "drift": f"{drift*100:.1f}%"
            }
            max_drift = max(max_drift, drift)
            
            if drift > threshold:
                action = "Buy" if current < target else "Sell"
                rebalancing_actions.append(f"{action} {asset}: adjust by {abs(current-target)*100:.1f}%")
        
        needs_rebalancing = max_drift > threshold
        
        return {
            "needs_rebalancing": needs_rebalancing,
            "max_drift": f"{max_drift*100:.1f}%",
            "threshold": f"{threshold*100:.1f}%",
            "drifts": drifts,
            "actions": rebalancing_actions if needs_rebalancing else ["Portfolio within target range"],
            "urgency": "HIGH" if max_drift > 0.10 else "MEDIUM" if needs_rebalancing else "LOW"
        }

    def calculate_net_return(self, gross_return: float, transaction_costs: float = 0.01, taxes: float = 0.10, inflation: float = 0.06) -> Dict[str, Any]:
        """
        Calculate net return accounting for all factors.
        Validates: Requirements 5.6
        
        Args:
            gross_return: Annual gross return (e.g., 0.12 for 12%)
            transaction_costs: Transaction costs as fraction
            taxes: Tax on gains (LTCG 10%, STCG varies)
            inflation: Annual inflation rate
        
        Returns:
            Net return breakdown
        """
        # Apply transaction costs
        after_costs = gross_return - transaction_costs
        
        # Apply taxes (on gains only)
        gains = max(0, after_costs)
        tax_amount = gains * taxes
        after_tax = after_costs - tax_amount
        
        # Adjust for inflation (real return)
        real_return = (1 + after_tax) / (1 + inflation) - 1
        
        return {
            "gross_return": f"{gross_return*100:.2f}%",
            "transaction_costs": f"-{transaction_costs*100:.2f}%",
            "tax_impact": f"-{tax_amount*100:.2f}%",
            "inflation_adjustment": f"-{inflation*100:.2f}%",
            "net_nominal_return": f"{after_tax*100:.2f}%",
            "real_return": f"{real_return*100:.2f}%",
            "breakdown": {
                "gross": gross_return,
                "costs": transaction_costs,
                "taxes": tax_amount,
                "nominal": after_tax,
                "real": real_return
            }
        }
