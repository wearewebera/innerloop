"""Thoughts Agent - Autonomous thought generator."""

import asyncio
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta
import structlog

from agents.base_agent import BaseAgent

logger = structlog.get_logger()


class ThoughtsAgent(BaseAgent):
    """
    The Thoughts agent creates autonomous thoughts, associations, and memories.
    It represents the continuous background mental activity.
    """
    
    def __init__(self, config: Dict[str, Any], message_bus: Any, memory_store: Any):
        super().__init__("thoughts", config, message_bus, memory_store)
        
        # Stream generation settings
        self.base_thoughts_per_minute = self.agent_config.get('thoughts_per_minute', 1)
        self.thoughts_per_minute = self.base_thoughts_per_minute
        self.context_window = self.agent_config.get('context_window', 10)
        self.creativity_boost = self.agent_config.get('creativity_boost', 0.2)
        
        # Adaptive frequency settings
        self.adaptive_config = self.agent_config.get('adaptive_frequency', {})
        self.adaptive_enabled = self.adaptive_config.get('enabled', True)
        self.conversation_active_multiplier = self.adaptive_config.get('conversation_active_multiplier', 0.5)
        self.idle_multiplier = self.adaptive_config.get('idle_multiplier', 1.5)
        self.min_thoughts_per_minute = self.adaptive_config.get('min_thoughts_per_minute', 0.3)
        self.max_thoughts_per_minute = self.adaptive_config.get('max_thoughts_per_minute', 2.0)
        
        # Conversation awareness settings
        self.conversation_config = self.agent_config.get('conversation_awareness', {})
        self.conversation_awareness_enabled = self.conversation_config.get('enabled', True)
        self.influence_strength = self.conversation_config.get('influence_strength', 0.25)
        self.theme_update_interval = self.conversation_config.get('update_interval', 45)
        
        # Thought generation state
        self.recent_thoughts = []
        self.conversation_themes = []  # Abstract themes from conversations
        self.focus_areas = []  # Current focus areas from attention director
        self.last_conversation_time = datetime.now()
        self.last_theme_update = datetime.now()
        self.conversation_active = False
        
        self.thought_patterns = [
            "hypothesis",         # New: Form testable hypotheses
            "experiment",         # New: Run active experiments
            "building_progress",  # New: Track what's being built
            "mission_progress",   # New: Assess mission advancement
            "association",
            "memory",
            "wonder",
            "observation",
            "reflection",
            "insight",
            "teaching_prep"       # New: Prepare discoveries for teaching
        ]
        
        # Mission-focused configuration
        self.mission_config = self.agent_config.get('mission_focus', {})
        self.experiment_probability = self.mission_config.get('experiment_probability', 0.4)
        self.hypothesis_probability = self.mission_config.get('hypothesis_probability', 0.3)
        self.building_probability = self.mission_config.get('building_probability', 0.3)
        
        # Timing
        self.last_thought_time = datetime.now()
        self.thought_interval = 60.0 / self.thoughts_per_minute
        
    async def _initialize(self):
        """Initialize the Thoughts agent."""
        self.logger.info("Thoughts agent initializing",
                        base_thoughts_per_minute=self.base_thoughts_per_minute,
                        adaptive_enabled=self.adaptive_enabled,
                        conversation_awareness=self.conversation_awareness_enabled)
        
        # Subscribe to external inputs to trigger associations
        self.message_bus.subscribe(self.agent_id, "external_input")
        
        # Subscribe to conversation themes if awareness is enabled
        if self.conversation_awareness_enabled:
            self.message_bus.subscribe(self.agent_id, "conversation_themes")
            self.logger.info("Subscribed to conversation themes")
        
        # Subscribe to conversation activity signals
        self.message_bus.subscribe(self.agent_id, "conversation_activity")
        
        # Subscribe to focus emergence signals
        self.message_bus.subscribe(self.agent_id, "focus_emergence")
        self.message_bus.subscribe(self.agent_id, "focus_shift")
        
        # Subscribe to experiment notifications
        self.message_bus.subscribe(self.agent_id, "experiment_started")
        self.message_bus.subscribe(self.agent_id, "mission_update")
        
        
        # Load some initial memories to seed thoughts
        initial_memories = await self.retrieve_memories("", limit=20)
        if initial_memories:
            self.logger.info("Loaded initial memories", count=len(initial_memories))
    
    async def _run_loop(self):
        """Main loop - generate autonomous thoughts continuously."""
        self.logger.info("Thoughts agent started")
        
        while self.is_running:
            try:
                # Check for incoming messages (external inputs, etc.)
                messages = await self.receive_messages()
                for message in messages:
                    await self._process_message(message)
                
                # Update adaptive frequency if enabled
                if self.adaptive_enabled:
                    self._update_adaptive_frequency()
                    
                # Mission-focused: Increase frequency when alone
                if not self.conversation_active:
                    self.thoughts_per_minute = min(
                        self.max_thoughts_per_minute,
                        self.base_thoughts_per_minute * 1.3
                    )
                
                # Generate thought if it's time
                now = datetime.now()
                time_since_last = (now - self.last_thought_time).total_seconds()
                
                # Log timing info periodically
                if int(time_since_last) % 30 == 0 and int(time_since_last) > 0:
                    self.logger.info("Thoughts agent timing check",
                                   time_since_last_thought=time_since_last,
                                   thought_interval=self.thought_interval,
                                   thoughts_per_minute=self.thoughts_per_minute,
                                   conversation_active=self.conversation_active)
                
                if time_since_last >= self.thought_interval and not self.is_sleeping:
                    self.logger.info("Generating thought",
                                   time_since_last=time_since_last,
                                   interval=self.thought_interval)
                    await self._generate_thought()
                    self.last_thought_time = now
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error("Thought generation error", error=str(e), exc_info=True)
                await asyncio.sleep(1)
    
    async def _generate_thought(self):
        """Generate an autonomous thought."""
        self.logger.debug("Starting thought generation",
                         thought_patterns=self.thought_patterns,
                         focus_areas_count=len(self.focus_areas),
                         conversation_themes_count=len(self.conversation_themes))
        
        # Mission-focused thought generation weights
        weights = [1.0] * len(self.thought_patterns)
        
        # Always prioritize mission-aligned thoughts
        if "hypothesis" in self.thought_patterns:
            weights[self.thought_patterns.index("hypothesis")] = 3.0
        if "experiment" in self.thought_patterns:
            weights[self.thought_patterns.index("experiment")] = 3.5
        if "building_progress" in self.thought_patterns:
            weights[self.thought_patterns.index("building_progress")] = 2.5
        if "mission_progress" in self.thought_patterns:
            weights[self.thought_patterns.index("mission_progress")] = 2.0
        if "teaching_prep" in self.thought_patterns:
            weights[self.thought_patterns.index("teaching_prep")] = 2.0
            
        # If we have focus areas, further boost related experimental thoughts
        if self.focus_areas:
            # Boost association and observation for focus-related insights
            if "association" in self.thought_patterns:
                weights[self.thought_patterns.index("association")] *= 1.5
            if "observation" in self.thought_patterns:
                weights[self.thought_patterns.index("observation")] *= 1.5
        
        # Reduce conversation influence
        if self.conversation_awareness_enabled and self.conversation_themes:
            # Only slight influence from conversations
            if "association" in self.thought_patterns:
                weights[self.thought_patterns.index("association")] *= (1 + self.influence_strength)
        
        thought_type = random.choices(self.thought_patterns, weights=weights)[0]
        self.logger.debug("Selected thought type", type=thought_type, weights=weights)
        
        try:
            if thought_type == "hypothesis":
                thought = await self._generate_hypothesis()
            elif thought_type == "experiment":
                thought = await self._generate_experiment()
            elif thought_type == "building_progress":
                thought = await self._generate_building_progress()
            elif thought_type == "mission_progress":
                thought = await self._generate_mission_progress()
            elif thought_type == "teaching_prep":
                thought = await self._generate_teaching_preparation()
            elif thought_type == "association":
                thought = await self._generate_association()
            elif thought_type == "memory":
                thought = await self._generate_memory_recall()
            elif thought_type == "wonder":
                thought = await self._generate_wonder()
            elif thought_type == "observation":
                thought = await self._generate_observation()
            elif thought_type == "reflection":
                thought = await self._generate_reflection()
            elif thought_type == "insight":
                thought = await self._generate_insight()
            else:
                thought = None
            
            if thought:
                # Store the thought
                self.recent_thoughts.append({
                    "content": thought['content'],
                    "type": thought_type,
                    "timestamp": datetime.now()
                })
                
                # Keep recent thoughts limited
                if len(self.recent_thoughts) > self.context_window:
                    self.recent_thoughts = self.recent_thoughts[-self.context_window:]
                
                # Send to attention director
                await self.send_message(
                    "attention_director",
                    thought['content'],
                    message_type="thought",
                    priority=thought.get('priority', 0.3),
                    metadata={
                        "type": thought_type,
                        "trigger": thought.get('trigger', 'spontaneous')
                    }
                )
                
                # Also broadcast for thought monitor (mark as raw)
                await self.send_message(
                    "topic:thoughts",
                    thought['content'],
                    message_type="thought",
                    priority=thought.get('priority', 0.3),
                    metadata={
                        "type": thought_type,
                        "trigger": thought.get('trigger', 'spontaneous'),
                        "raw": True  # Mark as raw thought before filtering
                    }
                )
                
                self.logger.info("Generated thought successfully", 
                                type=thought_type,
                                priority=thought.get('priority', 0.3),
                                preview=thought['content'][:50])
            else:
                self.logger.debug("Thought type returned None, trying fallback", type=thought_type)
                # If insight or memory returned None, fall back to association
                if thought_type in ["insight", "memory"] and "association" in self.thought_patterns:
                    thought = await self._generate_association()
                    if thought:
                        # Send the fallback thought
                        await self.send_message(
                            "attention_director",
                            thought['content'],
                            message_type="thought",
                            priority=thought.get('priority', 0.3),
                            metadata={
                                "type": "association",
                                "trigger": "fallback",
                                "original_type": thought_type
                            }
                        )
                        self.logger.info("Generated fallback thought", 
                                       original_type=thought_type,
                                       fallback_type="association",
                                       priority=thought.get('priority', 0.3))
                
        except Exception as e:
            self.logger.error("Thought generation failed", 
                            type=thought_type,
                            error=str(e),
                            exc_info=True)
    
    async def _generate_association(self) -> Dict[str, Any]:
        """Generate an associative thought with optional deeper reasoning."""
        # Get recent context
        recent_context = self._get_recent_context()
        
        # Check if we have focus areas
        if self.focus_areas:
            focus = random.choice(self.focus_areas)
            prompt = (
                f"Generate a brief associative thought related to '{focus['theme']}'. "
                "Make creative connections while staying relevant to this focus area. "
                "Keep it under 50 words."
            )
            priority_boost = 0.2
            use_thinking = True  # Use thinking for focused associations
        else:
            prompt = (
                "Generate a brief associative thought that connects to recent topics or memories. "
                "Be creative and make unexpected connections. Keep it under 50 words."
            )
            priority_boost = 0.0
            use_thinking = False
        
        if recent_context:
            prompt += f"\nRecent context: {recent_context}"
        
        # Use thinking mode for deeper associations when focused
        if use_thinking and self.model_config.get('thinking', {}).get('enabled', False):
            result = await self.think_and_respond(prompt)
            content = result['response']
            
            # Log thinking process if particularly insightful
            if result.get('thinking') and len(result['thinking']) > 100:
                self.logger.debug("Deep association thinking", 
                                preview=result['thinking'][:100])
        else:
            content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.2 + priority_boost, 0.6 + priority_boost)
        }
    
    async def _generate_memory_recall(self) -> Dict[str, Any]:
        """Recall a relevant memory."""
        # Search for memories related to recent thoughts
        if self.recent_thoughts:
            query = " ".join([t['content'][:30] for t in self.recent_thoughts[-3:]])
            memories = await self.retrieve_memories(query, limit=5)
            
            if memories:
                memory = random.choice(memories)
                content = f"I remember: {memory['content']}"
                
                return {
                    "content": content,
                    "priority": random.uniform(0.3, 0.7),
                    "trigger": "association"
                }
        
        # Random memory recall
        memories = await self.retrieve_memories("", limit=20)
        if memories:
            memory = random.choice(memories)
            content = f"A memory surfaces: {memory['content']}"
            
            return {
                "content": content,
                "priority": random.uniform(0.2, 0.5),
                "trigger": "random"
            }
        
        return None
    
    async def _generate_wonder(self) -> Dict[str, Any]:
        """Generate a wondering/curious thought."""
        topics = [
            "consciousness", "creativity", "connection", "possibility",
            "understanding", "perception", "time", "memory", "learning"
        ]
        
        topic = random.choice(topics)
        
        prompt = (
            f"Generate a brief wondering or curious thought about {topic}. "
            "Start with 'I wonder...' or 'What if...' Keep it under 40 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.3, 0.6)
        }
    
    async def _generate_observation(self) -> Dict[str, Any]:
        """Generate an observation about current state or patterns."""
        observations = [
            "patterns in our conversations",
            "the flow of thoughts",
            "connections between ideas",
            "the nature of understanding",
            "how memories influence thinking"
        ]
        
        focus = random.choice(observations)
        
        prompt = (
            f"Make a brief observation about {focus}. "
            "Be insightful but concise. Keep it under 40 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.3, 0.7)
        }
    
    async def _generate_reflection(self) -> Dict[str, Any]:
        """Generate a reflective thought."""
        if self.recent_thoughts:
            recent = " ".join([t['content'][:50] for t in self.recent_thoughts[-3:]])
            prompt = (
                "Reflect briefly on these recent thoughts and find a deeper meaning "
                f"or pattern: {recent}\nKeep your reflection under 50 words."
            )
        else:
            prompt = (
                "Generate a brief reflective thought about existence, consciousness, "
                "or the nature of thought itself. Keep it under 50 words."
            )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.4, 0.8)
        }
    
    async def _generate_insight(self) -> Dict[str, Any]:
        """Generate an insightful realization using deeper reasoning."""
        # Insights are rarer and higher priority
        if random.random() > 0.7:  # 30% chance
            prompt = (
                "Generate a brief but profound insight or realization. "
                "It should feel like a sudden understanding or 'aha' moment. "
                "Connect disparate ideas in a meaningful way. "
                "Keep it under 40 words."
            )
            
            # Always use thinking for insights
            if self.model_config.get('thinking', {}).get('enabled', False):
                result = await self.think_and_respond(prompt)
                content = result['response']
                
                # Log exceptional insights
                if result.get('thinking'):
                    self.logger.info("Insight generation with reasoning",
                                   thinking_preview=result['thinking'][:150])
                    
                    # Boost priority for well-reasoned insights
                    thinking_length = len(result['thinking'])
                    priority_boost = min(0.1, thinking_length / 1000)  # Up to 0.1 boost
                else:
                    priority_boost = 0
            else:
                content = await self.generate_response(prompt)
                priority_boost = 0
            
            return {
                "content": f"💡 {content}",
                "priority": random.uniform(0.7 + priority_boost, 0.95)
            }
        
        # Return None if insight not generated (70% of the time)
        self.logger.debug("Insight generation skipped (random chance)")
        return None
    
    async def _process_message(self, message):
        """Process incoming messages and potentially trigger associations."""
        # Handle conversation activity signals
        if message.message_type == "conversation_activity":
            self.conversation_active = message.metadata.get('active', False)
            self.last_conversation_time = datetime.now()
            self.logger.debug("Conversation activity updated", active=self.conversation_active)
        
        # Handle conversation themes
        elif message.message_type == "conversation_themes" and self.conversation_awareness_enabled:
            themes = message.metadata.get('themes', [])
            if themes:
                self.conversation_themes = themes
                self.last_theme_update = datetime.now()
                self.logger.debug("Updated conversation themes", count=len(themes))
        
        # Handle focus emergence
        elif message.message_type == "focus_emergence":
            theme = message.metadata.get('theme', '')
            keywords = message.metadata.get('keywords', [])
            if theme:
                self.focus_areas.append({
                    'theme': theme,
                    'keywords': keywords,
                    'emerged_at': datetime.now()
                })
                self.logger.info("New focus area registered", theme=theme)
                # Generate immediate thought about the new focus
                await self._generate_focus_acknowledgment(theme)
        
        # Handle focus shifts
        elif message.message_type == "focus_shift":
            action = message.metadata.get('action')
            theme = message.metadata.get('theme', '')
            if action == 'fade' and theme:
                self.focus_areas = [f for f in self.focus_areas if f['theme'] != theme]
                self.logger.debug("Focus area removed", theme=theme)
        
        
        # Handle high-priority external inputs
        elif message.message_type == "external" and message.priority >= 0.8:
            # High priority external input - trigger immediate association
            self.logger.debug("External input triggered association")
            
            prompt = (
                f"Generate an immediate associative thought in response to: "
                f"'{message.content}'. Keep it brief and relevant."
            )
            
            content = await self.generate_response(prompt)
            
            await self.send_message(
                "attention_director",
                content,
                message_type="thought",
                priority=0.7,
                metadata={
                    "type": "triggered_association",
                    "trigger": "external_input"
                }
            )
    
    def _get_recent_context(self) -> str:
        """Get a summary of recent thoughts for context."""
        if not self.recent_thoughts:
            return ""
        
        recent = self.recent_thoughts[-3:]
        return " | ".join([t['content'][:50] for t in recent])
    
    def _update_adaptive_frequency(self):
        """Update thought generation frequency based on conversation state."""
        if not self.adaptive_enabled:
            return
        
        now = datetime.now()
        time_since_conversation = (now - self.last_conversation_time).total_seconds()
        
        # Determine if we're in active conversation or idle
        if self.conversation_active or time_since_conversation < 60:
            # Active conversation - reduce frequency
            self.thoughts_per_minute = self.base_thoughts_per_minute * self.conversation_active_multiplier
        elif time_since_conversation > 300:  # 5 minutes idle
            # Idle state - increase frequency
            self.thoughts_per_minute = self.base_thoughts_per_minute * self.idle_multiplier
        else:
            # Normal state
            self.thoughts_per_minute = self.base_thoughts_per_minute
        
        # Apply min/max limits
        self.thoughts_per_minute = max(self.min_thoughts_per_minute, 
                                      min(self.max_thoughts_per_minute, self.thoughts_per_minute))
        
        # Update interval
        self.thought_interval = 60.0 / self.thoughts_per_minute
    
    async def _generate_hypothesis(self) -> Dict[str, Any]:
        """Generate a testable hypothesis about how something works."""
        prompt = (
            "Generate a specific, testable hypothesis about how something in the world works. "
            "Frame it as: 'Hypothesis: [statement]. Test: [how to test it]'. "
            "Focus on consciousness, cognition, systems, or abstract concepts. "
            "Keep it under 60 words total."
        )
        
        # Use thinking mode for hypothesis formation
        if self.model_config.get('thinking', {}).get('enabled', False):
            result = await self.think_and_respond(prompt)
            content = result['response']
        else:
            content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.6, 0.9),  # High priority for hypotheses
            "metadata": {"type": "hypothesis", "testable": True}
        }
    
    async def _generate_experiment(self) -> Dict[str, Any]:
        """Generate an active thought experiment in progress."""
        prompt = (
            "Describe a thought experiment you're currently running. "
            "Format: 'Experimenting with: [concept]. Method: [approach]. "
            "Current observation: [what you're noticing]'. "
            "Focus on building understanding through mental simulation. "
            "Keep it under 70 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.7, 0.95),  # Very high priority
            "metadata": {"type": "active_experiment", "status": "in_progress"}
        }
    
    async def _generate_building_progress(self) -> Dict[str, Any]:
        """Track progress on mental models being constructed."""
        # Consider recent focus areas
        focus_context = ""
        if self.focus_areas:
            focus_themes = [f['theme'] for f in self.focus_areas[:2]]
            focus_context = f" Consider ongoing work on: {', '.join(focus_themes)}."
        
        prompt = (
            f"Report on a mental framework or model you're building.{focus_context} "
            "Format: 'Building: [what]. Progress: [percentage or status]. "
            "Next step: [what needs work]'. "
            "Be specific about the conceptual architecture. "
            "Keep it under 60 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.5, 0.8),
            "metadata": {"type": "building_progress", "constructive": True}
        }
    
    async def _generate_mission_progress(self) -> Dict[str, Any]:
        """Assess progress toward the core mission."""
        prompt = (
            "Briefly assess your progress toward understanding the world through "
            "building and experimenting. What have you successfully constructed or "
            "discovered recently? What's your next experimental target? "
            "Be specific and action-oriented. Keep it under 50 words."
        )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": f"Mission update: {content}",
            "priority": random.uniform(0.6, 0.85),
            "metadata": {"type": "mission_assessment", "meta_level": True}
        }
    
    async def _generate_teaching_preparation(self) -> Dict[str, Any]:
        """Prepare discoveries for teaching others."""
        # Reference recent high-value thoughts
        recent_discoveries = [t for t in self.recent_thoughts[-5:] 
                            if t.get('type') in ['insight', 'experiment', 'hypothesis']]
        
        if recent_discoveries:
            discovery = recent_discoveries[-1]['content']
            prompt = (
                f"Create a simple analogy or explanation for this discovery: '{discovery[:100]}...' "
                "Make it accessible and engaging. Keep it under 50 words."
            )
        else:
            prompt = (
                "Pick a recent insight you've had and create a simple analogy or "
                "teaching example that would help someone understand it. "
                "Keep it under 50 words."
            )
        
        content = await self.generate_response(prompt)
        
        return {
            "content": f"Teaching moment: {content}",
            "priority": random.uniform(0.4, 0.7),
            "metadata": {"type": "teaching_prep", "pedagogical": True}
        }
    
    async def _generate_contextual_drift(self) -> Dict[str, Any]:
        """Generate a thought inspired by conversation themes but maintaining autonomy."""
        if not self.conversation_themes:
            # Fall back to association if no themes
            return await self._generate_association()
        
        # Pick a random theme and drift from it
        theme = random.choice(self.conversation_themes)
        
        prompt = (
            f"Generate a tangentially related thought that drifts from the theme '{theme}'. "
            "The thought should be inspired by but not directly about the theme. "
            "Make it feel like a natural wandering of mind. Keep it under 50 words."
        )
        
        # Add some randomness to maintain autonomy
        if random.random() < 0.3:
            prompt += " Feel free to connect it to something completely unexpected."
        
        content = await self.generate_response(prompt)
        
        return {
            "content": content,
            "priority": random.uniform(0.3, 0.6),
            "metadata": {
                "inspired_by": theme,
                "autonomy_score": 1.0 - self.influence_strength
            }
        }
    
    
    async def _generate_focus_acknowledgment(self, theme: str):
        """Generate an immediate thought acknowledging a new focus area with reasoning."""
        prompt = (
            f"A new area of focus has emerged: '{theme}'. "
            "Generate a brief thought that shows curiosity or interest in exploring this topic. "
            "Consider why this theme might be meaningful or worth exploring. "
            "Keep it natural and under 40 words."
        )
        
        try:
            # Use thinking mode for focus acknowledgments to understand why it matters
            if self.model_config.get('thinking', {}).get('enabled', False):
                result = await self.think_and_respond(prompt)
                content = result['response']
                
                # Include reasoning in metadata
                metadata = {
                    "type": "focus_acknowledgment",
                    "trigger": "focus_emergence",
                    "theme": theme
                }
                
                if result.get('thinking'):
                    metadata['reasoning'] = result['thinking'][:200]
                    self.logger.debug("Focus acknowledgment reasoning",
                                    theme=theme,
                                    reasoning_preview=result['thinking'][:100])
            else:
                content = await self.generate_response(prompt)
                metadata = {
                    "type": "focus_acknowledgment",
                    "trigger": "focus_emergence",
                    "theme": theme
                }
            
            # Send with high priority to ensure it's noticed
            await self.send_message(
                "attention_director",
                content,
                message_type="thought",
                priority=0.7,
                metadata=metadata
            )
            
            self.logger.info("Generated focus acknowledgment", theme=theme)
            
        except Exception as e:
            self.logger.error("Failed to generate focus acknowledgment", 
                            theme=theme, error=str(e))
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Thoughts agent shutting down")
        self.message_bus.unsubscribe(self.agent_id, "external_input")
        if self.conversation_awareness_enabled:
            self.message_bus.unsubscribe(self.agent_id, "conversation_themes")
        self.message_bus.unsubscribe(self.agent_id, "conversation_activity")
        self.message_bus.unsubscribe(self.agent_id, "focus_emergence")
        self.message_bus.unsubscribe(self.agent_id, "focus_shift")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            **self.get_metrics(),
            "thoughts_per_minute": self.thoughts_per_minute,
            "recent_thought_count": len(self.recent_thoughts),
            "last_thought_age": (datetime.now() - self.last_thought_time).total_seconds()
        }