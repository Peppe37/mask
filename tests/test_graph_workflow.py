"""Tests for LangGraph Workflow."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.core.graph.workflow import MaskWorkflow, get_workflow
from src.core.graph.state import AgentState
from src.core.agents.search_agent import SearchResult
from src.core.agents.scraper_agent import ScrapedContent


class TestAgentState:
    """Test cases for AgentState TypedDict."""

    def test_agent_state_creation(self, mock_agent_state):
        """Test AgentState creation."""
        state = AgentState(**mock_agent_state)
        assert state["session_id"] == mock_agent_state["session_id"]
        assert state["user_query"] == "Test query"
        assert state["messages"] == []

    def test_agent_state_optional_fields(self):
        """Test AgentState with only required fields."""
        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="test"
        )
        # Optional fields should be accessible
        assert "needs_search" not in state or state.get("needs_search") is None


class TestMaskWorkflow:
    """Test cases for MaskWorkflow."""

    def test_workflow_initialization(self):
        """Test MaskWorkflow initialization."""
        workflow = MaskWorkflow()
        assert workflow.graph is None

    @pytest.mark.asyncio
    async def test_router_node_needs_search(self):
        """Test router node when search is needed."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="What is the weather today?"
        )

        mock_agent = AsyncMock()
        mock_agent.should_search.return_value = True

        with patch('src.core.graph.workflow.get_search_agent', new_callable=AsyncMock) as mock_get_agent:
            mock_get_agent.return_value = mock_agent
            result = await workflow.router_node(state)

            assert result["needs_search"] is True

    @pytest.mark.asyncio
    async def test_router_node_no_search_needed(self):
        """Test router node when search is not needed."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="What is Python?"
        )

        mock_agent = AsyncMock()
        mock_agent.should_search.return_value = False

        with patch('src.core.graph.workflow.get_search_agent', new_callable=AsyncMock) as mock_get_agent:
            mock_get_agent.return_value = mock_agent
            result = await workflow.router_node(state)

            assert result["needs_search"] is False

    @pytest.mark.asyncio
    async def test_search_node(self):
        """Test search node."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="Test query",
            needs_search=True
        )

        mock_results = [
            SearchResult(title="Result 1", url="https://example.com/1", snippet="Snippet 1"),
            SearchResult(title="Result 2", url="https://example.com/2", snippet="Snippet 2")
        ]

        mock_agent = AsyncMock()
        mock_agent.extract_search_queries.return_value = ["query 1", "query 2"]
        mock_agent.search_multiple.return_value = mock_results

        # Patching an async function to return an AsyncMock
        with patch('src.core.graph.workflow.get_search_agent', new_callable=AsyncMock) as mock_get_agent:
            mock_get_agent.return_value = mock_agent
            result = await workflow.search_node(state)

            assert result["search_performed"] is True
            assert result["search_queries"] == ["query 1", "query 2"]
            assert len(result["search_results"]) == 2
            assert len(result["urls_to_scrape"]) == 2

    @pytest.mark.asyncio
    async def test_scrape_node(self):
        """Test scrape node."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="Test query",
            urls_to_scrape=["https://example.com/1", "https://example.com/2"]
        )

        mock_scraped = [
            ScrapedContent(url="https://example.com/1", title="Page 1", content="Content 1"),
            ScrapedContent(url="https://example.com/2", title="Page 2", content="Content 2")
        ]

        mock_agent = AsyncMock()
        mock_agent.scrape_multiple.return_value = mock_scraped
        mock_agent.extract_relevant_content.return_value = "Relevant content"

        with patch('src.core.graph.workflow.get_scraper_agent', new_callable=AsyncMock) as mock_get_agent:
            mock_get_agent.return_value = mock_agent
            result = await workflow.scrape_node(state)

            assert len(result["scraped_content"]) == 2
            assert result["web_context"]  # Should have content
            assert result["sources"]  # Should have sources

    @pytest.mark.asyncio
    async def test_scrape_node_no_urls(self):
        """Test scrape node with no URLs."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="Test query",
            urls_to_scrape=[]
        )

        mock_agent = AsyncMock()
        with patch('src.core.graph.workflow.get_scraper_agent', new_callable=AsyncMock) as mock_get_agent:
            mock_get_agent.return_value = mock_agent
            result = await workflow.scrape_node(state)

            assert result["scraped_content"] == []
            mock_agent.scrape_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_scrape_node_skips_errors(self):
        """Test that scrape node skips pages with errors."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[],
            session_id="test-id",
            user_query="Test query",
            urls_to_scrape=["https://example.com/1", "https://example.com/2"]
        )

        mock_scraped = [
            ScrapedContent(url="https://example.com/1", title="Page 1", content="Content 1"),
            ScrapedContent(url="https://example.com/2", title="Error", content="", error="Failed")
        ]

        mock_agent = AsyncMock()
        mock_agent.scrape_multiple.return_value = mock_scraped
        mock_agent.extract_relevant_content.return_value = "Relevant content"

        with patch('src.core.graph.workflow.get_scraper_agent', new_callable=AsyncMock) as mock_get_agent:
            mock_get_agent.return_value = mock_agent

            result = await workflow.scrape_node(state)

            # Should only extract from the successful scrape
            assert mock_agent.extract_relevant_content.call_count == 1

    @pytest.mark.asyncio
    async def test_coordinator_node_with_web_context(self):
        """Test coordinator node with web context."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[{"role": "user", "content": "Test query"}],
            session_id="test-id",
            user_query="Test query",
            web_context="Web context from sources",
            sources=[{"title": "Source 1", "url": "https://example.com"}]
        )

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {"content": "Generated response"}

        with patch('src.core.graph.workflow.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_get_llm.return_value = mock_llm
            result = await workflow.coordinator_node(state)

            assert "Generated response" in result["final_response"]
            assert "Source 1" in result["final_response"]
            assert "https://example.com" in result["final_response"]

    @pytest.mark.asyncio
    async def test_coordinator_node_search_found_nothing(self):
        """Test coordinator node when search was performed but returned no context."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[{"role": "user", "content": "Recent obscure event query"}],
            session_id="test-id",
            user_query="Recent obscure event query",
            search_performed=True,
            web_context="",
            sources=[]
        )

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {"content": "I couldn't find any recent information about this on the web."}

        with patch('src.core.graph.workflow.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_get_llm.return_value = mock_llm
            result = await workflow.coordinator_node(state)

            # Verify the response
            assert "couldn't find" in result["final_response"]
            
            # Verify system prompt content (debugging inspection of call args if needed, 
            # but here we just check that the LLM was called)
            mock_llm.chat.assert_called_once()
            messages = mock_llm.chat.call_args[0][0]
            system_msg = next(m for m in messages if m["role"] == "system")
            assert "searched the web" in system_msg["content"]
            assert "found no relevant" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_coordinator_node_without_web_context(self):
        """Test coordinator node without web context."""
        workflow = MaskWorkflow()

        state = AgentState(
            messages=[{"role": "user", "content": "Test query"}],
            session_id="test-id",
            user_query="Test query"
        )

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {"content": "Direct response"}

        with patch('src.core.graph.workflow.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_get_llm.return_value = mock_llm
            result = await workflow.coordinator_node(state)

            assert result["final_response"] == "Direct response"

    @pytest.mark.asyncio
    async def test_coordinator_node_sanitizes_messages(self):
        """Test that coordinator node sanitizes LangChain message objects."""
        workflow = MaskWorkflow()

        # Mock LangChain message-like objects
        class FakeMessage:
            def __init__(self, type_, content):
                self.type = type_
                self.content = content

        state = AgentState(
            messages=[
                FakeMessage("human", "User message"),
                FakeMessage("ai", "AI response"),
                {"role": "user", "content": "Dict message"}
            ],
            session_id="test-id",
            user_query="Test"
        )

        mock_llm = AsyncMock()
        mock_llm.chat.return_value = {"content": "Response"}

        with patch('src.core.graph.workflow.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_get_llm.return_value = mock_llm
            await workflow.coordinator_node(state)

            # Verify messages were sanitized and sent
            call_args = mock_llm.chat.call_args
            messages = call_args[0][0]

            # Should have system prompt + sanitized messages
            assert len(messages) > 1
            assert any(m["role"] == "user" and m["content"] == "User message" for m in messages)
            assert any(m["role"] == "assistant" and m["content"] == "AI response" for m in messages)

    def test_should_search_routing(self):
        """Test should_search routing logic."""
        workflow = MaskWorkflow()

        # When needs_search is True
        state_true = {"needs_search": True}
        assert workflow.should_search(state_true) == "search"

        # When needs_search is False
        state_false = {"needs_search": False}
        assert workflow.should_search(state_false) == "coordinator"

        # When needs_search is not set (defaults to False)
        state_empty = {}
        assert workflow.should_search(state_empty) == "coordinator"

    def test_build_graph(self):
        """Test graph building."""
        workflow = MaskWorkflow()

        # Mock StateGraph
        with patch('src.core.graph.workflow.StateGraph') as mock_graph_class:
            mock_graph = MagicMock()
            mock_graph.add_node = MagicMock()
            mock_graph.add_edge = MagicMock()
            mock_graph.add_conditional_edges = MagicMock()
            mock_graph.set_entry_point = MagicMock()
            mock_graph.compile = MagicMock(return_value=MagicMock())
            mock_graph_class.return_value = mock_graph

            result = workflow.build_graph()

            assert result is not None
            assert workflow.graph is not None
            mock_graph_class.assert_called_once_with(AgentState)
            assert mock_graph.add_node.call_count == 4  # router, search, scrape, coordinator
            mock_graph.compile.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_workflow(self):
        """Test running the complete workflow."""
        workflow = MaskWorkflow()

        # Mock compiled graph
        workflow.graph = AsyncMock()
        workflow.graph.ainvoke = AsyncMock(return_value={
            "final_response": "Complete response"
        })

        result = await workflow.run("session-id", "User query")

        assert result == "Complete response"
        workflow.graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_builds_graph_if_needed(self):
        """Test that run builds graph if not already built."""
        workflow = MaskWorkflow()

        with patch.object(workflow, 'build_graph') as mock_build:
            mock_graph = AsyncMock()
            mock_graph.ainvoke = AsyncMock(return_value={"final_response": "Response"})
            
            # Simulate build_graph setting self.graph
            def side_effect():
                workflow.graph = mock_graph
                return mock_graph
            
            mock_build.side_effect = side_effect

            await workflow.run("session-id", "Query")

            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_workflow(self):
        """Test streaming workflow execution."""
        workflow = MaskWorkflow()

        events = [
            {"router": {"needs_search": True}},
            {"search": {"search_results": []}},
            {"coordinator": {"final_response": "Response"}}
        ]

        workflow.graph = MagicMock()
        async def mock_stream_fn(*args, **kwargs):
            for event in events:
                yield event
        workflow.graph.astream = mock_stream_fn

        collected = []
        async for event in workflow.stream("session-id", "Query"):
            collected.append(event)

        assert len(collected) == 3


class TestGetWorkflow:
    """Test cases for get_workflow function."""

    def test_get_workflow_singleton(self):
        """Test that get_workflow returns singleton."""
        # Reset singleton for test
        import src.core.graph.workflow as workflow_module
        workflow_module._workflow = None

        workflow1 = get_workflow()
        workflow2 = get_workflow()
        assert workflow1 is workflow2

    def test_get_workflow_builds_graph(self):
        """Test that get_workflow builds graph on first call."""
        # Reset singleton for test
        import src.core.graph.workflow as workflow_module
        workflow_module._workflow = None

        with patch.object(MaskWorkflow, 'build_graph') as mock_build:
            mock_build.return_value = Mock()
            get_workflow()
            mock_build.assert_called_once()
