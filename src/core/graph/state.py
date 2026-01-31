"""State management for LangGraph workflow."""

from typing import TypedDict, List, Optional, Annotated
from typing_extensions import NotRequired
from langgraph.graph import add_messages
from src.core.agents.search_agent import SearchResult
from src.core.agents.scraper_agent import ScrapedContent


class AgentState(TypedDict):
    """Shared state across all agents in the workflow."""
    
    # Input
    messages: Annotated[List[dict], add_messages]  # Conversation history
    session_id: str  # Chat session ID
    user_query: str  # Current user question
    
    # Search flow
    needs_search: NotRequired[bool]  # Whether web search is needed
    search_performed: NotRequired[bool]  # Whether search was actually performed
    search_queries: NotRequired[List[str]]  # Generated search queries
    search_results: NotRequired[List[SearchResult]]  # Search results
    
    # Scraping flow
    urls_to_scrape: NotRequired[List[str]]  # URLs to scrape
    scraped_content: NotRequired[List[ScrapedContent]]  # Scraped content
    
    # Context enrichment
    web_context: NotRequired[str]  # Enriched context from web
    sources: NotRequired[List[dict]]  # Sources for citation
    
    # Output
    final_response: NotRequired[str]  # Final answer
    response_chunks: NotRequired[List[str]]  # Streaming chunks
