
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from loguru import logger

FEEDBACK_FILE = "data/feedback_logs.jsonl"

class FeedbackService:
    """
    Service for managing user feedback (RLHF data collection).
    """

    def __init__(self, log_file: str = FEEDBACK_FILE):
        self.log_file = log_file
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    async def log_feedback(self, feedback_data: Dict[str, Any]):
        """
        Log feedback to a JSONL file.
        
        Args:
            feedback_data: Dict containing query_id, rating, comment, etc.
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            **feedback_data
        }
        
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
            logger.info(f"Feedback logged for query {feedback_data.get('query_id')}")
        except Exception as e:
            logger.error(f"Failed to log feedback: {e}")
            raise

    async def get_recent_feedback(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent feedback entries."""
        entries = []
        if not os.path.exists(self.log_file):
            return []
            
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    entries.append(json.loads(line))
            return entries[-limit:]
        except Exception as e:
            logger.error(f"Failed to read feedback: {e}")
            return []
