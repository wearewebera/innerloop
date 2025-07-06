"""Focus analysis and management tools for InnerLoop agents."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from tools.base_tool import BaseTool, ToolParameter
import structlog

logger = structlog.get_logger()


class FocusAnalysisTool(BaseTool):
    """Tool for analyzing current focus areas and their relationships."""
    
    def __init__(self, agent_id: str = None, focus_areas: List = None):
        super().__init__(agent_id)
        self.focus_areas = focus_areas or []
        
    @property
    def name(self) -> str:
        return "focus_analysis"
    
    @property
    def description(self) -> str:
        return (
            "Analyze current focus areas, their intensities, and relationships. "
            "Can identify patterns, suggest connections, or recommend focus shifts."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="Analysis action: 'summarize', 'connections', 'recommend_shift', 'intensity_check'",
                required=True
            ),
            ToolParameter(
                name="theme",
                type="string",
                description="Specific theme to analyze (optional, for targeted analysis)",
                required=False,
                default=None
            )
        ]
    
    async def execute(self, action: str, theme: Optional[str] = None) -> Dict[str, Any]:
        """Analyze focus areas based on requested action."""
        try:
            if action == "summarize":
                return await self._summarize_focus_areas()
            elif action == "connections":
                return await self._find_connections()
            elif action == "recommend_shift":
                return await self._recommend_focus_shift()
            elif action == "intensity_check":
                return await self._check_intensities(theme)
            else:
                return {
                    "error": f"Unknown action: {action}",
                    "valid_actions": ["summarize", "connections", "recommend_shift", "intensity_check"]
                }
                
        except Exception as e:
            self.logger.error("Focus analysis failed", error=str(e))
            return {
                "error": f"Analysis failed: {str(e)}"
            }
    
    async def _summarize_focus_areas(self) -> Dict[str, Any]:
        """Summarize current focus areas."""
        if not self.focus_areas:
            return {
                "summary": "No active focus areas",
                "count": 0,
                "areas": []
            }
        
        areas_summary = []
        for focus in self.focus_areas:
            areas_summary.append({
                "theme": focus.theme,
                "intensity": focus.intensity,
                "thought_count": focus.thought_count,
                "keywords": list(focus.keywords)[:5],  # Top 5 keywords
                "age_minutes": (datetime.now() - focus.first_seen).total_seconds() / 60
            })
        
        return {
            "summary": f"Currently tracking {len(self.focus_areas)} focus area(s)",
            "count": len(self.focus_areas),
            "areas": areas_summary,
            "total_intensity": sum(f.intensity for f in self.focus_areas)
        }
    
    async def _find_connections(self) -> Dict[str, Any]:
        """Find connections between focus areas."""
        if len(self.focus_areas) < 2:
            return {
                "connections": [],
                "message": "Need at least 2 focus areas to find connections"
            }
        
        connections = []
        for i, focus1 in enumerate(self.focus_areas):
            for j, focus2 in enumerate(self.focus_areas[i+1:], i+1):
                # Find shared keywords
                shared = focus1.keywords & focus2.keywords
                if shared:
                    connections.append({
                        "themes": [focus1.theme, focus2.theme],
                        "shared_keywords": list(shared),
                        "connection_strength": len(shared) / min(len(focus1.keywords), len(focus2.keywords))
                    })
        
        return {
            "connections": connections,
            "connection_count": len(connections)
        }
    
    async def _recommend_focus_shift(self) -> Dict[str, Any]:
        """Recommend whether to shift focus based on intensities."""
        if not self.focus_areas:
            return {
                "recommendation": "explore",
                "reason": "No active focus areas - time to explore new topics"
            }
        
        # Check for weak focus areas
        weak_areas = [f for f in self.focus_areas if f.intensity < 0.3]
        strong_areas = [f for f in self.focus_areas if f.intensity > 0.7]
        
        if weak_areas:
            return {
                "recommendation": "release",
                "reason": f"Focus area '{weak_areas[0].theme}' has low intensity",
                "suggested_action": f"Consider releasing focus on '{weak_areas[0].theme}'"
            }
        elif not strong_areas and len(self.focus_areas) < 2:
            return {
                "recommendation": "explore",
                "reason": "All focus areas have moderate intensity",
                "suggested_action": "Open to exploring new themes"
            }
        else:
            return {
                "recommendation": "maintain",
                "reason": "Current focus areas are well-balanced",
                "suggested_action": "Continue with current focus distribution"
            }
    
    async def _check_intensities(self, theme: Optional[str]) -> Dict[str, Any]:
        """Check intensity levels of focus areas."""
        if theme:
            # Check specific theme
            matching = [f for f in self.focus_areas if f.theme.lower() == theme.lower()]
            if matching:
                focus = matching[0]
                return {
                    "theme": focus.theme,
                    "intensity": focus.intensity,
                    "status": "strong" if focus.intensity > 0.7 else "moderate" if focus.intensity > 0.3 else "weak",
                    "trend": "growing" if focus.intensity > 0.5 else "fading"
                }
            else:
                return {
                    "error": f"Theme '{theme}' not found in active focus areas"
                }
        else:
            # Check all intensities
            intensity_map = {
                "strong": [],
                "moderate": [],
                "weak": []
            }
            
            for focus in self.focus_areas:
                if focus.intensity > 0.7:
                    intensity_map["strong"].append(focus.theme)
                elif focus.intensity > 0.3:
                    intensity_map["moderate"].append(focus.theme)
                else:
                    intensity_map["weak"].append(focus.theme)
            
            return {
                "intensity_distribution": intensity_map,
                "average_intensity": sum(f.intensity for f in self.focus_areas) / len(self.focus_areas) if self.focus_areas else 0
            }

