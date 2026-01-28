import pytest
from unittest.mock import AsyncMock, patch, Mock
from src.core.llm.ollama_client import OllamaClient

@pytest.mark.asyncio
async def test_ollama_generate():
    client = OllamaClient()
    mock_response = AsyncMock()
    # json() is not async in httpx
    mock_response.json = Mock(return_value={"response": "test response"})
    mock_response.raise_for_status = Mock()

    with patch.object(client.client, "post", return_value=mock_response) as mock_post:
        response = await client.generate("test prompt")
        assert response == "test response"
        mock_post.assert_called_once()

    await client.close()

@pytest.mark.asyncio
async def test_ollama_chat():
    client = OllamaClient()
    mock_response = AsyncMock()
    mock_response.json = Mock(return_value={"message": {"role": "assistant", "content": "test answer"}})
    mock_response.raise_for_status = Mock()

    with patch.object(client.client, "post", return_value=mock_response) as mock_post:
        response = await client.chat([{"role": "user", "content": "hello"}])
        assert response["content"] == "test answer"
        mock_post.assert_called_once()

    await client.close()
