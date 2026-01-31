import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.core.graph.workflow import MaskWorkflow, AgentState
from src.core.agents.enhanced_coordinator import EnhancedCoordinator

@pytest.mark.asyncio
class TestFullChain:
    
    async def test_full_workflow_flow(self):
        """Test the full flow: Retrieve -> Router -> Coordinator -> Stream."""
        
        # Mock dependencies
        with patch('src.core.graph.workflow.memory_manager') as mock_memory, \
             patch('src.core.graph.workflow.graph_memory') as mock_graph, \
             patch('src.core.graph.workflow.tool_registry') as mock_registry, \
             patch('src.core.graph.workflow.get_llm', new_callable=AsyncMock) as mock_get_llm:
            
            # Setup Tools
            mock_registry.list_tools.return_value = [{"name": "fake_tool", "description": "desc", "inputSchema": {}}]

            # 1. Setup Memory Retrieval
            
            # 1. Setup Memory Retrieval
            mock_memory.search_relevant_history = AsyncMock(return_value="RAG Context")
            mock_graph.retrieve_context = AsyncMock(return_value="Graph Context")
            mock_memory.get_session = Mock(return_value=Mock(project_id="p1"))
            
            # 2. Setup LLM for Router (decides NO search) and Coordinator
            mock_client = AsyncMock()
            mock_get_llm.return_value = mock_client
            
            # Router response: NO search
            mock_client.chat.return_value = {"content": "NO"} 
            
            # 3. Setup Workflow
            workflow = MaskWorkflow()
            app = workflow.build_graph()
            
            # 4. Prepare State
            initial_state = AgentState(
                messages=[{"role": "user", "content": "Hello"}],
                session_id="s1",
                user_query="Hello"
            )
            
            # 5. Run Workflow (Simulate EnhancedCoordinator's loop)
            # We expect the state to eventually contain 'final_messages' and 'memory_context'
            final_state = await app.ainvoke(initial_state)
            
            # Verify Memory Context was populated
            assert "RAG Context" in final_state["memory_context"]
            assert "Graph Context" in final_state["memory_context"]
            
            # Verify Coordinator prepared messages
            assert "final_messages" in final_state
            
            # Verify Prompt contains context
            # We can check the system prompt in the messages
            system_msg = final_state["final_messages"][0]["content"]
            assert "RAG Context" in system_msg
            assert "Graph Context" in system_msg
            assert "AVAILABLE TOOLS" in system_msg

    async def test_streaming_coordinator(self):
        """Test EnhancedCoordinator streaming logic."""
        
        with patch('src.core.agents.enhanced_coordinator.get_workflow') as mock_get_wf, \
             patch('src.core.agents.enhanced_coordinator.memory_manager') as mock_memory, \
             patch('src.core.agents.enhanced_coordinator.get_llm', new_callable=AsyncMock) as mock_get_llm:
             
            # Setup Memory Manager Mocks
            mock_memory.add_message_async = AsyncMock()
            mock_memory.get_session.return_value = Mock(project_id="p1")

            # Setup Workflow to yield a "coordinator" event with prepared messages
            mock_wf_instance = Mock()
            mock_get_wf.return_value = mock_wf_instance
            
            # Mock stream generator
            async def mock_stream(*args, **kwargs):
                # Yield coordinator event
                yield {"coordinator": {
                    "final_messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
                    "final_response": "" # should be ignored
                }}
            mock_wf_instance.stream = mock_stream
            
            # Setup LLM Stream
            mock_client = AsyncMock()
            mock_get_llm.return_value = mock_client
            
            async def mock_chat_stream(*args):
                yield {"message": {"content": "Chunk1"}}
                yield {"message": {"content": "Chunk2"}}
            mock_client.chat_stream = mock_chat_stream
            
            # Initialize Coordinator
            coordinator = EnhancedCoordinator()
            
            # Run
            chunks = []
            async for chunk in coordinator.run_stream("s1", "hi"):
                chunks.append(chunk)
                
            # Verify
            assert "Chunk1" in chunks
            assert "Chunk2" in chunks
            # Check memory save (assistant response)
            mock_memory.add_message_async.assert_called()
            # Verify call args for assistant message
            call_args = mock_memory.add_message_async.call_args_list[-1] 
            assert call_args[0][2] == "Chunk1Chunk2" # accumulated content
