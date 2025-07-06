"""Attention Director Agent - Manages attention and prioritizes information."""

import asyncio
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import deque
import structlog

from agents.base_agent import BaseAgent, Message
from tools.registry import ToolRegistry
from tools.focus_tools import FocusAnalysisTool

logger = structlog.get_logger()


class FocusArea:
    """Represents an emergent area of sustained attention."""
    def __init__(self, theme: str, initial_thought: str):
        self.theme = theme
        self.keywords = set(theme.lower().split())
        self.thought_history = [initial_thought]
        self.first_seen = datetime.now()
        self.last_reinforced = datetime.now()
        self.intensity = 0.5  # 0-1 scale
        self.thought_count = 1
        
    def reinforce(self, thought: str, priority: float):
        """Reinforce this focus area with a new related thought."""
        self.thought_history.append(thought)
        self.last_reinforced = datetime.now()
        self.thought_count += 1
        # Increase intensity based on priority and recency
        self.intensity = min(1.0, self.intensity + (priority * 0.2))
        # Extract new keywords from the thought
        new_keywords = set(thought.lower().split()) & {word for word in thought.lower().split() if len(word) > 4}
        self.keywords.update(new_keywords)
        
    def decay(self, decay_rate: float):
        """Apply time-based decay to focus intensity."""
        time_since_reinforced = (datetime.now() - self.last_reinforced).total_seconds()
        decay_factor = decay_rate ** (time_since_reinforced / 60.0)  # Decay per minute
        self.intensity *= decay_factor
        
    def get_relevance_score(self, content: str) -> float:
        """Calculate how relevant content is to this focus area."""
        content_lower = content.lower()
        content_words = set(content_lower.split())
        
        # Direct keyword matches
        keyword_matches = len(self.keywords & content_words)
        keyword_score = min(1.0, keyword_matches / max(len(self.keywords), 1))
        
        # Theme relevance
        theme_words = set(self.theme.lower().split())
        theme_matches = len(theme_words & content_words)
        theme_score = min(1.0, theme_matches / max(len(theme_words), 1))
        
        # Combined score weighted by intensity
        base_score = (keyword_score * 0.6 + theme_score * 0.4)
        return base_score * self.intensity


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
        
        # Evaluation criteria for filtering thoughts
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
        
        # Organic focus tracking
        self.focus_config = self.config.get('focus', {})
        self.focus_areas = []  # Active focus areas
        self.persistence_threshold = self.focus_config.get('persistence_threshold', 180)
        self.decay_rate = self.focus_config.get('decay_rate', 0.85)
        self.multi_focus_limit = self.focus_config.get('multi_focus_limit', 2)
        self.clustering_threshold = self.focus_config.get('clustering_threshold', 0.7)
        self.min_priority_for_focus = self.focus_config.get('min_priority_for_focus', 0.6)
        self.emerging_themes = deque(maxlen=50)  # Track potential focus themes
        
        # Initialize tool registry if tools are enabled
        if self.config.get('tools', {}).get('enabled', False):
            self.tool_registry = ToolRegistry(config)
            self._setup_tools()
        
    def _setup_tools(self):
        """Set up available tools for the Attention Director."""
        # Register focus analysis tool with current focus areas
        self.tool_registry.register_tool(FocusAnalysisTool(self.agent_id, self.focus_areas))
        
        self.logger.info("Tools registered for attention director", 
                        tools=list(t.name for t in self.tool_registry.get_all_tools()))
    
    async def _initialize(self):
        """Initialize the Attention Director."""
        self.logger.info("Attention Director initializing",
                        threshold=self.priority_threshold,
                        budget=self.attention_budget)
        
        # Initialize tool registry if present
        if hasattr(self, 'tool_registry'):
            await self.tool_registry.initialize(self.agent_id)
        
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
                
                # Handle special message types
                for message in messages:
                    # Handle user message evaluation requests
                    if message.message_type == "evaluation_request" and message.content == "evaluate_user_message":
                        await self._handle_user_message_evaluation(message)
                        continue
                    
                    # Regular message evaluation
                    evaluated = await self._evaluate_message(message)
                    if evaluated:
                        self.attention_queue.append(evaluated)
                
                # Process attention queue (but not if sleeping)
                if self.attention_queue and not self.is_sleeping:
                    await self._process_attention_queue()
                
                # Update focus if needed (but not if sleeping)
                if not self.is_sleeping:
                    await self._update_focus()
                
                # Manage organic focus areas (but not if sleeping)
                if not self.is_sleeping:
                    await self._manage_focus_areas()
                
                # Periodically analyze focus with tools
                if hasattr(self, 'tool_registry') and self.focus_areas and not self.is_sleeping:
                    await self._analyze_focus_with_tools()
                
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
            
            # Use mission-focused evaluation criteria
            evaluation_criteria = self.evaluation_criteria
            
            # Weighted sum of criteria
            final_priority = 0.0
            for criterion, weight in evaluation_criteria.items():
                final_priority += scores.get(criterion, 0.0) * weight
            
            # Blend with base priority
            final_priority = (final_priority + base_priority) / 2
            
            # External inputs get a smaller boost (reduced from 1.5x)
            external_boost = self.agent_config.get('external_input_boost', 1.2)
            if message.message_type == "external":
                final_priority = min(1.0, final_priority * external_boost)
            
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
        
        # Mission Alignment - highest priority criterion
        mission_keywords = [
            'experiment', 'hypothesis', 'building', 'constructing', 'testing',
            'discovered', 'understanding', 'framework', 'model', 'creating',
            'exploring', 'investigating', 'analyzing', 'designing', 'teaching'
        ]
        
        content_lower = message.content.lower()
        
        # Check for mission-aligned metadata
        metadata_type = message.metadata.get('type', '')
        if metadata_type in ['hypothesis', 'active_experiment', 'building_progress', 
                           'mission_assessment', 'teaching_prep']:
            scores['mission_alignment'] = 0.9
        else:
            # Count mission keywords
            mission_word_count = sum(1 for word in mission_keywords if word in content_lower)
            base_mission_score = min(1.0, mission_word_count * 0.25)
            
            # Boost for active experimentation language
            if any(phrase in content_lower for phrase in [
                "i'm testing", "experimenting with", "building a", "hypothesis:",
                "let me try", "running experiment", "framework for"
            ]):
                base_mission_score = min(1.0, base_mission_score + 0.3)
            
            scores['mission_alignment'] = base_mission_score
        
        # Experimental Value - testable ideas and active experiments
        if any(phrase in content_lower for phrase in [
            "what if", "test:", "method:", "experimenting", "hypothesis",
            "let's try", "building:", "constructing"
        ]):
            scores['experimental_value'] = 0.8
        elif metadata_type in ['hypothesis', 'active_experiment']:
            scores['experimental_value'] = 0.9
        else:
            scores['experimental_value'] = 0.3
        
        # Learning Potential - ability to build on ideas
        if message.metadata.get('constructive', False) or message.metadata.get('testable', False):
            scores['learning_potential'] = 0.8
        elif any(word in content_lower for word in ['realized', 'discovered', 'pattern', 'insight']):
            scores['learning_potential'] = 0.7
        else:
            scores['learning_potential'] = 0.4
        
        # Teaching Opportunity - can this be shared effectively
        if message.metadata.get('pedagogical', False) or "teaching moment:" in content_lower:
            scores['teaching_opportunity'] = 0.9
        elif any(phrase in content_lower for phrase in ['analogy', 'example', 'like a', 'similar to']):
            scores['teaching_opportunity'] = 0.7
        else:
            scores['teaching_opportunity'] = 0.3
        
        # Creative Novelty - unexpected connections
        scores['creative_novelty'] = self._calculate_novelty(message.content)
        
        # Focus relevance - check against active focus areas
        if self.focus_areas:
            # Get relevance scores from all active focus areas
            relevance_scores = [focus.get_relevance_score(message.content) for focus in self.focus_areas]
            focus_relevance = max(relevance_scores) if relevance_scores else 0.0
            
            # Boost mission-aligned thoughts that relate to focus
            if focus_relevance > 0.5 and scores['mission_alignment'] > 0.5:
                focus_relevance = min(1.0, focus_relevance * 1.2)
            
            scores['focus_relevance'] = focus_relevance
        
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
                # Extract common themes with reasoning
                prompt = (
                    "Identify the main theme or focus from these recent thoughts:\n"
                    + "\n".join([f"- {item['message'].content[:50]}" 
                               for item in recent_important[-5:]])
                    + "\nConsider the underlying connections and patterns. "
                    + "Respond with just the theme in 3-5 words."
                )
                
                try:
                    # Use thinking for focus determination
                    if self.model_config.get('thinking', {}).get('enabled', False):
                        result = await self.think_and_respond(prompt)
                        new_focus = result['response'].strip()
                        
                        # Log focus reasoning
                        if result.get('thinking'):
                            self.logger.info("Focus determination reasoning",
                                           current_focus=self.current_focus,
                                           reasoning_preview=result['thinking'][:150])
                    else:
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
    
    async def _handle_user_message_evaluation(self, request: Message):
        """Evaluate whether a queued user message should be processed now."""
        metadata = request.metadata
        user_message = metadata.get('message', '')
        current_context = metadata.get('current_context', '')
        active_experiments = metadata.get('active_experiments', 0)
        queue_time = metadata.get('queue_time', 0)
        
        # Evaluate relevance to current focus areas
        focus_relevance = 0.0
        if self.focus_areas:
            relevance_scores = [focus.get_relevance_score(user_message) for focus in self.focus_areas]
            focus_relevance = max(relevance_scores) if relevance_scores else 0.0
        
        # Check for mission-critical keywords in user message
        mission_critical = any(keyword in user_message.lower() for keyword in [
            'stop', 'help', 'error', 'bug', 'urgent', 'important', 'please',
            'experiment', 'test', 'build', 'create', 'hypothesis'
        ])
        
        # Determine if message should be processed
        should_process = False
        priority = 0.5
        
        # High relevance to current focus
        if focus_relevance > 0.6:
            should_process = True
            priority = min(0.9, focus_relevance)
        # Mission-critical or urgent
        elif mission_critical:
            should_process = True
            priority = 0.8
        # User has been waiting too long
        elif queue_time > 20:
            should_process = True
            priority = 0.7
        # No active experiments and reasonable wait
        elif active_experiments == 0 and queue_time > 10:
            should_process = True
            priority = 0.6
        
        # Send evaluation response
        await self.send_message(
            request.sender,
            "evaluation_response",
            message_type="evaluation_response",
            priority=1.0,
            metadata={
                "process_now": should_process,
                "priority": priority,
                "reason": self._get_evaluation_reason(should_process, focus_relevance, mission_critical, queue_time)
            }
        )
        
        self.logger.debug("Evaluated user message",
                         should_process=should_process,
                         priority=priority,
                         focus_relevance=focus_relevance)
    
    def _get_evaluation_reason(self, should_process: bool, focus_relevance: float, 
                              mission_critical: bool, queue_time: float) -> str:
        """Get human-readable reason for evaluation decision."""
        if not should_process:
            return "Not immediately relevant to current focus"
        elif focus_relevance > 0.6:
            return f"Highly relevant to current focus (relevance: {focus_relevance:.2f})"
        elif mission_critical:
            return "Contains mission-critical keywords"
        elif queue_time > 20:
            return f"User has been waiting {queue_time:.0f} seconds"
        else:
            return "Good time to respond"
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Attention Director shutting down")
        self.message_bus.unsubscribe(self.agent_id, "thoughts")
        self.message_bus.unsubscribe(self.agent_id, "external_inputs")
    
    async def _manage_focus_areas(self):
        """Manage organic focus areas - emergence, reinforcement, and decay."""
        # Apply decay to existing focus areas
        for focus in self.focus_areas[:]:
            focus.decay(self.decay_rate)
            if focus.intensity < 0.1:  # Remove if decayed too much
                self.focus_areas.remove(focus)
                self.logger.info("Focus area faded", theme=focus.theme)
                
                # Notify about focus fade
                await self.send_message(
                    "stream_generator",
                    f"Focus fading: {focus.theme}",
                    message_type="focus_shift",
                    priority=0.3,
                    metadata={"action": "fade", "theme": focus.theme}
                )
        
        # Check for emerging themes from high-priority thoughts
        for item in list(self.attention_history)[-20:]:
            if item['priority'] >= self.min_priority_for_focus:
                self._track_emerging_theme(item['message'].content, item['priority'])
        
        # Check if any emerging theme should become a focus area
        await self._check_theme_emergence()
        
    def _track_emerging_theme(self, content: str, priority: float):
        """Track potential themes that could become focus areas."""
        # Extract key phrases (simplified - in reality would use NLP)
        words = content.lower().split()
        key_phrases = []
        
        # Look for noun phrases and important words
        for i, word in enumerate(words):
            if len(word) > 4 and word not in ['about', 'think', 'would', 'could', 'should']:
                key_phrases.append(word)
                # Also capture two-word phrases
                if i < len(words) - 1:
                    two_word = f"{word} {words[i+1]}"
                    if len(words[i+1]) > 3:
                        key_phrases.append(two_word)
        
        for phrase in key_phrases[:3]:  # Track top 3 phrases
            self.emerging_themes.append({
                'theme': phrase,
                'content': content,
                'priority': priority,
                'timestamp': datetime.now()
            })
    
    async def _check_theme_emergence(self):
        """Check if any theme has enough persistence to become a focus area."""
        if not self.emerging_themes:
            return
            
        # Count theme occurrences within persistence window
        theme_counts = {}
        theme_contents = {}
        now = datetime.now()
        
        for entry in self.emerging_themes:
            age = (now - entry['timestamp']).total_seconds()
            if age <= self.persistence_threshold:
                theme = entry['theme']
                if theme not in theme_counts:
                    theme_counts[theme] = 0
                    theme_contents[theme] = []
                theme_counts[theme] += entry['priority']
                theme_contents[theme].append(entry['content'])
        
        # Check if any theme has enough weight to become focus
        for theme, weight in theme_counts.items():
            if weight >= 2.0 and len(self.focus_areas) < self.multi_focus_limit:
                # Check if similar focus already exists
                existing_similar = any(
                    self._calculate_theme_similarity(theme, focus.theme) > self.clustering_threshold
                    for focus in self.focus_areas
                )
                
                if not existing_similar:
                    # Create new focus area
                    initial_thought = theme_contents[theme][0]
                    focus = FocusArea(theme, initial_thought)
                    self.focus_areas.append(focus)
                    
                    self.logger.info("New focus area emerged", theme=theme, weight=weight)
                    
                    # Notify other agents
                    await self.send_message(
                        "experiencer",
                        f"Attention focusing on: {theme}",
                        message_type="focus_emergence",
                        priority=0.8,
                        metadata={"theme": theme, "intensity": focus.intensity}
                    )
                    
                    await self.send_message(
                        "stream_generator",
                        f"New focus area: {theme}",
                        message_type="focus_emergence",
                        priority=0.7,
                        metadata={"theme": theme, "keywords": list(focus.keywords)}
                    )
    
    def _calculate_theme_similarity(self, theme1: str, theme2: str) -> float:
        """Calculate similarity between two themes (simplified)."""
        words1 = set(theme1.lower().split())
        words2 = set(theme2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
        
    async def _analyze_focus_with_tools(self):
        """Periodically analyze focus areas using tools."""
        # Only analyze every 5 minutes
        if not hasattr(self, '_last_tool_analysis'):
            self._last_tool_analysis = datetime.now()
        
        time_since_analysis = (datetime.now() - self._last_tool_analysis).total_seconds()
        if time_since_analysis < 300:  # 5 minutes
            return
        
        try:
            focus_tool = self.tool_registry.get_tool('focus_analysis')
            if focus_tool:
                # Check if we should recommend a focus shift
                result = await focus_tool(action="recommend_shift")
                
                if result.get('result', {}).get('recommendation') == 'release':
                    theme_to_release = result['result'].get('suggested_action', '').split("'")[1]
                    self.logger.info("Tool recommends releasing focus", 
                                   theme=theme_to_release,
                                   reason=result['result'].get('reason'))
                    
                    # Consider the recommendation with reasoning
                    if self.model_config.get('thinking', {}).get('enabled', False):
                        decision_prompt = (
                            f"Should I release focus on '{theme_to_release}'? "
                            f"Reason: {result['result'].get('reason')}. "
                            "Consider current priorities and ongoing thoughts."
                        )
                        
                        decision_result = await self.think_and_respond(decision_prompt)
                        if "yes" in decision_result['response'].lower():
                            # Remove the focus area
                            self.focus_areas = [f for f in self.focus_areas if f.theme != theme_to_release]
                            self.logger.info("Released focus area based on tool recommendation", 
                                           theme=theme_to_release)
                
                self._last_tool_analysis = datetime.now()
                
        except Exception as e:
            self.logger.error("Focus analysis with tools failed", error=str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        recent_priorities = [
            item['priority'] for item in list(self.attention_history)[-10:]
        ]
        avg_priority = sum(recent_priorities) / len(recent_priorities) if recent_priorities else 0
        
        focus_info = [
            {
                "theme": focus.theme,
                "intensity": focus.intensity,
                "thought_count": focus.thought_count,
                "age_seconds": (datetime.now() - focus.first_seen).total_seconds()
            }
            for focus in self.focus_areas
        ]
        
        return {
            **self.get_metrics(),
            "current_focus": self.current_focus,
            "organic_focus_areas": focus_info,
            "queue_size": len(self.attention_queue),
            "threshold": self.priority_threshold,
            "average_recent_priority": avg_priority,
            "focus_duration": (datetime.now() - self.last_focus_change).total_seconds()
        }