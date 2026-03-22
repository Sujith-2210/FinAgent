"""
Privacy Masking Utilities
Converts raw financial values to privacy-preserving bands.

This is a CRITICAL component for privacy-by-design:
- Raw ₹ amounts → Bands (LOW/MEDIUM/HIGH)
- Credit scores → Bands (POOR/FAIR/GOOD/EXCELLENT)
- Ratios → Bands (LOW/MEDIUM/HIGH)

These masked values are what agents and LLMs see.
"""

from typing import Optional, Any
from enum import Enum
from loguru import logger


class IncomeBand(str, Enum):
    """Income bands (monthly, INR)."""
    LOW = "LOW"        # < ₹50,000
    MEDIUM = "MEDIUM"  # ₹50,000 - ₹2,00,000
    HIGH = "HIGH"      # > ₹2,00,000


class NetWorthBand(str, Enum):
    """Net worth bands (INR)."""
    LOW = "LOW"        # < ₹5,00,000
    MEDIUM = "MEDIUM"  # ₹5,00,000 - ₹50,00,000
    HIGH = "HIGH"      # > ₹50,00,000


class CreditScoreBand(str, Enum):
    """Credit score bands (300-900 scale)."""
    POOR = "POOR"           # < 550
    FAIR = "FAIR"           # 550 - 649
    GOOD = "GOOD"           # 650 - 749
    EXCELLENT = "EXCELLENT"  # >= 750


class DebtIntensityBand(str, Enum):
    """Debt-to-income ratio bands."""
    LOW = "LOW"        # DTI < 30%
    MEDIUM = "MEDIUM"  # DTI 30% - 50%
    HIGH = "HIGH"      # DTI > 50%


class SavingsRateBand(str, Enum):
    """Savings rate bands."""
    LOW = "LOW"        # < 10%
    MEDIUM = "MEDIUM"  # 10% - 30%
    HIGH = "HIGH"      # > 30%


class CreditUtilizationBand(str, Enum):
    """Credit utilization bands."""
    LOW = "LOW"        # < 30%
    MEDIUM = "MEDIUM"  # 30% - 70%
    HIGH = "HIGH"      # > 70%


class PrivacyMasker:
    """
    Privacy masking service for financial data.
    
    All methods take raw values and return privacy-preserving bands.
    No raw values should ever be exposed to agents or LLMs.
    """
    
    def mask_income(self, monthly_income_inr: Optional[float]) -> Optional[str]:
        """
        Convert monthly income to band.
        
        Thresholds:
        - LOW: < ₹50,000
        - MEDIUM: ₹50,000 - ₹2,00,000
        - HIGH: > ₹2,00,000
        """
        if monthly_income_inr is None:
            return None
        
        if monthly_income_inr < 50000:
            return IncomeBand.LOW.value
        elif monthly_income_inr <= 200000:
            return IncomeBand.MEDIUM.value
        else:
            return IncomeBand.HIGH.value
    
    def mask_net_worth(self, net_worth_inr: Optional[float]) -> Optional[str]:
        """
        Convert net worth to band.
        
        Thresholds:
        - LOW: < ₹5,00,000
        - MEDIUM: ₹5,00,000 - ₹50,00,000
        - HIGH: > ₹50,00,000
        """
        if net_worth_inr is None:
            return None
        
        if net_worth_inr < 500000:
            return NetWorthBand.LOW.value
        elif net_worth_inr <= 5000000:
            return NetWorthBand.MEDIUM.value
        else:
            return NetWorthBand.HIGH.value
    
    def mask_credit_score(self, credit_score: Optional[int]) -> Optional[str]:
        """
        Convert credit score (300-900) to band.
        
        Thresholds:
        - POOR: < 550
        - FAIR: 550 - 649
        - GOOD: 650 - 749
        - EXCELLENT: >= 750
        """
        if credit_score is None:
            return None
        
        if credit_score < 550:
            return CreditScoreBand.POOR.value
        elif credit_score < 650:
            return CreditScoreBand.FAIR.value
        elif credit_score < 750:
            return CreditScoreBand.GOOD.value
        else:
            return CreditScoreBand.EXCELLENT.value
    
    def mask_dti_ratio(self, dti_ratio: Optional[float]) -> Optional[str]:
        """
        Convert Debt-to-Income ratio to band.
        
        DTI = (Monthly Debt Payments / Monthly Income) × 100
        
        Thresholds:
        - LOW: < 30%
        - MEDIUM: 30% - 50%
        - HIGH: > 50%
        """
        if dti_ratio is None:
            return None
        
        if dti_ratio < 0.30:
            return DebtIntensityBand.LOW.value
        elif dti_ratio <= 0.50:
            return DebtIntensityBand.MEDIUM.value
        else:
            return DebtIntensityBand.HIGH.value
    
    def mask_savings_rate(self, savings_rate: Optional[float]) -> Optional[str]:
        """
        Convert savings rate to band.
        
        Savings Rate = (Monthly Savings / Monthly Income) × 100
        
        Thresholds:
        - LOW: < 10%
        - MEDIUM: 10% - 30%
        - HIGH: > 30%
        """
        if savings_rate is None:
            return None
        
        if savings_rate < 0.10:
            return SavingsRateBand.LOW.value
        elif savings_rate <= 0.30:
            return SavingsRateBand.MEDIUM.value
        else:
            return SavingsRateBand.HIGH.value
    
    def mask_credit_utilization(self, utilization: Optional[float]) -> Optional[str]:
        """
        Convert credit utilization to band.
        
        Credit Utilization = (Credit Used / Credit Limit) × 100
        
        Thresholds:
        - LOW: < 30%
        - MEDIUM: 30% - 70%
        - HIGH: > 70%
        """
        if utilization is None:
            return None
        
        if utilization < 0.30:
            return CreditUtilizationBand.LOW.value
        elif utilization <= 0.70:
            return CreditUtilizationBand.MEDIUM.value
        else:
            return CreditUtilizationBand.HIGH.value
    
    def calculate_debt_intensity(self, net_worth_data: Any) -> Optional[str]:
        """
        Calculate debt intensity from net worth data.
        
        Based on liability-to-asset ratio and types of debt.
        """
        if net_worth_data is None:
            return None
        
        try:
            # Handle NetWorthResponse from FiMCPService
            total_assets = sum(
                a.value.units if hasattr(a, 'value') else getattr(a, 'value_inr', 0)
                for a in net_worth_data.assets
            )
            total_liabilities = sum(
                l.value.units if hasattr(l, 'value') else getattr(l, 'value_inr', 0)
                for l in net_worth_data.liabilities
            )
        except (AttributeError, TypeError):
            # Fallback for dict-based data
            total_assets = sum(
                a.get('value', {}).get('units', 0) if isinstance(a, dict) else 0
                for a in getattr(net_worth_data, 'assets', [])
            )
            total_liabilities = sum(
                l.get('value', {}).get('units', 0) if isinstance(l, dict) else 0
                for l in getattr(net_worth_data, 'liabilities', [])
            )
        
        if total_assets == 0:
            if total_liabilities > 0:
                return DebtIntensityBand.HIGH.value
            return DebtIntensityBand.LOW.value
        
        ratio = total_liabilities / total_assets
        
        if ratio < 0.20:
            return DebtIntensityBand.LOW.value
        elif ratio <= 0.50:
            return DebtIntensityBand.MEDIUM.value
        else:
            return DebtIntensityBand.HIGH.value
    
    def determine_income_stability(self, transactions: list) -> Optional[str]:
        """
        Determine income stability from transaction history.
        
        Returns:
        - STABLE: Regular, consistent income patterns
        - VARIABLE: Irregular or fluctuating income
        """
        if not transactions:
            return None
        
        # TODO: Implement actual analysis of transaction patterns
        # Look for:
        # - Regular salary credits
        # - Consistency of amounts
        # - Frequency of income
        
        return "STABLE"  # Placeholder
    
    def mask_all(self, raw_data: dict) -> dict:
        """
        Apply masking to all fields in a raw data dictionary.
        
        This is a bulk operation for processing complete financial data.
        """
        masked = {}
        
        if "monthly_income" in raw_data:
            masked["income_band"] = self.mask_income(raw_data["monthly_income"])
        
        if "net_worth" in raw_data:
            masked["net_worth_band"] = self.mask_net_worth(raw_data["net_worth"])
        
        if "credit_score" in raw_data:
            masked["credit_score_band"] = self.mask_credit_score(raw_data["credit_score"])
        
        if "dti_ratio" in raw_data:
            masked["dti_band"] = self.mask_dti_ratio(raw_data["dti_ratio"])
        
        if "savings_rate" in raw_data:
            masked["savings_rate_band"] = self.mask_savings_rate(raw_data["savings_rate"])
        
        if "credit_utilization" in raw_data:
            masked["credit_utilization_band"] = self.mask_credit_utilization(raw_data["credit_utilization"])
        
        logger.debug(f"Masked {len(masked)} fields")
        return masked
