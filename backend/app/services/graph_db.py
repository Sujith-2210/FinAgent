
import os
from neo4j import GraphDatabase, AsyncGraphDatabase
from loguru import logger
from typing import List, Dict, Any, Optional

class GraphDBService:
    """
    Service for managing Neo4j Graph Database operations.
    """

    def __init__(self, uri: Optional[str] = None, auth: Optional[tuple[str, str]] = None):
        """
        Initialize the Graph DB Service.

        Args:
            uri: Neo4j connection URI.
            auth: Tuple of (username, password).
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.auth = auth or (
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "neo4j_change_me")
        )
        self.driver = None
        if self.auth[1] == "neo4j_change_me":
            logger.warning("Using default Neo4j password placeholder. Set NEO4J_PASSWORD for non-dev usage.")

        try:
            # Using AsyncDriver for better performance in async app
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth)
            logger.info(f"GraphDB initialized at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to initialize GraphDB driver: {e}")
            raise

    async def verify_connectivity(self) -> bool:
        """Check if we can connect to the database."""
        try:
            await self.driver.verify_connectivity()
            logger.info("Verifed connectivity to Neo4j")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Neo4j: {e}")
            return False

    async def close(self):
        """Close the driver connection."""
        if self.driver:
            await self.driver.close()
            logger.info("GraphDB driver closed")

    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query.

        Args:
            query: Cypher query string.
            parameters: Dictionary of query parameters.

        Returns:
            List of records as dictionaries.
        """
        if parameters is None:
            parameters = {}

        try:
            records, summary, keys = await self.driver.execute_query(
                query,
                parameters,
                database_="neo4j"
            )

            # Convert to list of dicts
            results = [r.data() for r in records]
            return results

        except Exception as e:
            logger.error(f"Query failed: {query} | Error: {e}")
            raise

    async def create_node(self, label: str, properties: Dict[str, Any]):
        """Helper to create a simple node (MERGE to avoid duplicates)."""
        query = f"MERGE (n:{label} {{name: $props.name}}) SET n += $props RETURN n"
        # If 'name' is not in props, this might fail or create weird nodes.
        # For V1, we assume 'name' is the ID.
        if "name" not in properties:
             # Fallback to simple create if no name key
             query = f"CREATE (n:{label} $props) RETURN n"

        return await self.execute_query(query, {"props": properties})

    async def create_relationship(self, from_node: Dict[str, Any], to_node: Dict[str, Any], rel_type: str, properties: Dict[str, Any] = None):
        """
        Create a relationship between two nodes.
        Expects nodes to be identified by 'name' and 'label'.
        """
        if properties is None:
            properties = {}

        query = f"""
        MATCH (a:{from_node['label']} {{name: $from_name}})
        MATCH (b:{to_node['label']} {{name: $to_name}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props
        RETURN r
        """
        params = {
            "from_name": from_node['name'],
            "to_name": to_node['name'],
            "props": properties
        }
        return await self.execute_query(query, params)

    async def ensure_constraints(self):
        """Create uniqueness constraints for V1 schema."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE"
        ]

        for q in constraints:
            try:
                await self.execute_query(q)
            except Exception as e:
                logger.warning(f"Constraint creation failed (might already exist): {e}")
