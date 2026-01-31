"""LangGraph workflow for orchestrating search, scraping, and coordination."""

from langgraph.graph import StateGraph, END
from typing import Literal, List, Optional
from src.core.graph.state import AgentState
from src.core.agents.search_agent import get_search_agent
from src.core.agents.scraper_agent import get_scraper_agent
from src.core.llm.ollama_client import get_llm


class MaskWorkflow:
    """LangGraph workflow for multi-agent orchestration."""
    
    def __init__(self):
        self.graph = None
    
    async def router_node(self, state: AgentState) -> AgentState:
        """Determine if web search is needed."""
        print("🔀 Router: Analyzing query...")
        
        search_agent = await get_search_agent()
        user_query = state["user_query"]
        
        # Check if search is needed
        needs_search = await search_agent.should_search(user_query, state.get("messages", []))
        
        state["needs_search"] = needs_search
        
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
        scraped = await scraper_agent.scrape_multiple(urls, max_urls=3)
        state["scraped_content"] = scraped
        
        # Extract relevant content
        user_query = state["user_query"]
        relevant_parts = []
        sources = []
        
        for content in scraped:
            if content.error:
                print(f"   Error scraping {content.url}: {content.error}")
                continue
            
            # Extract relevant parts
            relevant = await scraper_agent.extract_relevant_content(content, user_query)
            if relevant and "no relevant" not in relevant.lower():
                relevant_parts.append(f"From {content.title}:\n{relevant}")
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
- DO NOT hallucinate or use internal knowledge that contradicts the sources
"""
        elif state.get("search_performed"):
            system_prompt += """
IMPORTANT: 
- I searched the web for your query but found no relevant or recent information.
- DO NOT answer based on old internal knowledge if it might be outdated.
- Explicitly tell the user that no relevant information was found on the web.
- Be honest about the lack of information rather than providing a generic or off-topic answer.
"""
        
        # Generate response
        # Generate response
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (excluding the last user message which is separate in user_query? 
        # Actually state["messages"] includes the full history + current user message if we appended it in coordinator.
        # Let's check enhanced_coordinator.py: history.append({"role": "user", "content": user_input})
        # So state["messages"] has EVERYTHING.
        # But wait, we shouldn't duplicate the system prompt if it's already in history?
        # The history passed from enhanced_coordinator might have a system prompt for Project Context.
        # Let's just append the history messages after our new system prompt.
        
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
                 # Filter out system messages if we already added ours?
                 # Let's keep them but ensure format
                 messages.append({
                     "role": msg.get("role", "user"),
                     "content": msg.get("content", "")
                 })
            else:
                # Fallback
                messages.append({"role": "user", "content": str(msg)})

        print(f"DEBUG: Messages sent to LLM: {len(messages)}")
        
        response_msg = await llm.chat(messages)
        response = response_msg.get("content", "")
        
        # Add source citations if available
        if sources:
            citations = "\n\n**Sources:**\n" + "\n".join([
                f"- [{s['title']}]({s['url']})" for s in sources
            ])
            response += citations
        
        state["final_response"] = response
        print("✅ CoordinatorAgent: Response generated")
        
        return state
    
    def should_search(self, state: AgentState) -> Literal["search", "coordinator"]:
        """Route to search or directly to coordinator."""
        return "search" if state.get("needs_search", False) else "coordinator"
    
    def build_graph(self) -> StateGraph:
        """Build and compile the LangGraph workflow."""
        
        # Create graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("router", self.router_node)
        workflow.add_node("search", self.search_node)
        workflow.add_node("scrape", self.scrape_node)
        workflow.add_node("coordinator", self.coordinator_node)
        
        # Set entry point
        workflow.set_entry_point("router")
        
        # Add conditional edges from router
        workflow.add_conditional_edges(
            "router",
            self.should_search,
            {
                "search": "search",
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
