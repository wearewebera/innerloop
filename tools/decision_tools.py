"""Decision-making tools for InnerLoop agents."""

from typing import Dict, Any, List, Optional
from tools.base_tool import BaseTool, ToolParameter
import structlog
import random

logger = structlog.get_logger()


class DecisionMakerTool(BaseTool):
    """Tool for making autonomous decisions based on context and priorities."""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)
        
    @property
    def name(self) -> str:
        return "decision_maker"
    
    @property
    def description(self) -> str:
        return (
            "Make autonomous decisions by evaluating options against criteria. "
            "Can choose between alternatives, prioritize actions, or determine next steps."
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="decision_type",
                type="string",
                description="Type of decision: 'choose_option', 'prioritize', 'yes_no', 'next_action'",
                required=True
            ),
            ToolParameter(
                name="context",
                type="string",
                description="Context or question requiring a decision",
                required=True
            ),
            ToolParameter(
                name="options",
                type="array",
                description="List of options to choose from (for choose_option/prioritize)",
                required=False,
                default=[]
            ),
            ToolParameter(
                name="criteria",
                type="array",
                description="Decision criteria to consider",
                required=False,
                default=["relevance", "impact", "feasibility"]
            )
        ]
    
    async def execute(self, decision_type: str, context: str, 
                     options: List[str] = None, criteria: List[str] = None) -> Dict[str, Any]:
        """Make a decision based on type and context."""
        try:
            if decision_type == "choose_option":
                return await self._choose_option(context, options or [], criteria or [])
            elif decision_type == "prioritize":
                return await self._prioritize_options(context, options or [], criteria or [])
            elif decision_type == "yes_no":
                return await self._yes_no_decision(context, criteria or [])
            elif decision_type == "next_action":
                return await self._determine_next_action(context, criteria or [])
            else:
                return {
                    "error": f"Unknown decision type: {decision_type}",
                    "valid_types": ["choose_option", "prioritize", "yes_no", "next_action"]
                }
                
        except Exception as e:
            self.logger.error("Decision making failed", error=str(e))
            return {
                "error": f"Decision failed: {str(e)}"
            }
    
    async def _choose_option(self, context: str, options: List[str], criteria: List[str]) -> Dict[str, Any]:
        """Choose the best option from a list."""
        if not options:
            return {
                "error": "No options provided for decision"
            }
        
        # Evaluate each option against criteria
        evaluations = []
        for option in options:
            scores = {}
            total_score = 0
            
            for criterion in criteria:
                # Simulate evaluation (in real implementation, would use model reasoning)
                score = self._evaluate_option(option, criterion, context)
                scores[criterion] = score
                total_score += score
            
            evaluations.append({
                "option": option,
                "scores": scores,
                "total": total_score / len(criteria) if criteria else 0
            })
        
        # Sort by total score
        evaluations.sort(key=lambda x: x["total"], reverse=True)
        
        return {
            "decision": evaluations[0]["option"],
            "confidence": evaluations[0]["total"],
            "reasoning": f"Best option based on {', '.join(criteria)}",
            "all_evaluations": evaluations
        }
    
    async def _prioritize_options(self, context: str, options: List[str], criteria: List[str]) -> Dict[str, Any]:
        """Prioritize a list of options."""
        if not options:
            return {
                "error": "No options provided for prioritization"
            }
        
        # Similar to choose_option but return ordered list
        evaluations = []
        for option in options:
            scores = {}
            total_score = 0
            
            for criterion in criteria:
                score = self._evaluate_option(option, criterion, context)
                scores[criterion] = score
                total_score += score
            
            evaluations.append({
                "option": option,
                "priority_score": total_score / len(criteria) if criteria else 0,
                "criteria_scores": scores
            })
        
        # Sort by priority score
        evaluations.sort(key=lambda x: x["priority_score"], reverse=True)
        
        return {
            "prioritized_list": [e["option"] for e in evaluations],
            "detailed_priorities": evaluations,
            "top_priority": evaluations[0]["option"] if evaluations else None
        }
    
    async def _yes_no_decision(self, context: str, criteria: List[str]) -> Dict[str, Any]:
        """Make a yes/no decision."""
        # Evaluate positive and negative factors
        positive_score = 0
        negative_score = 0
        factors = {
            "positive": [],
            "negative": []
        }
        
        # Simulate reasoning (in real implementation, would use model)
        for criterion in criteria:
            score = self._evaluate_option("yes", criterion, context)
            if score > 0.5:
                positive_score += score
                factors["positive"].append(f"{criterion}: {score:.2f}")
            else:
                negative_score += (1 - score)
                factors["negative"].append(f"{criterion}: {1-score:.2f}")
        
        decision = "yes" if positive_score > negative_score else "no"
        confidence = abs(positive_score - negative_score) / (positive_score + negative_score) if (positive_score + negative_score) > 0 else 0
        
        return {
            "decision": decision,
            "confidence": confidence,
            "reasoning": f"{'Positive' if decision == 'yes' else 'Negative'} factors outweigh",
            "factors": factors
        }
    
    async def _determine_next_action(self, context: str, criteria: List[str]) -> Dict[str, Any]:
        """Determine the next action to take."""
        # Generate potential actions based on context
        potential_actions = [
            "gather more information",
            "proceed with current plan",
            "reconsider approach",
            "seek input from others",
            "take immediate action"
        ]
        
        # Evaluate each action
        action_scores = {}
        for action in potential_actions:
            score = self._evaluate_option(action, "appropriateness", context)
            action_scores[action] = score
        
        # Choose best action
        best_action = max(action_scores.items(), key=lambda x: x[1])
        
        return {
            "next_action": best_action[0],
            "confidence": best_action[1],
            "alternatives": action_scores,
            "reasoning": f"Based on current context and {', '.join(criteria)}"
        }
    
    def _evaluate_option(self, option: str, criterion: str, context: str) -> float:
        """Evaluate an option against a criterion (simplified for demo)."""
        # In a real implementation, this would use the model's reasoning
        # For now, return a pseudo-random score based on string hashing
        combined = f"{option}{criterion}{context}"
        hash_value = sum(ord(c) for c in combined)
        
        # Add some deterministic variation
        if "urgent" in context.lower() and "immediate" in option.lower():
            return min(1.0, 0.7 + (hash_value % 30) / 100)
        elif "careful" in context.lower() and "gather" in option.lower():
            return min(1.0, 0.8 + (hash_value % 20) / 100)
        else:
            return (hash_value % 100) / 100