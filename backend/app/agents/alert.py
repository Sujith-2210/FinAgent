"""
Alert Agent
Generates proactive financial alerts based on detected signals.
"""

from typing import Dict, Any, List
from loguru import logger

from app.agents.base import BaseAgent


class AlertAgent(BaseAgent):
    """
    Alert Agent - Proactive intelligence.
    
    Responsibilities:
    - Monitor financial signals
    - Detect risk or opportunity triggers
    - Generate concise alerts with severity
    
    Rules:
    - Trigger alerts only when thresholds are crossed
    - Assign appropriate severity levels
    - Do NOT provide full advice
    """
    
    def __init__(self):
        super().__init__()
        self.name = "alert"
        self.description = "Generates proactive financial alerts"
        self.read_layers = {"transactional_signals", "user_financial_context"}
        self.write_layers = {"alert_context"}
        
        self.system_prompt = """You are an Alert Agent.

Your task is to:
- Monitor financial signals
- Detect risk or opportunity triggers
- Generate concise alerts

Rules:
- Trigger alerts only when thresholds are crossed
- Assign severity levels (LOW, MEDIUM, HIGH)
- Do NOT provide full advice
- Output must be structured JSON"""
        
        # Define alert rules
        self._alert_rules = self._initialize_alert_rules()
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "signals": {"type": "array", "items": {"type": "string"}},
                "context": {"type": "object"}
            }
        }
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "alerts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["RISK", "OPPORTUNITY", "INFO"]},
                            "title": {"type": "string"},
                            "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                            "reason": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["alerts"]
        }
    
    def _initialize_alert_rules(self) -> List[Dict[str, Any]]:
        """Initialize alert detection rules."""
        return [
            {
                "trigger_keywords": ["high emi", "high debt", "debt burden"],
                "alert": {
                    "type": "RISK",
                    "title": "High Debt Burden",
                    "severity": "HIGH",
                    "reason": "Your debt obligations may be impacting financial flexibility"
                }
            },
            {
                "trigger_keywords": ["low savings", "savings rate low", "low emergency"],
                "alert": {
                    "type": "RISK",
                    "title": "Low Savings Alert",
                    "severity": "MEDIUM",
                    "reason": "Current savings rate is below recommended levels"
                }
            },
            {
                "trigger_keywords": ["credit utilization high", "high credit"],
                "alert": {
                    "type": "RISK",
                    "title": "High Credit Utilization",
                    "severity": "HIGH",
                    "reason": "Credit card usage exceeds recommended 30% threshold"
                }
            },
            {
                "trigger_keywords": ["low diversification", "limited diversification"],
                "alert": {
                    "type": "OPPORTUNITY",
                    "title": "Diversification Opportunity",
                    "severity": "LOW",
                    "reason": "Consider spreading investments across more asset classes"
                }
            },
            {
                "trigger_keywords": ["tax", "80c", "deduction"],
                "alert": {
                    "type": "OPPORTUNITY",
                    "title": "Tax Saving Opportunity",
                    "severity": "LOW",
                    "reason": "You may have unused tax deduction benefits"
                }
            },
            {
                "trigger_keywords": ["retirement", "delay", "timeline"],
                "alert": {
                    "type": "RISK",
                    "title": "Retirement Planning Alert",
                    "severity": "MEDIUM",
                    "reason": "Current trajectory may impact retirement goals"
                }
            }
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze signals and generate appropriate alerts.
        """
        signals = input_data.get("signals", [])
        context = input_data.get("context", {})
        
        self.record_context_access("transactional_signals")
        self.add_reasoning_step(f"Analyzing {len(signals)} signals for alert conditions")
        
        alerts = []
        
        # Check each signal against alert rules
        signals_text = " ".join(signals).lower()
        
        for rule in self._alert_rules:
            for keyword in rule["trigger_keywords"]:
                if keyword in signals_text:
                    self.add_reasoning_step(f"Triggered alert: {rule['alert']['title']}")
                    alerts.append(rule["alert"])
                    break  # Don't duplicate same alert
        
        # Check context for additional alerts
        if context:
            context_alerts = self._check_context_alerts(context)
            alerts.extend(context_alerts)
        
        # Deduplicate alerts by title
        seen_titles = set()
        unique_alerts = []
        for alert in alerts:
            if alert["title"] not in seen_titles:
                seen_titles.add(alert["title"])
                unique_alerts.append(alert)
        
        # Sort by severity (HIGH first)
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        unique_alerts.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        self.add_reasoning_step(f"Generated {len(unique_alerts)} alerts")
        
        return {
            "alerts": unique_alerts,
            "confidence": "HIGH" if unique_alerts else "MEDIUM"
        }
    
    def _check_context_alerts(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts from context data."""
        alerts = []
        
        financial_context = context.get("user_financial_context", {}).get("data", {})
        
        # Check credit profile
        credit = financial_context.get("credit_profile", {})
        if credit.get("credit_score_band") == "POOR":
            alerts.append({
                "type": "RISK",
                "title": "Credit Score Alert",
                "severity": "HIGH",
                "reason": "Your credit score is in the poor range"
            })
        
        # Check debt intensity
        liabilities = financial_context.get("liabilities_profile", {})
        if liabilities.get("debt_intensity") == "HIGH":
            alerts.append({
                "type": "RISK",
                "title": "Debt Level Warning",
                "severity": "HIGH",
                "reason": "Your debt levels are elevated"
            })
        
        return alerts
