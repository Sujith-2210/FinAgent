
from typing import Dict, Any, List
from loguru import logger
from app.agents.base import BaseAgent
from app.services.graph_db import GraphDBService

class GraphReasoningAgent(BaseAgent):
    """
    Graph Reasoning Agent - Performs multi-hop analysis.
    Capabilities: Impact Analysis, Network Discovery, Path Finding.
    """
    
    def __init__(self, graph_db: GraphDBService = None):
        super().__init__()
        self.name = "graph_reasoning"
        self.description = "Analyzes relationships and network effects in the Knowledge Graph"
        self.read_layers = {"external_knowledge_context"}
        self.write_layers = {"agent_working_memory"}
        self._graph_db = graph_db

    def set_graph_db(self, db: GraphDBService):
        self._graph_db = db

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query_topic": {"type": "string"},
                "analysis_type": {"type": "string", "enum": ["impact", "network", "path"]}
            },
            "required": ["query_topic"]
        }
        
    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reasoning_trace": {"type": "array", "items": {"type": "string"}},
                "conclusion": {"type": "string"}
            }
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        topic = input_data.get("query_topic")
        analysis_type = input_data.get("analysis_type", "network")
        
        self.add_reasoning_step(f"Starting {analysis_type} analysis for: {topic}")
        
        if not self._graph_db:
             return {"conclusion": "Error: Graph DB not connected."}
             
        # Extract potential starting entity (Simple heuristic)
        # In a real system, use an Entity Resolution LLM call
        start_entity = self._extract_entity(topic)
        self.add_reasoning_step(f"Identified start entity: {start_entity}")
        
        results = []
        if analysis_type == "impact" or analysis_type == "network":
             results = await self._analyze_network(start_entity)
        
        # Format conclusion
        if not results:
            conclusion = f"No significant relationships found for {start_entity}."
        else:
            conclusion = f"Found {len(results)} related entities. " + "; ".join(results[:3])
            
        return {
            "reasoning_trace": self._reasoning_steps,
            "conclusion": conclusion,
            "raw_data": results
        }

    async def _analyze_network(self, entity_name: str) -> List[str]:
        """
        Perform a 2-hop traversal to find immediate network.
        (n)-[r1]-(m)-[r2]-(x)
        """
        self.add_reasoning_step("Querying Neo4j for 2-hop network...")
        
        # Cypher for 2 hops
        query = """
        MATCH (start {name: $name})
        MATCH (start)-[r1]-(mid)
        OPTIONAL MATCH (mid)-[r2]-(end)
        WHERE end <> start
        RETURN type(r1) as rel1, mid.name as mid_node, type(r2) as rel2, end.name as end_node
        LIMIT 20
        """
        
        try:
            data = await self._graph_db.execute_query(query, {"name": entity_name})
            
            findings = []
            for row in data:
                # 1-hop
                msg = f"{entity_name} {row['rel1']} {row['mid_node']}"
                findings.append(msg)
                
                # 2-hop
                if row.get('rel2') and row.get('end_node'):
                    msg_2 = f"  -> which {row['rel2']} {row['end_node']}"
                    findings.append(msg_2)
                    
            unique_findings = list(set(findings))
            self.add_reasoning_step(f"Graph traversal returned {len(unique_findings)} paths")
            return unique_findings
            
        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            self.add_reasoning_step(f"Error during traversal: {e}")
            return []

    def _extract_entity(self, text: str) -> str:
        # Very simple extraction for prototype
        # If text is "Competitors of A's suppliers", we need to extract "A"
        # For now, let's just look for capitalized words like our previous mock
        if not text:
             return "Tesla"
             
        words = text.split()
        for w in words:
            if w[0].isupper() and len(w) > 3 and w.lower() not in ["find", "what", "show"]:
                 return w
        return "Tesla" # Fallback for demo
