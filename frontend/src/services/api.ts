/**
 * REST API client for backend communication.
 */

import { SearchSource } from "../types/message";
import type { AgentState } from "../types/agent";
import type { SearchResult, SynthesizedAnswer } from "../types/search";

/**
 * API configuration.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/**
 * API error class.
 */
export class ApiError extends Error {
  status: number;
  details?: unknown;
  
  constructor(
    message: string,
    status: number,
    details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/**
 * Handle API response and errors.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.message || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      errorData.details
    );
  }
  
  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }
  
  return response.json();
}

/**
 * Request body types.
 */
export interface ResearchRequest {
  content: string;
  search_sources: SearchSource[];
}

/**
 * Response types.
 */
export interface ResearchResponse {
  content: string;
  answer: SynthesizedAnswer;
  research_plan: Record<string, unknown> | null;
  search_results: SearchResult[];
  agent_states: AgentState[];
}

/**
 * REST API client class.
 */
class ApiClient {
  private baseUrl: string;
  private defaultTimeout: number = 60000; // 60 seconds for long-running research queries
  
  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }
  
  /**
   * Make a request to the API with timeout handling.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs?: number
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      "Content-Type": "application/json",
      ...options.headers
    };
    
    const timeout = timeoutMs || this.defaultTimeout;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      return handleResponse<T>(response);
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof Error && error.name === "AbortError") {
        throw new ApiError(
          "Request timeout",
          408,
          `Request to ${endpoint} timed out after ${timeout}ms`
        );
      }
      
      throw error;
    }
  }
  
  // ============================================================================
  // Research
  // ============================================================================
  
  /**
   * Submit a research query and get complete results synchronously.
   * This will wait for the entire workflow to complete.
   */
  async submitResearch(
    content: string,
    searchSources: SearchSource[]
  ): Promise<ResearchResponse> {
    // Set a longer timeout for research (5 minutes)
    return this.request<ResearchResponse>("/research", {
      method: "POST",
      body: JSON.stringify({
        content,
        search_sources: searchSources
      })
    }, 300000); // 5 minutes
  }
  
  // ============================================================================
  // Health Check
  // ============================================================================
  
  /**
   * Check API health.
   */
  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    return this.request<{ status: string; service: string; version: string }>("/health");
  }
}

/**
 * Singleton API client instance.
 */
export const apiClient = new ApiClient();

/**
 * Export default instance.
 */
export default apiClient;
