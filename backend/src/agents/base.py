"""
Base Custom Agent implementation following Microsoft Agent Framework patterns.

This module provides the base class for all 4 custom agents using ChatAgent:
- Planning Agent
- Research Agent
- Reflect Agent
- Content Writing Agent

Using ChatAgent enables:
- Automatic chat history management via AgentThread
- Multi-turn conversation support
- Tools pattern for custom logic
"""

import logging
import os
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Optional

from agent_framework import ChatAgent, AgentRunContext
from agent_framework.azure import AzureOpenAIChatClient

from ..models import AgentId

logger = logging.getLogger(__name__)


def create_azure_chat_client() -> AzureOpenAIChatClient:
    """Create Azure OpenAI Chat Client from environment variables."""
    return AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    )


class BaseCustomAgent(ChatAgent):
    """
    Base class for all custom agents in the system using ChatAgent.
    
    Provides common functionality for multi-agent conversation:
    - ChatAgent-based LLM interaction with automatic history
    - Shared state access for inter-agent communication
    - Tools pattern for custom agent logic
    - Logging and error handling
    
    Subclasses must implement the `get_tools` method to return their custom tools.
    """
    
    def __init__(
        self,
        agent_id: AgentId,
        agent_name: str,
        agent_description: str,
        instructions: str = "",
        tools: Optional[List[Callable[..., Any]]] = None,
        **kwargs
    ):
        """
        Initialize the base agent with ChatAgent.
        
        Args:
            agent_id: Unique identifier from AgentId enum
            agent_name: Human-readable agent name
            agent_description: Agent purpose description
            instructions: System instructions for the agent
            tools: List of tool functions for this agent
            **kwargs: Additional arguments for ChatAgent
        """
        self.agent_id = agent_id
        
        # Create Azure OpenAI chat client
        chat_client = create_azure_chat_client()
        
        # Initialize ChatAgent with tools
        super().__init__(
            chat_client=chat_client,
            instructions=instructions,
            id=agent_id.value,
            name=agent_name,
            description=agent_description,
            tools=tools or [],
            temperature=0.7,
            **kwargs
        )
        
        # Workflow state reference (set by workflow)
        self._workflow_state: Dict[str, Any] = {}
    
    def log_step(self, step_description: str) -> None:
        """
        Log a step in the agent's execution and emit event.
        
        Args:
            step_description: Description of the current step
        """
        logger.info(f"{self.agent_id.value}: {step_description}")
        # Emit event for streaming (fire and forget)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit_event({
                "type": "agent_step",
                "agent": self.name,
                "step": step_description
            }))
        except RuntimeError:
            pass  # No running loop

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
        self._workflow_state[key] = value
    
    @abstractmethod
    async def execute(self, context: AgentRunContext) -> Dict[str, Any]:
        """
        Agent-specific execution logic.
        
        Must be implemented by subclasses. This is called when the agent
        is invoked through the GroupChat workflow.
        
        Args:
            context: Agent execution context with shared state
            
        Returns:
            Agent-specific result dictionary
        """
        pass

    async def run(
        self,
        messages: str | list = None,
        *,
        thread = None,
        **kwargs
    ) -> Any:
        """
        Main entry point called by Agent Framework / GroupChat.
        
        This overrides ChatAgent.run() to integrate our custom execute() logic
        while still supporting thread-based history management.
        
        Args:
            messages: Input messages (string or list of ChatMessage)
            thread: Optional agent thread for history management
            **kwargs: Additional keyword arguments
            
        Returns:
            Result from execute() method
        """
        logger.info(f"{self.agent_id.value} agent starting")
        logger.debug(f"Messages type: {type(messages)}, Thread: {thread}")
        
        try:
            # Create a simple context object that our agents can use
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
            logger.error(f"{self.agent_id.value} agent failed: {e}", exc_info=True)
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
        Log a step in the agent's execution and emit event for streaming.
        
        Args:
            step_description: Description of the current step
        """
        logger.info(f"{self.agent_id.value}: {step_description}")
        
        # Emit event for streaming to frontend
        import asyncio
        try:
            # Try to get the running event loop
            loop = asyncio.get_running_loop()
            # Create a task to emit the event
            loop.create_task(self.emit_event({
                "type": "agent_step",
                "agent": self.agent_id.value,
                "step": step_description
            }))
        except RuntimeError:
            # No event loop running (sync context), skip streaming
            pass

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
__all__ = ["BaseCustomAgent", "create_azure_chat_client"]
