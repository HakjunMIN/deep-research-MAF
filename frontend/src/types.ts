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
}

export interface SearchEvent {
  id: string;
  tool: string;
  query: string;
  keywords: string[];
  status: 'searching' | 'completed' | 'failed';
  results_count?: number;
  results?: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  error?: string;
}

export interface StreamEvent {
  type: 'workflow_start' | 'agent_start' | 'agent_complete' | 'plan_created' | 
        'research_complete' | 'search_event' | 'answer_start' | 'answer_chunk' | 'answer_complete' | 
        'workflow_complete' | 'error';
  agent?: string;
  plan?: {
    keywords: string[];
  };
  results_count?: number;
  search_events?: SearchEvent[];
  id?: string;
  tool?: string;
  query?: string;
  keywords?: string[];
  status?: 'searching' | 'completed' | 'failed';
  results?: Array<{
    title: string;
    url: string;
    snippet: string;
  }>;
  statistics?: {
    total: number;
    google: number;
    arxiv: number;
    duckduckgo: number;
    bing: number;
    avg_relevance: number;
    high_relevance_count: number;
  };
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
