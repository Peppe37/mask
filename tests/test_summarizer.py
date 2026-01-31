"""Tests for Summarizer Agent."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.agents.summarizer import SummarizerAgent, summarizer


class TestSummarizerAgent:
    """Test cases for SummarizerAgent."""

    def test_agent_initialization(self):
        """Test SummarizerAgent initialization."""
        agent = SummarizerAgent()
        assert "summarize" in agent.system_prompt.lower()
        assert "concise" in agent.system_prompt.lower()

    @pytest.mark.asyncio
    async def test_summarize_success(self):
        """Test successful summarization."""
        agent = SummarizerAgent()

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]

        with patch('src.core.agents.summarizer.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Conversation summary: greeting exchange")
            mock_get_llm.return_value = mock_llm

            result = await agent.summarize(history)

            assert result == "Conversation summary: greeting exchange"
            mock_llm.generate.assert_called_once()

            # Check prompt contains conversation
            call_args = mock_llm.generate.call_args
            assert "user: Hello" in call_args[0][0]
            assert "assistant: Hi there!" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_summarize_empty_history(self):
        """Test summarization with empty history."""
        agent = SummarizerAgent()

        with patch('src.core.agents.summarizer.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Empty conversation")
            mock_get_llm.return_value = mock_llm

            result = await agent.summarize([])

            assert result == "Empty conversation"

    @pytest.mark.asyncio
    async def test_summarize_uses_system_prompt(self):
        """Test that summarization uses correct system prompt."""
        agent = SummarizerAgent()

        with patch('src.core.agents.summarizer.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Summary")
            mock_get_llm.return_value = mock_llm

            await agent.summarize([{"role": "user", "content": "Hi"}])

            call_args = mock_llm.generate.call_args
            assert call_args[1]["system"] == agent.system_prompt

    @pytest.mark.asyncio
    async def test_summarize_uses_low_temperature(self):
        """Test that summarization uses low temperature for consistency."""
        agent = SummarizerAgent()

        with patch('src.core.agents.summarizer.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Summary")
            mock_get_llm.return_value = mock_llm

            await agent.summarize([{"role": "user", "content": "Hi"}])

            call_args = mock_llm.generate.call_args
            assert call_args[1]["options"]["temperature"] == 0.3


class TestSummarizerSingleton:
    """Test cases for summarizer singleton."""

    def test_singleton_exists(self):
        """Test that summarizer singleton exists."""
        assert isinstance(summarizer, SummarizerAgent)
