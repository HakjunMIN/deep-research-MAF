"""
Group Chat Workflow - Orchestrates all 4 agents to answer research questions.

This workflow uses GroupChatBuilder to orchestrate agents in sequence:
1. Planning Agent - Creates research strategy
2. Research Agent - Executes searches
3. Reflect Agent - Analyzes completeness
4. Content Writing Agent - Synthesizes answer

Thread Management:
- Supports multi-turn conversations via AgentThread
- Each workflow session can have a persistent thread_id
- Thread state can be serialized/deserialized for persistence
"""

import logging
from typing import Any, Dict, Optional, Callable, List
import uuid

import asyncio

from agent_framework import (
    GroupChatBuilder,
    GroupChatStateSnapshot,
    AgentRunUpdateEvent,
    WorkflowOutputEvent,
    AgentThread,
)

from ..agents.planning_agent import PlanningAgent
from ..agents.research_agent import ResearchAgent
from ..agents.reflect_agent import ReflectAgent
from ..agents.content_agent import ContentWritingAgent

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Ensure INFO level is enabled


def select_next_speaker(state: GroupChatStateSnapshot) -> str | None:
    """
    Orchestrate agent execution in sequence: Planning → Research → Reflect → Content.

    Args:
        state: Contains task, participants, conversation, history, and round_index

    Returns:
        Name or ID of next speaker, or None to finish
    """
    round_idx = state["round_index"]
    
    logger.info(f"select_next_speaker called with round_index={round_idx}")
    logger.info(f"State keys: {list(state.keys())}")
    logger.info(f"Participants: {state.get('participants', [])}")

    # Finish after 4 turns (planning → research → reflect → content)
    if round_idx >= 4:
        logger.info("Workflow complete - all 4 agents executed")
        return None

    # Sequential execution based on round index
    # Use agent names (as defined in each agent's __init__)
    agent_name_sequence = [
        "Planning Agent",
        "Research Agent", 
        "Reflect Agent",
        "Content Writing Agent"
    ]
    selected = agent_name_sequence[round_idx]
    logger.info(f"Selected next speaker: {selected}")
    return selected


class ResearchWorkflow:
    """
    Orchestrates the deep research workflow using GroupChat pattern.
    
    Agent execution order:
    1. Planning Agent - Creates research strategy
    2. Research Agent - Executes searches
    3. Reflect Agent - Analyzes completeness
    4. Content Writing Agent - Synthesizes answer
    
    Thread Management:
    - Supports persistent conversation threads via AgentThread
    - Thread state can be serialized/deserialized for storage
    - Enables multi-turn research conversations
    """
    
    # Class-level shared state that agents can access
    _shared_state: Dict[str, Any] = {}
    
    # Thread storage for multi-turn conversations
    _thread_store: Dict[str, AgentThread] = {}

    # Lightweight in-process message history per thread.
    # We intentionally keep this separate from AgentThread because our agents
    # don't rely on AgentThread message stores; instead we replay history as
    # prompt context for subsequent turns.
    _thread_histories: Dict[str, List[Dict[str, str]]] = {}

    # History limits to keep prompts bounded
    _max_history_messages: int = 12  # last N messages (user+assistant)
    _max_history_chars: int = 8000
    
    def __init__(
        self,
        websocket_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the research workflow.
        
        Args:
            websocket_callback: Optional callback for real-time updates
        """
        # Initialize agents
        self.planning_agent = PlanningAgent()
        self.research_agent = ResearchAgent()
        self.reflect_agent = ReflectAgent()
        self.content_agent = ContentWritingAgent()
        
        # Set shared state reference for all agents
        self.planning_agent._workflow_state = self._shared_state
        self.research_agent._workflow_state = self._shared_state
        self.reflect_agent._workflow_state = self._shared_state
        self.content_agent._workflow_state = self._shared_state
        
        # WebSocket callback for real-time updates
        self.websocket_callback = websocket_callback
        
        # Build the group chat workflow
        self.workflow = (
            GroupChatBuilder()
            .select_speakers(select_next_speaker, display_name="Orchestrator")
            .participants([
                self.planning_agent,
                self.research_agent,
                self.reflect_agent,
                self.content_agent
            ])
            .build()
        )
    
    def get_or_create_thread(self, thread_id: Optional[str] = None) -> tuple[str, AgentThread]:
        """
        Get existing thread or create a new one.
        
        Args:
            thread_id: Optional existing thread ID
            
        Returns:
            Tuple of (thread_id, AgentThread)
        """
        if thread_id and thread_id in self._thread_store:
            logger.info(f"Resuming existing thread: {thread_id}")
            self._thread_histories.setdefault(thread_id, [])
            return thread_id, self._thread_store[thread_id]
        
        # Create new thread
        new_thread_id = thread_id or str(uuid.uuid4())
        new_thread = AgentThread()
        self._thread_store[new_thread_id] = new_thread
        self._thread_histories.setdefault(new_thread_id, [])
        logger.info(f"Created new thread: {new_thread_id}")
        return new_thread_id, new_thread

    @classmethod
    def _build_task_with_history(cls, thread_id: str, user_message: str) -> str:
        """Compose the task prompt with prior conversation for multi-turn chat."""
        history = cls._thread_histories.get(thread_id, [])
        if not history:
            return user_message

        # Take last N messages and enforce a character budget.
        selected = history[-cls._max_history_messages :]
        rendered_lines: List[str] = [
            "You are continuing an ongoing conversation.",
            "Use the prior context to answer the NEW user message.",
            "If prior context is insufficient, ask a clarifying question.",
            "",
            "Conversation so far:",
        ]

        for msg in selected:
            role = msg.get("role", "user")
            label = "User" if role == "user" else "Assistant"
            content = (msg.get("content") or "").strip()
            if content:
                rendered_lines.append(f"{label}: {content}")

        rendered_lines.extend(["", "New user message:", user_message.strip()])
        rendered = "\n".join(rendered_lines)

        if len(rendered) <= cls._max_history_chars:
            return rendered

        # If over budget, trim oldest messages until it fits.
        trimmed = selected[:]
        while trimmed and len(rendered) > cls._max_history_chars:
            trimmed.pop(0)
            rendered_lines = [
                "You are continuing an ongoing conversation.",
                "Use the prior context to answer the NEW user message.",
                "If prior context is insufficient, ask a clarifying question.",
                "",
                "Conversation so far:",
            ]
            for msg in trimmed:
                role = msg.get("role", "user")
                label = "User" if role == "user" else "Assistant"
                content = (msg.get("content") or "").strip()
                if content:
                    rendered_lines.append(f"{label}: {content}")
            rendered_lines.extend(["", "New user message:", user_message.strip()])
            rendered = "\n".join(rendered_lines)

        return rendered

    @classmethod
    def _build_effective_query(cls, thread_id: str, user_message: str) -> str:
        """Build a standalone query for search/planning agents.

        Our agents currently rely on shared_state['query'].content for keyword
        generation, search queries, and answer synthesis. The GroupChat task
        string may include conversation framing, which is not ideal for web
        search. This function keeps the query clean while still being multi-turn.
        """

        current = (user_message or "").strip()
        if not current:
            return current

        history = cls._thread_histories.get(thread_id, [])
        if not history:
            return current
        
        # Language-agnostic heuristic: treat as follow-up when the new input is
        # short and does not look like a standalone query, or when it barely
        # overlaps with the previous topic.
        import re

        def tokenize(text: str) -> list[str]:
            return re.findall(r"\w+", text.lower())

        current_tokens = tokenize(current)
        
        # Standalone if long enough, has many tokens, or contains a question mark
        is_standalone = (
            len(current) >= 80
            or len(current_tokens) >= 10
            or "?" in current
        )

        if is_standalone:
            return current
        
        # Collect recent user messages (last 5 turns) for context
        recent_user_messages: List[str] = []
        for msg in reversed(history):
            if msg.get("role") == "user" and (msg.get("content") or "").strip():
                recent_user_messages.insert(0, str(msg.get("content")).strip())
                if len(recent_user_messages) >= 5:  # Limit to last 5 user messages
                    break
        
        if not recent_user_messages:
            return current
        
        # Check token overlap with recent context
        all_prev_tokens = set()
        for prev_msg in recent_user_messages:
            all_prev_tokens.update(tokenize(prev_msg))
        
        overlap = set(current_tokens) & all_prev_tokens
        overlap_ratio = len(overlap) / max(1, len(current_tokens))
        
        # If heavily overlaps with prior topics, it's already contextual enough
        if overlap_ratio >= 0.4:
            return current

        # Otherwise, blend recent user context + current follow-up
        # Build a compact context from recent messages
        context_parts = []
        for msg in recent_user_messages[-5:]:  # Last 5 user messages
            if len(msg) < 100:  # Keep short messages as-is
                context_parts.append(msg)
            else:  # Truncate long messages
                context_parts.append(msg[:100] + "...")
        
        context_str = " / ".join(context_parts)
        return f"{context_str}\n\n추가 요청: {current}"

    @classmethod
    def _append_turn_to_history(cls, thread_id: str, user_message: str, assistant_message: str) -> None:
        cls._thread_histories.setdefault(thread_id, [])
        cls._thread_histories[thread_id].append({"role": "user", "content": user_message})
        cls._thread_histories[thread_id].append({"role": "assistant", "content": assistant_message})
    
    def serialize_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Serialize thread state for persistence.
        
        Args:
            thread_id: Thread ID to serialize
            
        Returns:
            Serialized thread state or None if not found
        """
        if thread_id not in self._thread_store:
            return None
        
        thread = self._thread_store[thread_id]
        return {
            "thread_id": thread_id,
            "state": thread.serialize() if hasattr(thread, 'serialize') else {},
            "history": self._thread_histories.get(thread_id, []),
        }
    
    @classmethod
    def deserialize_thread(cls, data: Dict[str, Any]) -> Optional[tuple[str, AgentThread]]:
        """
        Deserialize thread state from storage.
        
        Args:
            data: Serialized thread data
            
        Returns:
            Tuple of (thread_id, AgentThread) or None if invalid
        """
        if not data or "thread_id" not in data:
            return None
        
        thread_id = data["thread_id"]
        
        if hasattr(AgentThread, 'deserialize'):
            thread = AgentThread.deserialize(data.get("state", {}))
        else:
            thread = AgentThread()
        
        cls._thread_store[thread_id] = thread
        # Restore lightweight history if present
        history = data.get("history")
        if isinstance(history, list):
            cls._thread_histories[thread_id] = [
                {
                    "role": str(m.get("role", "user")),
                    "content": str(m.get("content", "")),
                }
                for m in history
                if isinstance(m, dict)
            ]
        else:
            cls._thread_histories.setdefault(thread_id, [])
        return thread_id, thread
    
    def list_threads(self) -> List[str]:
        """Return list of all active thread IDs."""
        return list(self._thread_store.keys())
    
    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread from storage.
        
        Args:
            thread_id: Thread ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if thread_id in self._thread_store:
            del self._thread_store[thread_id]
            self._thread_histories.pop(thread_id, None)
            return True
        return False
    
    async def execute_query_stream(
        self,
        query_content: str,
        search_sources: List[str],
        thread_id: Optional[str] = None
    ):
        """
        Execute the complete research workflow with streaming updates.
        
        Args:
            query_content: The research question
            search_sources: List of search sources to use
            thread_id: Optional thread ID for multi-turn conversation
            
        Yields:
            Dict events with agent status and results
        """
        try:
            # Get or create thread for this conversation
            current_thread_id, thread = self.get_or_create_thread(thread_id)

            # Build the task prompt with conversation history (multi-turn)
            task_with_history = self._build_task_with_history(current_thread_id, query_content)

            # Build a clean standalone query for agents/search
            effective_query_content = self._build_effective_query(current_thread_id, query_content)
            
            # Prepare query
            from ..models.query import ResearchQuery
            from ..models import SearchSource
            
            source_enums = []
            for src in search_sources:
                if isinstance(src, SearchSource):
                    source_enums.append(src)
                elif isinstance(src, str):
                    clean_src = src.replace('SearchSource.', '').lower()
                    try:
                        source_enums.append(SearchSource(clean_src))
                    except ValueError:
                        logger.warning(f"Invalid search source: {src}, skipping")
                        continue
            
            if not source_enums:
                source_enums = [SearchSource.ARXIV]
            
            query = ResearchQuery(
                content=effective_query_content,
                search_sources=source_enums
            )
            
            # Initialize shared state
            self._shared_state.clear()
            self._shared_state["query"] = query
            self._shared_state["search_sources"] = source_enums
            self._shared_state["thread_id"] = current_thread_id
            self._shared_state["thread"] = thread

            # Queue for real-time streaming events emitted by agents
            event_queue: asyncio.Queue = asyncio.Queue()
            self._shared_state["_event_queue"] = event_queue
            
            # Agent names in order
            agent_names = [
                "Planning Agent",
                "Research Agent",
                "Reflect Agent",
                "Content Writing Agent"
            ]
            
            current_agent_idx = 0
            
            # Push start event with thread_id
            await event_queue.put({
                "type": "workflow_start",
                "query": query_content,
                "thread_id": current_thread_id,
            })

            async def _run_group_chat() -> None:
                nonlocal current_agent_idx

                async for event in self.workflow.run_stream(task_with_history):
                    event_type = type(event).__name__

                    # Agent started thinking
                    if event_type == 'ExecutorStartedEvent':
                        if current_agent_idx < len(agent_names):
                            agent_name = agent_names[current_agent_idx]
                            await event_queue.put({
                                "type": "agent_start",
                                "agent": agent_name,
                                "status": "thinking",
                            })

                    # Agent completed
                    elif event_type == 'ExecutorCompletedEvent':
                        if current_agent_idx < len(agent_names):
                            agent_name = agent_names[current_agent_idx]
                            result_data = getattr(event, 'data', None)

                            await event_queue.put({
                                "type": "agent_complete",
                                "agent": agent_name,
                                "status": "completed",
                            })

                            current_agent_idx += 1

                            # Store result in shared state
                            if agent_name == "Planning Agent" and result_data:
                                plan = getattr(result_data, 'research_plan', None)
                                if plan:
                                    await event_queue.put({
                                        "type": "plan_created",
                                        "plan": plan.model_dump(mode='json') if hasattr(plan, 'model_dump') else str(plan),
                                    })

                            elif agent_name == "Research Agent" and result_data:
                                results = getattr(result_data, 'search_results', [])
                                search_events = getattr(result_data, 'search_events', [])
                                statistics = getattr(result_data, 'statistics', {})
                                if results is not None:
                                    await event_queue.put({
                                        "type": "research_complete",
                                        "results_count": len(results),
                                        "search_events": search_events,
                                        "statistics": statistics,
                                    })

            group_chat_task = asyncio.create_task(_run_group_chat())

            # Yield events from the shared queue while the workflow runs
            while True:
                if group_chat_task.done() and event_queue.empty():
                    break

                try:
                    queued_event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                yield queued_event

            # Propagate any workflow exception
            await group_chat_task
            
            # Get final answer from shared state
            synthesized_answer = self._shared_state.get("synthesized_answer")
            if synthesized_answer:
                # Stream answer character by character
                content = synthesized_answer.content if hasattr(synthesized_answer, 'content') else str(synthesized_answer)
                
                yield {
                    "type": "answer_start"
                }
                
                # Stream in chunks for better performance
                chunk_size = 5
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield {
                        "type": "answer_chunk",
                        "content": chunk
                    }
                    # Small delay for streaming effect
                    await asyncio.sleep(0.01)
                
                # Send complete answer with metadata
                yield {
                    "type": "answer_complete",
                    "answer": synthesized_answer.model_dump(mode='json') if hasattr(synthesized_answer, 'model_dump') else {"content": content},
                    "research_plan": self._shared_state.get("research_plan").model_dump(mode='json') if self._shared_state.get("research_plan") and hasattr(self._shared_state.get("research_plan"), 'model_dump') else None,
                    "search_results": [r.model_dump(mode='json') if hasattr(r, 'model_dump') else r for r in self._shared_state.get("search_results", [])],
                    "thread_id": current_thread_id
                }

                # Persist this turn for subsequent multi-turn prompts
                try:
                    self._append_turn_to_history(current_thread_id, query_content, content)
                except Exception:
                    logger.exception("Failed to append turn to history")
            
            # Send completion event with thread_id
            yield {
                "type": "workflow_complete",
                "thread_id": current_thread_id
            }
            
        except Exception as e:
            logger.error(f"Streaming workflow error: {e}", exc_info=True)
            yield {
                "type": "error",
                "message": str(e)
            }
    
    async def execute_query(
        self,
        query_content: str,
        search_sources: List[str],
        ws_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the complete research workflow for a query.
        
        Args:
            query_content: The research question
            search_sources: List of search sources to use
            ws_callback: WebSocket callback for real-time updates
            
        Returns:
            Dict with synthesized answer and metadata
        """
        # Store WebSocket callback
        if ws_callback:
            self.websocket_callback = ws_callback
        
        try:
            current_thread_id, _thread = self.get_or_create_thread(thread_id)

            # Prepare task for workflow
            task = self._build_task_with_history(current_thread_id, query_content)

            # Build a clean standalone query for agents/search
            effective_query_content = self._build_effective_query(current_thread_id, query_content)
            
            # Create initial state for the workflow
            from ..models.query import ResearchQuery
            from ..models import SearchSource
            
            # Create Query object to pass in shared state
            # search_sources come as strings, convert to SearchSource enums
            source_enums = []
            for src in search_sources:
                # Handle both string and SearchSource enum
                if isinstance(src, SearchSource):
                    source_enums.append(src)
                elif isinstance(src, str):
                    # Remove any 'SearchSource.' prefix if present
                    clean_src = src.replace('SearchSource.', '').lower()
                    try:
                        source_enums.append(SearchSource(clean_src))
                    except ValueError:
                        logger.warning(f"Invalid search source: {src}, skipping")
                        continue
            
            if not source_enums:
                source_enums = [SearchSource.ARXIV]  # Default fallback
            
            query = ResearchQuery(
                content=effective_query_content,
                search_sources=source_enums
            )
            
            logger.info(f"Starting workflow for query: {query_content[:50]}...")
            
            # Initialize shared state for agents
            self._shared_state.clear()
            self._shared_state["query"] = query
            self._shared_state["search_sources"] = source_enums
            self._shared_state["thread_id"] = current_thread_id
            
            # Store results from each agent (keys must match AgentId enum values)
            results = {
                "planning": None,
                "research": None,
                "reflect": None,
                "content": None
            }
            
            # Run the workflow
            logger.info(f"Starting workflow.run_stream with task: {task[:100]}...")
            event_count = 0
            async for event in self.workflow.run_stream(task):
                event_count += 1
                logger.info(f"Received event #{event_count}: {type(event).__name__}")
                logger.info(f"  Event type full path: {type(event).__module__}.{type(event).__name__}")
                logger.info(f"  Event attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")
                
                # Check for ExecutorCompletedEvent (agents completing execution)
                if type(event).__name__ == 'ExecutorCompletedEvent':
                    executor_id = getattr(event, 'executor_id', '')
                    # executor_id format: "groupchat_agent:Agent Name"
                    if executor_id.startswith('groupchat_agent:'):
                        agent_name = executor_id.replace('groupchat_agent:', '')
                        result_data = getattr(event, 'data', None)
                        
                        logger.info(f"Agent '{agent_name}' completed execution")
                        logger.info(f"  result_data type: {type(result_data)}")
                        logger.info(f"  result_data value: {result_data}")
                        
                        # Map agent name to result key
                        agent_key = None
                        if agent_name == "Planning Agent":
                            agent_key = "planning"
                        elif agent_name == "Research Agent":
                            agent_key = "research"
                        elif agent_name == "Reflect Agent":
                            agent_key = "reflect"
                        elif agent_name == "Content Writing Agent":
                            agent_key = "content"
                        
                        logger.info(f"  agent_key: {agent_key}")
                        
                        if agent_key:
                            if result_data is not None:
                                results[agent_key] = {
                                    "author": agent_name,
                                    "data": result_data,
                                    "text": str(result_data) if result_data else ""
                                }
                                logger.info(f"✓ Stored result for {agent_key} from {agent_name}")
                            else:
                                logger.warning(f"✗ result_data is None for {agent_name}")
                
                if isinstance(event, AgentRunUpdateEvent):
                    # Handle streaming agent updates
                    executor_id = getattr(event, 'executor_id', getattr(event, 'agent_id', 'Unknown'))
                    agent_name = executor_id.lower() if isinstance(executor_id, str) else str(executor_id).lower()
                    logger.info(f"Agent update: {agent_name}")
                    
                elif isinstance(event, WorkflowOutputEvent):
                    # Handle workflow completion
                    # event.data contains the result from the agent's run_stream
                    result_data = event.data
                    
                    # DEBUG: Log all event attributes
                    logger.info(f"WorkflowOutputEvent attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")
                    logger.info(f"Event.origin: {event.origin if hasattr(event, 'origin') else 'No origin'}")
                    logger.info(f"Event.data: {event.data}")
                    logger.info(f"Event.data type: {type(event.data)}")
                    if hasattr(event.data, 'role'):
                        logger.info(f"Event.data.role: {event.data.role}")
                    if hasattr(event.data, 'text'):
                        logger.info(f"Event.data.text preview: {event.data.text[:100] if event.data.text else 'None'}")
                    
                    # Get the agent name from source_executor_id (correct attribute name)
                    source_executor_id = getattr(event, 'source_executor_id', 'Unknown')
                    agent_name = source_executor_id if isinstance(source_executor_id, str) else str(source_executor_id)
                    logger.info(f"WorkflowOutputEvent from {agent_name}, data type: {type(result_data)}")
                    logger.info(f"Result data preview: {str(result_data)[:200]}")
                    
                    # Store result for the corresponding agent
                    agent_key = agent_name.lower()
                    logger.info(f"Attempting to store result with key: '{agent_key}', available keys: {list(results.keys())}")
                    if agent_key in results:
                        results[agent_key] = {
                            "author": agent_name,
                            "data": result_data,
                            "text": str(result_data) if result_data else ""
                        }
                        logger.info(f"✓ Stored result for {agent_key}")
                    else:
                        logger.warning(f"✗ Unknown agent key: '{agent_key}', not in {list(results.keys())}")
                    
                    logger.info(f"Agent complete: {agent_name}")
            
            logger.info(f"Workflow loop completed. Total events: {event_count}")
            
            logger.info("Workflow completed")
            logger.info(f"Final results keys: {list(results.keys())}")
            logger.info(f"Final results values: {[(k, v is not None) for k, v in results.items()]}")
            logger.info(f"Shared state keys: {list(self._shared_state.keys())}")
            logger.info(f"Shared state values preview: {[(k, type(v).__name__) for k, v in self._shared_state.items()]}")
            
            # Extract results from shared_state (agents store their results there)
            final_results = {
                "success": True,
                "planning": {
                    "author": "Planning Agent",
                    "data": {"research_plan": self._shared_state.get("research_plan")},
                    "text": str(self._shared_state.get("research_plan", ""))
                } if "research_plan" in self._shared_state else None,
                "research": {
                    "author": "Research Agent",
                    "data": {"search_results": self._shared_state.get("search_results")},
                    "text": f"Found {len(self._shared_state.get('search_results', []))} results"
                } if "search_results" in self._shared_state else None,
                "reflect": {
                    "author": "Reflect Agent",
                    "data": {"reflect_feedback": self._shared_state.get("reflect_feedback")},
                    "text": str(self._shared_state.get("reflect_feedback", ""))
                } if "reflect_feedback" in self._shared_state else None,
                "content": {
                    "author": "Content Writing Agent",
                    "data": {"synthesized_answer": self._shared_state.get("synthesized_answer")},
                    "text": str(self._shared_state.get("synthesized_answer", ""))
                } if "synthesized_answer" in self._shared_state else None
            }
            
            logger.info(f"Extracted results from shared_state: {[(k, v is not None) for k, v in final_results.items()]}")
            
            # Return results
            # Persist history if we have an answer
            synthesized_answer = self._shared_state.get("synthesized_answer")
            if synthesized_answer:
                content = synthesized_answer.content if hasattr(synthesized_answer, "content") else str(synthesized_answer)
                try:
                    self._append_turn_to_history(current_thread_id, query_content, content)
                except Exception:
                    logger.exception("Failed to append turn to history")

            final_results["thread_id"] = current_thread_id
            return final_results
        
        except Exception as e:
            # Log error with full traceback
            logger.error(f"Workflow error: {e}", exc_info=True)
            raise
    
    async def _notify_update(self, update: Dict[str, Any]) -> None:
        """
        Send update via WebSocket callback if available.
        
        Args:
            update: Update dictionary to send
        """
        if self.websocket_callback:
            try:
                await self.websocket_callback(update)
            except Exception as e:
                logger.error(f"WebSocket notification failed: {e}")


# Factory function
def create_research_workflow(
    websocket_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> ResearchWorkflow:
    """
    Create a new research workflow instance.
    
    Args:
        websocket_callback: Optional callback for real-time updates
        
    Returns:
        ResearchWorkflow instance
    """
    return ResearchWorkflow(websocket_callback=websocket_callback)


# Export
__all__ = ["ResearchWorkflow", "create_research_workflow"]
