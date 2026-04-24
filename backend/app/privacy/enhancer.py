"""
Privacy Enhancer
Orchestrates privacy-preserving operations including anonymization,
differential privacy noise injection, and data deletion.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import random
from datetime import datetime

from app.privacy.masking import PrivacyMasker
from app.privacy.encryption import he_service

class PrivacyEnhancer:
    """
    Enhances data privacy through multiple techniques.
    """

    def __init__(self):
        self.masker = PrivacyMasker()
        self.he = he_service
        self._deletion_requests = {}  # In-memory store for requests

    def apply_differential_privacy(self, value: float, epsilon: float = 1.0) -> float:
        """
        Add Laplacian noise for differential privacy.

        Args:
            value: The true value
            epsilon: Privacy budget (lower = more noise/privacy)

        Returns:
            Noisy value
        """
        # Sensitivity assumed to be 1.0 for normalized data
        # Scale = sensitivity / epsilon
        scale = 1.0 / epsilon
        noise = random.choice([-1, 1]) * random.expovariate(1/scale)
        return value + noise

    def anonymize_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a privacy-safe view of user data.
        - Masks identifiers
        - Bands financial values
        """
        safe_data = user_data.copy()

        # Remove direct identifiers
        for field in ['name', 'email', 'phone', 'pan', 'aadhaar']:
            if field in safe_data:
                safe_data[field] = "[REDACTED]"

        # Mask financial fields if present raw
        if 'monthly_income' in safe_data and isinstance(safe_data['monthly_income'], (int, float)):
             safe_data['income_band'] = self.masker.mask_income(safe_data['monthly_income'])
             del safe_data['monthly_income']

        if 'credit_score' in safe_data and isinstance(safe_data['credit_score'], int):
             safe_data['credit_score_band'] = self.masker.mask_credit_score(safe_data['credit_score'])
             del safe_data['credit_score']

        return safe_data

    def request_data_deletion(self, user_id: str, reason: str = "User request") -> str:
        """
        Log a data deletion request (GDPR/DPDP compliance).
        """
        request_id = f"DEL-{int(datetime.utcnow().timestamp())}"

        self._deletion_requests[request_id] = {
            "user_id": user_id,
            "status": "PENDING",
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"Data deletion requested for {user_id}. Ticket: {request_id}")
        return request_id

    def check_deletion_status(self, request_id: str) -> Dict[str, Any]:
        """Check status of a deletion request."""
        return self._deletion_requests.get(request_id, {"status": "NOT_FOUND"})

    def execute_deletion(self, request_id: str) -> bool:
        """
        Execute the deletion (Mock implementation).
        In production, this would wipe DB records.
        """
        if request_id in self._deletion_requests:
            logger.warning(f"EXECUTING DATA DELETION for Ticket {request_id}")
            # ... database delete calls would go here ...
            self._deletion_requests[request_id]["status"] = "COMPLETED"
            self._deletion_requests[request_id]["completed_at"] = datetime.utcnow().isoformat()
            return True
        return False

    def sanitize_api_response(self, response: Dict[str, Any], raw_values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize API response before sending to frontend.

        This ensures raw financial values (actual ₹ amounts, credit scores)
        are replaced with masked bands in user-visible response fields.
        The frontend should NEVER see exact financial figures.

        Args:
            response: The API response dict
            raw_values: The raw financial values to check against

        Returns:
            Sanitized response safe for frontend display
        """
        sanitized = response.copy()

        # Fields that should never contain raw values in API responses
        sensitive_fields = ["message", "summary"]

        for field in sensitive_fields:
            if field in sanitized and isinstance(sanitized[field], str):
                text = sanitized[field]

                # Replace raw income amounts with bands
                if raw_values.get("monthly_income") and isinstance(raw_values["monthly_income"], (int, float)):
                    income = raw_values["monthly_income"]
                    band = self.masker.mask_income(income)
                    # Replace common formats of the raw value
                    for fmt in [
                        f"₹{income:,.0f}", f"₹{income:,.2f}",
                        f"₹{int(income):,}", f"Rs.{income:,.0f}",
                        f"₹{income:.0f}", str(int(income)),
                    ]:
                        if fmt in text:
                            text = text.replace(fmt, f"[{band} income range]")

                # Replace raw credit scores
                if raw_values.get("credit_score") and isinstance(raw_values["credit_score"], (int, float)):
                    score = raw_values["credit_score"]
                    band = self.masker.mask_credit_score(int(score))
                    text = text.replace(str(int(score)), f"[{band} credit score]")

                # Replace raw net worth
                if raw_values.get("net_worth") and isinstance(raw_values["net_worth"], (int, float)):
                    nw = raw_values["net_worth"]
                    band = self.masker.mask_net_worth(nw)
                    for fmt in [
                        f"₹{nw:,.0f}", f"₹{nw:,.2f}",
                        f"₹{int(nw):,}", f"Rs.{nw:,.0f}",
                    ]:
                        if fmt in text:
                            text = text.replace(fmt, f"[{band} net worth range]")

                sanitized[field] = text

        # Remove raw values from any nested data in the response
        if "agent_contributions" in sanitized:
            for contrib in sanitized.get("agent_contributions", []):
                for key in ["raw_values", "financial_context"]:
                    contrib.pop(key, None)

        # Remove any direct raw_values leakage
        sanitized.pop("raw_values", None)

        return sanitized

# Singleton
privacy_enhancer = PrivacyEnhancer()

