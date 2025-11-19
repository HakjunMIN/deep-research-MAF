/**
 * Agent state management with Zustand.
 * Manages agent states, progress, and real-time updates.
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { AgentState } from "../types/agent";
import { AgentId } from "../types/agent";

/**
 * Agent state interface.
 */
interface AgentStateStore {
  // Agent states by query ID
  agentStates: Record<string, AgentState[]>;
  
  // Current active agents
  activeAgents: Set<AgentId>;
  
  // Expanded agent details (UI state)
  expandedAgents: Set<AgentId>;
  
  // Actions
  setAgentStates: (queryId: string, states: AgentState[]) => void;
  updateAgentState: (queryId: string, agentState: AgentState) => void;
  clearAgentStates: (queryId: string) => void;
  
  setActiveAgent: (agentId: AgentId) => void;
  removeActiveAgent: (agentId: AgentId) => void;
  clearActiveAgents: () => void;
  
  toggleExpandedAgent: (agentId: AgentId) => void;
  setExpandedAgent: (agentId: AgentId, expanded: boolean) => void;
  collapseAllAgents: () => void;
  
  // Helper actions
  getAgentStateForQuery: (queryId: string, agentId: AgentId) => AgentState | null;
  getLatestAgentState: (queryId: string) => AgentState | null;
  isAgentActive: (agentId: AgentId) => boolean;
  isAgentExpanded: (agentId: AgentId) => boolean;
  getAgentProgress: (queryId: string, agentId: AgentId) => number;
  
  reset: () => void;
}

/**
 * Initial state values.
 */
const initialState = {
  agentStates: {},
  activeAgents: new Set<AgentId>(),
  expandedAgents: new Set<AgentId>()
};

/**
 * Agent state store with Zustand.
 */
export const useAgentStateStore = create<AgentStateStore>()(
  devtools(
    (set, get) => ({
      ...initialState,
      
      // Agent states management
      setAgentStates: (queryId, states) =>
        set(
          (state) => ({
            agentStates: {
              ...state.agentStates,
              [queryId]: states
            }
          }),
          false,
          "setAgentStates"
        ),
      
      updateAgentState: (queryId, agentState) =>
        set(
          (state) => {
            const existingStates = state.agentStates[queryId] || [];
            const existingIndex = existingStates.findIndex(
              (s) => s.agent_id === agentState.agent_id
            );
            
            let newStates: AgentState[];
            if (existingIndex >= 0) {
              // Update existing state
              newStates = [...existingStates];
              newStates[existingIndex] = agentState;
            } else {
              // Add new state
              newStates = [...existingStates, agentState];
            }
            
            return {
              agentStates: {
                ...state.agentStates,
                [queryId]: newStates
              }
            };
          },
          false,
          "updateAgentState"
        ),
      
      clearAgentStates: (queryId) =>
        set(
          (state) => {
            const newStates = { ...state.agentStates };
            delete newStates[queryId];
            return { agentStates: newStates };
          },
          false,
          "clearAgentStates"
        ),
      
      // Active agents management
      setActiveAgent: (agentId) =>
        set(
          (state) => {
            const newActive = new Set(state.activeAgents);
            newActive.add(agentId);
            return { activeAgents: newActive };
          },
          false,
          "setActiveAgent"
        ),
      
      removeActiveAgent: (agentId) =>
        set(
          (state) => {
            const newActive = new Set(state.activeAgents);
            newActive.delete(agentId);
            return { activeAgents: newActive };
          },
          false,
          "removeActiveAgent"
        ),
      
      clearActiveAgents: () =>
        set(
          { activeAgents: new Set<AgentId>() },
          false,
          "clearActiveAgents"
        ),
      
      // Expanded agents UI state
      toggleExpandedAgent: (agentId) =>
        set(
          (state) => {
            const newExpanded = new Set(state.expandedAgents);
            if (newExpanded.has(agentId)) {
              newExpanded.delete(agentId);
            } else {
              newExpanded.add(agentId);
            }
            return { expandedAgents: newExpanded };
          },
          false,
          "toggleExpandedAgent"
        ),
      
      setExpandedAgent: (agentId, expanded) =>
        set(
          (state) => {
            const newExpanded = new Set(state.expandedAgents);
            if (expanded) {
              newExpanded.add(agentId);
            } else {
              newExpanded.delete(agentId);
            }
            return { expandedAgents: newExpanded };
          },
          false,
          "setExpandedAgent"
        ),
      
      collapseAllAgents: () =>
        set(
          { expandedAgents: new Set<AgentId>() },
          false,
          "collapseAllAgents"
        ),
      
      // Helper actions
      getAgentStateForQuery: (queryId, agentId) => {
        const state = get();
        const states = state.agentStates[queryId] || [];
        return states.find((s) => s.agent_id === agentId) || null;
      },
      
      getLatestAgentState: (queryId) => {
        const state = get();
        const states = state.agentStates[queryId] || [];
        if (states.length === 0) return null;
        
        // Find the most recently updated state
        return states.reduce((latest, current) =>
          new Date(current.updated_at) > new Date(latest.updated_at) ? current : latest
        );
      },
      
      isAgentActive: (agentId) => {
        const state = get();
        return state.activeAgents.has(agentId);
      },
      
      isAgentExpanded: (agentId) => {
        const state = get();
        return state.expandedAgents.has(agentId);
      },
      
      getAgentProgress: (queryId, agentId) => {
        const state = get();
        const agentState = state.agentStates[queryId]?.find(
          (s) => s.agent_id === agentId
        );
        return agentState?.progress || 0;
      },
      
      // Reset state
      reset: () =>
        set(
          {
            agentStates: {},
            activeAgents: new Set<AgentId>(),
            expandedAgents: new Set<AgentId>()
          },
          false,
          "reset"
        )
    }),
    {
      name: "agent-state-store",
      enabled: import.meta.env.DEV
    }
  )
);

/**
 * Selector hooks for common queries.
 * Note: useActiveAgents returns a Set to avoid creating new array references.
 * Convert to array in the component using useMemo if needed.
 */
export const useAgentStatesForQuery = (queryId: string) =>
  useAgentStateStore((state) => state.agentStates[queryId] || []);

export const useActiveAgentsSet = () =>
  useAgentStateStore((state) => state.activeAgents);

export const useIsAgentExpanded = (agentId: AgentId) =>
  useAgentStateStore((state) => state.expandedAgents.has(agentId));

export const useAgentProgress = (queryId: string, agentId: AgentId) =>
  useAgentStateStore((state) => state.getAgentProgress(queryId, agentId));
