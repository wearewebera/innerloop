"""Memory-related tools for InnerLoop agents."""

from typing import Dict, Any, List
from tools.base_tool import BaseTool, ToolParameter
import structlog

logger = structlog.get_logger()


class MemorySearchTool(BaseTool):
    """Tool for performing deep memory searches with reasoning."""
    
    def __init__(self, agent_id: str = None, memory_store: Any = None):
        super().__init__(agent_id)
        self.memory_store = memory_store
        
    @property
    def name(self) -> str:
        return "memory_search"
    
    @property
    def description(self) -> str:
        return (
            "Search through stored memories using semantic similarity. "
            "Can find memories related to specific topics, timeframes, or contexts. "
            "Returns relevant memories with metadata."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="The search query or topic to find memories about",
                required=True
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of memories to return",
                required=False,
                default=10
            ),
            ToolParameter(
                name="memory_type",
                type="string",
                description="Type of memory to search (e.g., 'conversation', 'thought', 'all')",
                required=False,
                default="all"
            ),
            ToolParameter(
                name="min_relevance",
                type="number",
                description="Minimum relevance score (0-1) for returned memories",
                required=False,
                default=0.5
            )
        ]
    
    async def execute(self, query: str, limit: int = 10, 
                     memory_type: str = "all", min_relevance: float = 0.5) -> Dict[str, Any]:
        """Execute memory search."""
        if not self.memory_store:
            return {
                "error": "Memory store not initialized",
                "memories": []
            }
        
        try:
            # Perform the search
            memories = await self.memory_store.search_memories(
                query=query,
                limit=limit * 2,  # Get extra to filter by relevance
                agent_id=self.agent_id if memory_type != "all" else None
            )
            
            # Filter by memory type if specified
            if memory_type != "all":
                memories = [m for m in memories if m.get('memory_type') == memory_type]
            
            # Filter by minimum relevance
            memories = [m for m in memories if m.get('relevance', 1.0) >= min_relevance]
            
            # Limit results
            memories = memories[:limit]
            
            # Format results
            formatted_memories = []
            for memory in memories:
                # Safe timestamp handling
                timestamp = memory.get('timestamp', '')
                if timestamp and hasattr(timestamp, 'isoformat'):
                    timestamp_str = timestamp.isoformat()
                elif timestamp:
                    timestamp_str = str(timestamp)
                else:
                    timestamp_str = ''
                    
                formatted_memories.append({
                    "content": memory.get('content', ''),
                    "timestamp": timestamp_str,
                    "relevance": memory.get('relevance', 1.0),
                    "type": memory.get('memory_type', 'unknown'),
                    "agent": memory.get('agent_id', 'unknown')
                })
            
            return {
                "query": query,
                "found_count": len(formatted_memories),
                "memories": formatted_memories
            }
            
        except Exception as e:
            self.logger.error("Memory search failed", error=str(e))
            return {
                "error": f"Search failed: {str(e)}",
                "memories": []
            }


class MemoryStoreTool(BaseTool):
    """Tool for storing important memories with enhanced metadata."""
    
    def __init__(self, agent_id: str = None, memory_store: Any = None):
        super().__init__(agent_id)
        self.memory_store = memory_store
        
    @property
    def name(self) -> str:
        return "memory_store"
    
    @property
    def description(self) -> str:
        return (
            "Store an important memory with enhanced metadata and categorization. "
            "Use this to preserve significant insights, decisions, or observations."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="content",
                type="string",
                description="The memory content to store",
                required=True
            ),
            ToolParameter(
                name="memory_type",
                type="string",
                description="Type of memory (e.g., 'insight', 'decision', 'observation', 'reflection')",
                required=False,
                default="general"
            ),
            ToolParameter(
                name="importance",
                type="number",
                description="Importance level of the memory (0-1)",
                required=False,
                default=0.5
            ),
            ToolParameter(
                name="tags",
                type="array",
                description="List of tags for categorization",
                required=False,
                default=[]
            )
        ]
    
    async def execute(self, content: str, memory_type: str = "general",
                     importance: float = 0.5, tags: List[str] = None) -> Dict[str, Any]:
        """Store a memory with metadata."""
        if not self.memory_store:
            return {
                "success": False,
                "error": "Memory store not initialized"
            }
        
        try:
            # Store the memory with enhanced metadata
            metadata = {
                "importance": importance,
                "tags": tags or [],
                "stored_via_tool": True
            }
            
            await self.memory_store.add_memory(
                agent_id=self.agent_id,
                content=content,
                memory_type=memory_type,
                metadata=metadata
            )
            
            return {
                "success": True,
                "stored": {
                    "content": content,
                    "type": memory_type,
                    "importance": importance,
                    "tags": tags or []
                }
            }
            
        except Exception as e:
            self.logger.error("Memory storage failed", error=str(e))
            return {
                "success": False,
                "error": f"Storage failed: {str(e)}"
            }