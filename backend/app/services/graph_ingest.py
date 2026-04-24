
from typing import List, Dict, Any
from loguru import logger
from app.services.graph_db import GraphDBService

class GraphIngestionService:
    """
    Ingests unstructured text into the Knowledge Graph (Neo4j).
    """

    def __init__(self, graph_db: GraphDBService):
        self.graph_db = graph_db

    async def ingest_document(self, text: str, metadata: Dict[str, Any] = None):
        """
        Process text and ingest entities/relationships.
        """
        if metadata is None:
            metadata = {}

        logger.info(f"Ingesting document: {metadata.get('title', 'Unknown')}")

        # 1. ensure schema
        await self.graph_db.ensure_constraints()

        # 2. Extract Graph (Mocked for V1 Prototype)
        # In a real system, this calls an LLM or Named Entity Recognition model
        graph_data = self._mock_extract_graph(text)

        # 3. Load Nodes
        for node in graph_data["nodes"]:
            try:
                await self.graph_db.create_node(node["label"], node["properties"])
            except Exception as e:
                logger.error(f"Failed to create node {node}: {e}")

        # 4. Load Relationships
        for rel in graph_data["edges"]:
            try:
                await self.graph_db.create_relationship(
                    from_node=rel["from"],
                    to_node=rel["to"],
                    rel_type=rel["type"],
                    properties=rel.get("properties", {})
                )
            except Exception as e:
                logger.error(f"Failed to create relationship {rel}: {e}")

        logger.info("Ingestion complete.")

    def _mock_extract_graph(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Mock extraction for prototype.
        Detects capitalized words as entities for demo purposes.
        """
        # Very simple heuristic demo
        nodes = []
        edges = []

        if "Apple" in text:
            nodes.append({"label": "Company", "properties": {"name": "Apple Inc.", "ticker": "AAPL"}})

        if "Google" in text:
             nodes.append({"label": "Company", "properties": {"name": "Google", "ticker": "GOOGL"}})

        if "AI" in text:
            nodes.append({"label": "Topic", "properties": {"name": "Artificial Intelligence"}})

        if "Apple" in text and "AI" in text:
            edges.append({
                "from": {"label": "Company", "name": "Apple Inc."},
                "to": {"label": "Topic", "name": "Artificial Intelligence"},
                "type": "INVESTS_IN"
            })

        if "Apple" in text and "Google" in text:
             edges.append({
                "from": {"label": "Company", "name": "Apple Inc."},
                "to": {"label": "Company", "name": "Google"},
                "type": "COMPETES_WITH"
            })

        return {"nodes": nodes, "edges": edges}
