"""
Content Writing Agent - Synthesizes final answer with citations.

This agent:
1. Reviews all collected search results
2. Synthesizes a comprehensive answer
3. Structures content with sections
4. Adds proper citations
5. Generates metadata
"""

import logging
from typing import Any, Dict, List

from agent_framework import AgentRunContext

from .base import BaseCustomAgent
from ..models import AgentId
from ..models.search_result import SearchResult
from ..models.synthesized_answer import (
    SynthesizedAnswer,
    SourceCitation,
    AnswerSection,
    AnswerMetadata
)
from ..services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)


class ContentWritingAgent(BaseCustomAgent):
    """
    Content Writing Agent creates the final synthesized answer.
    
    Responsibilities:
    - Synthesize information from search results
    - Structure answer with sections
    - Add proper source citations
    - Generate answer in Markdown format
    - Create answer metadata
    """
    
    def __init__(self):
        """Initialize Content Writing Agent."""
        super().__init__(
            agent_id=AgentId.CONTENT,
            agent_name="Content Writing Agent",
            agent_description="Synthesizes comprehensive answers with citations"
        )
        self.openai_service = AzureOpenAIService()
    
    async def execute(self, context: AgentRunContext) -> Dict[str, Any]:
        """
        Synthesize final answer from research results.
        
        Args:
            context: Agent execution context
            
        Returns:
            Dict with synthesized_answer
        """
        try:
            logger.info("ContentWritingAgent.execute started")
            # Get data from context
            query = self.get_shared_state(context, "query")
            logger.info(f"Query: {query}")
            search_results: List[SearchResult] = self.get_shared_state(context, "search_results")
            logger.info(f"Search results count: {len(search_results) if search_results else 0}")
            
            if not search_results:
                logger.error("No search results available for synthesis")
                raise ValueError("No search results available for synthesis")
            
            # Step 1: Prepare sources and citations
            self.log_step("📚 Preparing sources and citations...")
            sources = self._prepare_sources(search_results)
            self.log_step(f"✓ Prepared {len(sources)} unique sources")
            
            # Step 2: Generate answer content
            self.log_step("✍️ Generating comprehensive answer content...")
            answer_content = await self._generate_content(
                query.content,
                search_results,
                sources
            )
            self.log_step(f"✓ Generated {len(answer_content)} characters of content")
            
            # Step 3: Structure answer into sections
            self.log_step("📑 Structuring answer into sections...")
            sections = self._create_sections(answer_content, sources)
            self.log_step(f"✓ Created {len(sections)} sections")
            
            # Step 4: Generate metadata
            self.log_step("✅ Finalizing answer with metadata...")
            metadata = self._create_metadata(search_results, answer_content, len(sources))
            
            # Create synthesized answer
            synthesized_answer = SynthesizedAnswer(
                query_id=str(query.id),
                thread_id=getattr(query, 'thread_id', str(query.id)),  # Use query_id as fallback if thread_id not available
                content=answer_content,
                sources=sources,
                sections=sections,
                metadata=metadata
            )
            
            # Store in shared state
            self.set_shared_state(context, "synthesized_answer", synthesized_answer)
            
            result = {
                "synthesized_answer": synthesized_answer,
                "word_count": metadata.word_count,
                "source_count": metadata.total_sources
            }
            logger.info(f"ContentWritingAgent.execute completed. Result keys: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"ContentWritingAgent.execute failed: {e}", exc_info=True)
            raise
    
    def _prepare_sources(
        self,
        results: List[SearchResult]
    ) -> List[SourceCitation]:
        """
        Prepare source citations from search results.
        
        Args:
            results: Search results
            
        Returns:
            List of SourceCitation instances (unique URLs only)
        """
        # Sort by relevance score
        sorted_results = sorted(
            results,
            key=lambda r: r.relevance_score,
            reverse=True
        )
        
        # Create citations, removing duplicates by URL
        citations = []
        seen_urls = set()
        citation_num = 1
        
        for result in sorted_results:
            # Skip if URL already seen
            if result.url in seen_urls:
                continue
            
            seen_urls.add(result.url)
            citation = SourceCitation(
                id=str(result.id),
                title=result.title,
                url=result.url,
                citation_number=citation_num
            )
            citations.append(citation)
            citation_num += 1
            
            # Limit to top 10 unique sources
            if len(citations) >= 10:
                break
        
        return citations
    
    async def _generate_content(
        self,
        query: str,
        results: List[SearchResult],
        sources: List[SourceCitation]
    ) -> str:
        """
        Generate comprehensive answer content using Azure OpenAI.
        
        Args:
            query: Original research question
            results: Search results
            sources: Prepared citations
            
        Returns:
            Answer content in Markdown format
        """
        # Prepare context from top results
        context_snippets = []
        for idx, result in enumerate(results[:10], start=1):
            snippet = f"[{idx}] {result.title}: {result.snippet}"
            context_snippets.append(snippet)
        
        context = "\n\n".join(context_snippets)
        
        # Create prompt for content generation
        prompt = f"""You are a research assistant synthesizing information to answer a user's question.

Question: {query}

Available information from search results:
{context}

Instructions:
1. Provide a comprehensive answer to the question
2. Use information from the search results
3. Structure your answer with clear sections
4. Cite sources using [number] notation (e.g., [1], [2])
5. Write in a clear, informative style
6. Use Markdown formatting (headings, lists, bold, etc.)
7. Be thorough but concise
8. If information is limited, acknowledge it

Generate the answer:"""
        
        try:
            # Generate content using OpenAI
            response = await self.openai_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract text content from ChatCompletion response
            content = response.choices[0].message.content
            return content
        
        except Exception as e:
            # Fallback: create basic answer
            logger.error(f"{self.agent_id.value}: Content generation failed for query {results[0].query_id if results else 'unknown'}, using fallback: {str(e)}", exc_info=True)
            
            return self._generate_fallback_content(query, results, sources)
    
    def _generate_fallback_content(
        self,
        query: str,
        results: List[SearchResult],
        sources: List[SourceCitation]
    ) -> str:
        """
        Generate basic answer content as fallback.
        
        Args:
            query: Original question
            results: Search results
            sources: Citations
            
        Returns:
            Basic Markdown answer
        """
        content_parts = [
            f"# Answer to: {query}\n",
            "## Summary\n",
            f"Based on {len(results)} search results, here are the key findings:\n"
        ]
        
        # Add top results
        for idx, result in enumerate(results[:5], start=1):
            content_parts.append(f"### {result.title} [{idx}]\n")
            content_parts.append(f"{result.snippet}\n")
        
        # Add sources section
        content_parts.append("\n## Sources\n")
        for source in sources[:10]:
            content_parts.append(
                f"{source.citation_number}. [{source.title}]({source.url})\n"
            )
        
        return "\n".join(content_parts)
    
    def _create_sections(
        self,
        content: str,
        sources: List[SourceCitation]
    ) -> List[AnswerSection]:
        """
        Parse content into structured sections.
        
        Args:
            content: Markdown content
            sources: Source citations
            
        Returns:
            List of AnswerSection instances
        """
        sections = []
        
        # Split by markdown headings
        lines = content.split("\n")
        current_heading = "Introduction"
        current_content = []
        current_citations = []
        
        for line in lines:
            # Check if line is a heading
            if line.startswith("##") and not line.startswith("###"):
                # Save previous section
                if current_content:
                    sections.append(AnswerSection(
                        heading=current_heading,
                        content="\n".join(current_content),
                        citations=current_citations
                    ))
                
                # Start new section
                current_heading = line.replace("##", "").strip()
                current_content = []
                current_citations = []
            else:
                current_content.append(line)
                
                # Extract citation numbers from line (e.g., [1], [2])
                import re
                citation_refs = re.findall(r'\[(\d+)\]', line)
                current_citations.extend(int(ref) for ref in citation_refs)
        
        # Add last section
        if current_content:
            sections.append(AnswerSection(
                heading=current_heading,
                content="\n".join(current_content),
                citations=list(set(current_citations))  # Remove duplicates
            ))
        
        return sections
    
    def _create_metadata(
        self,
        results: List[SearchResult],
        content: str,
        unique_source_count: int
    ) -> AnswerMetadata:
        """
        Create metadata for the answer.
        
        Args:
            results: Search results
            content: Generated content
            unique_source_count: Number of unique sources actually used
            
        Returns:
            AnswerMetadata instance
        """
        from datetime import datetime
        
        # Count sources by type
        # Handle both enum and string source values
        google_count = sum(1 for r in results if (r.source.value if hasattr(r.source, 'value') else r.source) == "google")
        arxiv_count = sum(1 for r in results if (r.source.value if hasattr(r.source, 'value') else r.source) == "arxiv")
        
        # Count words (approximate)
        word_count = len(content.split())
        
        return AnswerMetadata(
            total_sources=unique_source_count,  # Use actual unique sources count
            google_sources=google_count,
            arxiv_sources=arxiv_count,
            word_count=word_count,
            generated_at=datetime.utcnow().isoformat()
        )


# Export
__all__ = ["ContentWritingAgent"]
