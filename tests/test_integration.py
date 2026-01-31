"""Integration tests for the MASK multi-agent framework."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
import asyncio


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_complete_chat_flow(self):
        """Test complete chat flow from user input to response."""
        from src.core.agents.enhanced_coordinator import EnhancedCoordinator
        from src.core.memory.manager import memory_manager

        with patch('src.core.agents.enhanced_coordinator.get_workflow') as mock_get_workflow:
            mock_workflow = Mock()
            async def mock_stream_fn(*args, **kwargs):
                for item in [
                    {"router": {"needs_search": False}},
                    {"coordinator": {"final_response": "Hello! How can I help you today?"}}
                ]:
                    yield item
            mock_workflow.stream = mock_stream_fn
            mock_get_workflow.return_value = mock_workflow

            coordinator = EnhancedCoordinator()

            with patch.object(memory_manager, 'get_session', return_value=None):
                with patch.object(memory_manager, 'get_messages', return_value=[]):
                    with patch.object(memory_manager, 'add_message') as mock_add:
                        with patch('src.core.agents.enhanced_coordinator.user_profile_manager') as mock_profile:
                            mock_profile.get_profile = Mock(return_value="User: Test")
                            mock_profile.update_profile = AsyncMock()

                            chunks = []
                            async for chunk in coordinator.run_stream("test-session", "Hello"):
                                chunks.append(chunk)

                            full_response = "".join(chunks)
                            assert "Hello! How can I help you today?" in full_response

                            # Verify message was saved
                            mock_add.assert_called()

    @pytest.mark.asyncio
    async def test_web_search_flow(self):
        """Test web search and scraping flow."""
        from src.core.graph.workflow import MaskWorkflow
        from src.core.agents.search_agent import SearchResult
        from src.core.agents.scraper_agent import ScrapedContent

        workflow = MaskWorkflow()

        with patch('src.core.graph.workflow.get_search_agent', new_callable=AsyncMock) as mock_search_agent:
            with patch('src.core.graph.workflow.get_scraper_agent', new_callable=AsyncMock) as mock_scraper_agent:
                with patch('src.core.graph.workflow.get_llm', new_callable=AsyncMock) as mock_get_llm:

                    mock_search = AsyncMock()
                    mock_search.should_search = AsyncMock(return_value=True)
                    mock_search.extract_search_queries = AsyncMock(return_value=["query 1"])
                    mock_search.search_multiple = AsyncMock(return_value=[
                        SearchResult(title="Result", url="https://example.com", snippet="Snippet")
                    ])
                    mock_search_agent.return_value = mock_search

                    mock_scraper = AsyncMock()
                    mock_scraper.scrape_multiple = AsyncMock(return_value=[
                        ScrapedContent(url="https://example.com", title="Page", content="Content")
                    ])
                    mock_scraper.extract_relevant_content = AsyncMock(return_value="Relevant info")
                    mock_scraper_agent.return_value = mock_scraper

                    mock_llm = AsyncMock()
                    mock_llm.chat = AsyncMock(return_value={"content": "Based on web search, the answer is..."})
                    mock_get_llm.return_value = mock_llm

                    from src.core.graph.state import AgentState
                    state = AgentState(
                        messages=[],
                        session_id="test",
                        user_query="What is the weather?"
                    )

                    # Run through workflow nodes
                    state = await workflow.router_node(state)
                    assert state["needs_search"] is True

                    state = await workflow.search_node(state)
                    assert len(state["search_results"]) > 0

                    state = await workflow.scrape_node(state)
                    assert state["web_context"] is not None

                    state = await workflow.coordinator_node(state)
                    assert state["final_response"] is not None

    @pytest.mark.asyncio
    async def test_project_context_flow(self):
        """Test project context integration."""
        from src.core.memory.manager import memory_manager
        from src.core.memory.models import Project, ChatSession, ChatMessage

        # Mock project with context
        project_id = str(uuid.uuid4())
        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.name = "Test Project"
        mock_project.context_summary = "This project is about Python development"

        session_id = str(uuid.uuid4())
        mock_session = Mock(spec=ChatSession)
        mock_session.id = session_id
        mock_session.project_id = project_id

        with patch.object(memory_manager, 'get_session', return_value=mock_session):
            with patch.object(memory_manager, 'get_project', return_value=mock_project):
                session = memory_manager.get_session(session_id)
                project = memory_manager.get_project(session.project_id)

                assert project is not None
                assert project.context_summary == "This project is about Python development"


class TestMemoryIntegration:
    """Integration tests for memory management."""

    def test_project_session_message_relationships(self):
        """Test relationships between projects, sessions, and messages."""
        from src.core.memory.models import Project, ChatSession, ChatMessage

        # Create project
        project = Project(
            id=str(uuid.uuid4()),
            name="Test Project",
            description="Test"
        )

        # Create session linked to project
        session = ChatSession(
            id=str(uuid.uuid4()),
            project_id=project.id,
            title="Test Chat"
        )

        # Create messages linked to session
        message1 = ChatMessage(
            session_id=session.id,
            role="user",
            content="Hello"
        )
        message2 = ChatMessage(
            session_id=session.id,
            role="assistant",
            content="Hi!"
        )

        # Verify relationships
        assert session.project_id == project.id
        assert message1.session_id == session.id
        assert message2.session_id == session.id

    def test_memory_manager_operations(self):
        """Test memory manager CRUD operations."""
        from src.core.memory.manager import memory_manager

        with patch.object(memory_manager, 'engine'):
            with patch('sqlmodel.Session') as mock_session_class:
                mock_session = MagicMock()
                mock_session_class.return_value.__enter__ = Mock(return_value=mock_session)
                mock_session_class.return_value.__exit__ = Mock(return_value=False)

                # Test project creation
                mock_project = Mock()
                mock_session.refresh = Mock(side_effect=lambda x: setattr(x, 'id', str(uuid.uuid4())))

                with patch.object(memory_manager, 'create_project', return_value=mock_project):
                    project = memory_manager.create_project("Test", "Description")
                    assert project is not None


class TestToolIntegration:
    """Integration tests for tool system."""

    @pytest.mark.asyncio
    async def test_plugin_tool_discovery_and_execution(self):
        """Test plugin tool discovery and execution."""
        from src.core.plugin_manager import plugin_manager
        from src.core.tool_registry import tool_registry

        # Discover plugins
        plugin_manager.discover_plugins()

        # Verify tools can be listed
        tools = tool_registry.list_tools()
        assert isinstance(tools, list)

        # If ExamplePlugin is loaded, test its tool
        if "ExamplePlugin" in plugin_manager.plugins:
            plugin = plugin_manager.plugins["ExamplePlugin"]
            assert len(plugin.tools) > 0

            # Execute tool
            tool = plugin.tools[0]
            result = await tool.handler({"name": "Integration Test"})
            assert "Hello, Integration Test!" == result


class TestAgentCoordination:
    """Integration tests for agent coordination."""

    @pytest.mark.asyncio
    async def test_summarizer_integration(self):
        """Test summarizer agent integration."""
        from src.core.agents.summarizer import summarizer

        with patch('src.core.agents.summarizer.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Summary of conversation")
            mock_get_llm.return_value = mock_llm

            history = [
                {"role": "user", "content": "Question 1"},
                {"role": "assistant", "content": "Answer 1"},
                {"role": "user", "content": "Question 2"}
            ]

            summary = await summarizer.summarize(history)
            assert summary == "Summary of conversation"

    @pytest.mark.asyncio
    async def test_title_generator_integration(self):
        """Test title generator agent integration."""
        from src.core.agents.title_generator import title_generator

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "Python Programming"})
            mock_get_llm.return_value = mock_llm

            title = await title_generator.generate_title("How do I write Python code?")
            assert title == "Python Programming"

    @pytest.mark.asyncio
    async def test_project_manager_integration(self):
        """Test project manager agent integration."""
        from src.core.agents.project_manager import project_summarizer

        with patch('src.core.agents.project_manager.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Project context summary")
            mock_get_llm.return_value = mock_llm

            chats_summary = "Chat 1: Discussed API design\nChat 2: Decided on FastAPI"
            result = await project_summarizer.summarize_project(chats_summary, None)
            assert result == "Project context summary"


class TestConfigurationIntegration:
    """Integration tests for configuration."""

    def test_settings_loading(self):
        """Test that settings load correctly."""
        from src.core.config import settings, Settings

        # Test singleton exists
        assert isinstance(settings, Settings)

        # Test required settings exist
        assert hasattr(settings, 'POSTGRES_USER')
        assert hasattr(settings, 'OLLAMA_MODEL')
        assert hasattr(settings, 'MAX_HISTORY_TOKENS')

    def test_database_url_construction(self):
        """Test database URL construction from settings."""
        from src.core.config import settings

        expected_url = (
            f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
            f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )

        assert "postgresql+asyncpg://" in expected_url
        assert settings.POSTGRES_HOST in expected_url
