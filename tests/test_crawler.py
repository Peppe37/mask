import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.core.agents.scraper_agent import ScraperAgent, ScrapedContent

class TestCrawler:
    @pytest.mark.asyncio
    async def test_crawl_follows_links(self):
        """Test that crawler follows links to the next level."""
        agent = ScraperAgent()
        
        # Mock responses
        # Page 1 links to Page 2
        # Page 2 has no links
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            async def get_side_effect(url):
                mock_resp = Mock()
                mock_resp.raise_for_status = Mock()
                if url == "http://example.com/":
                    mock_resp.text = '<html><body><a href="/page2">Page 2</a></body></html>'
                elif url == "http://example.com/page2":
                    mock_resp.text = '<html><body><h1>Page 2 Content</h1></body></html>'
                else:
                    mock_resp.text = ""
                return mock_resp
            
            mock_client.get = AsyncMock(side_effect=get_side_effect)
            
            results = await agent.crawl("http://example.com/", max_depth=2, max_pages=5)
            
            assert len(results) == 2
            urls = [r.url for r in results]
            assert "http://example.com/" in urls
            assert "http://example.com/page2" in urls

    @pytest.mark.asyncio
    async def test_crawl_depth_limit(self):
        """Test that crawler respects max_depth."""
        agent = ScraperAgent()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            async def get_side_effect(url):
                mock_resp = Mock()
                mock_resp.raise_for_status = Mock()
                # Chain of links: p1 -> p2 -> p3 -> p4
                current_num = 1
                if url != "http://example.com/":
                    current_num = int(url.split("page")[-1])
                
                next_page = f"/page{current_num + 1}"
                mock_resp.text = f'<html><body><a href="{next_page}">Next</a></body></html>'
                return mock_resp
            
            mock_client.get = AsyncMock(side_effect=get_side_effect)
            
            # Depth 1 means start page (depth 0) + 1 level of links
            results = await agent.crawl("http://example.com/", max_depth=1, max_pages=10)
            
            # Should have http://example.com/ (depth 0) and http://example.com/page2 (depth 1)
            # http://example.com/page2 links to page3, but that is depth 2, so it shouldn't be crawled
            
            assert len(results) == 2
            
    @pytest.mark.asyncio
    async def test_crawl_max_pages(self):
        """Test that crawler respects max_pages."""
        agent = ScraperAgent()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            async def get_side_effect(url):
                mock_resp = Mock()
                mock_resp.raise_for_status = Mock()
                # Fan out: page 1 links to p2, p3, p4, p5
                if url == "http://example.com/":
                    mock_resp.text = """
                    <html><body>
                        <a href="/page2">2</a>
                        <a href="/page3">3</a>
                        <a href="/page4">4</a>
                        <a href="/page5">5</a>
                    </body></html>
                    """
                else:
                    mock_resp.text = "<html>Content</html>"
                return mock_resp
            
            mock_client.get = AsyncMock(side_effect=get_side_effect)
            
            # Limit to 3 pages total
            results = await agent.crawl("http://example.com/", max_depth=2, max_pages=3)
            
            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_crawl_external_links_ignored(self):
        """Test that crawler ignores external links."""
        agent = ScraperAgent()
        
        with patch('httpx.AsyncClient') as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            
            async def get_side_effect(url):
                mock_resp = Mock()
                mock_resp.raise_for_status = Mock()
                if url == "http://example.com/":
                    mock_resp.text = """
                    <html><body>
                        <a href="/internal">Internal</a>
                        <a href="http://google.com">External</a>
                    </body></html>
                    """
                elif url == "http://example.com/internal":
                    mock_resp.text = "<html>Internal Content</html>"
                else:
                    # Should not be called for external
                    mock_resp.text = ""
                return mock_resp
            
            mock_client.get = AsyncMock(side_effect=get_side_effect)
            
            results = await agent.crawl("http://example.com/", max_depth=2, max_pages=10)
            
            urls = [r.url for r in results]
            assert "http://example.com/internal" in urls
            assert "http://google.com" not in urls
