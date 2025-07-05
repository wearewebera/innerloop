"""Attention Director Agent - Manages attention and prioritizes information."""

import asyncio
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import deque
import structlog

from agents.base_agent import BaseAgent, Message

logger = structlog.get_logger()


class AttentionDirectorAgent(BaseAgent):
    """
    The Attention Director filters and prioritizes information flow.
    It decides what deserves conscious attention from the Experiencer.
    """
    
    def __init__(self, config: Dict[str, Any], message_bus: Any, memory_store: Any):
        super().__init__("attention_director", config, message_bus, memory_store)
        
        # Attention settings
        self.priority_threshold = self.agent_config.get('priority_threshold', 0.3)
        self.attention_budget = self.agent_config.get('attention_budget', 5)
        self.evaluation_criteria = self.agent_config.get('evaluation_criteria', {
            'relevance': 0.4,
            'urgency': 0.3,
            'novelty': 0.2,
            'emotional_significance': 0.1
        })
        
        # Attention state
        self.attention_queue = deque(maxlen=100)
        self.attention_history = deque(maxlen=1000)
        self.current_focus = None
        self.focus_duration = timedelta(seconds=5)
        self.last_focus_change = datetime.now()
        
        # Track patterns for better filtering
        self.thought_patterns = {}
        self.relevance_scores = {}
        
    async def _initialize(self):
        """Initialize the Attention Director."""
        self.logger.info("Attention Director initializing",
                        threshold=self.priority_threshold,
                        budget=self.attention_budget)
        
        # Subscribe to all thought streams
        self.message_bus.subscribe(self.agent_id, "thoughts")
        self.message_bus.subscribe(self.agent_id, "external_inputs")
    
    async def _run_loop(self):
        """Main loop - evaluate and prioritize incoming information."""
        self.logger.info("Attention Director started")
        
        while self.is_running:
            try:
                # Collect incoming messages
                messages = await self.receive_messages()
                
                # Add to attention queue with evaluated priority
                for message in messages:
                    evaluated = await self._evaluate_message(message)
                    if evaluated:
                        self.attention_queue.append(evaluated)
                
                # Process attention queue
                if self.attention_queue:
                    await self._process_attention_queue()
                
                # Update focus if needed
                await self._update_focus()
                
                # Small delay
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error("Attention loop error", error=str(e))
                await asyncio.sleep(1)
    
    async def _evaluate_message(self, message: Message) -> Dict[str, Any]:
        """Evaluate a message and determine its attention priority."""
        try:
            # Start with the message's base priority
            base_priority = message.priority
            
            # Calculate evaluation scores
            scores = await self._calculate_attention_scores(message)
            
            # Weighted sum of criteria
            final_priority = 0.0
            for criterion, weight in self.evaluation_criteria.items():
                final_priority += scores.get(criterion, 0.0) * weight
            
            # Blend with base priority
            final_priority = (final_priority + base_priority) / 2
            
            # External inputs get a boost
            if message.message_type == "external":
                final_priority = min(1.0, final_priority * 1.5)
            
            self.logger.debug("Evaluated message",
                            sender=message.sender,
                            type=message.message_type,
                            original_priority=base_priority,
                            final_priority=final_priority)
            
            # Broadcast evaluation result
            decision = "PASS" if final_priority >= self.priority_threshold else "FILTERED"
            await self.send_message(
                "topic:evaluations",
                f"Evaluated: {message.content[:50]}...",
                message_type="evaluation",
                priority=final_priority,
                metadata={
                    "evaluated_content": message.content,
                    "original_priority": base_priority,
                    "final_priority": final_priority,
                    "decision": decision,
                    "scores": scores,
                    "threshold": self.priority_threshold
                }
            )
            
            # Only keep if above threshold
            if final_priority >= self.priority_threshold:
                return {
                    "message": message,
                    "priority": final_priority,
                    "scores": scores,
                    "timestamp": datetime.now()
                }
            
            return None
            
        except Exception as e:
            self.logger.error("Evaluation error", error=str(e))
            return None
    
    async def _calculate_attention_scores(self, message: Message) -> Dict[str, float]:
        """Calculate individual attention criteria scores."""
        scores = {}
        
        # Relevance - based on current focus and recent context
        if self.current_focus:
            relevance_prompt = (
                f"Rate the relevance of this thought to our current focus "
                f"('{self.current_focus}'): '{message.content}'\n"
                "Respond with just a number between 0 and 1."
            )
            try:
                relevance = await self.generate_response(relevance_prompt)
                scores['relevance'] = float(relevance.strip())
            except:
                scores['relevance'] = 0.5
        else:
            scores['relevance'] = 0.5
        
        # Urgency - external inputs and time-sensitive thoughts
        if message.message_type == "external":
            scores['urgency'] = 0.9
        elif "now" in message.content.lower() or "urgent" in message.content.lower():
            scores['urgency'] = 0.7
        else:
            scores['urgency'] = 0.3
        
        # Novelty - how different from recent thoughts
        scores['novelty'] = self._calculate_novelty(message.content)
        
        # Emotional significance
        emotional_words = ['feel', 'felt', 'happy', 'sad', 'worried', 'excited', 
                          'love', 'fear', 'hope', 'wonder']
        word_count = sum(1 for word in emotional_words if word in message.content.lower())
        scores['emotional_significance'] = min(1.0, word_count * 0.2)
        
        return scores
    
    def _calculate_novelty(self, content: str) -> float:
        """Calculate how novel/different a thought is from recent ones."""
        if not self.attention_history:
            return 0.8
        
        # Simple novelty: check word overlap with recent thoughts
        content_words = set(content.lower().split())
        
        overlap_scores = []
        for item in list(self.attention_history)[-10:]:
            historical_words = set(item['message'].content.lower().split())
            if historical_words:
                overlap = len(content_words & historical_words) / len(content_words | historical_words)
                overlap_scores.append(overlap)
        
        if overlap_scores:
            avg_overlap = sum(overlap_scores) / len(overlap_scores)
            novelty = 1.0 - avg_overlap
        else:
            novelty = 0.8
        
        return novelty
    
    async def _process_attention_queue(self):
        """Process the attention queue and forward high-priority items."""
        # Sort by priority
        sorted_items = sorted(
            self.attention_queue,
            key=lambda x: x['priority'],
            reverse=True
        )
        
        # Take top items within budget
        to_process = sorted_items[:self.attention_budget]
        
        for item in to_process:
            message = item['message']
            
            # Forward to experiencer
            await self.send_message(
                "experiencer",
                message.content,
                message_type="filtered_thought",
                priority=item['priority'],
                metadata={
                    **message.metadata,
                    "attention_scores": item['scores'],
                    "original_sender": message.sender
                }
            )
            
            # Also broadcast for thought monitor
            await self.send_message(
                "topic:filtered_thoughts",
                message.content,
                message_type="filtered_thought",
                priority=item['priority'],
                metadata={
                    **message.metadata,
                    "attention_scores": item['scores'],
                    "original_sender": message.sender
                }
            )
            
            # Add to history
            self.attention_history.append(item)
            
            # Log high-priority items
            if item['priority'] >= 0.7:
                self.logger.info("High priority thought forwarded",
                               priority=item['priority'],
                               preview=message.content[:50])
        
        # Clear processed items
        self.attention_queue.clear()
    
    async def _update_focus(self):
        """Update current focus based on patterns and time."""
        now = datetime.now()
        
        # Check if it's time to potentially shift focus
        if (now - self.last_focus_change) > self.focus_duration:
            # Analyze recent high-priority thoughts for themes
            recent_important = [
                item for item in list(self.attention_history)[-20:]
                if item['priority'] >= 0.6
            ]
            
            if recent_important:
                # Extract common themes
                prompt = (
                    "Identify the main theme or focus from these recent thoughts:\n"
                    + "\n".join([f"- {item['message'].content[:50]}" 
                               for item in recent_important[-5:]])
                    + "\nRespond with just the theme in 3-5 words."
                )
                
                try:
                    new_focus = await self.generate_response(prompt)
                    if new_focus != self.current_focus:
                        self.current_focus = new_focus.strip()
                        self.last_focus_change = now
                        
                        self.logger.info("Focus updated", new_focus=self.current_focus)
                        
                        # Notify experiencer of focus change
                        await self.send_message(
                            "experiencer",
                            f"Attention shifting to: {self.current_focus}",
                            message_type="focus_change",
                            priority=0.8
                        )
                        
                        # Broadcast focus change for thought monitor
                        await self.send_message(
                            "topic:thoughts",
                            f"Attention shifting to: {self.current_focus}",
                            message_type="focus_change",
                            priority=0.8,
                            metadata={"type": "focus_change"}
                        )
                except Exception as e:
                    self.logger.error("Focus update failed", error=str(e))
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Attention Director shutting down")
        self.message_bus.unsubscribe(self.agent_id, "thoughts")
        self.message_bus.unsubscribe(self.agent_id, "external_inputs")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        recent_priorities = [
            item['priority'] for item in list(self.attention_history)[-10:]
        ]
        avg_priority = sum(recent_priorities) / len(recent_priorities) if recent_priorities else 0
        
        return {
            **self.get_metrics(),
            "current_focus": self.current_focus,
            "queue_size": len(self.attention_queue),
            "threshold": self.priority_threshold,
            "average_recent_priority": avg_priority,
            "focus_duration": (datetime.now() - self.last_focus_change).total_seconds()
        }