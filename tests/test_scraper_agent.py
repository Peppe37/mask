"""Tests for Scraper Agent."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
from bs4 import BeautifulSoup
from src.core.agents.scraper_agent import ScraperAgent, ScrapedContent, get_scraper_agent


class TestScrapedContent:
    """Test cases for ScrapedContent model."""

    def test_scraped_content_creation(self):
        """Test ScrapedContent creation."""
        content = ScrapedContent(
            url="https://example.com",
            title="Test Page",
            content="Page content"
        )
        assert content.url == "https://example.com"
        assert content.title == "Test Page"
        assert content.content == "Page content"
        assert content.error is None

    def test_scraped_content_with_error(self):
        """Test ScrapedContent with error."""
        content = ScrapedContent(
            url="https://example.com",
            title="Error",
            content="",
            error="Connection failed"
        )
        assert content.error == "Connection failed"


class TestScraperAgent:
    """Test cases for ScraperAgent."""

    def test_agent_initialization(self):
        """Test ScraperAgent initialization."""
        agent = ScraperAgent()
        assert agent.timeout == 10
        assert "User-Agent" in agent.headers

    @pytest.mark.asyncio
    async def test_scrape_url_success(self, mock_html_content):
        """Test successful URL scraping."""
        agent = ScraperAgent()

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = mock_html_content

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await agent.scrape_url("https://example.com")

            assert isinstance(result, ScrapedContent)
            assert result.url == "https://example.com"
            assert result.title == "Test Page"
            assert "Main Content" in result.content
            assert "Navigation items" not in result.content  # Nav removed
            assert "Footer content" not in result.content  # Footer removed
            assert result.error is None

    @pytest.mark.asyncio
    async def test_scrape_url_http_error(self):
        """Test handling of HTTP errors."""
        agent = ScraperAgent()

        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=httpx.Request("GET", "https://example.com/404"),
                response=httpx.Response(404, request=httpx.Request("GET", "https://example.com/404"))
            )
        )

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_async_client(*args, **kwargs):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            yield mock_client

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient', side_effect=mock_async_client):
            result = await agent.scrape_url("https://example.com/404")

            assert result.error == "HTTP 404"

    @pytest.mark.asyncio
    async def test_scrape_url_timeout(self):
        """Test handling of timeout."""
        agent = ScraperAgent()

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_async_client(*args, **kwargs):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("Timeout"))
            yield mock_client

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient', side_effect=mock_async_client):
            result = await agent.scrape_url("https://example.com")

            assert result.error == "Timeout"

    @pytest.mark.asyncio
    async def test_scrape_url_general_error(self):
        """Test handling of general errors."""
        agent = ScraperAgent()

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_async_client(*args, **kwargs):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            yield mock_client

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient', side_effect=mock_async_client):
            result = await agent.scrape_url("https://example.com")

            assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_scrape_url_no_content(self):
        """Test scraping page with no content."""
        agent = ScraperAgent()

        html = "<html><head><title>Empty</title></head></html>"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = html

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await agent.scrape_url("https://example.com")

            assert result.error == "Could not find content"

    @pytest.mark.asyncio
    async def test_scrape_url_truncates_long_content(self):
        """Test that long content is truncated."""
        agent = ScraperAgent()

        # Create HTML with very long content
        long_text = "A" * 15000
        html = f"<html><body><main>{long_text}</main></body></html>"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = html

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await agent.scrape_url("https://example.com")

            assert len(result.content) <= 10000 + len("...[truncated]")
            assert "...[truncated]" in result.content

    @pytest.mark.asyncio
    async def test_scrape_multiple(self, mock_html_content):
        """Test scraping multiple URLs."""
        agent = ScraperAgent()

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = mock_html_content

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            urls = ["https://example.com/1", "https://example.com/2"]
            results = await agent.scrape_multiple(urls, max_urls=2)

            assert len(results) == 2
            assert all(isinstance(r, ScrapedContent) for r in results)

    @pytest.mark.asyncio
    async def test_scrape_multiple_limits_urls(self, mock_html_content):
        """Test that scrape_multiple respects max_urls limit."""
        agent = ScraperAgent()

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = mock_html_content

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]
            results = await agent.scrape_multiple(urls, max_urls=2)

            assert len(results) == 2
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_scrape_multiple_handles_exceptions(self):
        """Test that scrape_multiple handles exceptions gracefully."""
        agent = ScraperAgent()

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_async_client(*args, **kwargs):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Error"))
            yield mock_client

        with patch('src.core.agents.scraper_agent.httpx.AsyncClient', side_effect=mock_async_client):

            urls = ["https://example.com/1"]
            results = await agent.scrape_multiple(urls)

            assert results == []  # Exceptions filtered out

    @pytest.mark.asyncio
    async def test_extract_relevant_content_success(self):
        """Test successful content extraction."""
        agent = ScraperAgent()

        scraped = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="Lots of content here about Python programming"
        )

        with patch('src.core.agents.scraper_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={
                "content": "This article discusses Python programming."
            })
            mock_get_llm.return_value = mock_llm

            result = await agent.extract_relevant_content(scraped, "Python programming")

            assert "Python" in result
            mock_llm.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_relevant_content_with_error(self):
        """Test extraction when scraped content has error."""
        agent = ScraperAgent()

        scraped = ScrapedContent(
            url="https://example.com",
            title="Error",
            content="",
            error="Failed"
        )

        result = await agent.extract_relevant_content(scraped, "query")
        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_relevant_content_empty(self):
        """Test extraction with empty content."""
        agent = ScraperAgent()

        scraped = ScrapedContent(
            url="https://example.com",
            title="Test",
            content=""
        )

        result = await agent.extract_relevant_content(scraped, "query")
        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_relevant_content_fallback(self):
        """Test fallback to raw content on LLM error."""
        agent = ScraperAgent()

        scraped = ScrapedContent(
            url="https://example.com",
            title="Test",
            content="A" * 2000  # Long content
        )

        with patch('src.core.agents.scraper_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(side_effect=Exception("LLM error"))
            mock_get_llm.return_value = mock_llm

            result = await agent.extract_relevant_content(scraped, "query")

            assert len(result) == 1000  # Fallback truncated content


class TestGetScraperAgent:
    """Test cases for get_scraper_agent function."""

    @pytest.mark.asyncio
    async def test_get_scraper_agent_singleton(self):
        """Test that get_scraper_agent returns singleton."""
        # Reset singleton for test
        import src.core.agents.scraper_agent as scraper_module
        scraper_module._scraper_agent = None

        agent1 = await get_scraper_agent()
        agent2 = await get_scraper_agent()
        assert agent1 is agent2

    @pytest.mark.asyncio
    async def test_get_scraper_agent_returns_scraper_agent(self):
        """Test that get_scraper_agent returns ScraperAgent instance."""
        # Reset singleton for test
        import src.core.agents.scraper_agent as scraper_module
        scraper_module._scraper_agent = None

        agent = await get_scraper_agent()
        assert isinstance(agent, ScraperAgent)
