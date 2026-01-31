"""New coordinator with LangGraph workflow integration."""

from typing import AsyncGenerator, List
from src.core.graph.workflow import get_workflow
from src.core.memory.manager import memory_manager
from src.core.llm.ollama_client import get_llm
from src.core.agents.summarizer import summarizer
from src.core.config import settings
from src.core.memory.user_profile import user_profile_manager
import asyncio


class EnhancedCoordinator:
    """Coordinator that uses LangGraph workflow for web search and scraping."""

    def __init__(self):
        self.workflow = get_workflow()

    async def run_stream(self, session_id: str, user_input: str) -> AsyncGenerator[str, None]:
        """Run the enhanced workflow with web search capabilities.

        Args:
            session_id: Chat session ID
            user_input: User's message

        Yields:
            Response chunks
        """
        # 1. Retrieve history & Project Context
        session = memory_manager.get_session(session_id)
        project_context = ""

        if session and session.project_id:
            project = memory_manager.get_project(session.project_id)
            if project and project.context_summary:
                project_context = f"\n\nPROJECT CONTEXT (Summary of other related chats):\n{project.context_summary}\n"

        db_messages = memory_manager.get_messages(session_id)
        history = [{"role": m.role, "content": m.content} for m in db_messages]

        # 2. Check token count & Summarize if needed
        full_text = "".join([m["content"] for m in history])
        approx_tokens = len(full_text) / 4

        if approx_tokens > settings.MAX_HISTORY_TOKENS:
            print("[EnhancedCoordinator] History too long. Summarizing...")
            summary = await summarizer.summarize(history)

            new_history = [
                {"role": "system", "content": f"Previous conversation summary: {summary}"}
            ]
            memory_manager.update_messages(session_id, new_history)
            history = new_history

        if project_context:
            history.insert(0, {"role": "system", "content": project_context})

        # 3. Add User Profile Context (WHO.md)
        try:
            user_profile_content = user_profile_manager.get_profile()
            profile_prompt = f"\n\nUSER PROFILE (WHO.md - Always strictly follow this context about the user):\n{user_profile_content}\n"
            history.insert(0, {"role": "system", "content": profile_prompt})

            # Trigger background update of profile based on the NEW user input
            # We use asyncio.create_task to run it without blocking the stream
            asyncio.create_task(user_profile_manager.update_profile(user_input))
        except Exception as e:
            print(f"[EnhancedCoordinator] Failed to process user profile: {e}")

        # 3. Add user message to memory
        await memory_manager.add_message_async(session_id, "user", user_input)
        # Note: History already has the user input if we appended it? No, history comes from DB which doesn't have it yet.
        # Check line 36-50. History is built from DB.
        # So we need to append current user input to history for the workflow.
        history.append({"role": "user", "content": user_input})

        # 4. Run LangGraph workflow with streaming
        print(f"[EnhancedCoordinator] Running workflow for: {user_input[:50]}...")

        final_response_accumulator = ""

        try:
            # Stream workflow updates
            async for event in self.workflow.stream(session_id, user_input, history):
                # event is a dict with node name as key
                for node_name, node_state in event.items():
                    # Yield status updates
                    if node_name == "router":
                        if node_state.get("needs_search"):
                            yield {"type": "status", "content": "🔍 Searching the web..."}

                    elif node_name == "search":
                        results_count = len(node_state.get("search_results", []))
                        yield {"type": "status", "content": f"📊 Found {results_count} sources"}

                    elif node_name == "scrape":
                        scraped = node_state.get("scraped_content", [])
                        success_count = sum(1 for s in scraped if not s.error)
                        yield {"type": "status", "content": f"📄 Reading {success_count} articles..."}

                    elif node_name == "coordinator":
                        # Detect if we have prepared messages for streaming
                        final_messages = node_state.get("final_messages")
                        if final_messages:
                            print("[EnhancedCoordinator] Starting LLM stream...")
                            llm = await get_llm()
                            async for chunk in llm.chat_stream(final_messages):
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield {"type": "token", "content": content}
                                    final_response_accumulator += content
                                    
                        # Fallback for non-streaming (if ever used)
                        elif node_state.get("final_response"):
                            response = node_state.get("final_response", "")
                            yield {"type": "token", "content": response}
                            final_response_accumulator = response
        except Exception as e:
            import traceback
            print(f"[EnhancedCoordinator] Error in workflow stream: {e}")
            traceback.print_exc()
            yield {"type": "token", "content": f"\n[Error] Something went wrong: {str(e)}"}

        # 5. Save assistant message to memory

        # 5. Save assistant message to memory
        # Use the accumulated response from the stream instead of re-running
        if final_response_accumulator:
            await memory_manager.add_message_async(session_id, "assistant", final_response_accumulator)
        else:
             print("[EnhancedCoordinator] Warning: No response generated to persist.")


# Create instance for backward compatibility
enhanced_coordinator = EnhancedCoordinator()
