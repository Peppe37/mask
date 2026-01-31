"""Tests for Title Generator Agent."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.agents.title_generator import TitleGenerator, title_generator


class TestTitleGenerator:
    """Test cases for TitleGenerator."""

    @pytest.mark.asyncio
    async def test_generate_title_success(self):
        """Test successful title generation."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "Python Tutorial"})
            mock_get_llm.return_value = mock_llm

            result = await generator.generate_title("How do I learn Python programming?")

            assert result == "Python Tutorial"

    @pytest.mark.asyncio
    async def test_generate_title_strips_quotes(self):
        """Test that quotes are stripped from generated title."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": '"Python Tutorial"'})
            mock_get_llm.return_value = mock_llm

            result = await generator.generate_title("How do I learn Python programming?")

            assert result == "Python Tutorial"
            assert '"' not in result

    @pytest.mark.asyncio
    async def test_generate_title_fallback_on_empty(self):
        """Test fallback to truncated message on empty response."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": ""})
            mock_get_llm.return_value = mock_llm

            long_message = "A" * 100
            result = await generator.generate_title(long_message)

            assert len(result) <= 50
            assert "..." in result

    @pytest.mark.asyncio
    async def test_generate_title_fallback_on_long_response(self):
        """Test fallback when LLM returns title that's too long."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "A" * 100})  # Too long
            mock_get_llm.return_value = mock_llm

            short_message = "Short message"
            result = await generator.generate_title(short_message)

            assert result == short_message  # Fallback to original

    @pytest.mark.asyncio
    async def test_generate_title_fallback_on_error(self):
        """Test fallback to truncated message on LLM error."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(side_effect=Exception("LLM error"))
            mock_get_llm.return_value = mock_llm

            long_message = "A" * 100
            result = await generator.generate_title(long_message)

            assert len(result) <= 50
            assert "..." in result

    @pytest.mark.asyncio
    async def test_generate_title_short_message_no_truncate(self):
        """Test that short messages aren't truncated in fallback."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(side_effect=Exception("LLM error"))
            mock_get_llm.return_value = mock_llm

            short_message = "Short message"
            result = await generator.generate_title(short_message)

            assert result == short_message

    @pytest.mark.asyncio
    async def test_generate_title_uses_temperature(self):
        """Test that title generation uses correct temperature."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "Title"})
            mock_get_llm.return_value = mock_llm

            await generator.generate_title("Test message")

            call_args = mock_llm.chat.call_args
            assert call_args[1]["options"]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_generate_title_prompt_contains_message(self):
        """Test that prompt contains the user's message."""
        generator = TitleGenerator()

        with patch('src.core.agents.title_generator.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "Title"})
            mock_get_llm.return_value = mock_llm

            message = "This is my test message"
            await generator.generate_title(message)

            call_args = mock_llm.chat.call_args
            assert message in call_args[0][0][1]["content"]  # user message content


class TestTitleGeneratorSingleton:
    """Test cases for title_generator singleton."""

    def test_singleton_exists(self):
        """Test that title_generator singleton exists."""
        assert isinstance(title_generator, TitleGenerator)
