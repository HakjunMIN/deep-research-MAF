export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  status?: 'pending' | 'completed' | 'error';
  sources?: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  toolCalls?: ToolCall[];
}

// AG-UI Protocol Event Types
export type AGUIEventType = 
  | 'RUN_STARTED'
  | 'RUN_FINISHED'
  | 'RUN_ERROR'
  | 'TEXT_MESSAGE_START'
  | 'TEXT_MESSAGE_CONTENT'
  | 'TEXT_MESSAGE_END'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_ARGS'
  | 'TOOL_CALL_END'
  | 'TOOL_CALL_RESULT';

export interface AGUIEvent {
  type: AGUIEventType;
  threadId?: string;
  runId?: string;
  messageId?: string;
  role?: string;
  delta?: string;
  toolCallId?: string;
  toolCallName?: string;
  content?: string;
  message?: string;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments?: string;
  result?: string;
  status: 'pending' | 'executing' | 'completed' | 'error';
}

// Legacy event types for backward compatibility
export interface StreamEvent {
  type: 'workflow_start' | 'agent_start' | 'agent_complete' | 'plan_created' | 
        'research_complete' | 'answer_start' | 'answer_chunk' | 'answer_complete' | 
        'workflow_complete' | 'error';
  agent?: string;
  plan?: {
    keywords: string[];
  };
  results_count?: number;
  content?: string;
  answer?: {
    sources: Array<{
      title: string;
      url: string;
      snippet: string;
    }>;
  };
  message?: string;
}

export interface ResearchRequest {
  content: string;
  search_sources: string[];
}

// AG-UI Request format
export interface AGUIMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface AGUIRequest {
  messages: AGUIMessage[];
  thread_id?: string;
}

