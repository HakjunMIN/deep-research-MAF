/**
 * Message-related type definitions (mirrors backend models).
 */

import { AgentId } from "./agent";

/**
 * Message type matching backend MessageType enum.
 */
export enum MessageType {
  REQUEST = "request",
  RESPONSE = "response",
  NOTIFICATION = "notification",
  ERROR = "error"
}

/**
 * Agent-to-agent message.
 * Mirrors backend AgentMessage model.
 */
export interface AgentMessage {
  id: string;
  query_id: string;
  sender: AgentId;
  recipient: AgentId | null;
  message_type: MessageType;
  content: Record<string, any>;
  timestamp: string;
  created_at: string;
  updated_at: string;
}

/**
 * Query status matching backend QueryStatus enum.
 */
export enum QueryStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled"
}

/**
 * Research query from user.
 * Mirrors backend ResearchQuery model.
 */
export interface ResearchQuery {
  id: string;
  content: string;
  search_sources: SearchSource[];
  status: QueryStatus;
  created_at: string;
  updated_at: string;
}

/**
 * Search source enum (referenced here, defined fully in search.ts).
 */
export enum SearchSource {
  GOOGLE = "google",
  ARXIV = "arxiv"
}

/**
 * UI message for displaying in chat interface.
 * Combines query and answer for display.
 */
export interface ChatMessage {
  id: string;
  type: "query" | "answer" | "error";
  content: string;
  timestamp: string;
  status?: QueryStatus;
  sources?: SourceCitation[];
}

/**
 * Source citation for answers (referenced from synthesized answer).
 */
export interface SourceCitation {
  id: string;
  title: string;
  url: string;
  citation_number: number;
}
