"""
Explainability Agent
Converts agent outputs to human-readable explanations.
"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger

from app.agents.base import BaseAgent


class ExplainabilityAgent(BaseAgent):
    """
    Explainability Agent - The human translator.

    Responsibilities:
    - Convert structured agent outputs to human-readable explanations
    - Preserve reasoning transparency
    - Avoid technical jargon
    - Maintain privacy masking

    Rules:
    - Do NOT add new insights
    - Do NOT introduce new data
    - Keep explanations concise and clear
    - Always reference reasoning steps
    """

    def __init__(self):
        super().__init__()
        self.name = "explainability"
        self.description = "Converts agent outputs to human-readable explanations"
        self.read_layers = {"agent_working_memory", "explainability_context"}
        self.write_layers = {"explainability_context"}

        self.system_prompt = """You are an Explainability Agent.

Your task is to:
- Convert structured agent outputs into human-readable explanations
- Preserve reasoning transparency
- Avoid technical jargon
- Maintain privacy masking

Rules:
- Do NOT add new insights
- Do NOT introduce new data
- Keep explanations concise and clear
- Always reference reasoning steps
- Output must be structured JSON"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "finance_output": {"type": "object"},
                "knowledge_output": {"type": "object"},
                "code_output": {"type": "object"},
                "confidence_level": {"type": "string"}
            }
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "key_reasons": {"type": "array", "items": {"type": "string"}},
                "assumptions_used": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                "actions": {"type": "array"}
            },
            "required": ["summary", "key_reasons"]
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process agent outputs and convert to user-friendly explanation.
        """
        query = input_data.get("user_query", "")
        agent_outputs = input_data.get("agent_outputs", {})

        self.add_reasoning_step(f"Processing query: {query}")

        # Extract data from various agents
        finance_output = agent_outputs.get("finance_reasoning", {})
        knowledge_output = agent_outputs.get("knowledge", {})
        code_output = agent_outputs.get("code", {})
        alert_output = agent_outputs.get("alert", {})
        trading_output = agent_outputs.get("trading_analysis", {})
        execution_trace = agent_outputs.get("execution_trace", [])

        # Raw financial context from coordinator (for deeply personalized responses)
        user_financial_ctx = input_data.get("user_financial_context", {})

        metrics = finance_output.get("metrics", {})
        signals = finance_output.get("signals_detected", [])
        reasoning_steps = finance_output.get("intermediate_reasoning", [])
        facts = knowledge_output.get("facts", [])

        # NEW: Extract user-specific data from finance agent + raw context
        user_age = finance_output.get("user_age")
        monthly_income = (
            finance_output.get("monthly_income")
            or user_financial_ctx.get("monthly_income")
        )
        monthly_expenses = (
            finance_output.get("monthly_expenses")
            or user_financial_ctx.get("monthly_expenses")
        )
        net_worth = (
            finance_output.get("net_worth")
            or user_financial_ctx.get("net_worth")
        )
        credit_score = (
            finance_output.get("credit_score")
            or user_financial_ctx.get("credit_score")
        )
        total_assets = user_financial_ctx.get("total_assets")
        total_liabilities = user_financial_ctx.get("total_liabilities")
        asset_classes = (
            finance_output.get("asset_classes")
            or user_financial_ctx.get("asset_classes", [])
        )
        specific_calculations = finance_output.get("specific_calculations", {})
        target_amount = finance_output.get("target_amount")
        specific_goal = finance_output.get("specific_goal")

        if user_age:
            self.add_reasoning_step(f"User age available: {user_age} years")
        if monthly_income:
            self.add_reasoning_step(f"User income available: ₹{monthly_income:,.0f}/month")
        if specific_calculations:
            self.add_reasoning_step(f"Specific calculations available: {list(specific_calculations.keys())}")

        # Extract generated visual actions once, regardless of output path.
        actions = self._extract_image_actions(code_output.get("images", []))
        if actions:
            logger.info(f"Including {len(actions)} chart(s) in response")

        # DEBUG: Check what facts and reasoning_steps contain
        logger.info(f"EXPLAINABILITY INPUT DEBUG: facts={facts[:2] if facts else 'EMPTY'}, reasoning_steps={reasoning_steps[:2] if reasoning_steps else 'EMPTY'}")

        house_keywords = ["house", "home", "property", "purchase", "buy", "emi", "down payment", "afford"]
        query_lower = query.lower().strip()
        is_house_query = any(kw in query_lower for kw in house_keywords) or specific_goal == "HOME_PURCHASE"
        is_technical_output_query = self._is_technical_output_query(query_lower)
        is_stock_trading_query = self._is_stock_trading_query(query_lower)

        # Handle stock trading analysis results from TradingAgents
        if is_stock_trading_query and trading_output and trading_output.get("success"):
            self.add_reasoning_step("Using TradingAgents pipeline response for stock trading query")
            return self._build_trading_analysis_response(
                trading_output=trading_output,
                query=query,
                actions=actions,
            )

        # Deterministic house-affordability response to avoid LLM number drift.
        if is_house_query and specific_calculations:
            self.add_reasoning_step("Using deterministic house affordability response")
            return self._build_house_affordability_response(
                specific_calculations=specific_calculations,
                monthly_income=monthly_income,
                actions=actions,
            )

        if is_house_query and not specific_calculations:
            self.add_reasoning_step("House query detected but calculations unavailable")
            amount_text = "requested house budget"
            if isinstance(target_amount, (int, float)) and target_amount > 0:
                amount_text = f"₹{target_amount:,.0f}"
            return {
                "summary": (
                    f"I could not compute precise home-affordability metrics for {amount_text} from the current context. "
                    "Please sync your latest income and liabilities data to generate down payment, EMI band, and risk factors."
                ),
                "key_reasons": [
                    "Missing or insufficient monthly income context for EMI-to-income analysis",
                    "Home affordability requires down payment, EMI, DTI, and credit-readiness calculation together",
                    "Run a context sync and retry this query for a deterministic result",
                ],
                "assumptions_used": [
                    "No synthetic financial values were introduced",
                ],
                "confidence": "LOW",
                "actions": actions,
            }

        # Deterministic handling for code-execution requests.
        # Avoid claiming success when no visual artifact is actually available.
        if is_technical_output_query and code_output:
            code_success = bool(code_output.get("success"))
            code_error = (
                code_output.get("error")
                or code_output.get("stderr")
                or code_output.get("output")
                or "Code execution failed without diagnostic output."
            )

            if not code_success:
                self.add_reasoning_step("Code execution failed for technical query")
                return self._build_code_failure_response(str(code_error), actions)

            if code_success and not actions:
                self.add_reasoning_step("Code execution succeeded but no chart artifact found")
                return self._build_code_missing_chart_response()

        if self._is_income_shock_rebalance_query(query_lower):
            self.add_reasoning_step("Using deterministic income shock rebalance response")
            return self._build_income_shock_rebalance_response(
                query_lower=query_lower,
                metrics=metrics,
                monthly_income=monthly_income,
                actions=actions,
            )

        if self._is_emergency_fund_target_query(query_lower):
            self.add_reasoning_step("Using deterministic emergency-fund target response")
            return self._build_emergency_fund_target_response(
                metrics=metrics,
                monthly_income=monthly_income,
                actions=actions,
            )

        if self._is_surplus_three_option_query(query_lower):
            self.add_reasoning_step("Using deterministic three-option surplus plan response")
            return self._build_surplus_three_option_response(
                metrics=metrics,
                monthly_income=monthly_income,
                actions=actions,
            )

        if self._is_weakness_30_day_query(query_lower):
            self.add_reasoning_step("Using deterministic weakness and 30-day action response")
            return self._build_weakness_30_day_response(
                metrics=metrics,
                signals=signals,
                monthly_income=monthly_income,
                actions=actions,
            )

        if self._is_debt_payoff_query(query_lower):
            self.add_reasoning_step("Using deterministic debt intensity and payoff response")
            return self._build_debt_payoff_response(
                metrics=metrics,
                monthly_income=monthly_income,
                actions=actions,
            )

        if self._is_asset_allocation_query(query_lower):
            self.add_reasoning_step("Using deterministic asset allocation response")
            return self._build_asset_allocation_response(
                metrics=metrics,
                actions=actions,
            )

        if self._is_alert_explain_query(query_lower):
            self.add_reasoning_step("Using deterministic alert explanation response")
            return self._build_alert_explanation_response(
                alert_output=alert_output,
                metrics=metrics,
                signals=signals,
                actions=actions,
            )

        if self._is_trace_query(query_lower):
            self.add_reasoning_step("Using deterministic trace explanation response")
            return self._build_trace_response(
                execution_trace=execution_trace,
                actions=actions,
            )

        # Prepare prompt for LLM
        # IMPORTANT: _build_prompt signature is (query, metrics, signals, reasoning, facts, ...)
        # NOT (query, metrics, signals, facts, reasoning, ...) - reasoning comes before facts!
        prompt = self._build_prompt(
            query,
            metrics,
            signals,
            reasoning_steps,
            facts,
            code_output,
            user_age,
            monthly_income,
            specific_calculations,
            net_worth=net_worth,
            credit_score=credit_score,
            monthly_expenses=monthly_expenses,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            asset_classes=asset_classes,
        )
        self.add_reasoning_step("Built prompt for LLM explanation generation")

        # DEBUG: Log the actual prompt being sent
        logger.info(f"EXPLAINABILITY PROMPT DEBUG: First 500 chars of prompt: {prompt[:500]}")

        # Call the LLM for natural language generation
        try:
            llm_response = await self.invoke_llm(prompt)
            self.add_reasoning_step("Generated explanation using LLM")

            # If LLM returns valid structured response, use it BUT ALWAYS ADD ACTIONS
            if isinstance(llm_response, dict) and "summary" in llm_response:
                return {
                    "summary": llm_response.get("summary", ""),
                    "key_reasons": llm_response.get("key_reasons", []),
                    "assumptions_used": llm_response.get("assumptions_used", ["Stable income", "No major changes in expenses"]),
                    "confidence": llm_response.get("confidence", "MEDIUM"),
                    "actions": actions  # CRITICAL: Always include actions
                }
        except Exception as e:
            logger.warning(f"LLM call failed, using fallback: {e}")
            self.add_reasoning_step("LLM call failed, using structured fallback")

        # Fallback: Build response from structured data if LLM fails
        summary = self._build_summary(query, metrics, signals, facts)
        self.add_reasoning_step("Generated summary from financial metrics and signals")

        key_reasons = self._build_key_reasons(signals, reasoning_steps)
        self.add_reasoning_step("Extracted key reasons from agent reasoning")

        assumptions = self._build_assumptions(metrics)

        if facts and facts[0] != "No specific information found for this query":
            key_reasons.append(f"Relevant regulation: {facts[0]}")
            self.add_reasoning_step("Integrated external knowledge into explanation")

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence("MEDIUM", len(signals), len(facts))

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": confidence,
            "actions": actions
        }

    def _build_house_affordability_response(
        self,
        specific_calculations: Dict[str, Any],
        monthly_income: Optional[float],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic, number-faithful response for house affordability queries."""
        calc = specific_calculations

        affordability = str(calc.get("affordability", "UNKNOWN")).upper()
        affordability_reason = str(calc.get("affordability_reason", ""))
        emi_formatted = str(calc.get("emi_formatted", "N/A"))
        down_payment_formatted = str(calc.get("down_payment_formatted", "N/A"))
        loan_formatted = str(calc.get("loan_formatted", "N/A"))
        credit_score = calc.get("credit_score_required", "N/A")
        dti_after = str(calc.get("dti_after_loan", "N/A"))
        savings_gap = float(calc.get("savings_gap", 0) or 0)
        months_to_save = int(calc.get("months_to_save", 0) or 0)
        monthly_income_text = f"₹{monthly_income:,.0f}" if monthly_income else "N/A"

        summary = (
            f"For this home purchase, required down payment is {down_payment_formatted}, loan size is {loan_formatted}, "
            f"and estimated EMI is {emi_formatted}. Affordability assessment is {affordability} "
            f"(DTI after loan: {dti_after}). Recommended minimum credit score is {credit_score}+."
        )
        if affordability_reason:
            summary += f" {affordability_reason}."

        key_reasons = [
            f"Down payment requirement: {down_payment_formatted}",
            f"Estimated monthly EMI: {emi_formatted}",
            f"Post-loan DTI band: {dti_after}",
            f"Credit readiness target: {credit_score}+",
        ]
        if affordability == "UNKNOWN":
            key_reasons.append("Risk band is partial because monthly income context is missing or stale")
        if savings_gap > 0:
            key_reasons.append(
                f"Savings gap to down payment: ₹{savings_gap:,.0f} (approx. {months_to_save} months at current assumptions)"
            )

        assumptions = [
            "Home loan interest assumption: 8.5% annual",
            "Loan tenure assumption: 20 years",
            "Down payment assumption: 20%",
            f"Monthly income used: {monthly_income_text}",
        ]

        confidence = "HIGH" if affordability in {"GOOD", "MARGINAL", "HIGH_RISK"} else "MEDIUM"
        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": confidence,
            "actions": actions,
        }

    def _is_income_shock_rebalance_query(self, query_lower: str) -> bool:
        """Detect personal income-drop stress test queries that require deterministic rebalancing output."""
        personal_terms = [" my ", " me ", " i ", "mine", "myself", "my context"]
        income_terms = ["income", "salary", "pay"]
        drop_terms = ["drop", "drops", "decrease", "decreases", "cut", "cuts", "fall", "falls", "reduce", "reduces"]
        rebalance_terms = ["rebalance", "re-balance", "reallocate", "reprioritize", "re-prioritize", "impacted first", "which goals"]

        padded_query = f" {query_lower} "
        has_personal_context = any(term in padded_query for term in personal_terms)
        has_income_context = any(term in query_lower for term in income_terms)
        has_drop_context = any(term in query_lower for term in drop_terms) or "%" in query_lower
        has_rebalance_context = any(term in query_lower for term in rebalance_terms)

        return has_personal_context and has_income_context and has_drop_context and has_rebalance_context

    def _extract_income_drop_percent(self, query_lower: str) -> float:
        """Extract drop percentage from query, defaulting to 20 when unspecified."""
        matches = re.findall(r"(\d{1,2}(?:\.\d+)?)\s*%", query_lower)
        for match in matches:
            value = float(match)
            if 0 < value < 100:
                return value
        return 20.0

    def _build_income_shock_rebalance_response(
        self,
        query_lower: str,
        metrics: Dict[str, Any],
        monthly_income: Optional[float],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic goal-impact and rebalancing response for income-shock scenarios."""
        drop_percent = self._extract_income_drop_percent(query_lower)
        drop_ratio = drop_percent / 100.0

        savings_rate = str(metrics.get("savings_rate", "MEDIUM")).upper()
        debt_to_income = str(metrics.get("debt_to_income_ratio", "LOW")).upper()
        diversification = str(metrics.get("investment_diversification", "LOW")).upper()

        savings_buffer_ratio = {
            "LOW": 0.05,
            "MEDIUM": 0.20,
            "HIGH": 0.35,
        }.get(savings_rate, 0.20)

        summary_parts = [
            f"If income drops by {drop_percent:.0f}%, the first goals impacted should be discretionary goals, then medium-term optional goals.",
            "Core obligations and long-term wealth goals should be protected and rebalanced, not stopped.",
        ]

        risk_factors = []
        if savings_rate == "LOW":
            risk_factors.append("Low savings rate limits your buffer against income shocks.")
        if debt_to_income == "HIGH":
            risk_factors.append("High debt-to-income means EMI obligations can force aggressive goal cuts.")
        if diversification in {"LOW", "MODERATE", "ALERT - CHECK ALLOCATION"}:
            risk_factors.append("Limited diversification increases drawdown risk if you pause contributions.")

        assumptions = [
            f"Income shock applied: {drop_percent:.0f}%",
            "Expenses assumed unchanged in the first month",
            f"Savings-rate band used: {savings_rate}",
            f"Debt-to-income band used: {debt_to_income}",
            f"Diversification band used: {diversification}",
        ]

        key_reasons = [
            "Impact order: discretionary lifestyle goals first, medium-term optional goals second, long-term compounding goals last.",
            "Rebalance step 1 (Week 1): lock mandatory expenses/EMIs and pause non-essential spending.",
            f"Rebalance step 2 (Week 1): cut variable expenses by at least {drop_percent:.0f}% to absorb the income shock.",
            "Rebalance step 3 (Week 2): reduce SIP/investment contributions temporarily instead of fully stopping long-term plans.",
            "Rebalance step 4 (Week 3-4): rebuild a 3-6 month emergency runway before restoring discretionary goals.",
        ]

        if monthly_income and monthly_income > 0:
            reduced_income = monthly_income * (1 - drop_ratio)
            baseline_surplus = monthly_income * savings_buffer_ratio
            post_shock_surplus = baseline_surplus - (monthly_income * drop_ratio)
            summary_parts.append(
                f"Estimated monthly income moves from ₹{monthly_income:,.0f} to ₹{reduced_income:,.0f}."
            )
            key_reasons.append(
                f"Estimated surplus shifts from about ₹{baseline_surplus:,.0f} to ₹{post_shock_surplus:,.0f} if fixed costs stay constant."
            )
            if post_shock_surplus < 0:
                risk_factors.append("Current plan likely turns cash-flow negative after the income drop unless expenses are cut quickly.")
            assumptions.append(f"Monthly income used: ₹{monthly_income:,.0f}")
        else:
            summary_parts.append(
                "Monthly income is unavailable in context, so prioritization is based on your financial risk bands."
            )
            assumptions.append("Monthly income unavailable; impact quantified using qualitative bands")

        for risk_factor in risk_factors:
            key_reasons.append(f"Risk factor: {risk_factor}")

        confidence = "HIGH" if monthly_income else "MEDIUM"
        return {
            "summary": " ".join(summary_parts),
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": confidence,
            "actions": actions,
        }

    def _is_emergency_fund_target_query(self, query_lower: str) -> bool:
        """Detect emergency-fund sizing and parking queries."""
        emergency_terms = [
            "emergency fund", "emergency", "job loss", "unemploy", "layoff",
            "survive without income", "contingency fund", "rainy day"
        ]
        sizing_terms = [
            "target", "how many months", "months", "where should i park",
            "where to park", "park it", "allocate", "split"
        ]
        has_emergency_context = any(term in query_lower for term in emergency_terms)
        has_target_context = any(term in query_lower for term in sizing_terms)
        return has_emergency_context and has_target_context

    def _build_emergency_fund_target_response(
        self,
        metrics: Dict[str, Any],
        monthly_income: Optional[float],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic emergency-fund target and parking guidance."""
        savings_rate = str(metrics.get("savings_rate", "MEDIUM")).upper()
        debt_to_income = str(metrics.get("debt_to_income_ratio", "LOW")).upper()

        base_month_ranges = {
            "LOW": (8, 12),
            "MEDIUM": (6, 9),
            "HIGH": (4, 6),
        }
        target_min, target_max = base_month_ranges.get(savings_rate, (6, 9))

        if debt_to_income == "HIGH":
            target_min += 2
            target_max += 3
        elif debt_to_income == "MEDIUM":
            target_min += 1
            target_max += 1

        target_min = max(3, target_min)
        target_max = max(target_min + 1, target_max)

        summary_parts = [
            f"Based on your profile, target an emergency fund of {target_min}-{target_max} months of essential expenses.",
            "Keep this in a 3-bucket structure so money is liquid, low-volatility, and accessible during shocks.",
        ]

        key_reasons = [
            f"Month target uses your savings-rate band ({savings_rate}) and debt-to-income band ({debt_to_income}).",
            "Bucket 1 (instant access): keep 1 month of expenses in savings account or sweep-in FD.",
            "Bucket 2 (near-term liquidity): keep 2-3 months in overnight or liquid mutual funds.",
            "Bucket 3 (reserve): keep remaining months in FD ladder (3-12 month maturities) or ultra-short debt fund.",
            "Replenishment rule: if used, rebuild the fund within 90 days before increasing discretionary investing.",
        ]

        assumptions = [
            f"Savings-rate band used: {savings_rate}",
            f"Debt-to-income band used: {debt_to_income}",
            "Emergency corpus is measured in months of essential expenses",
        ]

        if monthly_income and monthly_income > 0:
            essential_expense_ratio_by_savings = {"LOW": 0.85, "MEDIUM": 0.70, "HIGH": 0.55}
            essential_expense_ratio = essential_expense_ratio_by_savings.get(savings_rate, 0.70)
            estimated_essential_expense = monthly_income * essential_expense_ratio
            corpus_min = estimated_essential_expense * target_min
            corpus_max = estimated_essential_expense * target_max
            summary_parts.append(
                f"Using estimated essential expense of about ₹{estimated_essential_expense:,.0f}/month, target corpus is roughly ₹{corpus_min:,.0f}-₹{corpus_max:,.0f}."
            )
            key_reasons.append(
                "This amount estimate is illustrative; replace with your actual monthly essentials for final sizing."
            )
            assumptions.append(f"Monthly income used: ₹{monthly_income:,.0f}")
            assumptions.append(f"Essential-expense ratio assumption: {essential_expense_ratio:.0%} of income")
            confidence = "HIGH"
        else:
            summary_parts.append(
                "Income is unavailable in current context, so month-based sizing is provided without a rupee estimate."
            )
            assumptions.append("Income unavailable; rupee corpus estimate omitted")
            confidence = "MEDIUM"

        return {
            "summary": " ".join(summary_parts),
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": confidence,
            "actions": actions,
        }

    def _is_surplus_three_option_query(self, query_lower: str) -> bool:
        """Detect request for conservative/balanced/aggressive surplus plans."""
        terms = ["3-option", "conservative", "balanced", "aggressive", "monthly surplus"]
        return sum(1 for term in terms if term in query_lower) >= 2

    def _build_surplus_three_option_response(
        self,
        metrics: Dict[str, Any],
        monthly_income: Optional[float],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic 3-option surplus allocation plan."""
        savings_rate = str(metrics.get("savings_rate", "MEDIUM")).upper()
        surplus_ratio_by_savings = {"LOW": 0.10, "MEDIUM": 0.20, "HIGH": 0.35}
        surplus_ratio = surplus_ratio_by_savings.get(savings_rate, 0.20)
        surplus_estimate = monthly_income * surplus_ratio if monthly_income else None

        summary = (
            "Here is a 3-option monthly-surplus plan tailored to your profile: conservative, balanced, and aggressive. "
            "Choose one track for 90 days, then review and rebalance."
        )
        if surplus_estimate:
            summary += f" Estimated monthly surplus used for sizing: ₹{surplus_estimate:,.0f}."

        key_reasons = []
        if surplus_estimate:
            key_reasons.extend([
                f"Conservative: Emergency/Safe Debt first -> 50% emergency top-up (₹{surplus_estimate * 0.50:,.0f}), 30% debt prepayment (₹{surplus_estimate * 0.30:,.0f}), 20% low-volatility debt/liquid funds (₹{surplus_estimate * 0.20:,.0f}).",
                f"Balanced: Stability + Growth -> 30% emergency/debt buffer (₹{surplus_estimate * 0.30:,.0f}), 50% diversified equity index funds (₹{surplus_estimate * 0.50:,.0f}), 20% debt/gold hedge (₹{surplus_estimate * 0.20:,.0f}).",
                f"Aggressive: Growth-heavy -> 20% safety buffer (₹{surplus_estimate * 0.20:,.0f}), 65% equity index + flexi-cap (₹{surplus_estimate * 0.65:,.0f}), 15% tactical/satellite allocation (₹{surplus_estimate * 0.15:,.0f}).",
            ])
        else:
            key_reasons.extend([
                "Conservative: 50% emergency top-up, 30% debt prepayment, 20% low-volatility debt/liquid funds.",
                "Balanced: 30% emergency/debt buffer, 50% diversified equity index funds, 20% debt/gold hedge.",
                "Aggressive: 20% safety buffer, 65% equity index + flexi-cap, 15% tactical/satellite allocation.",
            ])
        key_reasons.append("Risk control rule: if debt-to-income rises or income becomes unstable, shift one tier toward conservative.")

        assumptions = [
            f"Savings-rate band used: {savings_rate}",
            "Surplus allocation reviewed every 90 days",
        ]
        if monthly_income:
            assumptions.append(f"Monthly income used: ₹{monthly_income:,.0f}")
            assumptions.append(f"Surplus ratio assumption: {surplus_ratio:.0%} of monthly income")

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": "HIGH" if monthly_income else "MEDIUM",
            "actions": actions,
        }

    def _is_weakness_30_day_query(self, query_lower: str) -> bool:
        """Detect biggest weakness + next 30 days coaching prompts."""
        has_weakness = "weakness" in query_lower
        has_30_day = "next 30 days" in query_lower or "30 days" in query_lower
        return has_weakness and has_30_day

    def _build_weakness_30_day_response(
        self,
        metrics: Dict[str, Any],
        signals: List[str],
        monthly_income: Optional[float],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic weakness diagnosis and 30-day action plan."""
        savings_rate = str(metrics.get("savings_rate", "MEDIUM")).upper()
        debt_to_income = str(metrics.get("debt_to_income_ratio", "LOW")).upper()
        diversification = str(metrics.get("investment_diversification", "LOW")).upper()
        signal_text = " ".join(signals).lower()

        if debt_to_income == "HIGH":
            weakness = "debt burden is your biggest current weakness"
        elif savings_rate == "LOW":
            weakness = "insufficient savings velocity is your biggest current weakness"
        elif "limited investment diversification" in signal_text or diversification in {"LOW", "MODERATE", "ALERT - CHECK ALLOCATION"}:
            weakness = "low diversification is your biggest current weakness"
        else:
            weakness = "execution consistency (budget discipline and periodic rebalancing) is your biggest current weakness"

        summary = f"Your biggest financial weakness right now is that {weakness}. The next 30 days should focus on a single corrective plan with measurable weekly targets."

        weekly_target = None
        if monthly_income and monthly_income > 0:
            weekly_target = monthly_income * 0.05 / 4.0
            summary += f" Suggested weekly correction target: about ₹{weekly_target:,.0f}."

        key_reasons = [
            "Week 1: Freeze non-essential spending and define a hard monthly cap for discretionary categories.",
            "Week 2: Automate transfers on salary day (emergency/debt/investment buckets).",
            "Week 3: Fix the highest-impact leak (high-interest debt, missed SIP, or concentration risk).",
            "Week 4: Review outcomes and lock next month’s rules based on actual cash-flow behavior.",
        ]
        if weekly_target:
            key_reasons.append(f"Numerical target: free up or redirect at least ₹{weekly_target:,.0f} per week for the next 4 weeks.")

        assumptions = [
            f"Savings-rate band used: {savings_rate}",
            f"Debt-to-income band used: {debt_to_income}",
            f"Diversification band used: {diversification}",
        ]
        if monthly_income:
            assumptions.append(f"Monthly income used: ₹{monthly_income:,.0f}")

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": "HIGH" if monthly_income else "MEDIUM",
            "actions": actions,
        }

    def _is_debt_payoff_query(self, query_lower: str) -> bool:
        """Detect debt intensity and payoff-priority requests."""
        debt_terms = ["debt", "emi", "loan", "liabilities"]
        payoff_terms = ["payoff", "priority order", "priority", "timeline", "debt intensity"]
        return any(t in query_lower for t in debt_terms) and any(t in query_lower for t in payoff_terms)

    def _build_debt_payoff_response(
        self,
        metrics: Dict[str, Any],
        monthly_income: Optional[float],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic debt payoff order with expected timeline."""
        debt_band = str(metrics.get("debt_to_income_ratio", "LOW")).upper()
        timeline_by_band = {
            "LOW": "6-12 months for unsecured debt cleanup",
            "MEDIUM": "12-24 months for meaningful debt reduction",
            "HIGH": "24-36+ months unless income increases or expenses are cut aggressively",
        }
        allocation_ratio_by_band = {"LOW": 0.15, "MEDIUM": 0.25, "HIGH": 0.35}
        payoff_ratio = allocation_ratio_by_band.get(debt_band, 0.25)
        timeline = timeline_by_band.get(debt_band, timeline_by_band["MEDIUM"])

        summary = f"Your debt intensity is {debt_band}. Recommended payoff strategy is debt-avalanche order, with an expected timeline of {timeline}."
        if monthly_income and monthly_income > 0:
            monthly_payoff_budget = monthly_income * payoff_ratio
            summary += f" Suggested monthly payoff budget: about ₹{monthly_payoff_budget:,.0f}."

        key_reasons = [
            "Priority 1: Credit cards and revolving balances (highest interest, highest compounding drag).",
            "Priority 2: Personal/consumer loans and BNPL balances.",
            "Priority 3: Vehicle/other secured loans with higher effective rate.",
            "Priority 4: Home loan prepayment only after high-interest debt is controlled.",
            "Execution rule: keep minimum payments on all loans, direct all extra cash to one highest-rate loan at a time.",
        ]

        assumptions = [
            f"Debt intensity inferred from DTI band: {debt_band}",
            "Payoff method assumed: debt avalanche",
        ]
        if monthly_income:
            assumptions.append(f"Monthly income used: ₹{monthly_income:,.0f}")
            assumptions.append(f"Payoff allocation assumption: {payoff_ratio:.0%} of monthly income")

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": "HIGH" if monthly_income else "MEDIUM",
            "actions": actions,
        }

    def _is_asset_allocation_query(self, query_lower: str) -> bool:
        """Detect asset-allocation suitability requests."""
        allocation_terms = ["asset allocation", "allocation range", "risk profile", "current liabilities", "suitable"]
        return any(t in query_lower for t in allocation_terms)

    def _build_asset_allocation_response(
        self,
        metrics: Dict[str, Any],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic allocation range based on risk and liabilities."""
        savings_rate = str(metrics.get("savings_rate", "MEDIUM")).upper()
        debt_band = str(metrics.get("debt_to_income_ratio", "LOW")).upper()

        if debt_band == "HIGH":
            risk_profile = "CONSERVATIVE"
            ranges = "Equity 35-45% | Debt 45-55% | Gold 5-10% | Cash/Liquid 5-10%"
        elif debt_band == "MEDIUM" or savings_rate == "LOW":
            risk_profile = "BALANCED"
            ranges = "Equity 50-65% | Debt 25-40% | Gold 5-10% | Cash/Liquid 5%"
        else:
            risk_profile = "GROWTH"
            ranges = "Equity 65-80% | Debt 15-25% | Gold 5-10% | Cash/Liquid 5%"

        summary = (
            f"Based on your risk/liability context, a {risk_profile} allocation is suitable right now. "
            f"Suggested range: {ranges}."
        )

        key_reasons = [
            f"Liability adjustment applied using DTI band: {debt_band}.",
            f"Savings-capacity adjustment applied using savings-rate band: {savings_rate}.",
            "Guardrail: maintain emergency fund before increasing equity allocation.",
            "Rebalancing trigger: if any asset class drifts by more than 5%, rebalance back to target range.",
        ]

        assumptions = [
            f"Savings-rate band used: {savings_rate}",
            f"Debt-to-income band used: {debt_band}",
            "Allocation designed for medium-term stability + long-term growth",
        ]

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": "HIGH",
            "actions": actions,
        }

    def _is_alert_explain_query(self, query_lower: str) -> bool:
        """Detect proactive alert-check and alert explanation prompts."""
        has_alert = "alert" in query_lower
        has_trigger_or_explain = any(t in query_lower for t in ["trigger", "check now", "explain each", "plain language"])
        return has_alert and has_trigger_or_explain

    def _build_alert_explanation_response(
        self,
        alert_output: Dict[str, Any],
        metrics: Dict[str, Any],
        signals: List[str],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic plain-language explanation of active alerts."""
        alerts = list(alert_output.get("alerts", []) or [])
        if not alerts:
            debt_band = str(metrics.get("debt_to_income_ratio", "LOW")).upper()
            savings_rate = str(metrics.get("savings_rate", "MEDIUM")).upper()
            diversification = str(metrics.get("investment_diversification", "LOW")).upper()
            if debt_band == "HIGH":
                alerts.append({"type": "RISK", "title": "High Debt Burden", "severity": "HIGH", "reason": "High EMI burden can reduce financial flexibility."})
            if savings_rate == "LOW":
                alerts.append({"type": "RISK", "title": "Low Savings Alert", "severity": "MEDIUM", "reason": "Savings buffer may be insufficient for shocks."})
            if diversification in {"LOW", "MODERATE", "ALERT - CHECK ALLOCATION"}:
                alerts.append({"type": "OPPORTUNITY", "title": "Diversification Opportunity", "severity": "LOW", "reason": "Portfolio concentration risk can be reduced."})
            if not alerts:
                alerts.append({"type": "INFO", "title": "No Critical Alert", "severity": "LOW", "reason": "No major threshold breach detected from current context."})

        summary = f"Proactive alert check complete. I found {len(alerts)} alert(s) and explained each in plain language below."
        key_reasons = []
        for idx, alert in enumerate(alerts, 1):
            severity = alert.get("severity", "LOW")
            title = alert.get("title", "Alert")
            reason = alert.get("reason", "Threshold condition detected.")
            key_reasons.append(f"{idx}. [{severity}] {title}: {reason}")

        assumptions = [
            "Alerts are derived from currently available financial signals and masked context",
            f"Signals reviewed: {len(signals)}",
        ]

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": "HIGH" if alert_output else "MEDIUM",
            "actions": actions,
        }

    def _is_trace_query(self, query_lower: str) -> bool:
        """Detect explicit trace-introspection prompts."""
        trace_terms = ["reasoning trace", "which agents were used", "agent trace", "show the reasoning trace"]
        return any(t in query_lower for t in trace_terms)

    def _build_trace_response(
        self,
        execution_trace: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic trace summary from the execution trace context."""
        if not execution_trace:
            return {
                "summary": "No execution trace is available for this turn.",
                "key_reasons": ["Run a recommendation query first, then ask for reasoning trace."],
                "assumptions_used": [],
                "confidence": "LOW",
                "actions": actions,
            }

        key_reasons = []
        for idx, trace in enumerate(execution_trace, 1):
            agent = trace.get("agent", "unknown")
            reasoning = (trace.get("reasoning_steps") or ["Contributed to response"])[0]
            key_reasons.append(f"{idx}. {agent}: {reasoning}")

        return {
            "summary": "Here is the reasoning trace showing which agents were used and why.",
            "key_reasons": key_reasons,
            "assumptions_used": [],
            "confidence": "HIGH",
            "actions": actions,
        }

    def _is_stock_trading_query(self, query_lower: str) -> bool:
        """Detect stock trading buy/sell/hold queries."""
        trading_terms = [
            "should i buy", "should i sell", "should i hold",
            "buy or sell", "good investment", "worth buying", "worth investing",
            "entry point", "exit point", "bullish", "bearish",
            "trading recommendation", "investment recommendation",
            "bull case", "bear case",
        ]
        return any(t in query_lower for t in trading_terms)

    def _build_trading_analysis_response(
        self,
        trading_output: Dict[str, Any],
        query: str,
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build a user-friendly response from TradingAgents pipeline output.

        Synthesizes:
        - Multi-analyst reports (fundamentals, market, social, news)
        - Bull/Bear debate arguments
        - Trader decision (buy/sell/hold)
        - Risk assessment
        """
        ticker = trading_output.get("ticker", "N/A")
        recommendation = trading_output.get("recommendation", "HOLD")
        confidence = trading_output.get("confidence", "MEDIUM")
        reasoning = trading_output.get("reasoning", "")

        # Analyst reports
        reports = trading_output.get("analyst_reports", {})
        debate = trading_output.get("debate", {})
        trader = trading_output.get("trader_decision", {})
        risk = trading_output.get("risk_assessment", {})

        # Build summary
        summary_parts = [
            f"**{ticker} Trading Analysis — Recommendation: {recommendation}** (Confidence: {confidence})",
        ]

        if reasoning:
            summary_parts.append(f"\n{reasoning}")

        # Add analyst highlights
        if reports:
            summary_parts.append("\n**Analyst Insights:**")
            for report_name, report_content in reports.items():
                if report_content and isinstance(report_content, str):
                    # Take first 150 chars as highlight
                    highlight = report_content[:150].strip()
                    if len(report_content) > 150:
                        highlight += "..."
                    label = report_name.replace("_", " ").title()
                    summary_parts.append(f"• {label}: {highlight}")

        # Add debate highlights
        if debate.get("bull_arguments") or debate.get("bear_arguments"):
            summary_parts.append("\n**Bull vs Bear Debate:**")
            if debate.get("bull_arguments"):
                bull_highlight = str(debate["bull_arguments"])[:200]
                summary_parts.append(f"🐂 Bull Case: {bull_highlight}")
            if debate.get("bear_arguments"):
                bear_highlight = str(debate["bear_arguments"])[:200]
                summary_parts.append(f"🐻 Bear Case: {bear_highlight}")

        summary = "\n".join(summary_parts)

        # Key reasons
        key_reasons = []
        if isinstance(trader, dict):
            if trader.get("action"):
                key_reasons.append(f"Trader recommendation: {trader['action']}")
            if trader.get("reasoning"):
                key_reasons.append(f"Rationale: {trader['reasoning'][:200]}")

        if isinstance(risk, dict) and risk.get("risk_debate_state"):
            risk_state = risk["risk_debate_state"]
            if isinstance(risk_state, dict):
                key_reasons.append(f"Risk assessment conducted with {risk_state.get('count', 0)} debate round(s)")

        key_reasons.append(f"Analysis used {len([r for r in reports.values() if r])} analyst report(s)")

        assumptions = [
            "Analysis based on publicly available market data",
            f"Analysis date: {trading_output.get('analysis_date', 'current')}",
            "Past performance is not indicative of future results",
            "This is not financial advice; consult a certified advisor before trading",
        ]

        return {
            "summary": summary,
            "key_reasons": key_reasons,
            "assumptions_used": assumptions,
            "confidence": confidence,
            "actions": actions,
        }

    def _is_technical_output_query(self, query_lower: str) -> bool:
        """Detect code-first technical output requests (charts, forecasts, simulations)."""
        technical_output_keywords = [
            "plot", "chart", "graph", "visualize", "prediction", "predict", "forecast",
            "simulate", "backtest", "run code", "python", "model", "stock price",
        ]
        return any(kw in query_lower for kw in technical_output_keywords)

    def _extract_image_actions(self, images: Any) -> List[Dict[str, str]]:
        """
        Normalize image payloads into UI actions.
        Supports:
        - {"base64": "...", "name": "..."}
        - {"data": "data:image/..."} or {"url": "..."} or {"path": "..."} or {"name": "..."}
        - "data:image/..." or "http(s)://..." or "filename.png"
        """
        actions: List[Dict[str, str]] = []
        if not images or not isinstance(images, list):
            return actions

        for idx, img in enumerate(images, 1):
            image_data = None
            description = "Generated Chart"

            if isinstance(img, dict):
                base64_data = img.get("base64")
                if isinstance(base64_data, str) and base64_data.strip():
                    image_data = f"data:image/png;base64,{base64_data}"
                else:
                    raw_data = img.get("data")
                    if isinstance(raw_data, str) and raw_data.strip():
                        image_data = raw_data
                    elif isinstance(img.get("url"), str) and img.get("url", "").strip():
                        image_data = img["url"]
                    elif isinstance(img.get("path"), str) and img.get("path", "").strip():
                        image_data = img["path"]
                    else:
                        filename = str(img.get("name", "")).strip().split("/")[-1]
                        if filename:
                            image_data = f"/files/{filename}"
                            logger.warning(f"Image missing base64 data, using URL fallback: {filename}")

                if isinstance(img.get("description"), str) and img["description"].strip():
                    description = img["description"].strip()

            elif isinstance(img, str):
                raw = img.strip()
                if raw:
                    if raw.startswith("data:image") or raw.startswith("http://") or raw.startswith("https://") or raw.startswith("/"):
                        image_data = raw
                    else:
                        image_data = f"/files/{raw.split('/')[-1]}"

            if image_data:
                actions.append({
                    "type": "image",
                    "data": image_data,
                    "description": f"{description} {idx}" if len(images) > 1 else description,
                })

        return actions

    def _build_code_failure_response(
        self,
        error_message: str,
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Return deterministic response when chart-generation code fails."""
        concise_error = error_message.strip().replace("\n", " ")
        if len(concise_error) > 220:
            concise_error = concise_error[:220].rstrip() + "..."
        return {
            "summary": (
                "I could not generate the chart because the code execution environment failed. "
                f"Error: {concise_error}"
            ),
            "key_reasons": [
                "Chart rendering requires successful code execution plus generated image artifacts",
                "No valid chart image was returned for this run",
                "Retry once sandbox execution and market-data access are available",
            ],
            "assumptions_used": [
                "No synthetic chart was generated",
            ],
            "confidence": "LOW",
            "actions": actions,
        }

    def _build_code_missing_chart_response(self) -> Dict[str, Any]:
        """Return deterministic response when code succeeds but image artifact is missing."""
        return {
            "summary": (
                "The analysis run completed, but no chart image artifact was produced in this response. "
                "Please rerun the request so I can attach the chart."
            ),
            "key_reasons": [
                "Execution reported success but returned zero image artifacts",
                "UI can only display charts that arrive as image actions",
                "A rerun usually regenerates the visual artifact",
            ],
            "assumptions_used": [
                "No placeholder image was fabricated",
            ],
            "confidence": "MEDIUM",
            "actions": [],
        }


    def _build_prompt(self, query: str, metrics: Dict[str, Any], signals: List[str],
                          reasoning: List[str], facts: List[str], code_output: Dict[str, Any],
                          user_age: Optional[int] = None,
                          monthly_income: Optional[float] = None,
                          specific_calculations: Dict[str, Any] = None,
                          net_worth: Optional[float] = None,
                          credit_score: Optional[int] = None,
                          monthly_expenses: Optional[float] = None,
                          total_assets: Optional[float] = None,
                          total_liabilities: Optional[float] = None,
                          asset_classes: List[str] = None) -> str:
        """Build a prompt for the LLM to generate explanation with full MCP financial context."""
        query_lower = query.lower().strip()
        specific_calculations = specific_calculations or {}
        house_keywords = ["house", "home", "property", "purchase", "buy", "emi", "down payment", "afford"]
        is_house_query = any(kw in query_lower for kw in house_keywords)
        monthly_income_display = f"₹{monthly_income:,.0f}" if monthly_income else "N/A"
        is_technical_output_query = self._is_technical_output_query(query_lower)


        # 1. CHECK FOR CODE EXECUTION RESULTS FIRST (Prioritize "Action" over "Advice")
        if code_output and code_output.get("success") and not is_house_query and is_technical_output_query:
            output_text = code_output.get("output", "")
            explanation = code_output.get("explanation", "")
            images = code_output.get("images", [])

            prompt = f"""User Query: {query}

            Code Execution Result:
            - Success: True
            - Generated Output: {output_text}
            - Generated Images: {len(images)} images created (e.g., charts)
            - Technical Explanation: {explanation}

            The user asked for an analysis that required code execution (e.g., plotting, calculation).
            The system has successfully run the code.

            Generate a response that:
            1. Confirms the task was completed (e.g., "I have generated the plot...")
            2. Explains the result or chart briefly based on the technical explanation
            3. Mentions that the visual is available below

            Output as JSON with keys: summary (the confirmation and explanation), key_reasons (steps taken in code), assumptions_used (array), confidence ("HIGH")"""
            return prompt

        elif code_output and not code_output.get("success") and (code_output.get("stderr") or code_output.get("error")) and not is_house_query and is_technical_output_query:
            # Code ran but failed
            error_msg = code_output.get("stderr") or code_output.get("error") or "Unknown error"
            prompt = f"""User Query: {query}

            Code Execution Failed:
            - Error: {error_msg}

            The user asked for a technical task, but the code failed to run.

            Generate a response that:
            1. Apologizes for the technical issue
            2. Briefly explains what went wrong (based on the error)
            3. Suggests trying again or rephrasing

            Output as JSON with keys: summary (apology and error explanation), key_reasons (empty array), assumptions_used (empty array), confidence ("LOW")"""
            return prompt

        # Check if this is a Greeting
        greeting_words = ["hi", "hello", "hey", "greetings", "good morning", "good evening"]
        is_greeting = any(query_lower == g or query_lower.startswith(g + " ") for g in greeting_words)

        if is_greeting:
            return """The user sent a greeting. Respond warmly and professionally as their AI Financial Advisor.

Generate a friendly greeting response that:
1. Welcomes them warmly
2. Briefly mentions you can help with financial questions (investments, savings, retirement, budgeting)
3. Asks how you can help them today

Output as JSON with keys: summary (your greeting response), key_reasons (empty array), assumptions_used (empty array), confidence ("HIGH")"""

        # Check for emergency fund / job loss queries
        emergency_keywords = ["job", "survive", "survival", "lost", "lose", "emergency", "unemploy", "layoff", "fired"]
        is_emergency_query = any(kw in query_lower for kw in emergency_keywords)

        if is_emergency_query:
            savings_rate = metrics.get('savings_rate', 'MEDIUM')
            if savings_rate == 'LOW':
                survival_estimate = "1-2 months"
            elif savings_rate == 'MEDIUM':
                survival_estimate = "3-6 months"
            else:
                survival_estimate = "6+ months"

            prompt = f"""User Query: {query}

Financial Situation:
- Savings Rate: {savings_rate}
- Debt Level: {metrics.get('debt_to_income_ratio', 'UNKNOWN')}
- Investment Diversification: {metrics.get('investment_diversification', 'UNKNOWN')}

The user is asking about emergency preparedness or job loss survival.

Based on their {savings_rate} savings rate, estimate they could survive approximately {survival_estimate} without income.

Generate a response that:
1. Directly answers: "Based on your {savings_rate} savings rate, you could survive approximately {survival_estimate} without income."
2. Explains what this means practically
3. Provides 2-3 tips to improve their emergency fund

Output as JSON with keys: summary (2-3 sentences with the specific survival estimate), key_reasons (3-4 specific tips), assumptions_used (array), confidence (MEDIUM)"""
            return prompt


        # NEW: Check for user age queries
        age_keywords = ["age", "how old"]
        is_age_query = any(kw in query_lower for kw in age_keywords) and any(pronoun in query_lower for pronoun in ["my", "me", "i"])

        if is_age_query:
            if user_age:
                retirement_years = 65 - user_age if user_age < 65 else 0
                prompt = f"""User Query: {query}

User Age: {user_age} years (extracted from credit report)
Years to retirement (assuming age 65): {retirement_years} years

The user is asking about their age.

Generate a response that:
1. Clearly states: "Your age is {user_age} years."
2. Mentions retirement planning timeline if relevant: "You have {retirement_years} years until standard retirement age (65)."
3. Provides age-appropriate investment strategy advice
4. Suggests specific financial milestones for their age group

Output as JSON with keys: summary, key_reasons, assumptions_used, confidence ("HIGH")"""
                return prompt
            else:
                prompt = f"""User Query: {query}

Age data not available in user profile.

Generate a response that:
1. Apologizes that age information is not currently available
2. Explains that age data would be extracted from credit report or user profile
3. Suggests how to update their profile or provide this information
4. Offers general age-independent financial advice instead

Output as JSON with keys: summary, key_reasons, assumptions_used, confidence ("LOW")"""
                return prompt

        # NEW: Check for house purchase queries with calculations
        if is_house_query and specific_calculations:
            calc = specific_calculations
            prompt = f"""User Query: {query}

House Purchase Calculations:
- Down Payment Required: {calc.get('down_payment_formatted', 'N/A')} (20% of price)
- Loan Amount: {calc.get('loan_formatted', 'N/A')}
- Monthly EMI: {calc.get('emi_formatted', 'N/A')} @ 8.5% for 20 years
- Required Credit Score: {calc.get('credit_score_required', 'N/A')}+
- Reason: {calc.get('credit_score_reason', '')}
- Debt-to-Income After Loan: {calc.get('dti_after_loan', 'N/A')}
- Affordability: {calc.get('affordability', 'N/A')}
- Reason: {calc.get('affordability_reason', '')}
- Current Savings: ₹{calc.get('current_savings', 0):,.0f}
- Savings Gap: ₹{calc.get('savings_gap', 0):,.0f}
- Months to Save: {calc.get('months_to_save', 0)} months

User's Monthly Income: {monthly_income_display}

Generate a response that:
1. Clearly states the required credit score: {calc.get('credit_score_required')}+
2. Explains the down payment needed and EMI amount
3. Provides NUMBERED STEPS to achieve this goal:
   Step 1: Build credit score to {calc.get('credit_score_required')}+ (current strategies)
   Step 2: Save {calc.get('down_payment_formatted')} for down payment (timeline: {calc.get('months_to_save')} months)
   Step 3: Ensure income stability for EMI of {calc.get('emi_formatted')}
   Step 4: Apply for home loan pre-approval
4. Assesses affordability: {calc.get('affordability')} - {calc.get('affordability_reason')}
5. Provides realistic timeline estimate

BE SPECIFIC with the numbers. DO NOT give generic advice.

Output as JSON with keys: summary, key_reasons (specific steps), assumptions_used (8.5% interest, 20-year tenure), confidence ("HIGH")"""
            return prompt

        # NEW: Check for stock/investment queries with web data
        stock_keywords = ["stock", "predict", "price", "forecast", "tesla", "invest"]
        is_stock_query = any(kw in query_lower for kw in stock_keywords)

        if is_stock_query and facts:
            facts_text = "\n".join([f"- {fact}" for fact in facts[:3]])
            prompt = f"""User Query: {query}

Web Data Retrieved:
{facts_text}

Generate a response that:
1. Includes current stock price from web data if available
2. Provides specific price prediction with timeframe
3. Lists key factors influencing the prediction (from web data)
4. Adds disclaimer about market volatility

CRITICAL: Use the web data above. DO NOT give generic stock advice without current data.

Output as JSON with keys: summary, key_reasons, assumptions_used, confidence"""
            return prompt

        # NEW: Check for historical/comparison queries
        historical_keywords = ["worst", "downfall", "crash", "history", "who invested"]
        is_historical_query = any(kw in query_lower for kw in historical_keywords)

        if is_historical_query and facts:
            facts_text = "\n".join([f"- {fact}" for fact in facts[:5]])
            prompt = f"""User Query: {query}

Historical Data from Web:
{facts_text}

Generate a response that:
1. Provides SPECIFIC examples from the web data (names, dates, percentages)
2. Lists 3-5 concrete examples with details
3. Explains the context and lessons learned

DO NOT give generic historical narratives. Use the specific data above.

Output as JSON with keys: summary, key_reasons, assumptions_used, confidence ("HIGH")"""
            return prompt

        # Check for insurance queries
        insurance_keywords = ["insurance", "term life", "health insurance", "policy", "premium", "coverage", "lic", "hdfc life"]
        is_insurance_query = any(kw in query_lower for kw in insurance_keywords)

        if is_insurance_query:
            prompt = f"""User Query: {query}

User's Financial Profile:
- Savings Rate: {metrics.get('savings_rate', 'MEDIUM')}
- Debt-to-Income Ratio: {metrics.get('debt_to_income_ratio', 'LOW')}

The user is asking about insurance. Generate a helpful response that includes:

1. Key factors to consider when buying term life insurance:
   - Coverage amount (typically 10-15x annual income)
   - Policy term (until retirement age, typically 60-65)
   - Premium affordability
   - Claim settlement ratio of insurer
   - Rider options (critical illness, accidental death)

2. Top 5 term life insurance plans in India:
   - **HDFC Life Click 2 Protect** - High claim settlement ratio (99%+)
   - **ICICI Prudential iProtect Smart** - Flexible premium options
   - **Max Life Smart Term Plan** - Comprehensive coverage
   - **Tata AIA Sampoorna Raksha** - Good value for money
   - **LIC Tech Term** - Government-backed security

3. A disclaimer about comparing plans on aggregator sites

Output as JSON with keys: summary (comprehensive response with all 5 plans listed), key_reasons (array of considerations), assumptions_used (array), confidence ("MEDIUM")"""
            return prompt

        # Check for stock/investment queries - require "stock" word to avoid false positives
        is_stock_query = ("stock" in query_lower or "stocks" in query_lower or
                          ("invest" in query_lower and "insurance" not in query_lower) or
                          "nifty" in query_lower or "sensex" in query_lower or
                          "share" in query_lower or "shares" in query_lower)

        if is_stock_query:
            prompt = f"""User Query: {query}

User's Financial Profile:
- Savings Rate: {metrics.get('savings_rate', 'MEDIUM')}
- Debt-to-Income Ratio: {metrics.get('debt_to_income_ratio', 'LOW')}
- Investment Diversification: {metrics.get('investment_diversification', 'LOW')}

Available Stock Data: {facts[:3] if facts else 'No external data'}

Generate a stock recommendation response that MUST include:
1. A list of EXACTLY 5 specific stock names with their current recommendations
2. For Indian users, recommend: Reliance Industries, HDFC Bank, Infosys, TCS, ICICI Bank
3. Brief reason for each recommendation (1 line each)
4. A disclaimer about consulting a financial advisor

The response should look like:
"Based on your profile, here are 5 stocks to consider:
1. **Reliance Industries** (₹2,850) - Diversified conglomerate with strong growth
2. **HDFC Bank** (₹1,650) - India's leading private bank
3. **Infosys** (₹1,780) - IT sector leader with global presence
4. **TCS** (₹3,950) - Consistent performer in IT services
5. **ICICI Bank** (₹1,100) - Growing retail banking portfolio

Note: This is for educational purposes. Please consult a SEBI-registered advisor."

Output as JSON with keys: summary (the full response with 5 stocks listed), key_reasons (array), assumptions_used (array), confidence ("MEDIUM")"""
            return prompt

        # Check for retirement corpus queries - use explicit retirement indicators only
        retirement_keywords = ["retire", "retirement", "pension", "corpus", "5cr", "crore", "fire"]
        is_retirement_query = any(kw in query_lower for kw in retirement_keywords)

        if is_retirement_query:
            savings_rate = metrics.get('savings_rate', 'MEDIUM')
            diversification = metrics.get('investment_diversification', 'LOW')

            prompt = f"""User Query: {query}

User's Financial Profile:
- Savings Rate: {savings_rate}
- Debt-to-Income Ratio: {metrics.get('debt_to_income_ratio', 'LOW')}
- Investment Diversification: {diversification}
- Signals: {signals}

The user is asking about retirement planning or a long-term financial goal (likely 5 crore retirement corpus).

GENERATE A SPECIFIC RESPONSE WITH REAL CALCULATIONS:

**If asking "at what age should I retire with 5cr":**
- Assume current age: 30-35 years old
- Goal: ₹5 crore ($600k USD)
- Based on {savings_rate} savings rate:
  * LOW savings: Retire at 55-60 years | Save ₹20,000-25,000/month | 25-30 years | Assumes 12% annual returns
  * MEDIUM savings: Retire at 50-55 years | Save ₹30,000-40,000/month | 20-25 years | Assumes 12% annual returns
  * HIGH savings: Retire at 45-50 years| Save ₹50,000-60,000/month | 15-20 years | Assumes 12% annual returns
- Provide specific age range and monthly savings amount based on their current savings rate

**If asking "what steps to take" or "how to reach 5cr":**
Provide 5-6 SPECIFIC, NUMBERED action steps:
1. **Increase Monthly SIP**: Invest ₹X,000/month (calculate based on savings_rate: LOW=₹25k, MEDIUM=₹35k, HIGH=₹50k)
2. **Tax-Advantaged Accounts**: Open PPF (₹1.5L/year), NPS (₹50k/year for tax benefit), maximize EPF
3. **Asset Allocation** (especially if diversification is {diversification}):
   - 60% Equity (Nifty 50 index funds, Large-cap mutual funds)
   - 30% Debt (Corporate bonds, Debt mutual funds)
   - 10% Gold (Gold ETF or Sovereign Gold Bonds)
4. **Automate Investments**: Set up automatic SIPs on 1st of every month
5. **Annual Rebalancing**: Review portfolio every year, rebalance if needed
6. **Emergency Fund First**: Build 6 months expenses (₹3-5 lakhs) before aggressive investing

**If asking "how to increase savings/income":**
Provide 5 UNIQUE strategies they haven't heard before:
1. **Reduce Subscriptions**: Cancel unused subscriptions (OTT, gym, etc.) - Save ₹2,000-3,000/month
2. **Side Hustle**: Freelancing/consulting in your domain - Target ₹10,000-15,000/month extra
3. **Optimize Taxes**: Use Section 80C, 80D deductions - Save ₹30,000-50,000/year
4. **Invest Windfall Income**: Put 100% of bonuses, increments into investments
5. **Employer EPF Matching**: Maximize VPF contribution to get full employer match

**Include Milestones**:
- Age 35: ₹15-25 lakhs
- Age 40: ₹60-80 lakhs
- Age 45: ₹1.5-2 crores
- Age 50: ₹3-3.5 crores
- Age 55: ₹5+ crores

Output as JSON:
- summary: 2-3 sentences with SPECIFIC retirement age or monthly savings amount
- key_reasons: 5-6 NUMBERED, SPECIFIC action steps (not generic  advice)
- assumptions_used: ["Savings Rate: {savings_rate}", "Investment Diversification: {diversification}", "Expected Returns: 12% annually"]
- confidence: "MEDIUM"

CRITICAL: Use actual numbers (₹20,000/month, retire at 55, etc.), not vague statements."""
            return prompt


        # Standard query - could be financial analysis OR factual question
        # Check if we have external knowledge facts (from knowledge agent)
        # Filter out useless placeholder facts
        useful_facts = [f for f in facts if f and "No specific information found" not in f and len(f) > 20] if facts else []
        has_knowledge = bool(useful_facts and len(useful_facts) > 0)
        has_financial_data = metrics.get('savings_rate') != 'UNKNOWN' or monthly_income or user_age

        # DEBUG: Log what we received
        logger.info(f"EXPLAINABILITY DEBUG: facts={facts[:2] if facts else 'None'}, useful_facts_count={len(useful_facts)}, has_knowledge={has_knowledge}, has_financial_data={has_financial_data}")

        # Check if this is a stock query (even if finance_reasoning ran)
        stock_keywords = ["price", "stock", "trading", "worth", "value", "hdfc", "reliance", "tcs", "infosys", "tesla"]
        is_stock_query = any(kw in query.lower() for kw in stock_keywords)

        logger.info(f"EXPLAINABILITY DEBUG: is_stock_query={is_stock_query}, query_lower={query.lower()[:50]}")

        # For stock queries OR any factual query with knowledge, use factual prompt
        if has_knowledge and (is_stock_query or not has_financial_data):
            logger.info("EXPLAINABILITY DEBUG: Using FACTUAL prompt for stock/factual query")
            # This is a factual query (e.g., "what is the price of HDFC stock")
            # Don't give financial advice, just relay the facts
            prompt = f"""User Query: {query}

External Knowledge Retrieved:
{chr(10).join('- ' + fact for fact in useful_facts[:5]) if useful_facts else '- No specific data found'}

Your task: Answer the user's query using ONLY the external knowledge provided above. Be specific and factual.
- If the data contains stock prices, report them exactly as provided
- If the data has specific numbers, use them
- DO NOT give generic financial advice
- DO NOT mention savings rates or DTI unless the user asks for it
- Keep your response concise and directly answer the question

Respond in JSON format with this structure:

The user asked a factual question (about stock prices, market data, or general information).
External knowledge has been retrieved to answer this.

Generate a response that:
1. DIRECTLY answers their question using the facts provided
2. Presents the information clearly and concisely
3. If no relevant facts were found, politely say you don't have that information

DO NOT provide generic financial advice (PPF/EPF/NPS) - just answer their specific question.

Output as JSON with keys:
- summary (direct answer to their question using the facts)
- key_reasons (key points from the facts, if any)
- assumptions_used (empty array or relevant context)
- confidence (HIGH if facts found, LOW if not)"""
            return prompt

        # Build comprehensive financial snapshot for the LLM
        asset_classes = asset_classes or []
        asset_names = [a.replace("ASSET_TYPE_", "").replace("_", " ").title() for a in asset_classes] if asset_classes else []

        financial_snapshot = ""
        if any([monthly_income, net_worth, credit_score, total_assets]):
            financial_snapshot = "\n\n== USER'S FINANCIAL SNAPSHOT (from MCP/Fi Money) =="
            if monthly_income:
                financial_snapshot += f"\n- Monthly Income: ₹{monthly_income:,.0f}"
            if monthly_expenses:
                financial_snapshot += f"\n- Monthly Expenses: ₹{monthly_expenses:,.0f}"
                if monthly_income and monthly_income > 0:
                    sr = (monthly_income - monthly_expenses) / monthly_income * 100
                    financial_snapshot += f"\n- Savings Rate: {sr:.1f}%"
            if net_worth:
                financial_snapshot += f"\n- Total Net Worth: ₹{net_worth:,.0f}"
            if total_assets:
                financial_snapshot += f"\n- Total Assets: ₹{total_assets:,.0f}"
            if total_liabilities:
                financial_snapshot += f"\n- Total Liabilities: ₹{total_liabilities:,.0f}"
            if credit_score:
                financial_snapshot += f"\n- Credit Score: {credit_score}"
            if asset_names:
                financial_snapshot += f"\n- Asset Classes: {', '.join(asset_names)}"
            if user_age:
                financial_snapshot += f"\n- Age: {user_age} years"
            financial_snapshot += "\n== END FINANCIAL SNAPSHOT =="

        # Financial planning query with metrics AND full financial data
        prompt = f"""User Query: {query}
{financial_snapshot}

Financial Analysis Results:
- Savings Rate: {metrics.get('savings_rate', 'UNKNOWN')}
- Debt-to-Income Ratio: {metrics.get('debt_to_income_ratio', 'UNKNOWN')}
- Investment Diversification: {metrics.get('investment_diversification', 'UNKNOWN')}
- Signals Detected: {signals}
- Supporting Facts: {facts[:2] if facts else 'None'}

You are a personalized AI financial advisor. You have access to this user's ACTUAL financial data from their connected accounts (via Fi Money MCP).

Generate a helpful, PERSONALIZED financial response that:
1. DIRECTLY answers the user's question using their ACTUAL financial data
2. References their SPECIFIC numbers (net worth, income, credit score, asset allocation)
3. Provides personalized actionable recommendations based on their financial situation
4. Calculates specific amounts when possible (e.g., "save ₹15,000/month" not "save more")

CRITICAL REQUIREMENTS:
1. **Be Personal**: Use the user's actual financial data in your response. Say "Your net worth is ₹6.58L" not "Your net worth is unknown"
2. **Be Specific**: Use actual numbers, percentages, and timelines from their data
3. **Provide Action Steps**: Give numbered, concrete steps the user can take
4. **Asset-Aware**: Reference their actual investments (MFs, EPF, FDs, savings accounts)
5. **Use Indian Context**: ₹ currency, PPF, EPF, NPS, ELSS, etc.

Output as JSON with keys: summary (2-4 sentences with specific personalized advice referencing their actual numbers), key_reasons (3-5 actionable steps), assumptions_used (array of data sources used), confidence (HIGH if financial snapshot available, MEDIUM otherwise)"""
        return prompt

    def _build_summary(self, query: str, metrics: Dict[str, Any], signals: List[str], facts: List[str] = None) -> str:
        """Build a human-readable summary based on query context."""

        # Extract metric values
        savings = metrics.get("savings_rate", "UNKNOWN")
        dti = metrics.get("debt_to_income_ratio", "UNKNOWN")
        diversification = metrics.get("investment_diversification", "UNKNOWN")

        query_lower = query.lower()

        # Retirement-focused query
        if "retire" in query_lower or "retirement" in query_lower:
            if savings == "LOW":
                summary = "Based on your current savings rate (LOW), you may need to increase your monthly savings to meet retirement goals. "
            elif savings == "HIGH":
                summary = "Your savings rate is healthy for retirement planning. "
            else:
                summary = "Your savings rate is moderate for retirement planning. "

            if diversification == "LOW":
                summary += "Consider diversifying investments across more asset classes for long-term growth."
            elif diversification == "HIGH":
                summary += "Your investments are well-diversified, which is good for long-term stability."
            return summary

        # Debt-focused query
        if "debt" in query_lower or "loan" in query_lower or "dti" in query_lower:
            if dti == "HIGH":
                return "Your debt-to-income ratio is HIGH, which may limit your borrowing capacity. Consider reducing existing debt before taking on new obligations."
            elif dti == "LOW":
                return "Your debt-to-income ratio is LOW and manageable. This gives you flexibility for future borrowing if needed."
            else:
                return "Your debt levels appear moderate. Monitor your monthly obligations to maintain financial health."

        # Savings-focused query
        if "save" in query_lower or "saving" in query_lower:
            if savings == "LOW":
                return "Your savings rate is currently LOW. Consider setting up automatic transfers to increase your savings rate to at least 20% of income."
            elif savings == "HIGH":
                return "Excellent! Your savings rate is HIGH. You're building a strong financial foundation."
            else:
                return "Your savings rate is MEDIUM. There's room to increase savings for faster goal achievement."

        # Investment-focused query
        if "invest" in query_lower or "mutual fund" in query_lower or "stock" in query_lower:
            # Include knowledge facts if available
            if facts and len(facts) > 0 and facts[0] != "No specific information found for this query":
                return f"{facts[0]} Based on your portfolio, your investment diversification is {diversification}."
            if diversification == "LOW":
                return "Your investments could benefit from more diversification across asset classes like equity, debt, and gold."
            elif diversification == "HIGH":
                return "Your investments are well-diversified across multiple asset classes, reducing overall portfolio risk."
            return "Your investment diversification is moderate. Consider reviewing asset allocation based on your risk tolerance."

        # Tax-focused query
        if "tax" in query_lower:
            if facts and len(facts) > 0:
                return facts[0]
            return "For tax-related advice, I recommend consulting the latest tax regulations or a certified tax professional."

        # General financial health query
        summary_parts = []

        if savings == "LOW":
            summary_parts.append("Your savings rate is currently low")
        elif savings == "HIGH":
            summary_parts.append("You have a healthy savings rate")
        else:
            summary_parts.append("Your savings rate is moderate")

        if dti == "HIGH":
            summary_parts.append("with a high debt burden that needs attention")
        elif dti == "LOW":
            summary_parts.append("with manageable debt levels")

        if diversification == "LOW":
            summary_parts.append("Your investments could benefit from more diversification")
        elif diversification == "HIGH":
            summary_parts.append("Your investments are well-diversified")

        if summary_parts:
            return ". ".join(summary_parts) + "."
        else:
            return "Based on your financial profile, here's what we found."

    def _build_key_reasons(
        self,
        signals: List[str],
        reasoning: List[str]
    ) -> List[str]:
        """Extract key reasons from signals and reasoning."""
        key_reasons = []

        # Add signals as reasons
        for signal in signals[:3]:  # Limit to top 3
            key_reasons.append(signal)

        # Add summary reasoning
        if reasoning:
            key_reasons.append(f"Analysis included: {reasoning[0]}")

        if not key_reasons:
            key_reasons.append("Financial analysis completed based on available data")

        return key_reasons

    def _build_assumptions(self, metrics: Dict[str, Any]) -> List[str]:
        """Build list of assumptions used in analysis."""
        assumptions = [
            "Stable income assumed",
            "No major changes in expenses expected"
        ]

        if metrics.get("savings_rate"):
            assumptions.append("Savings calculated from income-expense patterns")

        return assumptions

    def _calculate_confidence(
        self,
        base: str,
        signal_count: int,
        fact_count: int
    ) -> str:
        """Calculate final confidence level."""
        # Start with base confidence
        confidence_score = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get(base, 2)

        # Adjust based on evidence
        if signal_count >= 3:
            confidence_score += 1
        if fact_count >= 2:
            confidence_score += 1

        # Convert back to band
        if confidence_score >= 4:
            return "HIGH"
        elif confidence_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
