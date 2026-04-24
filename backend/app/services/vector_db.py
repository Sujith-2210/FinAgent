
import os
from typing import List, Dict, Any, Optional
from loguru import logger
import uuid

class VectorDBService:
    """
    Service for managing vector database operations using ChromaDB.
    
    Attributes:
        client: The ChromaDB client.
        collection: The specific collection for FinAgent documents.
        embedding_function: The embedding function (SentenceTransformer).
    """

    def __init__(self, persistence_path: str = "./data/chroma_db", collection_name: str = "finagent_docs"):
        """
        Initialize the Vector DB Service.

        Args:
            persistence_path: Path to store ChromaDB data.
            collection_name: Name of the collection to use.
        """
        self.persistence_path = persistence_path
        self.collection_name = collection_name
        
        # Ensure data directory exists
        os.makedirs(persistence_path, exist_ok=True)
        
        try:
            # Lazy import so the module can still be imported in environments
            # where optional Chroma telemetry dependencies are mismatched.
            import chromadb
            from chromadb.utils import embedding_functions

            # Initialize Client
            self.client = chromadb.PersistentClient(path=persistence_path)
            
            # Use a lightweight, local embedding model
            # all-MiniLM-L6-v2 is standard for efficiency/performance balance
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Get or Create Collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
            logger.info(f"VectorDB initialized at {persistence_path} with collection '{collection_name}'")
            
        except Exception as e:
            logger.error(f"Failed to initialize VectorDB: {e}")
            raise

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: Optional[List[str]] = None) -> None:
        """
        Add documents to the vector store.

        Args:
            documents: List of text content to embed.
            metadatas: List of metadata dicts for filtering/retrieval.
            ids: Optional list of unique IDs. Generated UUIDs if None.
        """
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
            
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to VectorDB.")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def query(self, query_text: str, n_results: int = 3, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents.

        Args:
            query_text: The search query.
            n_results: Number of results to return.
            where: Metadata filter (optional).

        Returns:
            List of results with 'document', 'metadata', and 'distance'.
        """
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
            
            # Format results into a cleaner structure
            formatted_results = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append({
                        "document": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "id": results["ids"][0][i],
                        "distance": results["distances"][0][i] if results["distances"] else None
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error querying VectorDB: {e}")
            return []

    def count(self) -> int:
        """Return total number of documents in collection."""
        return self.collection.count()

    def reset(self):
        """Delete and recreate the collection (Use with caution)."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )
            logger.warning(f"Collection '{self.collection_name}' has been reset.")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
