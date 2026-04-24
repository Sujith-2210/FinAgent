
from typing import List, Dict, Any, Optional
from loguru import logger
from app.services.vector_db import VectorDBService
from app.services.graph_db import GraphDBService

class GraphRAGService:
    """
    GraphRAG Service - Orchestrates Hybrid Search.
    Combines Vector Semantic Search with Graph Relationship Traversal.
    """

    def __init__(self, vector_db: VectorDBService, graph_db: GraphDBService):
        self.vector_db = vector_db
        self.graph_db = graph_db

    async def hybrid_search(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """
        Perform hybrid search:
        1. Vector Search: Find relevant text chunks.
        2. Graph Search: Find related entities and relationships.
        3. Combine: Return structured context.
        """
        logger.info(f"Performing hybrid search for: {query}")

        # 1. Vector Search
        vector_results = self.vector_db.query(query, n_results=limit)
        docs = [r.get("document", "") for r in vector_results]

        # 2. Graph Search (Concept Expansion)
        # Extract potential entities from query (Simple heuristic for V1)
        # In production, use an LLM or NER model here.
        potential_entities = self._extract_query_entities(query)
        graph_facts = []

        if potential_entities:
            logger.info(f"query entities: {potential_entities}")
            # Cypher query to find 1-hop relationships for these entities
            cypher = """
            MATCH (n) WHERE n.name IN $names
            MATCH (n)-[r]-(m)
            RETURN n.name, type(r), m.name
            LIMIT 10
            """
            try:
                graph_data = await self.graph_db.execute_query(cypher, {"names": potential_entities})
                for row in graph_data:
                    fact = f"{row['n.name']} {row['type(r)']} {row['m.name']}"
                    graph_facts.append(fact)
            except Exception as e:
                logger.warning(f"Graph search failed: {e}")

        return {
            "documents": docs,
            "graph_context": graph_facts,
            "combined_context": self._format_combined_context(docs, graph_facts)
        }

    def _extract_query_entities(self, query: str) -> List[str]:
        """
        Extract potential entity names from query.
        Simple heuristic: extract capitalized words (excluding start of sentence if possible).
        """
        words = query.split()
        entities = []
        # basic cleanup
        clean_words = [w.strip("?,.!") for w in words]

        for w in clean_words:
            if w[0].isupper() and len(w) > 1:
                # specific check for our mock data
                if w.lower() not in ["what", "how", "who", "tell", "me"]:
                     entities.append(w)

        # Handle multi-word entities hardcoded for prototype (e.g. "Apple Inc.")
        if "Apple" in entities:
            entities.append("Apple Inc.")

        return list(set(entities))

    def _format_combined_context(self, docs: List[str], graph_facts: List[str]) -> str:
        """Format chunks and facts into a single string for LLM."""
        context = "Relevant Documents:\n"
        for i, doc in enumerate(docs):
            context += f"[{i+1}] {doc}\n"

        if graph_facts:
            context += "\nKnowledge Graph Relationships:\n"
            for i, fact in enumerate(graph_facts):
                context += f"- {fact}\n"

        return context
