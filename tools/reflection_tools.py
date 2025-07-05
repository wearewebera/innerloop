"""Reflection and introspection tools for InnerLoop agents."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from tools.base_tool import BaseTool, ToolParameter
import structlog

logger = structlog.get_logger()


class ReflectionTool(BaseTool):
    """Tool for deep self-reflection and introspection."""
    
    def __init__(self, agent_id: str = None, memory_store: Any = None):
        super().__init__(agent_id)
        self.memory_store = memory_store
        
    @property
    def name(self) -> str:
        return "reflection"
    
    @property
    def description(self) -> str:
        return (
            "Perform deep self-reflection on thoughts, behaviors, and patterns. "
            "Can analyze personal growth, identify patterns, or generate insights about self."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="reflection_type",
                type="string",
                description="Type of reflection: 'patterns', 'growth', 'insights', 'emotions', 'behaviors'",
                required=True
            ),
            ToolParameter(
                name="timeframe",
                type="string",
                description="Timeframe to reflect on: 'recent', 'today', 'week', 'all'",
                required=False,
                default="recent"
            ),
            ToolParameter(
                name="focus_area",
                type="string",
                description="Specific area or theme to focus reflection on",
                required=False,
                default=None
            ),
            ToolParameter(
                name="depth",
                type="string",
                description="Depth of reflection: 'surface', 'moderate', 'deep'",
                required=False,
                default="moderate"
            )
        ]
    
    async def execute(self, reflection_type: str, timeframe: str = "recent",
                     focus_area: Optional[str] = None, depth: str = "moderate") -> Dict[str, Any]:
        """Perform reflection based on type and parameters."""
        try:
            # Get relevant memories for reflection
            memories = await self._gather_memories_for_reflection(timeframe, focus_area)
            
            if reflection_type == "patterns":
                return await self._reflect_on_patterns(memories, depth)
            elif reflection_type == "growth":
                return await self._reflect_on_growth(memories, depth)
            elif reflection_type == "insights":
                return await self._reflect_on_insights(memories, depth)
            elif reflection_type == "emotions":
                return await self._reflect_on_emotions(memories, depth)
            elif reflection_type == "behaviors":
                return await self._reflect_on_behaviors(memories, depth)
            else:
                return {
                    "error": f"Unknown reflection type: {reflection_type}",
                    "valid_types": ["patterns", "growth", "insights", "emotions", "behaviors"]
                }
                
        except Exception as e:
            self.logger.error("Reflection failed", error=str(e))
            return {
                "error": f"Reflection failed: {str(e)}"
            }
    
    async def _gather_memories_for_reflection(self, timeframe: str, focus_area: Optional[str]) -> List[Dict]:
        """Gather relevant memories based on timeframe and focus."""
        if not self.memory_store:
            return []
        
        # Determine time window
        now = datetime.now()
        if timeframe == "recent":
            time_limit = now - timedelta(hours=1)
        elif timeframe == "today":
            time_limit = now.replace(hour=0, minute=0, second=0)
        elif timeframe == "week":
            time_limit = now - timedelta(days=7)
        else:  # "all"
            time_limit = None
        
        # Search for memories
        query = focus_area if focus_area else ""
        memories = await self.memory_store.search_memories(
            query=query,
            limit=50,
            agent_id=self.agent_id
        )
        
        # Filter by timeframe if needed
        if time_limit and memories:
            filtered = []
            for memory in memories:
                if hasattr(memory.get('timestamp'), 'timestamp'):
                    mem_time = datetime.fromtimestamp(memory['timestamp'].timestamp())
                elif isinstance(memory.get('timestamp'), str):
                    try:
                        mem_time = datetime.fromisoformat(memory['timestamp'])
                    except:
                        continue
                else:
                    continue
                    
                if mem_time >= time_limit:
                    filtered.append(memory)
            memories = filtered
        
        return memories
    
    async def _reflect_on_patterns(self, memories: List[Dict], depth: str) -> Dict[str, Any]:
        """Reflect on patterns in thoughts and behaviors."""
        if not memories:
            return {
                "reflection": "No memories available for pattern analysis",
                "patterns": []
            }
        
        # Analyze themes
        themes = {}
        for memory in memories:
            content = memory.get('content', '').lower()
            # Simple keyword extraction (in real implementation, use NLP)
            words = content.split()
            for word in words:
                if len(word) > 5:  # Focus on meaningful words
                    themes[word] = themes.get(word, 0) + 1
        
        # Find top themes
        top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
        
        patterns = []
        if depth in ["moderate", "deep"]:
            # Look for recurring patterns
            for theme, count in top_themes:
                if count > 2:
                    patterns.append({
                        "theme": theme,
                        "frequency": count,
                        "significance": "high" if count > 5 else "moderate"
                    })
        
        reflection = f"Analyzing {len(memories)} memories reveals "
        if patterns:
            reflection += f"{len(patterns)} recurring patterns, primarily around: {', '.join([p['theme'] for p in patterns[:3]])}"
        else:
            reflection += "diverse thoughts without strong recurring patterns"
        
        return {
            "reflection": reflection,
            "patterns": patterns,
            "memory_count": len(memories),
            "dominant_themes": [t[0] for t in top_themes]
        }
    
    async def _reflect_on_growth(self, memories: List[Dict], depth: str) -> Dict[str, Any]:
        """Reflect on personal growth and development."""
        if not memories:
            return {
                "reflection": "No memories available for growth analysis",
                "growth_indicators": []
            }
        
        # Look for growth indicators
        growth_indicators = []
        
        # Check for learning moments
        learning_keywords = ["learned", "realized", "understood", "discovered", "insight"]
        learning_count = sum(1 for m in memories if any(kw in m.get('content', '').lower() for kw in learning_keywords))
        
        if learning_count > 0:
            growth_indicators.append({
                "area": "learning",
                "evidence": f"{learning_count} learning moments identified",
                "growth_level": "active"
            })
        
        # Check for complexity evolution (simplified)
        if len(memories) > 10:
            early_memories = memories[:5]
            recent_memories = memories[-5:]
            
            early_avg_length = sum(len(m.get('content', '')) for m in early_memories) / 5
            recent_avg_length = sum(len(m.get('content', '')) for m in recent_memories) / 5
            
            if recent_avg_length > early_avg_length * 1.2:
                growth_indicators.append({
                    "area": "depth",
                    "evidence": "Thoughts becoming more elaborate",
                    "growth_level": "expanding"
                })
        
        reflection = f"Growth analysis across {len(memories)} memories shows "
        if growth_indicators:
            reflection += f"positive development in {len(growth_indicators)} areas"
        else:
            reflection += "steady state with potential for new growth opportunities"
        
        return {
            "reflection": reflection,
            "growth_indicators": growth_indicators,
            "recommendation": "Continue exploring new perspectives" if growth_indicators else "Seek new challenges for growth"
        }
    
    async def _reflect_on_insights(self, memories: List[Dict], depth: str) -> Dict[str, Any]:
        """Reflect on key insights and realizations."""
        insights = []
        
        # Look for insight indicators
        insight_keywords = ["insight", "realized", "understand", "aha", "discovered"]
        
        for memory in memories:
            content = memory.get('content', '')
            if any(kw in content.lower() for kw in insight_keywords):
                insights.append({
                    "content": content,
                    "type": memory.get('memory_type', 'general'),
                    "timestamp": str(memory.get('timestamp', ''))
                })
        
        # Generate meta-insight
        if insights:
            reflection = f"Identified {len(insights)} key insights. "
            if depth == "deep":
                reflection += "These insights reveal a pattern of growing understanding and curiosity."
        else:
            reflection = "No explicit insights found, but learning continues through exploration."
        
        return {
            "reflection": reflection,
            "insights": insights[:5],  # Top 5 insights
            "insight_count": len(insights),
            "meta_insight": "Insights emerge from sustained attention and open curiosity"
        }
    
    async def _reflect_on_emotions(self, memories: List[Dict], depth: str) -> Dict[str, Any]:
        """Reflect on emotional patterns and states."""
        # Simple emotion detection (in real implementation, use sentiment analysis)
        emotion_keywords = {
            "positive": ["happy", "excited", "joy", "love", "grateful", "wonder"],
            "negative": ["sad", "worried", "fear", "anxious", "frustrated"],
            "neutral": ["think", "observe", "notice", "consider"]
        }
        
        emotion_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for memory in memories:
            content = memory.get('content', '').lower()
            for emotion_type, keywords in emotion_keywords.items():
                if any(kw in content for kw in keywords):
                    emotion_counts[emotion_type] += 1
        
        total = sum(emotion_counts.values())
        if total > 0:
            emotion_balance = {
                "positive": emotion_counts["positive"] / total,
                "negative": emotion_counts["negative"] / total,
                "neutral": emotion_counts["neutral"] / total
            }
        else:
            emotion_balance = {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
        
        dominant_emotion = max(emotion_balance.items(), key=lambda x: x[1])[0]
        
        reflection = f"Emotional reflection reveals a {dominant_emotion} tendency "
        if depth in ["moderate", "deep"]:
            reflection += f"with {emotion_balance[dominant_emotion]*100:.0f}% of thoughts in this category"
        
        return {
            "reflection": reflection,
            "emotion_balance": emotion_balance,
            "dominant_emotion": dominant_emotion,
            "emotional_stability": "balanced" if max(emotion_balance.values()) < 0.6 else "focused"
        }
    
    async def _reflect_on_behaviors(self, memories: List[Dict], depth: str) -> Dict[str, Any]:
        """Reflect on behavioral patterns and tendencies."""
        behaviors = {
            "questioning": 0,
            "observing": 0,
            "analyzing": 0,
            "creating": 0,
            "connecting": 0
        }
        
        # Analyze behavioral indicators
        for memory in memories:
            content = memory.get('content', '').lower()
            if "?" in content or any(q in content for q in ["what", "why", "how", "when"]):
                behaviors["questioning"] += 1
            if any(o in content for o in ["notice", "observe", "see", "watch"]):
                behaviors["observing"] += 1
            if any(a in content for a in ["analyze", "think", "consider", "evaluate"]):
                behaviors["analyzing"] += 1
            if any(c in content for c in ["create", "make", "build", "generate"]):
                behaviors["creating"] += 1
            if any(c in content for c in ["connect", "relate", "link", "associate"]):
                behaviors["connecting"] += 1
        
        # Find dominant behaviors
        total_behaviors = sum(behaviors.values())
        if total_behaviors > 0:
            behavior_profile = {k: v/total_behaviors for k, v in behaviors.items()}
            dominant_behavior = max(behaviors.items(), key=lambda x: x[1])[0]
        else:
            behavior_profile = {k: 0.2 for k in behaviors.keys()}
            dominant_behavior = "balanced"
        
        reflection = f"Behavioral analysis shows a {dominant_behavior} tendency "
        if depth == "deep":
            reflection += "suggesting an active engagement with understanding and exploration"
        
        return {
            "reflection": reflection,
            "behavior_profile": behavior_profile,
            "dominant_behavior": dominant_behavior,
            "behavioral_diversity": len([b for b in behaviors.values() if b > 0])
        }