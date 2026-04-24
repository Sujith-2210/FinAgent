"""
Privacy Audit Logging
Implements immutable audit trail with hash chaining for agent invocations.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
from loguru import logger


@dataclass
class PrivacyAuditLog:
    """
    Immutable audit log entry with blockchain-like hash chaining.

    Each log entry contains:
    - Unique log ID
    - Timestamp of the event
    - Agent name that was invoked
    - Context layers accessed
    - Query hash (SHA256 of the query)
    - User ID hash (SHA256 of user ID)
    - Epsilon consumed (for differential privacy tracking)
    - Previous log hash (for immutability chain)
    - Current log hash (computed from all fields)
    """
    log_id: str
    timestamp: datetime
    agent_name: str
    context_layers_accessed: List[str]
    query_hash: str
    user_id_hash: str
    reasoning: str
    epsilon_consumed: float = 0.0
    previous_log_hash: str = ""
    current_log_hash: str = field(default="", init=False)

    def __post_init__(self):
        """Compute the current log hash after initialization."""
        self.current_log_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """
        Compute SHA256 hash of the log entry.

        Includes all fields except current_log_hash to create the hash.
        This creates a blockchain-like chain where each log references
        the previous log's hash.
        """
        # Create a dictionary of all fields except current_log_hash
        log_data = {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "context_layers_accessed": sorted(self.context_layers_accessed),
            "query_hash": self.query_hash,
            "user_id_hash": self.user_id_hash,
            "reasoning": self.reasoning,
            "epsilon_consumed": self.epsilon_consumed,
            "previous_log_hash": self.previous_log_hash
        }

        # Convert to JSON string (sorted keys for consistency)
        json_str = json.dumps(log_data, sort_keys=True)

        # Compute SHA256 hash
        return hashlib.sha256(json_str.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """
        Verify that the log entry hasn't been tampered with.

        Returns:
            True if the hash matches, False if tampered
        """
        expected_hash = self._compute_hash()
        return expected_hash == self.current_log_hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrivacyAuditLog":
        """Create from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        # Remove current_log_hash as it will be recomputed
        data.pop("current_log_hash", None)
        return cls(**data)


class AuditLogger:
    """
    Manages the audit log chain for agent invocations.

    Maintains an immutable chain of audit logs with hash verification.
    """

    def __init__(self):
        self._logs: List[PrivacyAuditLog] = []
        self._last_hash: str = ""

    def log_agent_invocation(
        self,
        agent_name: str,
        query: str,
        user_id: str,
        context_layers: List[str],
        reasoning: str,
        epsilon_consumed: float = 0.0
    ) -> PrivacyAuditLog:
        """
        Log an agent invocation with hash chaining.

        Args:
            agent_name: Name of the agent being invoked
            query: User query (will be hashed)
            user_id: User ID (will be hashed)
            context_layers: List of context layers accessed
            reasoning: Reasoning for agent selection
            epsilon_consumed: Differential privacy epsilon consumed

        Returns:
            The created audit log entry
        """
        # Generate log ID
        log_id = self._generate_log_id()

        # Hash sensitive data
        query_hash = self._hash_string(query)
        user_id_hash = self._hash_string(user_id)

        # Create log entry with chain to previous log
        log_entry = PrivacyAuditLog(
            log_id=log_id,
            timestamp=datetime.utcnow(),
            agent_name=agent_name,
            context_layers_accessed=context_layers,
            query_hash=query_hash,
            user_id_hash=user_id_hash,
            reasoning=reasoning,
            epsilon_consumed=epsilon_consumed,
            previous_log_hash=self._last_hash
        )

        # Add to chain
        self._logs.append(log_entry)
        self._last_hash = log_entry.current_log_hash

        logger.info(f"Audit log created: {log_id} for agent {agent_name}")

        return log_entry

    def verify_chain_integrity(self) -> bool:
        """
        Verify the integrity of the entire audit log chain.

        Checks:
        1. Each log's hash is valid
        2. Each log's previous_log_hash matches the previous log's current_log_hash

        Returns:
            True if chain is intact, False if tampered
        """
        if not self._logs:
            return True

        # Verify first log
        if not self._logs[0].verify_integrity():
            logger.error(f"Log {self._logs[0].log_id} failed integrity check")
            return False

        # Verify chain links
        for i in range(1, len(self._logs)):
            current_log = self._logs[i]
            previous_log = self._logs[i - 1]

            # Verify current log's hash
            if not current_log.verify_integrity():
                logger.error(f"Log {current_log.log_id} failed integrity check")
                return False

            # Verify chain link
            if current_log.previous_log_hash != previous_log.current_log_hash:
                logger.error(f"Chain broken between {previous_log.log_id} and {current_log.log_id}")
                return False

        return True

    def get_logs(
        self,
        agent_name: Optional[str] = None,
        user_id_hash: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[PrivacyAuditLog]:
        """
        Retrieve audit logs with optional filtering.

        Args:
            agent_name: Filter by agent name
            user_id_hash: Filter by user ID hash
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp

        Returns:
            List of matching audit logs
        """
        filtered_logs = self._logs.copy()

        if agent_name:
            filtered_logs = [log for log in filtered_logs if log.agent_name == agent_name]

        if user_id_hash:
            filtered_logs = [log for log in filtered_logs if log.user_id_hash == user_id_hash]

        if start_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp >= start_time]

        if end_time:
            filtered_logs = [log for log in filtered_logs if log.timestamp <= end_time]

        return filtered_logs

    def get_total_epsilon_consumed(self, user_id_hash: str) -> float:
        """
        Get total epsilon consumed for a user across all queries.

        Used for differential privacy budget tracking.
        """
        user_logs = self.get_logs(user_id_hash=user_id_hash)
        return sum(log.epsilon_consumed for log in user_logs)

    def export_logs(self) -> List[Dict[str, Any]]:
        """Export all logs as dictionaries for storage."""
        return [log.to_dict() for log in self._logs]

    def import_logs(self, logs_data: List[Dict[str, Any]]) -> None:
        """Import logs from dictionaries."""
        self._logs = [PrivacyAuditLog.from_dict(data) for data in logs_data]
        if self._logs:
            self._last_hash = self._logs[-1].current_log_hash

        # Verify integrity after import
        if not self.verify_chain_integrity():
            logger.error("Imported audit log chain failed integrity check!")

    def _generate_log_id(self) -> str:
        """Generate a unique log ID."""
        import uuid
        return str(uuid.uuid4())

    def _hash_string(self, value: str) -> str:
        """Hash a string using SHA256."""
        return hashlib.sha256(value.encode()).hexdigest()

    def hash_identifier(self, value: str) -> str:
        """
        Public helper to hash identifiers for lookups without exposing raw values.
        """
        return self._hash_string(value)


# Singleton instance
audit_logger = AuditLogger()
