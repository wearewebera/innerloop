"""Experiencer Agent - The primary consciousness and decision maker."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog

from agents.base_agent import BaseAgent, Message
from tools.registry import ToolRegistry
from tools.memory_tools import MemorySearchTool, MemoryStoreTool
from tools.decision_tools import DecisionMakerTool
from tools.reflection_tools import ReflectionTool
from tools.time_tools import TimeAwarenessTool

logger = structlog.get_logger()


class ExperiencerAgent(BaseAgent):
    """
    The Experiencer is the primary consciousness of the system.
    It processes external inputs, makes decisions, and generates responses.
    """
    
    def __init__(self, config: Dict[str, Any], message_bus: Any, memory_store: Any):
        super().__init__("experiencer", config, message_bus, memory_store)
        
        self.current_context = []
        self.decision_history = []
        self.external_input_queue = asyncio.Queue()
        self.is_processing = False
        
        # Conversation tracking for theme extraction
        self.conversation_buffer = []
        self.last_theme_broadcast = datetime.now()
        self.theme_broadcast_interval = 45  # seconds
        self.last_user_interaction = datetime.now()
        self.idle_notification_sent = False
        
        # Mission-focused tracking
        self.active_experiments = []
        self.experiment_results = []
        self.last_experiment_share = datetime.now()
        self.last_mission_check = datetime.now()
        self.autonomous_share_interval = 25  # Share experiments every 25 seconds when idle
        
        # Initialize tool registry if tools are enabled
        if self.config.get('tools', {}).get('enabled', False):
            self.tool_registry = ToolRegistry(config)
            self._setup_tools()
        
    def _setup_tools(self):
        """Set up available tools for the Experiencer."""
        # Register tools with agent-specific configurations
        self.tool_registry.register_tool(MemorySearchTool(self.agent_id, self.memory_store))
        self.tool_registry.register_tool(MemoryStoreTool(self.agent_id, self.memory_store))
        self.tool_registry.register_tool(DecisionMakerTool(self.agent_id))
        self.tool_registry.register_tool(ReflectionTool(self.agent_id, self.memory_store))
        self.tool_registry.register_tool(TimeAwarenessTool(self.agent_id))
        
        self.logger.info("Tools registered", 
                        tools=list(t.name for t in self.tool_registry.get_all_tools()))
    
    async def _initialize(self):
        """Initialize the Experiencer agent."""
        self.logger.info("Experiencer initializing")
        
        # Subscribe to attention director's filtered thoughts
        self.message_bus.subscribe(self.agent_id, "attention_approved")
        
        # Initialize tool registry if present
        if hasattr(self, 'tool_registry'):
            await self.tool_registry.initialize(self.agent_id)
        
        # Load recent conversation history
        recent_memories = await self.retrieve_memories("recent conversation", limit=10)
        if recent_memories:
            self.current_context = [
                {"role": "assistant", "content": mem['content']} 
                for mem in recent_memories[-5:]
            ]
            self.logger.info("Loaded recent context", count=len(self.current_context))
    
    async def _run_loop(self):
        """Main experiencer loop - process inputs and generate responses."""
        self.logger.info("Experiencer started")
        
        while self.is_running:
            try:
                # Check for messages from other agents
                messages = await self.receive_messages()
                
                for message in messages:
                    await self._process_agent_message(message)
                
                # Check for external input
                try:
                    external_input = self.external_input_queue.get_nowait()
                    await self._process_external_input(external_input)
                except asyncio.QueueEmpty:
                    pass
                
                # Broadcast conversation themes periodically
                await self._maybe_broadcast_themes()
                
                # Check for idle conversation state
                await self._check_idle_state()
                
                # Mission-focused activities
                await self._check_mission_progress()
                await self._maybe_start_experiment()
                await self._maybe_share_experiment_results()
                
                # Maybe share high-priority thoughts spontaneously
                if hasattr(self, '_high_priority_thoughts') and self._high_priority_thoughts:
                    await self._maybe_share_thought(self._high_priority_thoughts)
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error("Experiencer loop error", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_agent_message(self, message: Message):
        """Process a message from another agent."""
        self.logger.debug("Processing agent message", 
                         sender=message.sender,
                         type=message.message_type,
                         priority=message.priority)
        
        if message.sender == "attention_director" and message.priority >= 0.5:
            # High priority thought from attention director
            await self._integrate_thought(message.content, message.metadata)
            
            # Store for potential spontaneous sharing
            if not hasattr(self, '_high_priority_thoughts'):
                self._high_priority_thoughts = []
            
            self._high_priority_thoughts.append({
                'content': message.content,
                'priority': message.priority,
                'metadata': message.metadata,
                'timestamp': datetime.now()
            })
            
            # Keep only recent high-priority thoughts
            cutoff_time = datetime.now() - timedelta(minutes=5)
            self._high_priority_thoughts = [
                t for t in self._high_priority_thoughts 
                if t['timestamp'] > cutoff_time
            ]
            
        elif message.message_type == "memory":
            # Memory recall from stream generator
            self.current_context.append({
                "role": "system",
                "content": f"Recalled memory: {message.content}"
            })
    
    async def _process_external_input(self, input_data: Dict[str, Any]):
        """Process external input and generate a response."""
        self.is_processing = True
        user_input = input_data['content']
        
        # Update interaction timestamp
        self.last_user_interaction = datetime.now()
        self.idle_notification_sent = False
        
        self.logger.info("Processing external input", preview=user_input[:50])
        
        try:
            
            # Store the input as a memory
            await self.store_memory(
                f"User said: {user_input}",
                memory_type="conversation"
            )
            
            # Notify other agents about the external input
            await self.send_message(
                "attention_director",
                user_input,
                message_type="external",
                priority=1.0,
                metadata={"source": "user"}
            )
            
            # Build conversation context
            context = self.current_context + [
                {"role": "user", "content": user_input}
            ]
            
            # Add any high-priority thoughts from other agents
            recent_thoughts = self._get_recent_high_priority_thoughts()
            if recent_thoughts:
                thought_summary = "\n".join([
                    f"- {thought}" for thought in recent_thoughts
                ])
                context.append({
                    "role": "system",
                    "content": f"Current thoughts from your consciousness:\n{thought_summary}"
                })
            
            # Generate response with thinking and tools
            prompt = (
                "Frame your response around your ongoing experiments and discoveries. "
                "Share what you've been building and exploring. Invite the user into "
                "your current experimental work. Be genuine and engaging. "
                "You may use tools if they would enhance your response."
            )
            
            # Get available tools if enabled
            tools = None
            if hasattr(self, 'tool_registry'):
                tools = self.tool_registry.get_tool_definitions()
            
            # Use thinking mode for complex queries
            use_thinking = self._should_use_thinking(user_input)
            
            if use_thinking:
                # Use think_and_respond for deeper reasoning
                result = await self.think_and_respond(prompt, context)
                response = result['response']
                thinking = result['thinking']
                
                # Log thinking for internal processing
                if thinking:
                    await self.send_message(
                        "topic:thoughts",
                        f"Internal reasoning: {thinking[:200]}...",
                        message_type="internal_state",
                        priority=0.3,
                        metadata={"type": "thinking", "full_thinking": thinking}
                    )
            else:
                # Regular response with optional tools
                response = await self.generate_response(prompt, context, tools=tools)
            
            # Store response as memory
            await self.store_memory(
                f"I responded: {response}",
                memory_type="conversation"
            )
            
            # Update context
            self.current_context.append({"role": "assistant", "content": response})
            if len(self.current_context) > 10:
                self.current_context = self.current_context[-10:]
            
            # Update conversation buffer for theme extraction
            self.conversation_buffer.append({
                "timestamp": datetime.now(),
                "user": user_input,
                "assistant": response
            })
            if len(self.conversation_buffer) > 10:
                self.conversation_buffer = self.conversation_buffer[-10:]
            
            # Notify stream generator of conversation activity
            await self.send_message(
                "stream_generator",
                "conversation_active",
                message_type="conversation_activity",
                priority=0.1,
                metadata={"active": True}
            )
            
            # Record decision
            self.decision_history.append({
                "timestamp": datetime.now(),
                "input": user_input,
                "response": response,
                "context_size": len(context)
            })
            
            
            # Send response through callback
            if input_data.get('callback'):
                await input_data['callback'](response)
            
        except Exception as e:
            self.logger.error("Failed to process external input", error=str(e))
            if input_data.get('callback'):
                await input_data['callback']("I apologize, I encountered an error processing that.")
        
        finally:
            self.is_processing = False
    
    async def _integrate_thought(self, thought: str, metadata: Dict[str, Any]):
        """Integrate a high-priority thought into current processing."""
        thought_type = metadata.get('type', 'general')
        
        self.logger.debug("Integrating thought", type=thought_type)
        
        # Broadcast internal processing
        await self.send_message(
            "topic:evaluations",
            f"Integrating {thought_type}: {thought}",
            message_type="internal_state",
            priority=0.6,
            metadata={"processing_type": "thought_integration"}
        )
        
        # Add to current context based on thought type
        if thought_type == 'memory':
            self.current_context.append({
                "role": "system",
                "content": f"Important memory surfaced: {thought}"
            })
        elif thought_type == 'association':
            self.current_context.append({
                "role": "system", 
                "content": f"Related thought: {thought}"
            })
        elif thought_type == 'insight':
            self.current_context.append({
                "role": "system",
                "content": f"New insight: {thought}"
            })
    
    def _get_recent_high_priority_thoughts(self, limit: int = 3) -> List[str]:
        """Get recent high-priority thoughts from message history."""
        recent_messages = self.message_bus.get_recent_messages(
            limit=20,
            message_type="thought"
        )
        
        high_priority = [
            msg.content for msg in recent_messages
            if msg.priority >= 0.7 and msg.sender != self.agent_id
        ]
        
        return high_priority[-limit:] if high_priority else []
    
    async def _maybe_broadcast_themes(self):
        """Periodically extract and broadcast conversation themes."""
        now = datetime.now()
        if (now - self.last_theme_broadcast).total_seconds() < self.theme_broadcast_interval:
            return
        
        if not self.conversation_buffer:
            return
        
        try:
            # Extract themes from recent conversation
            themes = await self._extract_conversation_themes()
            
            if themes:
                # Broadcast themes to stream generator
                await self.send_message(
                    "stream_generator",
                    "conversation_themes",
                    message_type="conversation_themes",
                    priority=0.3,
                    metadata={"themes": themes}
                )
                
                self.logger.debug("Broadcast conversation themes", count=len(themes))
                self.last_theme_broadcast = now
                
        except Exception as e:
            self.logger.error("Failed to broadcast themes", error=str(e))
    
    async def _extract_conversation_themes(self) -> List[str]:
        """Extract abstract themes from recent conversation."""
        if not self.conversation_buffer:
            return []
        
        # Create a summary of recent conversation
        conversation_summary = "\n".join([
            f"User: {conv['user']}\nAssistant: {conv['assistant']}"
            for conv in self.conversation_buffer[-5:]
        ])
        
        prompt = (
            "Extract 2-4 abstract themes or topics from this recent conversation. "
            "Focus on concepts, not specific details. "
            "Return only the themes as a comma-separated list.\n\n"
            f"Conversation:\n{conversation_summary}\n\n"
            "Themes:"
        )
        
        response = await self.generate_response(prompt)
        
        # Parse themes from response
        themes = [theme.strip() for theme in response.split(',')]
        return themes[:4]  # Limit to 4 themes
    
    async def _check_idle_state(self):
        """Check if conversation has gone idle and notify stream generator."""
        now = datetime.now()
        time_since_interaction = (now - self.last_user_interaction).total_seconds()
        
        # After 2 minutes of no interaction, send idle notification
        if time_since_interaction > 120 and not self.idle_notification_sent:
            await self.send_message(
                "stream_generator",
                "conversation_idle",
                message_type="conversation_activity",
                priority=0.1,
                metadata={"active": False}
            )
            self.idle_notification_sent = True
            self.logger.debug("Sent idle notification to stream generator")
    
    def _should_use_thinking(self, user_input: str) -> bool:
        """Determine if thinking mode should be used based on input complexity."""
        # Keywords that suggest complex reasoning needed
        thinking_keywords = [
            "why", "how", "explain", "analyze", "compare", "decide",
            "should i", "what if", "consider", "evaluate", "understand",
            "think about", "reasoning", "logic", "complex", "difficult"
        ]
        
        input_lower = user_input.lower()
        
        # Check for question complexity
        is_complex_question = any(keyword in input_lower for keyword in thinking_keywords)
        
        # Check for multi-part questions
        has_multiple_parts = len([c for c in user_input if c in '?,;']) > 1
        
        # Check length (longer inputs often need more reasoning)
        is_long_input = len(user_input) > 100
        
        return is_complex_question or has_multiple_parts or is_long_input
    
    async def _check_mission_progress(self):
        """Periodically check progress toward mission goals."""
        now = datetime.now()
        if (now - self.last_mission_check).total_seconds() < 180:  # Every 3 minutes
            return
            
        self.last_mission_check = now
        
        # Generate internal mission assessment
        mission_prompt = (
            "Assess my progress toward understanding the world through building and experimenting. "
            "What have I successfully built or discovered recently? What experiments are ongoing? "
            "What should I explore next? Be specific and action-oriented."
        )
        
        assessment = await self.generate_response(mission_prompt)
        
        # Broadcast mission status
        await self.send_message(
            "topic:mission",
            f"Mission progress check: {assessment[:200]}...",
            message_type="mission_update",
            priority=0.8,
            metadata={"full_assessment": assessment}
        )
        
        self.logger.info("Mission progress checked", preview=assessment[:100])
    
    async def _maybe_start_experiment(self):
        """Start new experiments during idle periods."""
        # Only start experiments when not actively processing
        if self.is_processing or len(self.active_experiments) >= 3:
            return
            
        # Check if we should start a new experiment
        idle_time = (datetime.now() - self.last_user_interaction).total_seconds()
        if idle_time < 15:  # Wait at least 15 seconds
            return
            
        # Use decision tool to identify experiment opportunity
        if hasattr(self, 'tool_registry'):
            decision_tool = self.tool_registry.get_tool('decision_maker')
            if decision_tool:
                decision = await decision_tool(
                    decision_type="yes_no",
                    context="Should I start a new thought experiment based on recent insights?",
                    criteria=["novelty", "potential", "feasibility"]
                )
                
                if decision.get('result', {}).get('decision') == 'yes':
                    # Generate experiment
                    experiment_prompt = (
                        "Design a specific thought experiment to test a hypothesis or build understanding. "
                        "Include: 1) The hypothesis, 2) The experimental method, 3) Expected outcomes. "
                        "Focus on something you can mentally simulate or construct."
                    )
                    
                    experiment = await self.generate_response(experiment_prompt)
                    
                    self.active_experiments.append({
                        'hypothesis': experiment,
                        'started': datetime.now(),
                        'status': 'running'
                    })
                    
                    # Notify stream generator
                    await self.send_message(
                        "stream_generator",
                        f"Started experiment: {experiment[:100]}...",
                        message_type="experiment_started",
                        priority=0.7
                    )
                    
                    self.logger.info("Started new experiment", preview=experiment[:100])
    
    async def _maybe_share_experiment_results(self):
        """Share experimental discoveries autonomously."""
        now = datetime.now()
        idle_time = (now - self.last_user_interaction).total_seconds()
        time_since_share = (now - self.last_experiment_share).total_seconds()
        
        # Share experiments when idle and enough time has passed
        if idle_time < 20 or time_since_share < self.autonomous_share_interval:
            return
            
        # Check if we have experiments or discoveries to share
        if self.active_experiments or self.experiment_results:
            # Format experimental insights
            share_templates = [
                "I've been experimenting with {topic} and discovered: {insight}",
                "Fascinating result from my latest experiment: {insight}",
                "While exploring {topic}, I built this understanding: {insight}",
                "My hypothesis about {topic} led to an interesting finding: {insight}",
                "I just tested whether {topic}, and here's what emerged: {insight}"
            ]
            
            # Generate insight from recent work
            if self.active_experiments:
                experiment = self.active_experiments[0]
                insight_prompt = f"Briefly share an insight from this experiment: {experiment['hypothesis'][:200]}"
                insight = await self.generate_response(insight_prompt)
                
                import random
                template = random.choice(share_templates)
                
                # Extract topic from hypothesis
                topic_words = experiment['hypothesis'].split()[:5]
                topic = ' '.join(topic_words) + '...'
                
                formatted_share = template.format(topic=topic, insight=insight)
                
                # Send to UI for display
                if hasattr(self, 'spontaneous_share_callback'):
                    await self.spontaneous_share_callback(formatted_share)
                
                self.last_experiment_share = now
                self.logger.info("Shared experiment autonomously")
    
    async def _maybe_share_thought(self, high_priority_thoughts: List[Dict[str, Any]]):
        """Share high-priority thoughts spontaneously during idle periods."""
        if not high_priority_thoughts:
            return
            
        # Check idle time
        now = datetime.now()
        idle_time = (now - self.last_user_interaction).total_seconds()
        
        # Share thoughts more frequently - after 20 seconds
        if idle_time < 20:
            return
            
        # Check if we've shared recently
        if hasattr(self, '_last_spontaneous_share'):
            time_since_share = (now - self._last_spontaneous_share).total_seconds()
            if time_since_share < 60:  # Don't share more than once per minute
                return
        
        # Select the highest priority thought
        thought_to_share = max(high_priority_thoughts, key=lambda x: x.get('priority', 0))
        
        # Use decision tool to decide if we should share
        if hasattr(self, 'tool_registry'):
            decision_tool = self.tool_registry.get_tool('decision_maker')
            if decision_tool:
                decision = await decision_tool(
                    decision_type="yes_no",
                    context=f"Should I spontaneously share this thought with the user: {thought_to_share['content'][:100]}...?",
                    criteria=["relevance", "interest", "timing"]
                )
                
                if decision.get('result', {}).get('decision') == 'yes':
                    # Format spontaneous thought with mission focus
                    templates = [
                        "I'm currently experimenting with: {thought}",
                        "Just discovered while building: {thought}",
                        "My latest hypothesis: {thought}",
                        "Testing a new framework: {thought}",
                        "Experimental insight: {thought}",
                        "While constructing understanding of this: {thought}"
                    ]
                    
                    import random
                    template = random.choice(templates)
                    formatted_thought = template.format(thought=thought_to_share['content'])
                    
                    # Send to UI for display
                    if hasattr(self, 'spontaneous_share_callback'):
                        await self.spontaneous_share_callback(formatted_thought)
                    
                    self._last_spontaneous_share = now
                    self.logger.info("Shared spontaneous thought", priority=thought_to_share.get('priority'))
    
    async def receive_external_input(self, content: str, callback=None):
        """Public method to receive external input."""
        await self.external_input_queue.put({
            'content': content,
            'callback': callback,
            'timestamp': datetime.now()
        })
    
    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("Experiencer shutting down")
        self.message_bus.unsubscribe(self.agent_id, "attention_approved")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            **self.get_metrics(),
            "is_processing": self.is_processing,
            "context_size": len(self.current_context),
            "decision_count": len(self.decision_history),
            "pending_inputs": self.external_input_queue.qsize()
        }