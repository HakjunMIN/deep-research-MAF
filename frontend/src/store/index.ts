/**
 * Store index - exports all Zustand stores and hooks.
 */

// Conversation store
export {
  useConversationStore,
  useMessages,
  useIsLoading,
  useConversationError
} from "./conversationSlice";

// Agent state store
export {
  useAgentStateStore,
  useAgentStatesForQuery,
  useActiveAgentsSet,
  useIsAgentExpanded,
  useAgentProgress
} from "./agentSlice";

// Re-export types for convenience
export type { ResearchQuery, ChatMessage } from "../types/message";
export type { AgentState } from "../types/agent";
export { QueryStatus } from "../types/message";
export { AgentId, AgentStatus } from "../types/agent";
