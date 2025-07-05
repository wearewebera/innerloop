"""Base Tool class for InnerLoop tool system."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class ToolParameter(BaseModel):
    """Defines a tool parameter."""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Tool definition for Ollama API."""
    type: str = "function"
    function: Dict[str, Any]


class BaseTool(ABC):
    """Abstract base class for all InnerLoop tools."""
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id
        self.logger = logger.bind(tool=self.name, agent=agent_id)
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name - must be unique."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the model."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """List of tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass
    
    def get_definition(self) -> ToolDefinition:
        """Get tool definition in Ollama format."""
        # Build parameters schema
        properties = {}
        required = []
        
        for param in self.parameters:
            prop_def = {
                "type": param.type,
                "description": param.description
            }
            if param.default is not None:
                prop_def["default"] = param.default
                
            properties[param.name] = prop_def
            
            if param.required:
                required.append(param.name)
        
        return ToolDefinition(
            type="function",
            function={
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        )
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and normalize parameters."""
        validated = {}
        
        for param in self.parameters:
            if param.name in kwargs:
                validated[param.name] = kwargs[param.name]
            elif param.required:
                if param.default is not None:
                    validated[param.name] = param.default
                else:
                    raise ValueError(f"Missing required parameter: {param.name}")
            elif param.default is not None:
                validated[param.name] = param.default
                
        return validated
    
    async def __call__(self, **kwargs) -> Dict[str, Any]:
        """Allow tool to be called directly."""
        self.logger.debug("Tool called", parameters=kwargs)
        
        try:
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute tool
            result = await self.execute(**validated_params)
            
            self.logger.info("Tool executed successfully", 
                           result_keys=list(result.keys()) if isinstance(result, dict) else type(result))
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            self.logger.error("Tool execution failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }