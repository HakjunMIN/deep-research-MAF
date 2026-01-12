"""
Base Custom Agent implementation following Microsoft Agent Framework patterns.

This module provides the base class for all 4 custom agents:
- Planning Agent
- Research Agent
- Reflect Agent
- Content Writing Agent
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, Optional

from agent_framework import BaseAgent, AgentRunContext

from ..models import AgentId

logger = logging.getLogger(__name__)


class BaseCustomAgent(BaseAgent):
    """
    Base class for all custom agents in the system.
    
    Provides common functionality for multi-agent conversation:
    - Shared state access
    - Logging
    - Error handling
    
    Subclasses must implement the `execute` method with agent-specific logic.
    """
    
    def __init__(
        self,
        agent_id: AgentId,
        agent_name: str,
        agent_description: str,
        **kwargs
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_id: Unique identifier from AgentId enum
            agent_name: Human-readable agent name
            agent_description: Agent purpose description
            **kwargs: Additional arguments (unused, for compatibility)
        """
        # Call parent constructor with proper arguments
        super().__init__(
            id=agent_id.value,
            name=agent_name,
            description=agent_description,
            **kwargs
        )
        
        self.agent_id = agent_id
        
        # Workflow state reference (set by workflow)
        self._workflow_state: Dict[str, Any] = {}
    
    async def run(
        self,
        messages: str | list = None,
        *,
        thread = None,
        **kwargs
    ) -> Any:
        """
        Main entry point called by Agent Framework.
        
        Wraps execute() with logging and error handling.
        
        Args:
            messages: Input messages (string or list of ChatMessage)
            thread: Optional agent thread
            **kwargs: Additional keyword arguments
            
        Returns:
            Result from execute() method
        """
        logger.info(f"{self.agent_id.value} agent starting")
        logger.debug(f"Messages type: {type(messages)}, Thread: {thread}")
        
        try:
            # Create a simple context object that our agents can use
            # GroupChat doesn't provide AgentRunContext, so we create our own
            from types import SimpleNamespace
            
            context = SimpleNamespace()
            context.messages = messages if isinstance(messages, list) else [messages] if messages else []
            context.thread = thread
            context.state = kwargs.get('state', {})
            context.kwargs = kwargs
            
            # Execute agent-specific logic
            result = await self.execute(context)
            
            # Log completion
            logger.info(f"{self.agent_id.value} agent completed")
            
            return result
        
        except Exception as e:
            # Log error
            logger.error(f"{self.agent_id.value} agent failed: {e}", exc_info=True)
            
            # Re-raise to propagate to workflow
            raise
    
    async def run_stream(
        self,
        messages: str | list = None,
        *,
        thread = None,
        **kwargs
    ):
        """
        Streaming version of run with status updates.
        
        Args:
            messages: Input messages (string or list of ChatMessage)
            thread: Optional agent thread
            **kwargs: Additional keyword arguments
            
        Yields:
            AgentRunResponseUpdate with status and result
        """
        from agent_framework import AgentRunResponseUpdate
        
        logger.debug(f"{self.agent_id.value}: run_stream called")
        
        # Yield thinking status
        yield AgentRunResponseUpdate(
            text=f"{self.name} is thinking...",
            author_name=self.name,
            role="assistant",
            additional_properties={"status": "thinking"}
        )
        
        # Execute the agent logic
        result = await self.run(messages=messages, thread=thread, **kwargs)
        
        # Convert result to AgentRunResponseUpdate
        result_text = str(result) if result else "No result"
        
        # Yield final result
        yield AgentRunResponseUpdate(
            text=result_text,
            author_name=self.name,
            role="assistant",
            additional_properties=result if isinstance(result, dict) else {"data": result}
        )
    
    def get_new_thread(self):
        """
        Create a new thread for this agent.
        Required by AgentProtocol but not used in group chat context.
        
        Returns:
            None - group chat manages threads
        """
        return None
    
    @abstractmethod
    async def execute(self, context: AgentRunContext) -> Dict[str, Any]:
        """
        Agent-specific execution logic.
        
        Must be implemented by subclasses.
        
        Args:
            context: Agent execution context with shared state
            
        Returns:
            Agent-specific result dictionary
        """
        pass
    
    def log_step(self, step_description: str) -> None:
        """
        Log a step in the agent's execution.
        
        Args:
            step_description: Description of the current step
        """
        logger.info(f"{self.agent_id.value}: {step_description}")

    async def emit_event(self, event: Dict[str, Any]) -> None:
        """Emit a real-time event into the workflow stream (if enabled).

        The workflow may place an asyncio.Queue into shared state under
        the private key "_event_queue". When present, agents can push
        structured events (dicts) for the streaming API to forward to
        the frontend.
        """
        queue: Optional[Any] = self._workflow_state.get("_event_queue")
        if queue is None:
            return

        try:
            queue.put_nowait(event)
        except Exception:
            await queue.put(event)
    
    def get_shared_state(
        self,
        context,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get value from shared state.
        
        Args:
            context: Agent execution context (not used, state comes from workflow)
            key: State key
            default: Default value if key not found
            
        Returns:
            Value from shared state or default
        """
        # Use workflow state instead of context state
        return self._workflow_state.get(key, default)
    
    def set_shared_state(
        self,
        context,
        key: str,
        value: Any
    ) -> None:
        """
        Set value in shared state.
        
        Args:
            context: Agent execution context (not used, state comes from workflow)
            key: State key
            value: Value to store
        """
        # Use workflow state instead of context state
        self._workflow_state[key] = value
    
# Export base class
__all__ = ["BaseCustomAgent"]
