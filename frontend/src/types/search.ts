/**
 * Search-related type definitions (mirrors backend models).
 */

/**
 * Search source matching backend SearchSource enum.
 */
export enum SearchSource {
  GOOGLE = "google",
  ARXIV = "arxiv"
}

/**
 * Individual search result from Google or arXiv.
 * Mirrors backend SearchResult model.
 */
export interface SearchResult {
  id: string;
  query_id: string;
  source: SearchSource;
  title: string;
  url: string;
  snippet: string;
  authors: string[] | null; // arXiv only
  published_date: string | null; // arXiv only
  relevance_score: number; // 0.0 to 1.0
  created_at: string;
  updated_at: string;
}

/**
 * Search step in research plan.
 * Mirrors backend SearchStep nested model.
 */
export interface SearchStep {
  step_number: number;
  description: string;
  sources: SearchSource[];
  keywords: string[];
}

/**
 * Research plan from Planning Agent.
 * Mirrors backend ResearchPlan model.
 */
export interface ResearchPlan {
  id: string;
  query_id: string;
  strategy: string;
  keywords: string[];
  search_steps: SearchStep[];
  estimated_time: number; // seconds
  created_at: string;
  updated_at: string;
}

/**
 * Source citation in synthesized answer.
 * Mirrors backend SourceCitation nested model.
 */
export interface SourceCitation {
  id: string;
  title: string;
  url: string;
  citation_number: number;
}

/**
 * Answer section in synthesized answer.
 * Mirrors backend AnswerSection nested model.
 */
export interface AnswerSection {
  heading: string;
  content: string;
  citations: number[]; // Citation numbers
}

/**
 * Answer metadata.
 * Mirrors backend AnswerMetadata nested model.
 */
export interface AnswerMetadata {
  total_sources: number;
  google_sources: number;
  arxiv_sources: number;
  word_count: number;
  generated_at: string;
}

/**
 * Final synthesized answer from Content Writing Agent.
 * Mirrors backend SynthesizedAnswer model.
 */
export interface SynthesizedAnswer {
  id: string;
  query_id: string;
  content: string; // Markdown
  sources: SourceCitation[];
  sections: AnswerSection[];
  metadata: AnswerMetadata;
  created_at: string;
  updated_at: string;
}

/**
 * Search filters for UI.
 */
export interface SearchFilters {
  sources: SearchSource[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  minRelevance?: number;
}
