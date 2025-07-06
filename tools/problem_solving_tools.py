"""Problem-solving tools for generating and saving suggestions."""

import os
import yaml
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog
import aiofiles

from tools.base_tool import BaseTool, ToolParameter

logger = structlog.get_logger()


class ProblemLoaderTool(BaseTool):
    """Load and parse problem definitions."""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id)
    
    @property
    def name(self) -> str:
        return "problem_loader"
    
    @property
    def description(self) -> str:
        return "Load problem definition from problem.yaml file"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="problem_file",
                type="string",
                description="Path to problem file (default: problem.yaml)",
                required=False,
                default="problem.yaml"
            )
        ]
    
    async def execute(self, problem_file: str = "problem.yaml") -> Dict[str, Any]:
        """Load problem definition from YAML file."""
        try:
            with open(problem_file, 'r') as f:
                problem_data = yaml.safe_load(f)
            
            self.logger.info("Problem loaded successfully", 
                           problem_id=problem_data.get('problem', {}).get('id'))
            
            return {
                "success": True,
                "problem": problem_data.get('problem', {}),
                "message": f"Loaded problem: {problem_data.get('problem', {}).get('title', 'Unknown')}"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Problem file not found: {problem_file}",
                "message": "No problem definition found. Please create a problem.yaml file."
            }
        except Exception as e:
            self.logger.error("Failed to load problem", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to load problem definition"
            }


class SuggestionGeneratorTool(BaseTool):
    """Generate structured suggestions for problems."""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id)
    
    @property
    def name(self) -> str:
        return "suggestion_generator"
    
    @property
    def description(self) -> str:
        return "Generate a structured suggestion for the current problem"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="problem_id",
                type="string",
                description="ID of the problem being solved",
                required=True
            ),
            ToolParameter(
                name="suggestion_type",
                type="string",
                description="Type of suggestion (improvement, solution, analysis, insight)",
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Brief title of the suggestion",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="Detailed content of the suggestion",
                required=True
            ),
            ToolParameter(
                name="confidence",
                type="number",
                description="Confidence score (0.0-1.0)",
                required=True
            ),
            ToolParameter(
                name="implementation_steps",
                type="array",
                description="List of implementation steps",
                required=False,
                default=[]
            )
        ]
    
    async def execute(self, problem_id: str, suggestion_type: str, title: str, 
                      content: str, confidence: float, 
                      implementation_steps: List[str] = None) -> Dict[str, Any]:
        """Generate a structured suggestion."""
        suggestion = {
            "id": f"{problem_id}_{suggestion_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "problem_id": problem_id,
            "type": suggestion_type,
            "title": title,
            "content": content,
            "confidence": confidence,
            "implementation_steps": implementation_steps or [],
            "generated_at": datetime.now().isoformat(),
            "agent_id": self.agent_id
        }
        
        self.logger.info("Generated suggestion", 
                        suggestion_id=suggestion['id'],
                        confidence=confidence)
        
        return {
            "success": True,
            "suggestion": suggestion,
            "message": f"Generated {suggestion_type} suggestion: {title}"
        }


class SuggestionSaverTool(BaseTool):
    """Save suggestions to files."""
    
    def __init__(self, agent_id: str, output_dir: str = "suggestions"):
        super().__init__(agent_id=agent_id)
        self.output_dir = Path(output_dir)
    
    @property
    def name(self) -> str:
        return "suggestion_saver"
    
    @property
    def description(self) -> str:
        return "Save a suggestion to a file"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="suggestion",
                type="object",
                description="The suggestion object to save",
                required=True
            ),
            ToolParameter(
                name="format",
                type="string",
                description="Output format (markdown or json)",
                required=False,
                default="markdown"
            )
        ]
    
    async def execute(self, suggestion: Dict[str, Any], 
                      format: str = "markdown") -> Dict[str, Any]:
        """Save a suggestion to a file."""
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{suggestion.get('problem_id', 'unknown')}_{timestamp}_{suggestion.get('id', '')[:8]}"
        
        try:
            if format == "markdown":
                filepath = self.output_dir / f"{filename}.md"
                content = self._format_markdown(suggestion)
            else:
                filepath = self.output_dir / f"{filename}.json"
                content = json.dumps(suggestion, indent=2)
            
            # Write to file asynchronously
            async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
                await f.write(content)
            
            self.logger.info("Suggestion saved", filepath=str(filepath))
            
            return {
                "success": True,
                "filepath": str(filepath),
                "message": f"Saved suggestion to {filepath}"
            }
            
        except Exception as e:
            self.logger.error("Failed to save suggestion", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to save suggestion"
            }
    
    def _format_markdown(self, suggestion: Dict[str, Any]) -> str:
        """Format suggestion as markdown."""
        md = f"""# {suggestion.get('title', 'Untitled Suggestion')}

**Type**: {suggestion.get('type', 'Unknown')}  
**Problem ID**: {suggestion.get('problem_id', 'Unknown')}  
**Confidence**: {suggestion.get('confidence', 0):.2f}  
**Generated**: {suggestion.get('generated_at', 'Unknown')}  
**Agent**: {suggestion.get('agent_id', 'Unknown')}  

## Description

{suggestion.get('content', 'No description provided.')}

## Implementation Steps

"""
        
        steps = suggestion.get('implementation_steps', [])
        if steps:
            for i, step in enumerate(steps, 1):
                md += f"{i}. {step}\n"
        else:
            md += "No implementation steps provided.\n"
        
        return md


class ProblemProgressTool(BaseTool):
    """Track progress on problem-solving."""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id=agent_id)
    
    @property
    def name(self) -> str:
        return "problem_progress"
    
    @property
    def description(self) -> str:
        return "Track and report progress on current problem"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="problem_id",
                type="string",
                description="ID of the problem",
                required=True
            ),
            ToolParameter(
                name="suggestions_generated",
                type="number",
                description="Number of suggestions generated",
                required=True
            ),
            ToolParameter(
                name="areas_analyzed",
                type="array",
                description="List of areas analyzed",
                required=True
            ),
            ToolParameter(
                name="next_steps",
                type="array",
                description="Next steps to take",
                required=True
            )
        ]
    
    async def execute(self, problem_id: str, suggestions_generated: int,
                      areas_analyzed: List[str], next_steps: List[str]) -> Dict[str, Any]:
        """Track problem-solving progress."""
        progress = {
            "problem_id": problem_id,
            "suggestions_generated": suggestions_generated,
            "areas_analyzed": areas_analyzed,
            "next_steps": next_steps,
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate completion estimate
        # This is a simple heuristic - could be more sophisticated
        completion_percentage = min(100, (suggestions_generated / 5) * 100)
        
        self.logger.info("Problem progress tracked",
                        problem_id=problem_id,
                        suggestions=suggestions_generated,
                        completion=completion_percentage)
        
        return {
            "success": True,
            "progress": progress,
            "completion_percentage": completion_percentage,
            "message": f"Progress: {suggestions_generated} suggestions generated ({completion_percentage:.0f}% complete)"
        }