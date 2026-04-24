"""
Fi MCP Service
Provides typed methods for interacting with Fi MCP tools.

Handles:
- Net worth fetching (assets, liabilities)
- Credit report fetching
- Bank transactions
- EPF details
- Mutual fund transactions
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from loguru import logger
import json

from app.mcp.client import MCPClientManager


# Data Models for Fi MCP Responses

class MoneyValue(BaseModel):
    """Represents a monetary value."""
    currency_code: str = "INR"
    units: int = 0
    nanos: int = 0

    @property
    def amount(self) -> float:
        """Get the total amount as a float."""
        return self.units + (self.nanos / 1_000_000_000)


class AssetValue(BaseModel):
    """Asset in net worth."""
    asset_type: str
    value: MoneyValue


class LiabilityValue(BaseModel):
    """Liability in net worth."""
    liability_type: str
    value: MoneyValue


class NetWorthResponse(BaseModel):
    """Net worth response from Fi MCP."""
    assets: List[AssetValue] = Field(default_factory=list)
    liabilities: List[LiabilityValue] = Field(default_factory=list)
    total_net_worth: float = 0.0


class CreditReportResponse(BaseModel):
    """Credit report response from Fi MCP."""
    credit_score: int = 0
    score_category: str = "UNKNOWN"
    loans: List[Dict[str, Any]] = Field(default_factory=list)
    credit_utilization: float = 0.0


class BankTransaction(BaseModel):
    """Bank transaction."""
    transaction_id: str = ""
    amount: float = 0.0
    type: str = ""  # CREDIT or DEBIT
    category: str = ""
    description: str = ""
    date: Optional[datetime] = None


class BankTransactionsResponse(BaseModel):
    """Bank transactions response."""
    transactions: List[BankTransaction] = Field(default_factory=list)
    total_credits: float = 0.0
    total_debits: float = 0.0


class UserProfileResponse(BaseModel):
    """User profile response."""
    name: str = "Unknown"
    email: str = ""
    phone: str = ""
    dob: Optional[str] = None
    age: Optional[int] = None
    risk_profile: str = "MODERATE"


class FiMCPService:
    """
    Service for interacting with Fi MCP server.

    Provides high-level methods for fetching and parsing financial data.
    """

    def __init__(self, mcp_manager: MCPClientManager):
        self.mcp_manager = mcp_manager
        self._cache: Dict[str, Any] = {}
        self._use_test_data = False  # Fallback to test data when MCP unavailable

    def enable_test_mode(self):
        """Enable test mode for development without MCP server."""
        self._use_test_data = True
        logger.info("Fi MCP Service: Test mode enabled")

    async def fetch_net_worth(self, session_id: Optional[str] = None) -> NetWorthResponse:
        """
        Fetch net worth data from Fi MCP.

        Returns parsed net worth with assets and liabilities.
        """
        if self._use_test_data:
            return self._get_test_net_worth()

        try:
            client = self.mcp_manager.get_fi_client(session_id=session_id)
            result = await client.call_tool_with_connection("fetch_net_worth", {})

            if "requires_auth" in result:
                logger.warning("Fi MCP requires authentication")
                return self._get_test_net_worth()

            return self._parse_net_worth(result)

        except Exception as e:
            logger.error(f"Failed to fetch net worth: {e}")
            return self._get_test_net_worth()

    async def fetch_credit_report(self, session_id: Optional[str] = None) -> CreditReportResponse:
        """
        Fetch credit report from Fi MCP.

        Returns parsed credit report with score and loan info.
        """
        if self._use_test_data:
            return self._get_test_credit_report()

        try:
            client = self.mcp_manager.get_fi_client(session_id=session_id)
            result = await client.call_tool_with_connection("fetch_credit_report", {})

            if "requires_auth" in result:
                logger.warning("Fi MCP requires authentication")
                return self._get_test_credit_report()

            return self._parse_credit_report(result)

        except Exception as e:
            logger.error(f"Failed to fetch credit report: {e}")
            return self._get_test_credit_report()

    async def fetch_bank_transactions(
        self,
        session_id: Optional[str] = None,
        limit: int = 50
    ) -> BankTransactionsResponse:
        """
        Fetch bank transactions from Fi MCP.
        """
        if self._use_test_data:
            return self._get_test_transactions()

        try:
            client = self.mcp_manager.get_fi_client(session_id=session_id)
            result = await client.call_tool_with_connection("fetch_bank_transactions", {})

            if "requires_auth" in result:
                logger.warning("Fi MCP requires authentication")
                return self._get_test_transactions()

            return self._parse_bank_transactions(result)

        except Exception as e:
            logger.error(f"Failed to fetch transactions: {e}")
            return self._get_test_transactions()

    async def fetch_user_profile(self, session_id: Optional[str] = None) -> UserProfileResponse:
        """
        Fetch user profile (KYC) from Fi MCP.
        """
        if self._use_test_data:
            return self._get_test_user_profile()

        try:
            client = self.mcp_manager.get_fi_client(session_id=session_id)
            # Assuming tool name is fetch_user_profile, if not found, it will throw specific error
            # For now, since Go code likely doesn't have it, we might fall back to test data anyway
            result = await client.call_tool_with_connection("fetch_user_profile", {})

            if "requires_auth" in result:
                logger.warning("Fi MCP requires authentication")
                return self._get_test_user_profile()

            return self._parse_user_profile(result)

        except Exception as e:
            logger.warning(f"Failed to fetch user profile (using fallback): {e}")
            return self._get_test_user_profile()

    async def fetch_all_financial_data(
        self,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all available financial data.

        Returns a consolidated view of:
        - Net worth (assets, liabilities)
        - Credit report
        - Bank transactions summary
        """
        logger.info("Fetching all financial data...")

        net_worth = await self.fetch_net_worth(session_id)
        credit_report = await self.fetch_credit_report(session_id)
        transactions = await self.fetch_bank_transactions(session_id)
        user_profile = await self.fetch_user_profile(session_id)

        return {
            "net_worth": net_worth,
            "credit_report": credit_report,
            "transactions": transactions,
            "user_profile": user_profile,
            "fetched_at": datetime.utcnow().isoformat()
        }

    # Parsing Methods

    def _parse_net_worth(self, data: Dict[str, Any]) -> NetWorthResponse:
        """Parse raw net worth response from Fi MCP."""
        try:
            nw_response = data.get("netWorthResponse", {})

            assets = []
            for asset in nw_response.get("assetValues", []):
                value = asset.get("value", {})
                assets.append(AssetValue(
                    asset_type=asset.get("netWorthAttribute", "UNKNOWN"),
                    value=MoneyValue(
                        currency_code=value.get("currencyCode", "INR"),
                        units=int(value.get("units", 0)),
                        nanos=int(value.get("nanos", 0))
                    )
                ))

            liabilities = []
            for liability in nw_response.get("liabilityValues", []):
                value = liability.get("value", {})
                liabilities.append(LiabilityValue(
                    liability_type=liability.get("netWorthAttribute", "UNKNOWN"),
                    value=MoneyValue(
                        currency_code=value.get("currencyCode", "INR"),
                        units=int(value.get("units", 0)),
                        nanos=int(value.get("nanos", 0))
                    )
                ))

            total_value = nw_response.get("totalNetWorthValue", {})
            total = int(total_value.get("units", 0))

            return NetWorthResponse(
                assets=assets,
                liabilities=liabilities,
                total_net_worth=total
            )

        except Exception as e:
            logger.error(f"Failed to parse net worth: {e}")
            return NetWorthResponse()

    def _parse_credit_report(self, data: Dict[str, Any]) -> CreditReportResponse:
        """Parse raw credit report response from Fi MCP (actual JSON structure)."""
        try:
            # fi-mcp-dev returns: { creditReports: [{ creditReportData: { ... }, vendor: "EXPERIAN" }] }
            credit_reports = data.get("creditReports", [])

            score = 0
            loans = []
            credit_utilization = 0.0

            if credit_reports:
                report_data = credit_reports[0].get("creditReportData", {})

                # Extract credit score: score.bureauScore
                score_data = report_data.get("score", {})
                if isinstance(score_data, dict):
                    score = int(score_data.get("bureauScore", 0))

                # Extract credit account details for loans and utilization
                credit_account = report_data.get("creditAccount", {})
                account_details = credit_account.get("creditAccountDetails", [])

                total_credit_limit = 0
                total_current_balance = 0

                for account in account_details:
                    credit_limit = int(account.get("creditLimitAmount", 0))
                    current_balance = int(account.get("currentBalance", 0))
                    total_credit_limit += credit_limit
                    total_current_balance += current_balance

                    loans.append({
                        "subscriber": account.get("subscriberName", "Unknown"),
                        "type": "CREDIT_CARD" if account.get("portfolioType") == "R" else "LOAN",
                        "credit_limit": credit_limit,
                        "current_balance": current_balance,
                        "status": account.get("accountStatus", "Unknown"),
                        "interest_rate": account.get("rateOfInterest", "N/A"),
                        "open_date": account.get("openDate", ""),
                        "amount_past_due": int(account.get("amountPastDue", 0)),
                    })

                # Calculate credit utilization
                if total_credit_limit > 0:
                    credit_utilization = total_current_balance / total_credit_limit

                # Also get outstanding balance summary
                balance_summary = credit_account.get("creditAccountSummary", {}).get("totalOutstandingBalance", {})
                int(balance_summary.get("outstandingBalanceAll", 0))
            else:
                # Fallback: try alternate format
                credit_data = data.get("creditReport", {})
                score_data = credit_data.get("creditScore", {})
                if isinstance(score_data, dict):
                    score = int(score_data.get("score", 0))
                elif isinstance(score_data, (int, str)):
                    score = int(score_data)
                loans = credit_data.get("loanDetails", [])

            # Determine score category
            if score >= 750:
                category = "EXCELLENT"
            elif score >= 700:
                category = "GOOD"
            elif score >= 650:
                category = "FAIR"
            elif score > 0:
                category = "POOR"
            else:
                category = "UNKNOWN"

            return CreditReportResponse(
                credit_score=score,
                score_category=category,
                loans=loans,
                credit_utilization=credit_utilization
            )

        except Exception as e:
            logger.error(f"Failed to parse credit report: {e}")
            return CreditReportResponse()

    def _parse_bank_transactions(self, data: Dict[str, Any]) -> BankTransactionsResponse:
        """Parse raw bank transactions response from Fi MCP."""
        try:
            txn_list = data.get("transactionsList", data.get("transactions", []))

            transactions = []
            total_credits = 0.0
            total_debits = 0.0

            for txn in txn_list[:100]:  # Limit to 100
                amount = float(txn.get("amount", {}).get("units", 0))
                txn_type = txn.get("type", "UNKNOWN")

                if txn_type == "CREDIT":
                    total_credits += amount
                elif txn_type == "DEBIT":
                    total_debits += amount

                transactions.append(BankTransaction(
                    transaction_id=txn.get("transactionId", ""),
                    amount=amount,
                    type=txn_type,
                    category=txn.get("category", "UNKNOWN"),
                    description=txn.get("description", "")
                ))

            return BankTransactionsResponse(
                transactions=transactions,
                total_credits=total_credits,
                total_debits=total_debits
            )

        except Exception as e:
            logger.error(f"Failed to parse transactions: {e}")
            return BankTransactionsResponse()

    def _parse_user_profile(self, data: Dict[str, Any]) -> UserProfileResponse:
        """Parse raw user profile from Fi MCP."""
        try:
            profile = data.get("userProfile", data)
            dob_str = profile.get("dob", "1990-01-01")

            # Calculate age
            age = 30
            try:
                 dob_date = datetime.strptime(dob_str, "%Y-%m-%d")
                 today = datetime.now()
                 age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
            except Exception:
                pass

            return UserProfileResponse(
                name=profile.get("name", "Unknown"),
                email=profile.get("email", ""),
                phone=profile.get("phone", ""),
                dob=dob_str,
                age=age,
                risk_profile=profile.get("risk_profile", "MODERATE")
            )
        except Exception as e:
            logger.error(f"Failed to parse user profile: {e}")
            return self._get_test_user_profile()

    # Test Data Methods (for development without MCP server)

    def _get_test_net_worth(self) -> NetWorthResponse:
        """Get test net worth data matching phone 2222222222."""
        return NetWorthResponse(
            assets=[
                AssetValue(asset_type="ASSET_TYPE_MUTUAL_FUND", value=MoneyValue(units=84642)),
                AssetValue(asset_type="ASSET_TYPE_EPF", value=MoneyValue(units=211111)),
                AssetValue(asset_type="ASSET_TYPE_INDIAN_SECURITIES", value=MoneyValue(units=200642)),
                AssetValue(asset_type="ASSET_TYPE_SAVINGS_ACCOUNTS", value=MoneyValue(units=195297)),
                AssetValue(asset_type="ASSET_TYPE_US_SECURITIES", value=MoneyValue(units=30613)),
            ],
            liabilities=[
                LiabilityValue(liability_type="LIABILITY_TYPE_VEHICLE_LOAN", value=MoneyValue(units=5000)),
                LiabilityValue(liability_type="LIABILITY_TYPE_HOME_LOAN", value=MoneyValue(units=17000)),
                LiabilityValue(liability_type="LIABILITY_TYPE_OTHER_LOAN", value=MoneyValue(units=42000)),
            ],
            total_net_worth=658305
        )

    def _get_test_credit_report(self) -> CreditReportResponse:
        """Get test credit report data."""
        return CreditReportResponse(
            credit_score=758,
            score_category="EXCELLENT",
            loans=[
                {"type": "HOME_LOAN", "status": "ACTIVE", "balance": 17000},
                {"type": "VEHICLE_LOAN", "status": "ACTIVE", "balance": 5000},
            ],
            credit_utilization=0.15
        )

    def _get_test_transactions(self) -> BankTransactionsResponse:
        """Get test bank transactions data."""
        return BankTransactionsResponse(
            transactions=[
                BankTransaction(transaction_id="1", amount=75000, type="CREDIT", category="SALARY", description="Salary Credit"),
                BankTransaction(transaction_id="2", amount=15000, type="DEBIT", category="RENT", description="Rent Payment"),
                BankTransaction(transaction_id="3", amount=5000, type="DEBIT", category="SIP", description="SIP Investment"),
                BankTransaction(transaction_id="4", amount=3000, type="DEBIT", category="FOOD", description="Groceries"),
                BankTransaction(transaction_id="5", amount=2000, type="DEBIT", category="UTILITIES", description="Bills"),
            ],
            total_credits=75000,
            total_debits=25000
        )

    def _get_test_user_profile(self) -> UserProfileResponse:
        """Get test user profile."""
        return UserProfileResponse(
            name="Test User",
            email="test@example.com",
            phone="2222222222",
            dob="1994-01-01",
            age=32,
            risk_profile="AGGRESSIVE"
        )
