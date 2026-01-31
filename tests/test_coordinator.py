"""Tests for Coordinator Agents."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from src.core.agents.coordinator import CoordinatorAgent, coordinator
from src.core.agents.enhanced_coordinator import EnhancedCoordinator, enhanced_coordinator
from src.core.config import settings


class TestCoordinatorAgent:
    """Test cases for CoordinatorAgent."""

    def test_initialization(self):
        """Test CoordinatorAgent initialization."""
        agent = CoordinatorAgent()
        assert "Coordinator Agent" in agent.system_prompt
        assert "tools" in agent.system_prompt.lower()

    @pytest.mark.asyncio
    async def test_run_stream_direct_response(self):
        """Test run_stream with direct response (no tools)."""
        agent = CoordinatorAgent()

        with patch('src.core.agents.coordinator.memory_manager') as mock_memory:
            mock_memory.get_session = Mock(return_value=None)
            mock_memory.get_messages = Mock(return_value=[])
            mock_memory.add_message = Mock()
            mock_memory.add_message_async = AsyncMock()

            with patch('src.core.agents.coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
                mock_llm = AsyncMock()
                # Simulate streaming response
                async def mock_stream(*args, **kwargs):
                    for chunk in [{"content": "Hello "}, {"content": "world"}]:
                        yield chunk

                mock_llm.chat_stream = mock_stream
                mock_get_llm.return_value = mock_llm

                with patch('src.core.agents.coordinator.tool_registry') as mock_registry:
                    mock_registry.list_tools = Mock(return_value=[])

                    chunks = []
                    async for chunk in agent.run_stream("session-123", "Hi there"):
                        chunks.append(chunk)

                    assert "".join(chunks) == "Hello world"

    @pytest.mark.asyncio
    async def test_run_stream_with_tool_call(self):
        """Test run_stream with tool execution."""
        agent = CoordinatorAgent()

        with patch('src.core.agents.coordinator.memory_manager') as mock_memory:
            mock_memory.get_session = Mock(return_value=None)
            mock_memory.get_messages = Mock(return_value=[])
            mock_memory.add_message = Mock()
            mock_memory.add_message_async = AsyncMock()

            with patch('src.core.agents.coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
                mock_llm = AsyncMock()

                # First response is tool call, second is final response
                responses = [
                    [{"content": '{"tool": "test_tool", "arguments": {"arg": "val"}}'}],
                    [{"content": "Tool result processed"}]
                ]
                response_iter = iter(responses)

                async def mock_stream(*args, **kwargs):
                    for chunk in next(response_iter):
                        yield chunk

                mock_llm.chat_stream = mock_stream
                mock_get_llm.return_value = mock_llm

                with patch('src.core.agents.coordinator.tool_registry') as mock_registry:
                    mock_registry.list_tools = Mock(return_value=[])
                    mock_registry.call_tool = AsyncMock(return_value="tool output")

                    chunks = []
                    async for chunk in agent.run_stream("session-123", "Use tool"):
                        chunks.append(chunk)

                    # Tool results shouldn't be streamed directly
                    mock_registry.call_tool.assert_called_once_with("test_tool", {"arg": "val"})

    @pytest.mark.asyncio
    async def test_run_stream_with_project_context(self):
        """Test run_stream includes project context."""
        agent = CoordinatorAgent()

        mock_session = Mock()
        mock_session.project_id = "project-123"

        mock_project = Mock()
        mock_project.context_summary = "Project about AI development"

        with patch('src.core.agents.coordinator.memory_manager') as mock_memory:
            mock_memory.get_session = Mock(return_value=mock_session)
            mock_memory.get_project = Mock(return_value=mock_project)
            mock_memory.get_messages = Mock(return_value=[])
            mock_memory.add_message = Mock()
            mock_memory.add_message_async = AsyncMock()

            with patch('src.core.agents.coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
                mock_llm = AsyncMock()

                async def mock_stream(*args, **kwargs):
                    # Verify project context is in system prompt
                    messages = args[0]
                    system_msg = messages[0]["content"]
                    assert "PROJECT CONTEXT" in system_msg
                    assert "AI development" in system_msg
                    yield {"content": "Response"}

                mock_llm.chat_stream = mock_stream
                mock_get_llm.return_value = mock_llm

                with patch('src.core.agents.coordinator.tool_registry') as mock_registry:
                    mock_registry.list_tools = Mock(return_value=[])

                    async for _ in agent.run_stream("session-123", "Hi"):
                        pass

    @pytest.mark.asyncio
    async def test_run_stream_summarizes_long_history(self):
        """Test that long history is summarized."""
        agent = CoordinatorAgent()

        # Create history that exceeds MAX_HISTORY_TOKENS
        long_content = "A" * int(settings.MAX_HISTORY_TOKENS * 5)  # ~5x the limit

        mock_messages = [
            Mock(role="user", content=long_content)
        ]

        with patch('src.core.agents.coordinator.memory_manager') as mock_memory:
            mock_memory.get_session = Mock(return_value=None)
            mock_memory.get_messages = Mock(return_value=mock_messages)
            mock_memory.update_messages = Mock()
            mock_memory.add_message = Mock()
            mock_memory.add_message_async = AsyncMock()

            with patch('src.core.agents.coordinator.summarizer') as mock_summarizer:
                mock_summarizer.summarize = AsyncMock(return_value="Summary of long conversation")

                with patch('src.core.agents.coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
                    mock_llm = AsyncMock()

                    async def mock_stream(*args, **kwargs):
                        yield {"content": "Response"}

                    mock_llm.chat_stream = mock_stream
                    mock_get_llm.return_value = mock_llm

                    with patch('src.core.agents.coordinator.tool_registry') as mock_registry:
                        mock_registry.list_tools = Mock(return_value=[])

                        async for _ in agent.run_stream("session-123", "Hi"):
                            pass

                        # Verify summarization was called
                        mock_summarizer.summarize.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_stream_handles_tool_error(self):
        """Test handling of tool execution errors."""
        agent = CoordinatorAgent()

        with patch('src.core.agents.coordinator.memory_manager') as mock_memory:
            mock_memory.get_session = Mock(return_value=None)
            mock_memory.get_messages = Mock(return_value=[])
            mock_memory.add_message = Mock()
            mock_memory.add_message_async = AsyncMock()

            with patch('src.core.agents.coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
                mock_llm = AsyncMock()

                responses = [
                    [{"content": '{"tool": "bad_tool", "arguments": {}}'}],
                    [{"content": "Error handled"}]
                ]
                response_iter = iter(responses)

                async def mock_stream(*args, **kwargs):
                    for chunk in next(response_iter):
                        yield chunk

                mock_llm.chat_stream = mock_stream
                mock_get_llm.return_value = mock_llm

                with patch('src.core.agents.coordinator.tool_registry') as mock_registry:
                    mock_registry.list_tools = Mock(return_value=[])
                    mock_registry.call_tool = AsyncMock(side_effect=Exception("Tool error"))

                    chunks = []
                    async for chunk in agent.run_stream("session-123", "Hi"):
                        chunks.append(chunk)

                    # Error should be handled gracefully
                    assert mock_registry.call_tool.called

    @pytest.mark.asyncio
    async def test_run_stream_handles_invalid_json(self):
        """Test handling of invalid JSON tool calls."""
        agent = CoordinatorAgent()

        with patch('src.core.agents.coordinator.memory_manager') as mock_memory:
            mock_memory.get_session = Mock(return_value=None)
            mock_memory.get_messages = Mock(return_value=[])
            mock_memory.add_message = Mock()
            mock_memory.add_message_async = AsyncMock()

            with patch('src.core.agents.coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
                mock_llm = AsyncMock()

                async def mock_stream(*args, **kwargs):
                    # Looks like JSON but isn't valid
                    yield {"content": '{invalid json'}

                mock_llm.chat_stream = mock_stream
                mock_get_llm.return_value = mock_llm

                with patch('src.core.agents.coordinator.tool_registry') as mock_registry:
                    mock_registry.list_tools = Mock(return_value=[])

                    chunks = []
                    async for chunk in agent.run_stream("session-123", "Hi"):
                        chunks.append(chunk)

                    # Should treat as text and not call tools
                    assert "".join(chunks) == '{invalid json'


class TestEnhancedCoordinator:
    """Test cases for EnhancedCoordinator."""

    def test_initialization(self):
        """Test EnhancedCoordinator initialization."""
        with patch('src.core.agents.enhanced_coordinator.get_workflow') as mock_get_workflow:
            coordinator = EnhancedCoordinator()
            assert coordinator.workflow is mock_get_workflow.return_value

    @pytest.mark.asyncio
    async def test_run_stream_with_workflow(self):
        """Test run_stream with LangGraph workflow."""
        with patch('src.core.agents.enhanced_coordinator.get_workflow') as mock_get_workflow:
            mock_workflow = Mock()
            # Use Mock instead of AsyncMock for stream because it returns an async iterator directly
            async def mock_stream_fn(*args, **kwargs):
                for item in [
                    {"router": {"needs_search": True}},
                    {"search": {"search_results": []}},
                    {"scrape": {"scraped_content": []}},
                    {"coordinator": {"final_response": "Final answer"}}
                ]:
                    yield item
            mock_workflow.stream = mock_stream_fn
            mock_get_workflow.return_value = mock_workflow

            coordinator = EnhancedCoordinator()

            with patch('src.core.agents.enhanced_coordinator.memory_manager') as mock_memory:
                mock_memory.get_session = Mock(return_value=None)
                mock_memory.get_messages = Mock(return_value=[])
                mock_memory.add_message = Mock()
                mock_memory.add_message_async = AsyncMock()

                chunks = []
                async for chunk in coordinator.run_stream("session-123", "Test query"):
                    chunks.append(chunk)

                full_response = "".join(chunks)
                assert "Final answer" in full_response

    @pytest.mark.asyncio
    async def test_run_stream_saves_response(self):
        """Test that final response is saved to memory."""
        with patch('src.core.agents.enhanced_coordinator.get_workflow') as mock_get_workflow:
            mock_workflow = Mock()
            async def mock_stream_fn(*args, **kwargs):
                yield {"coordinator": {"final_response": "The answer is 42"}}
            mock_workflow.stream = mock_stream_fn
            mock_get_workflow.return_value = mock_workflow

            coordinator = EnhancedCoordinator()

            with patch('src.core.agents.enhanced_coordinator.memory_manager') as mock_memory:
                mock_memory.get_session = Mock(return_value=None)
                mock_memory.get_messages = Mock(return_value=[])
                mock_memory.add_message = Mock()
                mock_memory.add_message_async = AsyncMock()

                async for _ in coordinator.run_stream("session-123", "Test"):
                    pass

                # Verify response was saved
                mock_memory.add_message_async.assert_called_with("session-123", "assistant", "The answer is 42")

    @pytest.mark.asyncio
    async def test_run_stream_with_user_profile(self):
        """Test run_stream includes user profile."""
        with patch('src.core.agents.enhanced_coordinator.get_workflow') as mock_get_workflow:
            mock_workflow = Mock()
            async def mock_stream_fn(*args, **kwargs):
                yield {"coordinator": {"final_response": "Response"}}
            mock_workflow.stream = mock_stream_fn
            mock_get_workflow.return_value = mock_workflow

            coordinator = EnhancedCoordinator()

            with patch('src.core.agents.enhanced_coordinator.memory_manager') as mock_memory:
                mock_memory.get_session = Mock(return_value=None)
                mock_memory.get_messages = Mock(return_value=[])
                mock_memory.add_message = Mock()
                mock_memory.add_message_async = AsyncMock()

                with patch('src.core.agents.enhanced_coordinator.user_profile_manager') as mock_profile:
                    mock_profile.get_profile = Mock(return_value="User: John, Developer")
                    mock_profile.update_profile = AsyncMock()

                    with patch('src.core.agents.enhanced_coordinator.asyncio'):
                        async for _ in coordinator.run_stream("session-123", "Test"):
                            pass

                        # Verify profile was retrieved
                        mock_profile.get_profile.assert_called_once()


class TestCoordinatorSingletons:
    """Test cases for coordinator singletons."""

    def test_coordinator_singleton(self):
        """Test that coordinator singleton exists."""
        assert isinstance(coordinator, CoordinatorAgent)

    def test_enhanced_coordinator_singleton(self):
        """Test that enhanced_coordinator singleton exists."""
        assert isinstance(enhanced_coordinator, EnhancedCoordinator)
