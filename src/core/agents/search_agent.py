"""Search Agent - Performs web searches when information is needed."""

from typing import List, Optional
from pydantic import BaseModel
from ddgs import DDGS
from src.core.llm.ollama_client import get_llm


class SearchResult(BaseModel):
    """Single search result."""
    title: str
    url: str
    snippet: str
    

class SearchAgent:
    """Agent that performs web searches using DuckDuckGo."""
    
    def __init__(self):
        self.ddgs = DDGS()
    
    async def should_search(self, query: str, conversation_history: List[dict] = None) -> bool:
        """Determine if web search is needed using LLM.
        
        Args:
            query: User's question
            conversation_history: Recent messages for context
            
        Returns:
            True if search is needed, False otherwise
        """
        llm = await get_llm()
        
        prompt = f"""Analyze if this question requires current web information or if you can answer from general knowledge.

User question: "{query}"

Instructions:
1. If the query contains UNKNOWN technical terms, acronyms (e.g., "p8s", "k9s", specific library names), or names you are not 100% sure about -> Return YES
2. If the query asks for recent events, news, or current prices -> Return YES
3. If the query is about general programming concepts (e.g., "what is a loop") -> Return NO
4. If you are unsure -> Return YES (Better to search than hallucinate)

Return ONLY "YES" or "NO".

Examples:
- "What is Python?" → NO
- "Who won the latest Super Bowl?" → YES
- "What happened in tech news today?" → YES
- "Explain machine learning" → NO
- "Dimmi qualcosa su p8s" → YES (Ambiguous acronym)
- "Come si usa la libreria xyz-latest" → YES

Answer (YES/NO):"""
        
        try:
            response_msg = await llm.chat([
                {"role": "system", "content": "You are a decision making assistant. Answer only YES or NO."},
                {"role": "user", "content": prompt}
            ])
            
            response = response_msg.get("content", "")
            decision = response.strip().upper()
            return "YES" in decision
        except Exception as e:
            print(f"Error in should_search: {e}")
            # Default to not searching on error
            return False
    
    async def extract_search_queries(self, user_query: str) -> List[str]:
        """Generate optimal search queries from user question.
        
        Args:
            user_query: Original user question
            
        Returns:
            List of search queries (1-3)
        """
        llm = await get_llm()
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""Generate 1-3 simple, keyword-based search queries to find info for this question.

Question: "{user_query}"
Current Date: {current_date}

Instructions:
1. Return ONLY a numbered list of queries
2. Do NOT use placeholders like [date] - insert the actual date {current_date}
3. Do NOT use markdown bolding (**) or quotes
4. Keep queries simple and effective for a search engine

Example:
1. tech news headlines {current_date}
2. major technology updates today

Search queries:"""
        
        try:
            response_msg = await llm.chat([
                {"role": "system", "content": "You are a search query optimization expert."},
                {"role": "user", "content": prompt}
            ])
            
            response = response_msg.get("content", "")
            
            # Parse numbered list
            lines = response.strip().split('\n')
            queries = []
            for line in lines:
                # Remove numbering (1., 2., etc) and markdown
                clean = line.strip().replace('*', '').replace('"', '')
                if clean and (clean[0].isdigit() or clean.startswith('-')):
                    # Remove number and dot/dash
                    query = clean.split('.', 1)[-1].split('-', 1)[-1].strip()
                    if query:
                        queries.append(query)
            
            # Fallback to original query if parsing failed
            return queries if queries else [user_query]
        except Exception as e:
            print(f"Error generating search queries: {e}")
            return [user_query]
    
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform DuckDuckGo search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        try:
            results = []
            # DuckDuckGo text search
            ddg_results = self.ddgs.text(query, max_results=max_results)
            
            for result in ddg_results:
                results.append(SearchResult(
                    title=result.get('title', ''),
                    url=result.get('href', result.get('link', '')),
                    snippet=result.get('body', result.get('snippet', ''))
                ))
            
            return results
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    async def search_multiple(self, queries: List[str], max_results_per_query: int = 3) -> List[SearchResult]:
        """Search multiple queries and combine results.
        
        Args:
            queries: List of search queries
            max_results_per_query: Max results per query
            
        Returns:
            Combined unique search results
        """
        all_results = []
        seen_urls = set()
        
        for query in queries:
            results = await self.search(query, max_results_per_query)
            for result in results:
                # Deduplicate by URL
                if result.url not in seen_urls:
                    all_results.append(result)
                    seen_urls.add(result.url)
        
        return all_results


# Singleton instance
_search_agent = None

async def get_search_agent() -> SearchAgent:
    """Get singleton search agent instance."""
    global _search_agent
    if _search_agent is None:
        _search_agent = SearchAgent()
    return _search_agent
