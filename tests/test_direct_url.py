
import pytest
from unittest.mock import AsyncMock, patch
from src.core.graph.workflow import MaskWorkflow, AgentState

@pytest.mark.asyncio
async def test_direct_url_routing():
    """Test that a query with a URL routes directly to scrape."""
    workflow = MaskWorkflow()
    
    # Mock components
    with patch('src.core.graph.workflow.get_search_agent') as mock_get_search, \
         patch('src.core.graph.workflow.get_scraper_agent') as mock_get_scraper, \
         patch('src.core.graph.workflow.get_llm') as mock_get_llm:
        
        # Scraper mock
        mock_scraper = AsyncMock()
        mock_scraper.crawl.return_value = []
        mock_scraper.scrape_url.return_value = AsyncMock(error=None, content="Scraped content", title="Test Page")
        mock_scraper.extract_relevant_content.return_value = "Relevant info"
        mock_get_scraper.return_value = mock_scraper
        
        # Router State
        state = AgentState(
            session_id="test",
            user_query="Analyze this site https://example.com/docs",
            messages=[]
        )
        
        # 1. Test Router Node Logic
        new_state = await workflow.router_node(state)
        
        assert new_state["direct_scrape"] is True
        assert new_state["needs_search"] is False
        assert "https://example.com/docs" in new_state["urls_to_scrape"]
        
        # 2. Test Direct Routing Edge
        route = workflow.should_search(new_state)
        assert route == "scrape"
        
        # 3. Test Scrape Node Logic (should use urls_to_scrape)
        scraped_state = await workflow.scrape_node(new_state)
        # Should verify crawl is called because it contains "docs"
        mock_scraper.crawl.assert_called() 
        
