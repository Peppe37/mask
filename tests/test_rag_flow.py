import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.core.memory.manager import MemoryManager
from src.core.memory.models import ChatMessage

@pytest.mark.asyncio
class TestRAGFlow:
    
    async def test_add_message_async_embeds_and_stores(self):
        """Test that add_message_async embeds content and stores in Qdrant."""
        
        # Mock dependencies in context manager
        with patch('src.core.memory.manager.get_llm', new_callable=AsyncMock) as mock_get_llm, \
             patch('src.core.memory.manager.qdrant') as mock_qdrant, \
             patch('src.core.memory.manager.Session') as mock_session_cls:
            
            # Setup LLM mock
            mock_client = AsyncMock()
            mock_get_llm.return_value = mock_client
            mock_client.embeddings.return_value = [0.1, 0.2, 0.3]
            
            # Setup Qdrant mock
            mock_qdrant.ensure_collection = AsyncMock(return_value=True)
            mock_qdrant.store_memory = AsyncMock(return_value=True)
            
            # Setup Session mock (synchronous DB part)
            mock_session =  Mock()
            mock_session_cls.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.all.return_value = [] # for checks
            
            # Initialize Manager
            manager = MemoryManager()
            # Mock get_session internal call
            manager.get_session = Mock(return_value=Mock(project_id="proj-123"))
            
            # Action
            await manager.add_message_async("session-1", "user", "Hello World")
            
            # Verification
            # 1. Check Embedding generation
            # args[0] is prompt, kwargs may contain model
            mock_client.embeddings.assert_called_once()
            args, kwargs = mock_client.embeddings.call_args
            assert args[0] == "Hello World"
            # We can optionally check if model arg is passed, but just ensuring it doesn't fail on strict signature
            
            # 2. Check Qdrant storage
            mock_qdrant.store_memory.assert_called_once()
            call_args = mock_qdrant.store_memory.call_args
            assert call_args[0][0] == "chat_history"
            assert call_args[0][1] == "Hello World"
            assert call_args[0][2]["session_id"] == "session-1"
            assert call_args[0][3] == [0.1, 0.2, 0.3]

    async def test_search_relevant_history(self):
        """Test searching relevant history via Qdrant."""
        
        with patch('src.core.memory.manager.get_llm', new_callable=AsyncMock) as mock_get_llm, \
             patch('src.core.memory.manager.qdrant') as mock_qdrant:
            
            # Setup LLM
            mock_client = AsyncMock()
            mock_get_llm.return_value = mock_client
            mock_client.embeddings.return_value = [0.1, 0.1, 0.1]
            
            # Setup Qdrant Search Result
            mock_point = Mock()
            mock_point.payload = {"content": "Past message", "role": "user", "project_id": "proj-123"}
            mock_qdrant.search_memory = AsyncMock(return_value=[mock_point])
            
            manager = MemoryManager()
            
            # Action
            result = await manager.search_relevant_history("Query", project_id="proj-123")
            
            # Verify
            assert "RELEVANT PAST CONVERSATION" in result
            assert "[user]: Past message" in result
            
            mock_qdrant.search_memory.assert_called_once()
