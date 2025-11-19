/**
 * Conversation state management with Zustand.
 * Manages chat messages and loading state.
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { ChatMessage } from "../types/message";

/**
 * Conversation state interface.
 */
interface ConversationState {
  // Chat messages for UI display
  messages: ChatMessage[];
  
  // Loading states
  isLoading: boolean;
  
  // Error state
  error: string | null;
  
  // Actions
  addMessage: (message: ChatMessage) => void;
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  
  setIsLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  reset: () => void;
}

/**
 * Initial state values.
 */
const initialState = {
  messages: [],
  isLoading: false,
  error: null
};

/**
 * Conversation store with Zustand.
 */
export const useConversationStore = create<ConversationState>()(
  devtools(
    (set) => ({
      ...initialState,
      
      // Message management
      addMessage: (message) =>
        set(
          (state) => ({
            messages: [...state.messages, message]
          }),
          false,
          "addMessage"
        ),
      
      updateMessage: (messageId, updates) =>
        set(
          (state) => ({
            messages: state.messages.map((m) =>
              m.id === messageId ? { ...m, ...updates } : m
            )
          }),
          false,
          "updateMessage"
        ),
      
      clearMessages: () =>
        set({ messages: [] }, false, "clearMessages"),
      
      // Loading states
      setIsLoading: (isLoading) =>
        set({ isLoading }, false, "setIsLoading"),
      
      setError: (error) =>
        set({ error }, false, "setError"),
      
      // Reset state
      reset: () =>
        set(initialState, false, "reset")
    }),
    {
      name: "conversation-store",
      enabled: import.meta.env.DEV
    }
  )
);

/**
 * Selector hooks for common queries.
 */
export const useMessages = () =>
  useConversationStore((state) => state.messages);

export const useIsLoading = () =>
  useConversationStore((state) => state.isLoading);

export const useConversationError = () =>
  useConversationStore((state) => state.error);
