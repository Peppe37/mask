import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.core.memory.graph_memory import GraphMemory

@pytest.mark.asyncio
class TestGraphMemory:
    
    async def test_extract_and_store(self):
        """Test entity extraction and storage."""
        
        with patch('src.core.memory.graph_memory.get_llm', new_callable=AsyncMock) as mock_get_llm, \
             patch('src.core.memory.graph_memory.get_neo4j', new_callable=AsyncMock) as mock_get_neo4j:
             
            # Setup LLM mock response
            mock_client = AsyncMock()
            mock_get_llm.return_value = mock_client
            mock_client.chat.return_value = {
                "content": """
                {
                    "nodes": [{"id": "TestEntity", "label": "Concept"}],
                    "edges": []
                }
                """
            }
            
            # Setup Neo4j mock
            mock_db = AsyncMock()
            mock_get_neo4j.return_value = mock_db
            mock_db.execute_write = AsyncMock()
            
            graph = GraphMemory()
            await graph.extract_and_store("Some text")
            
            # Verify Neo4j was called
            mock_db.execute_write.assert_called()
            # Check the cypher query in the call args contains appropriate MERGE
            call_args = mock_db.execute_write.call_args_list[0]
            assert "MERGE (n:Concept {id: $id})" in call_args[0][0]

    async def test_retrieve_context(self):
        """Test context retrieval."""
        
        with patch('src.core.memory.graph_memory.get_neo4j', new_callable=AsyncMock) as mock_get_neo4j:
            
            mock_db = AsyncMock()
            mock_get_neo4j.return_value = mock_db
            
            # Mock return for generic query
            mock_db.execute_read.return_value = [
                {"n.id": "EntityA", "type(r)": "RELATED_TO", "m.id": "EntityB"}
            ]
            
            graph = GraphMemory()
            result = await graph.retrieve_context("Tell me about EntityA")
            
            assert "GRAPH KNOWLEDGE" in result
            assert "EntityA --[RELATED_TO]--> EntityB" in result
