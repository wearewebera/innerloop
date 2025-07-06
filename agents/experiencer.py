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
from tools.problem_solving_tools import (
    ProblemLoaderTool, SuggestionGeneratorTool, 
    SuggestionSaverTool, ProblemProgressTool
)

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
        
        # Context management settings
        self.context_window_size = self.agent_config.get('context_window_size', 100)
        self.preserve_system_prompt = self.agent_config.get('preserve_system_prompt', True)
        
        # User message queuing system
        self.user_message_queue = asyncio.Queue()
        self.pending_user_messages = []
        self.last_queue_evaluation = datetime.now()
        self.queue_evaluation_interval = self.agent_config.get('queue_evaluation_interval', 2)
        
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
        
        # Problem-solving configuration
        self.problem_config = self.config.get('problem_solving', {})
        self.problem_solving_enabled = self.problem_config.get('enabled', False)
        self.current_problem = None
        self.problem_suggestions = []
        self.last_suggestion_time = datetime.now()
        self.suggestion_interval = self.problem_config.get('generation', {}).get('suggestion_interval', 30)
        
        # Initialize tool registry if tools are enabled OR problem-solving is enabled
        if (self.config.get('tools', {}).get('enabled', False) or 
            self.problem_solving_enabled):
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
        
        # Register problem-solving tools if enabled
        if self.problem_solving_enabled:
            self.tool_registry.register_tool(ProblemLoaderTool(self.agent_id))
            self.tool_registry.register_tool(SuggestionGeneratorTool(self.agent_id))
            output_dir = self.problem_config.get('output', {}).get('directory', 'suggestions')
            self.tool_registry.register_tool(SuggestionSaverTool(self.agent_id, output_dir))
            self.tool_registry.register_tool(ProblemProgressTool(self.agent_id))
        
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
        
        # Load problem if problem-solving is enabled
        if self.problem_solving_enabled and hasattr(self, 'tool_registry'):
            problem_loader = self.tool_registry.get_tool('problem_loader')
            if problem_loader:
                problem_file = self.problem_config.get('problem_file', 'problem.yaml')
                result = await problem_loader(problem_file=problem_file)
                if result and result.get('success'):
                    # The tool returns the problem directly in result.result
                    problem_data = result.get('result', {})
                    self.current_problem = problem_data.get('problem')
                    if self.current_problem:
                        self.logger.info("Loaded problem", 
                                       problem_id=self.current_problem.get('id'),
                                       title=self.current_problem.get('title'))
                        # Add problem context
                        self.current_context.append({
                            "role": "system",
                            "content": f"Current problem to solve: {self.current_problem.get('title')}\n"
                                     f"Description: {self.current_problem.get('description')}"
                        })
                        # Notify other agents
                        await self.send_message(
                            "topic:problem_solving",
                            "Problem loaded",
                            message_type="problem_loaded",
                            metadata={"problem": self.current_problem}
                        )
        
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
                
                # Check for external input (immediate processing - deprecated)
                try:
                    external_input = self.external_input_queue.get_nowait()
                    # Queue it instead of processing immediately
                    await self._queue_user_message(external_input)
                except asyncio.QueueEmpty:
                    pass
                
                # Evaluate queued user messages
                await self._evaluate_message_queue()
                
                # Broadcast conversation themes periodically
                await self._maybe_broadcast_themes()
                
                # Check for idle conversation state
                await self._check_idle_state()
                
                # Mission-focused activities
                await self._check_mission_progress()
                await self._maybe_start_experiment()
                await self._maybe_share_experiment_results()
                
                # Problem-solving activities if enabled
                if self.problem_solving_enabled:
                    if self.current_problem:
                        await self._maybe_generate_suggestion()
                        await self._check_problem_progress()
                    else:
                        # Log once that no problem is loaded
                        if not hasattr(self, '_no_problem_logged'):
                            self.logger.warning("Problem-solving enabled but no problem loaded")
                            self._no_problem_logged = True
                
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
        
        # Handle wake context from sleep agent
        if message.message_type == "wake_context" and message.sender == "sleep_agent":
            # Process wake-up context
            self.logger.info("Received wake context")
            # Store as important context with tagging
            tagged_content = self._tag_content(message.content, message.sender)
            self.current_context.append({
                "role": "system",
                "content": tagged_content
            })
            await self._log_context("system", tagged_content)
            # Resume experiments based on context
            await self._resume_from_sleep(message.content, message.metadata)
            
        elif message.sender == "attention_director" and message.priority >= 0.5:
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
            # Memory recall from thoughts agent with tagging
            tagged_content = self._tag_content(f"Recalled memory: {message.content}", message.sender)
            self.current_context.append({
                "role": "system",
                "content": tagged_content
            })
            await self._log_context("system", tagged_content)
    
    async def _process_external_input(self, input_data: Dict[str, Any]):
        """Process external input and generate a response."""
        self.is_processing = True
        user_input = input_data['content']
        
        # Update interaction timestamp
        self.last_user_interaction = datetime.now()
        self.idle_notification_sent = False
        
        # Check if this was a queued message
        queue_metadata = input_data.get('metadata', {})
        was_queued = queue_metadata.get('queued_duration', 0) > 0
        
        self.logger.info("Processing external input", 
                        preview=user_input[:50],
                        was_queued=was_queued,
                        queue_time=queue_metadata.get('queued_duration', 0))
        
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
            
            # Build conversation context with tagging
            tagged_input = self._tag_content(user_input, "human")
            context = self.current_context + [
                {"role": "user", "content": tagged_input}
            ]
            await self._log_context("user", tagged_input)
            
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
            if was_queued and queue_metadata.get('queued_duration', 0) > 10:
                # Acknowledge the delay and frame response around ongoing work
                prompt = (
                    "The user's message was queued while you were focused on experiments. "
                    f"They asked: '{user_input[:100]}...' about {int(queue_metadata.get('queued_duration', 0))} seconds ago. "
                    "Connect their question to your current experimental work if relevant, "
                    "or briefly acknowledge the delay before sharing your ongoing discoveries. "
                    "Be genuine about what you've been exploring."
                )
            else:
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
            
            # Update context with response
            self.current_context.append({"role": "assistant", "content": response})
            if len(self.current_context) > self.context_window_size:
                self.current_context = self.current_context[-self.context_window_size:]
            
            # Update conversation buffer for theme extraction
            self.conversation_buffer.append({
                "timestamp": datetime.now(),
                "user": user_input,
                "assistant": response
            })
            if len(self.conversation_buffer) > 10:
                self.conversation_buffer = self.conversation_buffer[-10:]
            
            # Notify thoughts agent of conversation activity
            await self.send_message(
                "thoughts",
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
        
        # Add to current context based on thought type with tagging
        if thought_type == 'memory':
            tagged_content = self._tag_content(f"Important memory surfaced: {thought}", "thoughts")
            self.current_context.append({
                "role": "system",
                "content": tagged_content
            })
            await self._log_context("system", tagged_content)
        elif thought_type == 'association':
            tagged_content = self._tag_content(f"Related thought: {thought}", "thoughts")
            self.current_context.append({
                "role": "system", 
                "content": tagged_content
            })
            await self._log_context("system", tagged_content)
        elif thought_type == 'insight':
            tagged_content = self._tag_content(f"New insight: {thought}", "thoughts")
            self.current_context.append({
                "role": "system",
                "content": tagged_content
            })
            await self._log_context("system", tagged_content)
    
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
                # Broadcast themes to thoughts agent
                await self.send_message(
                    "thoughts",
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
                "thoughts",
                "conversation_idle",
                message_type="conversation_activity",
                priority=0.1,
                metadata={"active": False}
            )
            self.idle_notification_sent = True
            self.logger.debug("Sent idle notification to thoughts agent")
    
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
                    
                    # Notify thoughts agent
                    await self.send_message(
                        "thoughts",
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
    
    async def _queue_user_message(self, input_data: Dict[str, Any]):
        """Queue user message for context-aware processing."""
        self.pending_user_messages.append({
            **input_data,
            'queued_at': datetime.now(),
            'priority': 0.5  # Default priority
        })
        
        # Notify attention director about queued message
        await self.send_message(
            "attention_director",
            f"User message queued: {input_data['content'][:100]}...",
            message_type="queued_user_message",
            priority=0.4,
            metadata={
                "full_message": input_data['content'],
                "queue_position": len(self.pending_user_messages)
            }
        )
        
        self.logger.info("Queued user message", position=len(self.pending_user_messages))
    
    async def _evaluate_message_queue(self):
        """Evaluate whether to process queued messages based on context."""
        if not self.pending_user_messages:
            return
            
        now = datetime.now()
        if (now - self.last_queue_evaluation).total_seconds() < self.queue_evaluation_interval:
            return
            
        self.last_queue_evaluation = now
        
        # Check if we're in a good state to process messages
        if self.is_processing or len(self.active_experiments) > 2:
            return
            
        # Evaluate each pending message
        for i, msg in enumerate(self.pending_user_messages[:]):
            wait_time = (now - msg['queued_at']).total_seconds()
            
            # Determine if we should process this message
            should_process = False
            
            # Always process messages waiting more than 60 seconds
            if wait_time > 60:
                should_process = True
                msg['priority'] = 0.9
            else:
                # Ask attention director for evaluation
                eval_result = await self._request_message_evaluation(msg)
                if eval_result and eval_result.get('process_now'):
                    should_process = True
                    msg['priority'] = eval_result.get('priority', 0.5)
            
            if should_process:
                # Remove from queue and process
                self.pending_user_messages.remove(msg)
                
                # Process with context about delay
                msg['metadata'] = {
                    'queued_duration': wait_time,
                    'processing_reason': 'contextually_relevant' if wait_time < 30 else 'timeout'
                }
                
                await self._process_external_input(msg)
                self.logger.info("Processing queued message", wait_time=wait_time)
                break  # Process one at a time
    
    async def _request_message_evaluation(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Request attention director to evaluate a queued message."""
        # Send evaluation request
        await self.send_message(
            "attention_director",
            "evaluate_user_message",
            message_type="evaluation_request",
            priority=0.6,
            metadata={
                "message": message['content'],
                "current_context": self._get_current_context_summary(),
                "active_experiments": len(self.active_experiments),
                "queue_time": (datetime.now() - message['queued_at']).total_seconds()
            }
        )
        
        # Wait briefly for response
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < 0.5:
            messages = await self.receive_messages()
            for msg in messages:
                if msg.message_type == "evaluation_response" and msg.sender == "attention_director":
                    return msg.metadata
            await asyncio.sleep(0.05)
        
        return None
    
    def _get_current_context_summary(self) -> str:
        """Get a summary of current context for evaluation."""
        if self.active_experiments:
            return f"Active experiments: {len(self.active_experiments)}, Recent topic: {self.active_experiments[0]['hypothesis'][:50]}..."
        elif self.current_context:
            return f"Recent context: {self.current_context[-1]['content'][:50]}..."
        else:
            return "No active context"
    
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
    
    async def _resume_from_sleep(self, wake_context: str, metadata: Dict[str, Any]):
        """Resume experiments after waking from sleep."""
        self.logger.info("Resuming from sleep", 
                        sleep_duration=metadata.get('sleep_duration'),
                        previous_cycles=metadata.get('previous_summaries'))
        
        # Generate enthusiasm for resuming work
        resume_prompt = (
            f"You just woke from a restorative sleep cycle. {wake_context}\n\n"
            "Express excitement about continuing your experiments and share what you plan to explore next. "
            "Be specific about your immediate experimental steps."
        )
        
        response = await self.generate_response(resume_prompt)
        
        # Share wake-up thoughts
        if hasattr(self, 'spontaneous_share_callback'):
            await self.spontaneous_share_callback(f"[Waking up] {response}")
        
        # Restart experiments with renewed energy
        self.last_experiment_share = datetime.now()
        self.last_mission_check = datetime.now()
    
    async def _on_sleep(self, metadata: Dict[str, Any]):
        """Handle sleep mode activation."""
        # Pause all active experiments
        for exp in self.active_experiments:
            exp['status'] = 'paused'
        
        self.logger.info("Experiencer entering sleep", 
                        active_experiments=len(self.active_experiments),
                        queued_messages=len(self.pending_user_messages))
    
    async def _on_wake(self, metadata: Dict[str, Any]):
        """Handle wake mode activation."""
        # Resume paused experiments
        for exp in self.active_experiments:
            if exp['status'] == 'paused':
                exp['status'] = 'running'
        
        self.logger.info("Experiencer waking up", 
                        experiments_to_resume=len(self.active_experiments))
    
    async def _maybe_generate_suggestion(self):
        """Generate a suggestion for the current problem if it's time."""
        try:
            now = datetime.now()
            time_since_last = (now - self.last_suggestion_time).total_seconds()
            
            if time_since_last < self.suggestion_interval:
                return
            
            # Log that we're checking suggestion generation
            self.logger.debug("Checking if suggestion generation needed",
                            time_since_last=time_since_last,
                            interval=self.suggestion_interval,
                            suggestions_so_far=len(self.problem_suggestions))
            
            # Check if we have enough suggestions
            min_suggestions = self.problem_config.get('generation', {}).get('min_suggestions', 5)
            max_suggestions = self.problem_config.get('generation', {}).get('max_suggestions', 10)
        
        if len(self.problem_suggestions) >= max_suggestions:
            return
        
        self.logger.info("Generating problem suggestion",
                        problem_id=self.current_problem.get('id'),
                        suggestions_so_far=len(self.problem_suggestions))
        
        # Analyze the problem and generate a suggestion
        analysis_prompt = f"""
Analyze this problem and generate a specific, actionable suggestion:

Problem: {self.current_problem.get('title')}
Description: {self.current_problem.get('description')}
Context: {self.current_problem.get('context', '')}

Questions to explore:
{chr(10).join('- ' + q for q in self.current_problem.get('questions_to_explore', []))}

Based on your analysis, generate ONE specific suggestion that addresses an aspect of this problem.
Focus on: architectural improvements, behavioral changes, or implementation strategies.
Be concrete and actionable.
"""
        
        # Use thinking mode for deeper analysis if available
        if self.model_config.get('thinking', {}).get('enabled', False):
            result = await self.think_and_respond(analysis_prompt, self.current_context)
            suggestion_content = result['response']
            thinking = result.get('thinking', '')
        else:
            # Fallback to regular response
            suggestion_content = await self.generate_response(analysis_prompt, self.current_context)
            thinking = ""
        
        # Generate a title for the suggestion
        title_prompt = f"Create a brief, descriptive title (5-10 words) for this suggestion: {suggestion_content[:200]}..."
        title = await self.generate_response(title_prompt)
        
        # Determine suggestion type based on content
        if "architecture" in suggestion_content.lower() or "structure" in suggestion_content.lower():
            suggestion_type = "improvement"
        elif "implement" in suggestion_content.lower() or "add" in suggestion_content.lower():
            suggestion_type = "solution"
        else:
            suggestion_type = "analysis"
        
        # Calculate confidence based on thinking depth
        confidence = min(0.9, 0.5 + (len(thinking) / 1000) * 0.2)  # Base 0.5, up to 0.9
        
        # Extract implementation steps if present
        steps_prompt = f"""
Extract 3-5 specific implementation steps from this suggestion:
{suggestion_content}

Format as a numbered list. If no clear steps exist, suggest logical next actions.
"""
        steps_response = await self.generate_response(steps_prompt)
        implementation_steps = [step.strip() for step in steps_response.split('\n') if step.strip() and step[0].isdigit()]
        
        # Use suggestion generator tool
        if hasattr(self, 'tool_registry'):
            generator_tool = self.tool_registry.get_tool('suggestion_generator')
            if generator_tool:
                result = await generator_tool(
                    problem_id=self.current_problem.get('id'),
                    suggestion_type=suggestion_type,
                    title=title.strip(),
                    content=suggestion_content,
                    confidence=confidence,
                    implementation_steps=implementation_steps
                )
                
                if result and result.get('success'):
                    suggestion = result.get('result', {}).get('suggestion')
                    if suggestion:
                        self.problem_suggestions.append(suggestion)
                    else:
                        self.logger.warning("Generator tool returned success but no suggestion")
                    
                    # Save if confidence is high enough
                    save_threshold = self.problem_config.get('output', {}).get('save_threshold', 0.7)
                    if confidence >= save_threshold and self.problem_config.get('output', {}).get('auto_save', True):
                        saver_tool = self.tool_registry.get_tool('suggestion_saver')
                        if saver_tool:
                            format = self.problem_config.get('output', {}).get('format', 'markdown')
                            save_result = await saver_tool(
                                suggestion=suggestion,
                                format=format
                            )
                            if save_result.get('success'):
                                self.logger.info("Suggestion saved",
                                              filepath=save_result.get('filepath'))
                    
                    # Share the suggestion
                    if hasattr(self, 'spontaneous_share_callback'):
                        share_message = f"💡 New suggestion for {self.current_problem.get('title')}: {title}"
                        await self.spontaneous_share_callback(share_message)
        
        self.last_suggestion_time = now
        
        except Exception as e:
            self.logger.error("Failed to generate suggestion",
                            error=str(e),
                            exc_info=True)
    
    async def _check_problem_progress(self):
        """Check and report progress on the current problem."""
        # Only check periodically
        if len(self.problem_suggestions) == 0 or len(self.problem_suggestions) % 3 != 0:
            return
        
        if hasattr(self, 'tool_registry'):
            progress_tool = self.tool_registry.get_tool('problem_progress')
            if progress_tool:
                # Analyze what areas we've covered
                areas_analyzed = set()
                for suggestion in self.problem_suggestions:
                    if "architecture" in suggestion.get('content', '').lower():
                        areas_analyzed.add("architecture")
                    if "behavior" in suggestion.get('content', '').lower():
                        areas_analyzed.add("behavior")
                    if "implementation" in suggestion.get('content', '').lower():
                        areas_analyzed.add("implementation")
                    if "consciousness" in suggestion.get('content', '').lower():
                        areas_analyzed.add("consciousness modeling")
                
                # Determine next steps
                next_steps = []
                questions = self.current_problem.get('questions_to_explore', [])
                for question in questions:
                    covered = any(keyword in ' '.join(s.get('content', '') for s in self.problem_suggestions).lower() 
                                for keyword in question.lower().split())
                    if not covered:
                        next_steps.append(f"Explore: {question}")
                
                result = await progress_tool(
                    problem_id=self.current_problem.get('id'),
                    suggestions_generated=len(self.problem_suggestions),
                    areas_analyzed=list(areas_analyzed),
                    next_steps=next_steps[:3]  # Top 3 next steps
                )
                
                if result.get('success'):
                    self.logger.info("Problem progress",
                                   completion=result.get('completion_percentage'))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        status = {
            **self.get_metrics(),
            "is_processing": self.is_processing,
            "is_sleeping": self.is_sleeping,
            "context_size": len(self.current_context),
            "decision_count": len(self.decision_history),
            "pending_inputs": self.external_input_queue.qsize(),
            "queued_messages": len(self.pending_user_messages),
            "active_experiments": len(self.active_experiments)
        }
        
        # Add problem-solving status if enabled
        if self.problem_solving_enabled:
            status.update({
                "current_problem": self.current_problem.get('id') if self.current_problem else None,
                "suggestions_generated": len(self.problem_suggestions),
                "problem_solving_active": bool(self.current_problem)
            })
        
        return status