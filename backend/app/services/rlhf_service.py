
import json
import os
from typing import List, Dict, Any
from loguru import logger
from app.services.feedback_service import FeedbackService, FEEDBACK_FILE

class RLHFService:
    """
    Service to process raw feedback logs into training datasets (DPO/PPO).
    """

    def __init__(self, feedback_service: FeedbackService = None):
        self.feedback_service = feedback_service or FeedbackService(FEEDBACK_FILE)

    async def export_dataset(self, output_file: str = "data/rlhf_dataset.json") -> Dict[str, Any]:
        """
        Convert feedback logs into a DPO-compatible dataset.

        Format:
        [
            {
                "prompt": "User query...",
                "chosen": "Agent response (Rated +1)",
                "rejected": "Agent response (Rated -1)"
            }
        ]

        Note: Since we might not have pairs for the same query in this simple prototype,
        we will treat +1 as "chosen" and generate a placeholder "rejected" (or ignore single -1s).
        For a real system, you'd want actual pairs or use PPO with reward modeling.
        """
        raw_feedback = await self.feedback_service.get_recent_feedback(limit=1000)

        dataset = []
        stats = {"positive": 0, "negative": 0, "pairs": 0}

        # Group by query_id/original_query to find pairs if multiple runs exist
        # For prototype, we'll just format individual entries

        for entry in raw_feedback:
            rating = entry.get("rating", 0)
            query = entry.get("original_query", "") or entry.get("query_id", "")
            # We need the actual agent response text here.
            # In a real system, feedback log should include the response text.
            # Assuming our feedback log structure will be updated or we use a placeholder.
            # For this demo, let's assume we can't retrieve the full text if it wasn't logged,
            # so we'll skip incomplete entries or use placeholders for demonstration.

            response_text = entry.get("response_text", "[Response Text Placeholder]")

            if rating == 1:
                stats["positive"] += 1
                # DPO format requires a rejected example.
                # In production, we'd find a -1 rating for the same query.
                dataset.append({
                    "prompt": query,
                    "chosen": response_text,
                    "rejected": "[Generic Negative Response]", # Placeholder
                    "score": 1
                })
            elif rating == -1:
                stats["negative"] += 1
                dataset.append({
                    "prompt": query,
                    "chosen": "[Generic Positive Response]", # Placeholder
                    "rejected": response_text,
                    "score": 0
                })

        # Save dataset
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(dataset, f, indent=2)

        logger.info(f"Exported {len(dataset)} examples to {output_file}")
        return {"count": len(dataset), "stats": stats, "path": output_file}
