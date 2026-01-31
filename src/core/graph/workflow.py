"""LangGraph workflow for orchestrating search, scraping, and coordination."""

from langgraph.graph import StateGraph, END
from typing import Literal, List, Optional
from src.core.graph.state import AgentState
from src.core.agents.search_agent import get_search_agent
from src.core.agents.scraper_agent import get_scraper_agent
from src.core.llm.ollama_client import get_llm
from src.core.memory.manager import memory_manager
from src.core.memory.graph_memory import graph_memory
from src.core.tool_registry import tool_registry
import json


class MaskWorkflow:
    """LangGraph workflow for multi-agent orchestration."""
    
    def __init__(self):
        self.graph = None
    
    def __init__(self):
        self.graph = None
    
    async def retrieve_node(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from memory (RAG + Graph)."""
        print("🧠 Retrieve: Fetching memory context...")
        
        user_query = state["user_query"]
        session_id = state["session_id"]
        
        # Get project ID for context filtering
        try:
            session = memory_manager.get_session(session_id)
            project_id = session.project_id if session else None
        except:
            project_id = None
            
        # 1. RAG Search (Vector DB)
        rag_context = await memory_manager.search_relevant_history(user_query, project_id=project_id)
        
        # 2. Graph Search (Neo4j)
        graph_context = await graph_memory.retrieve_context(user_query)
        
        # Combine
        full_context = ""
        if rag_context:
            full_context += f"{rag_context}\n\n"
        if graph_context:
            full_context += f"{graph_context}\n\n"
            
        state["memory_context"] = full_context.strip()
        if full_context:
            print("✅ Retrieve: Found relevant memory")
        else:
            print("   Retrieve: No relevant memory found")
            
        return state

    async def router_node(self, state: AgentState) -> AgentState:
        """Determine if web search is needed."""
        print("🔀 Router: Analyzing query...")
        
        user_query = state["user_query"]
        
        # Check for direct URLs in the query
        import re
        # Regex to capture URLs
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        direct_urls = re.findall(url_pattern, user_query)
        
        if direct_urls:
            print(f"✅ Router: Direct URLs detected: {direct_urls}")
            state["urls_to_scrape"] = direct_urls
            state["needs_search"] = False
            state["direct_scrape"] = True # New flag to indicate direct routing
            return state

        search_agent = await get_search_agent()
        
        # Check if search is needed
        needs_search = await search_agent.should_search(user_query, state.get("messages", []))
        
        state["needs_search"] = needs_search
        state["direct_scrape"] = False
        
        if needs_search:
            print("✅ Router: Web search required")
        else:
            print("✅ Router: Direct answer possible")
        
        return state
    
    async def search_node(self, state: AgentState) -> AgentState:
        """Perform web search."""
        print("🔍 SearchAgent: Searching web...")
        
        # Mark that search was performed
        state["search_performed"] = True
        
        search_agent = await get_search_agent()
        user_query = state["user_query"]
        
        # Generate search queries
        queries = await search_agent.extract_search_queries(user_query)
        state["search_queries"] = queries
        print(f"   Queries: {queries}")
        
        # Perform search
        results = await search_agent.search_multiple(queries, max_results_per_query=3)
        state["search_results"] = results
        
        # Extract URLs for scraping (top 3)
        urls = [r.url for r in results[:3]]
        state["urls_to_scrape"] = urls
        
        print(f"✅ SearchAgent: Found {len(results)} results")
        
        return state
    
    async def scrape_node(self, state: AgentState) -> AgentState:
        """Scrape web pages."""
        print("🕷️  ScraperAgent: Scraping pages...")
        
        scraper_agent = await get_scraper_agent()
        urls = state.get("urls_to_scrape", [])
        
        if not urls:
            print("   No URLs to scrape")
            state["scraped_content"] = []
            state["web_context"] = ""
            state["sources"] = []
            return state
        
        # Scrape URLs
        scraped = []
        # Deduplicate URLs while preserving order
        unique_urls = []
        seen = set()
        for u in urls:
            if u not in seen:
                unique_urls.append(u)
                seen.add(u)
                
        # Limit to 3 (or more if direct scrape? maybe strict 3 for perf)
        # If direct scrape, maybe just scrape the ones provided.
        # Let's keep max 3 for now.
        for i, url in enumerate(unique_urls[:3]):
            try:
                # Heuristic: Crawl the first result if it looks like a documentation site
                # or if the user specifically asked for depth (which we assume for now)
                
                is_docs = any(kw in url.lower() for kw in ["docs", "documentation", "wiki", "manual", "guide", "github.io"])
                
                # If direct scrape of a doc site, ALWAYS crawl
                should_crawl = (i == 0 and is_docs) or state.get("direct_scrape")
                
                if should_crawl and is_docs: 
                    print(f"🕷️  Crawling {url} (Depth: 2)...")
                    crawl_results = await scraper_agent.crawl(url, max_depth=2, max_pages=8)
                    scraped.extend(crawl_results)
                else:
                    # Standard scraping for others
                    print(f"🕷️  Scraping {url}...")
                    result = await scraper_agent.scrape_url(url)
                    if not result.error:
                        scraped.append(result)
                        
            except Exception as e:
                print(f"   Error processing {url}: {e}")

        state["scraped_content"] = scraped
        
        # Extract relevant content
        user_query = state["user_query"]
        relevant_parts = []
        sources = []
        
        for content in scraped:
            if content.error:
                continue
            
            # Extract relevant parts
            relevant = await scraper_agent.extract_relevant_content(content, user_query)
            if relevant and "no relevant" not in relevant.lower():
                relevant_parts.append(f"From {content.title} ({content.url}):\n{relevant}")
                sources.append({"title": content.title, "url": content.url})
        
        # Combine into web context
        if relevant_parts:
            web_context = "\n\n---\n\n".join(relevant_parts)
            state["web_context"] = web_context
            state["sources"] = sources
            print(f"✅ ScraperAgent: Extracted content from {len(relevant_parts)} pages")
        else:
            state["web_context"] = ""
            state["sources"] = []
            print("   No relevant content found")
        
        return state
    
    async def coordinator_node(self, state: AgentState) -> AgentState:
        """Generate final response using coordinator."""
        print("🤖 CoordinatorAgent: Generating response...")
        
        llm = await get_llm()
        user_query = state["user_query"]
        web_context = state.get("web_context", "")
        sources = state.get("sources", [])
        
        # Build prompt with web context
        system_prompt = "You are a helpful AI assistant with access to web search."
        
        if web_context:
            system_prompt += f"""
{web_context}

IMPORTANT: 
- Use the information from the sources above to answer accurately
- Be accurate and cite when using specific facts
- If sources don't fully answer the question, say so
- If sources don't fully answer the question, say so
- DO NOT hallucinate or use internal knowledge that contradicts the sources
- DO NOT use tools (like 'get_weather') unless they are specifically relevant to the request. A URL is NOT a location.
"""
        elif state.get("search_performed"):
            system_prompt += """
IMPORTANT: 
- I searched the web for your query but found no relevant or recent information.
- DO NOT answer based on old internal knowledge if it might be outdated.
- Explicitly tell the user that no relevant information was found on the web.
- Be honest about the lack of information rather than providing a generic or off-topic answer.
"""
        # Fallback for direct scrape failure
        elif state.get("direct_scrape") and not web_context:
             system_prompt += """
IMPORTANT: 
- You attempted to access the specific URL provided by the user but extracted no content.
- This might be due to the site blocking scrapers or being inaccessible.
- Apologize and state that you could not read the content of the provided URL.
- DO NOT hallucinate the content.
"""

        # Add Memory Context
        memory_context = state.get("memory_context", "")
        if memory_context:
            system_prompt += f"\n\n{memory_context}\n"
            
        # Add Tools
        tools = tool_registry.list_tools()
        if tools:
            tools_json = json.dumps(tools, indent=2)
            system_prompt += f"""
\n\nAVAILABLE TOOLS:
You have access to the following tools. If you need to use one, output a JSON block like:
```json
{{
    "tool": "tool_name",
    "arguments": {{ "arg1": "value" }}
}}
```

Tools Definition:
{tools_json}
"""

        # Add instructions to avoid tool hallucination
        system_prompt += """
IMPORTANT TOOL USAGE RULES:
- Only use a tool if it matches the user's intent perfectly.
- "get_weather" requires a CITY name and is for weather ONLY. It cannot be used for URLs.
- If unsure, do not use any tool.
"""
        
        # Generate response
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        input_messages = state.get("messages", [])
        
        # Sanitize messages for Ollama (ensure explicit list of dicts)
        for msg in input_messages:
            # Handle LangChain objects if present (Duck typing)
            if hasattr(msg, "type") and hasattr(msg, "content"):
                role = "user"
                if msg.type == "human": role = "user"
                elif msg.type == "ai": role = "assistant"
                elif msg.type == "system": role = "system"
                messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                 messages.append({
                     "role": msg.get("role", "user"),
                     "content": msg.get("content", "")
                 })
            else:
                # Fallback
                messages.append({"role": "user", "content": str(msg)})

        print(f"DEBUG: Messages prepared for LLM: {len(messages)}")
        
        # Prepare for streaming - do NOT run chat here
        state["final_messages"] = messages
        
        return state
    
    def should_search(self, state: AgentState) -> Literal["search", "scrape", "coordinator"]:
        """Route to search or directly to coordinator."""
        if state.get("direct_scrape", False):
            return "scrape"
        return "search" if state.get("needs_search", False) else "coordinator"
    
    def build_graph(self) -> StateGraph:
        """Build and compile the LangGraph workflow."""
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("router", self.router_node)
        workflow.add_node("search", self.search_node)
        workflow.add_node("scrape", self.scrape_node)
        workflow.add_node("coordinator", self.coordinator_node)
        
        # Set entry point
        workflow.set_entry_point("retrieve")
        
        # Edge from retrieve to router
        workflow.add_edge("retrieve", "router")
        
        # Add conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self.should_search,
            {
                "search": "search",
                "scrape": "scrape",
                "coordinator": "coordinator"
            }
        )
        
        # Linear flow: search -> scrape -> coordinator
        workflow.add_edge("search", "scrape")
        workflow.add_edge("scrape", "coordinator")
        
        # End after coordinator
        workflow.add_edge("coordinator", END)
        
        # Compile
        self.graph = workflow.compile()
        return self.graph
    
    async def run(self, session_id: str, user_query: str, messages: List[dict] = None) -> str:
        """Run the workflow and return final response.
        
        Args:
            session_id: Chat session ID
            user_query: User's question
            messages: Conversation history
            
        Returns:
            Final response
        """
        if self.graph is None:
            self.build_graph()
        
        # Initial state
        initial_state = AgentState(
            messages=messages or [],
            session_id=session_id,
            user_query=user_query
        )
        
        # Run workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state.get("final_response", "I couldn't generate a response.")
    
    async def stream(self, session_id: str, user_query: str, messages: List[dict] = None):
        """Stream workflow execution.
        
        Yields:
            Updates from each node
        """
        if self.graph is None:
            self.build_graph()
        
        # Initial state
        initial_state = AgentState(
            messages=messages or [],
            session_id=session_id,
            user_query=user_query
        )
        
        # Stream workflow
        async for event in self.graph.astream(initial_state):
            yield event


# Singleton instance
_workflow = None

def get_workflow() -> MaskWorkflow:
    """Get singleton workflow instance."""
    global _workflow
    if _workflow is None:
        _workflow = MaskWorkflow()
        _workflow.build_graph()
    return _workflow
