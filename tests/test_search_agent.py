"""Tests for Search Agent."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.core.agents.search_agent import SearchAgent, SearchResult, get_search_agent


class TestSearchResult:
    """Test cases for SearchResult model."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet"
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"


class TestSearchAgent:
    """Test cases for SearchAgent."""

    def test_agent_initialization(self):
        """Test SearchAgent initialization."""
        agent = SearchAgent()
        assert hasattr(agent, 'ddgs')

    @pytest.mark.asyncio
    async def test_should_search_returns_true_for_current_events(self):
        """Test that should_search returns True for current events queries."""
        agent = SearchAgent()

        mock_llm_response = {"content": "YES"}

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value=mock_llm_response)
            mock_get_llm.return_value = mock_llm

            result = await agent.should_search("Who won the latest Super Bowl?")
            assert result is True

    @pytest.mark.asyncio
    async def test_should_search_returns_false_for_general_knowledge(self):
        """Test that should_search returns False for general knowledge."""
        agent = SearchAgent()

        mock_llm_response = {"content": "NO"}

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value=mock_llm_response)
            mock_get_llm.return_value = mock_llm

            result = await agent.should_search("What is Python?")
            assert result is False

    @pytest.mark.asyncio
    async def test_should_search_defaults_false_on_error(self):
        """Test that should_search defaults to False on LLM error."""
        agent = SearchAgent()

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(side_effect=Exception("LLM error"))
            mock_get_llm.return_value = mock_llm

            result = await agent.should_search("Test query")
            assert result is False

    @pytest.mark.asyncio
    async def test_should_search_yes_in_response(self):
        """Test that should_search detects YES in response."""
        agent = SearchAgent()

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "Yes, search needed"})
            mock_get_llm.return_value = mock_llm

            result = await agent.should_search("Test")
            assert result is True

    @pytest.mark.asyncio
    async def test_extract_search_queries(self):
        """Test extraction of search queries from user query."""
        agent = SearchAgent()

        llm_response = """1. query one
2. query two
3. query three"""

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": llm_response})
            mock_get_llm.return_value = mock_llm

            queries = await agent.extract_search_queries("Test question")

            assert len(queries) == 3
            assert "query one" in queries
            assert "query two" in queries
            assert "query three" in queries

    @pytest.mark.asyncio
    async def test_extract_search_queries_dash_format(self):
        """Test extraction with dash format."""
        agent = SearchAgent()

        llm_response = """- first query
- second query"""

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": llm_response})
            mock_get_llm.return_value = mock_llm

            queries = await agent.extract_search_queries("Test")

            assert len(queries) == 2
            assert "first query" in queries

    @pytest.mark.asyncio
    async def test_extract_search_queries_fallback(self):
        """Test fallback to original query on parsing failure."""
        agent = SearchAgent()

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "invalid format"})
            mock_get_llm.return_value = mock_llm

            queries = await agent.extract_search_queries("Original query")

            assert queries == ["Original query"]

    @pytest.mark.asyncio
    async def test_extract_search_queries_error_fallback(self):
        """Test fallback on LLM error."""
        agent = SearchAgent()

        with patch('src.core.agents.search_agent.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(side_effect=Exception("LLM error"))
            mock_get_llm.return_value = mock_llm

            queries = await agent.extract_search_queries("Original query")

            assert queries == ["Original query"]

    @pytest.mark.asyncio
    async def test_search_success(self, mock_search_results):
        """Test successful search."""
        agent = SearchAgent()
        agent.ddgs = Mock()
        agent.ddgs.text = Mock(return_value=mock_search_results)

        results = await agent.search("test query", max_results=2)

        assert len(results) == 2
        assert results[0].title == "Test Result 1"
        assert results[0].url == "https://example.com/1"
        assert results[1].title == "Test Result 2"
        agent.ddgs.text.assert_called_once_with("test query", max_results=2)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no results."""
        agent = SearchAgent()
        agent.ddgs = Mock()
        agent.ddgs.text = Mock(return_value=[])

        results = await agent.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_error(self):
        """Test search handling errors."""
        agent = SearchAgent()
        agent.ddgs = Mock()
        agent.ddgs.text = Mock(side_effect=Exception("Search error"))

        results = await agent.search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_multiple_queries(self, mock_search_results):
        """Test searching multiple queries."""
        agent = SearchAgent()
        agent.ddgs = Mock()
        agent.ddgs.text = Mock(return_value=mock_search_results[:1])

        queries = ["query 1", "query 2"]
        results = await agent.search_multiple(queries, max_results_per_query=1)

        assert len(results) == 1  # Same results deduplicated
        assert agent.ddgs.text.call_count == 2

    @pytest.mark.asyncio
    async def test_search_multiple_deduplicates(self):
        """Test that search_multiple deduplicates by URL."""
        agent = SearchAgent()
        agent.ddgs = Mock()
        # Return same URL for different queries
        agent.ddgs.text = Mock(return_value=[{
            "title": "Result",
            "href": "https://same.com",
            "body": "Content"
        }])

        queries = ["query 1", "query 2"]
        results = await agent.search_multiple(queries, max_results_per_query=1)

        assert len(results) == 1  # Deduplicated


class TestGetSearchAgent:
    """Test cases for get_search_agent function."""

    @pytest.mark.asyncio
    async def test_get_search_agent_singleton(self):
        """Test that get_search_agent returns singleton."""
        agent1 = await get_search_agent()
        agent2 = await get_search_agent()
        assert agent1 is agent2

    @pytest.mark.asyncio
    async def test_get_search_agent_returns_search_agent(self):
        """Test that get_search_agent returns SearchAgent instance."""
        agent = await get_search_agent()
        assert isinstance(agent, SearchAgent)
