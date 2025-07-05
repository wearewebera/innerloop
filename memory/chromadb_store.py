"""ChromaDB-based memory store for semantic search and retrieval."""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import structlog
import hashlib

logger = structlog.get_logger()


class ChromaMemoryStore:
    """In-memory ChromaDB store for agent memories."""
    
    def __init__(self, collection_name: str = "innerloop_memories"):
        self.collection_name = collection_name
        
        # Initialize ChromaDB client in-memory mode
        self.client = chromadb.Client(Settings(
            is_persistent=False,     # In-memory mode
            anonymized_telemetry=False
        ))
        
        # Create or get collection
        try:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except:
            self.collection = self.client.get_collection(name=collection_name)
        
        self.logger = logger.bind(component="chromadb_store")
        self.logger.info("ChromaDB memory store initialized", 
                        collection=collection_name)
    
    def _generate_id(self, content: str, agent_id: str, timestamp: datetime) -> str:
        """Generate a unique ID for a memory."""
        data = f"{agent_id}:{content}:{timestamp.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def add_memory(self, agent_id: str, content: str, 
                        memory_type: str = "general",
                        timestamp: Optional[datetime] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a memory to the store."""
        if timestamp is None:
            timestamp = datetime.now()
        
        memory_id = self._generate_id(content, agent_id, timestamp)
        
        # Prepare metadata
        memory_metadata = {
            "agent_id": agent_id,
            "memory_type": memory_type,
            "timestamp": timestamp.isoformat(),
            "content_length": len(content)
        }
        
        if metadata:
            memory_metadata.update(metadata)
        
        try:
            # Add to ChromaDB
            self.collection.add(
                documents=[content],
                metadatas=[memory_metadata],
                ids=[memory_id]
            )
            
            self.logger.debug("Memory added",
                            agent_id=agent_id,
                            type=memory_type,
                            id=memory_id)
            
            return memory_id
            
        except Exception as e:
            self.logger.error("Failed to add memory", 
                            error=str(e),
                            agent_id=agent_id)
            raise
    
    async def search_memories(self, query: str, limit: int = 10,
                            agent_id: Optional[str] = None,
                            memory_type: Optional[str] = None,
                            min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """Search for relevant memories."""
        try:
            # Build where clause for filtering
            where = {}
            if agent_id:
                where["agent_id"] = agent_id
            if memory_type:
                where["memory_type"] = memory_type
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where if where else None
            )
            
            # Format results
            memories = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    # Calculate similarity from distance
                    distance = results['distances'][0][i] if results['distances'] else 0
                    similarity = 1.0 - distance  # Convert distance to similarity
                    
                    if similarity >= min_similarity:
                        memory = {
                            'id': results['ids'][0][i],
                            'content': doc,
                            'metadata': results['metadatas'][0][i],
                            'similarity': similarity
                        }
                        memories.append(memory)
            
            self.logger.debug("Memory search completed",
                            query_preview=query[:50],
                            results=len(memories))
            
            return memories
            
        except Exception as e:
            self.logger.error("Memory search failed", error=str(e))
            return []
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID."""
        try:
            result = self.collection.get(
                ids=[memory_id],
                include=["documents", "metadatas"]
            )
            
            if result['documents']:
                return {
                    'id': memory_id,
                    'content': result['documents'][0],
                    'metadata': result['metadatas'][0] if result['metadatas'] else {}
                }
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get memory", 
                            memory_id=memory_id,
                            error=str(e))
            return None
    
    async def update_memory(self, memory_id: str, 
                          content: Optional[str] = None,
                          metadata_updates: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing memory."""
        try:
            # Get existing memory
            existing = await self.get_memory(memory_id)
            if not existing:
                return False
            
            # Prepare updates
            new_content = content if content is not None else existing['content']
            new_metadata = existing['metadata'].copy()
            
            if metadata_updates:
                new_metadata.update(metadata_updates)
            
            new_metadata['last_updated'] = datetime.now().isoformat()
            
            # Update in ChromaDB
            self.collection.update(
                ids=[memory_id],
                documents=[new_content],
                metadatas=[new_metadata]
            )
            
            self.logger.debug("Memory updated", memory_id=memory_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to update memory",
                            memory_id=memory_id,
                            error=str(e))
            return False
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        try:
            self.collection.delete(ids=[memory_id])
            self.logger.debug("Memory deleted", memory_id=memory_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete memory",
                            memory_id=memory_id,
                            error=str(e))
            return False
    
    async def get_agent_memories(self, agent_id: str, 
                               limit: int = 100,
                               memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all memories for a specific agent."""
        # Use a broad search to get agent's memories
        return await self.search_memories(
            query="",  # Empty query to get all
            limit=limit,
            agent_id=agent_id,
            memory_type=memory_type
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics."""
        try:
            # Get collection count
            count = self.collection.count()
            
            return {
                "collection_name": self.collection_name,
                "total_memories": count,
                "storage_type": "in-memory"
            }
        except:
            return {
                "collection_name": self.collection_name,
                "total_memories": 0,
                "storage_type": "in-memory"
            }