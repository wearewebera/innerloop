"""Tool Registry for managing and executing tools."""

from typing import Dict, Any, List, Optional, Type
import importlib
import inspect
from pathlib import Path
import structlog

from tools.base_tool import BaseTool, ToolDefinition

logger = structlog.get_logger()


class ToolRegistry:
    """Central registry for tool discovery and management."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logger.bind(component="tool_registry")
        
        # Tool configuration
        self.tools_config = self.config.get('tools', {})
        self.enabled = self.tools_config.get('enabled', True)
        self.available_tools = self.tools_config.get('available_tools', [])
        self.timeout = self.tools_config.get('timeout', 10)
        
    async def initialize(self, agent_id: str = None):
        """Initialize the tool registry and load configured tools."""
        if not self.enabled:
            self.logger.info("Tools disabled in configuration")
            return
            
        self.logger.info("Initializing tool registry", 
                        available_tools=self.available_tools)
        
        # Auto-discover tools in the tools directory
        await self._discover_tools(agent_id)
        
        self.logger.info("Tool registry initialized", 
                        loaded_tools=list(self.tools.keys()))
    
    async def _discover_tools(self, agent_id: str):
        """Discover and load tools from the tools directory."""
        tools_dir = Path(__file__).parent
        
        # Map of tool names to their module/class names
        tool_mapping = {
            'memory_search': ('memory_tools', 'MemorySearchTool'),
            'focus_analysis': ('focus_tools', 'FocusAnalysisTool'),
            'decision_maker': ('decision_tools', 'DecisionMakerTool'),
            'reflection': ('reflection_tools', 'ReflectionTool'),
            'time_awareness': ('time_tools', 'TimeAwarenessTool'),
            'problem_loader': ('problem_solving_tools', 'ProblemLoaderTool'),
            'suggestion_generator': ('problem_solving_tools', 'SuggestionGeneratorTool'),
            'suggestion_saver': ('problem_solving_tools', 'SuggestionSaverTool'),
            'problem_progress': ('problem_solving_tools', 'ProblemProgressTool'),
            # 'web_search': ('web_tools', 'WebSearchTool'),  # Not implemented yet
        }
        
        for tool_name in self.available_tools:
            if tool_name not in tool_mapping:
                self.logger.warning(f"Unknown tool in config: {tool_name}")
                continue
                
            module_name, class_name = tool_mapping[tool_name]
            
            try:
                # Try to import the tool module
                module_path = f"tools.{module_name}"
                module = importlib.import_module(module_path)
                
                # Get the tool class
                tool_class = getattr(module, class_name, None)
                
                if tool_class and issubclass(tool_class, BaseTool):
                    # Instantiate the tool
                    tool_instance = tool_class(agent_id=agent_id)
                    self.register_tool(tool_instance)
                    self.logger.info(f"Loaded tool: {tool_name}")
                else:
                    self.logger.warning(f"Invalid tool class: {class_name} in {module_name}")
                    
            except ImportError as e:
                self.logger.debug(f"Tool module not found: {module_name} - {str(e)}")
                # This is expected for tools not yet implemented
            except Exception as e:
                self.logger.error(f"Failed to load tool: {tool_name}", error=str(e))
    
    def register_tool(self, tool: BaseTool):
        """Register a tool instance."""
        if not isinstance(tool, BaseTool):
            raise ValueError("Tool must inherit from BaseTool")
            
        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")
    
    def unregister_tool(self, tool_name: str):
        """Unregister a tool."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.logger.debug(f"Unregistered tool: {tool_name}")
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self.tools
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for Ollama API."""
        definitions = []
        for tool in self.tools.values():
            definition = tool.get_definition()
            definitions.append(definition.dict())
        return definitions
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool by name with given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
            
        # Execute with timeout
        import asyncio
        try:
            result = await asyncio.wait_for(
                tool(**parameters),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            self.logger.error(f"Tool execution timed out: {tool_name}")
            return {
                "success": False,
                "error": f"Tool execution timed out after {self.timeout} seconds"
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get registry status."""
        return {
            "enabled": self.enabled,
            "registered_tools": list(self.tools.keys()),
            "configured_tools": self.available_tools,
            "timeout": self.timeout
        }