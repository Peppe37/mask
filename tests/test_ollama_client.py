"""Tests for Ollama LLM client."""

import pytest
import pytest_asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx
from src.core.llm.ollama_client import OllamaClient, get_llm, ollama_client


class TestOllamaClient:
    """Test cases for OllamaClient."""

    def test_client_initialization(self, mock_settings):
        """Test Ollama client initialization."""
        client = OllamaClient(
            base_url=mock_settings.OLLAMA_BASE_URL,
            model=mock_settings.OLLAMA_MODEL
        )
        assert client.base_url == mock_settings.OLLAMA_BASE_URL
        assert client.model == mock_settings.OLLAMA_MODEL
        assert isinstance(client.client, httpx.AsyncClient)

    def test_default_initialization(self):
        """Test Ollama client initialization with defaults."""
        with patch('src.core.llm.ollama_client.settings') as mock_settings:
            mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
            mock_settings.OLLAMA_MODEL = "test-model"
            client = OllamaClient()
            assert client.base_url == "http://localhost:11434"
            assert client.model == "test-model"

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_ollama_response):
        """Test successful text generation."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value=mock_ollama_response)

        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await client.generate("Test prompt", system="Test system")

            assert result == "This is a test response"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/api/generate"
            assert call_args[1]["json"]["model"] == client.model
            assert call_args[1]["json"]["prompt"] == "Test prompt"
            assert call_args[1]["json"]["system"] == "Test system"
            assert call_args[1]["json"]["stream"] is False

    @pytest.mark.asyncio
    async def test_generate_with_options(self):
        """Test text generation with options."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"response": "Test"})

        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            options = {"temperature": 0.5, "top_p": 0.9}
            await client.generate("Prompt", options=options)

            call_args = mock_post.call_args
            assert call_args[1]["json"]["options"] == options

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        """Test handling of HTTP errors in generation."""
        client = OllamaClient()

        async def mock_post_error(*args, **kwargs):
            raise httpx.HTTPError("Connection failed")

        with patch.object(client.client, 'post', side_effect=mock_post_error) as mock_post:
            with pytest.raises(httpx.HTTPError):
                await client.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat completion."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "message": {"role": "assistant", "content": "Chat response"}
        })

        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ]
            result = await client.chat(messages)

            assert result == {"role": "assistant", "content": "Chat response"}
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/api/chat"
            assert call_args[1]["json"]["messages"] == messages
            assert call_args[1]["json"]["stream"] is False

    @pytest.mark.asyncio
    async def test_chat_with_options(self):
        """Test chat with options."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"message": {"content": "Test"}})

        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            options = {"temperature": 0.7}
            await client.chat([{"role": "user", "content": "Hi"}], options=options)

            call_args = mock_post.call_args
            assert call_args[1]["json"]["options"] == options

    @pytest.mark.asyncio
    async def test_chat_stream_success(self):
        """Test successful streaming chat."""
        client = OllamaClient()

        chunks = [
            json.dumps({"message": {"content": "Hello "}}),
            json.dumps({"message": {"content": "world"}}),
            json.dumps({"done": True})
        ]

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        async def mock_aiter_lines():
            for line in chunks:
                yield line
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        with patch.object(client.client, 'stream', return_value=mock_response):
            chunks_collected = []
            async for chunk in client.chat_stream([{"role": "user", "content": "Hi"}]):
                chunks_collected.append(chunk)

            assert len(chunks_collected) == 3
            assert chunks_collected[0]["message"]["content"] == "Hello "
            assert chunks_collected[1]["message"]["content"] == "world"
            assert chunks_collected[2]["done"] is True

    @pytest.mark.asyncio
    async def test_chat_stream_ignores_invalid_json(self):
        """Test that chat_stream ignores invalid JSON lines."""
        client = OllamaClient()

        chunks = [
            json.dumps({"message": {"content": "Valid"}}),
            "invalid json",
            json.dumps({"message": {"content": "Also valid"}})
        ]

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock()
        async def mock_aiter_lines():
            for line in chunks:
                yield line
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        with patch.object(client.client, 'stream', return_value=mock_response):
            chunks_collected = []
            async for chunk in client.chat_stream([{"role": "user", "content": "Hi"}]):
                chunks_collected.append(chunk)

            assert len(chunks_collected) == 2  # Invalid JSON skipped

    @pytest.mark.asyncio
    async def test_chat_stream_http_error(self):
        """Test handling of HTTP errors in streaming."""
        client = OllamaClient()

        mock_response = MagicMock()
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Stream failed",
            request=httpx.Request("POST", "http://test"),
            response=httpx.Response(500, request=httpx.Request("POST", "http://test"))
        ))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_stream(*args, **kwargs):
            yield mock_response

        with patch.object(client.client, 'stream', side_effect=mock_stream):
            with pytest.raises(httpx.HTTPError):
                async for _ in client.chat_stream([{"role": "user", "content": "Hi"}]):
                    pass

    @pytest.mark.asyncio
    async def test_close(self):
        """Test client cleanup."""
        client = OllamaClient()

        with patch.object(client.client, 'aclose', new_callable=AsyncMock) as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestGetLLM:
    """Test cases for get_llm function."""

    @pytest.mark.asyncio
    async def test_get_llm_returns_client(self):
        """Test that get_llm returns the ollama_client singleton."""
        client = await get_llm()
        assert client is ollama_client

    @pytest.mark.asyncio
    async def test_get_llm_returns_same_instance(self):
        """Test that get_llm always returns the same instance."""
        client1 = await get_llm()
        client2 = await get_llm()
        assert client1 is client2
