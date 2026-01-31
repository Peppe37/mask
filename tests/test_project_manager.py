"""Tests for Project Manager Agent."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.agents.project_manager import ProjectSummarizerAgent, project_summarizer


class TestProjectSummarizerAgent:
    """Test cases for ProjectSummarizerAgent."""

    def test_agent_initialization(self):
        """Test ProjectSummarizerAgent initialization."""
        agent = ProjectSummarizerAgent()
        assert "Project Manager" in agent.system_prompt
        assert "synthesizing" in agent.system_prompt.lower()

    @pytest.mark.asyncio
    async def test_summarize_project_with_existing_context(self):
        """Test project summarization with existing context."""
        agent = ProjectSummarizerAgent()

        chats_summary = """
Chat 1: Discussed Python best practices
Chat 2: Decided to use FastAPI for backend
"""
        current_summary = "Project about Web API development"

        with patch('src.core.agents.project_manager.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Web API project using FastAPI and Python best practices")
            mock_get_llm.return_value = mock_llm

            result = await agent.summarize_project(chats_summary, current_summary)

            assert result == "Web API project using FastAPI and Python best practices"

            # Verify prompt contains both context and chats
            call_args = mock_llm.generate.call_args
            assert "Web API" in call_args[0][0]  # current summary
            assert "Python best practices" in call_args[0][0]  # chats summary

    @pytest.mark.asyncio
    async def test_summarize_project_without_existing_context(self):
        """Test project summarization without existing context."""
        agent = ProjectSummarizerAgent()

        chats_summary = """
Chat 1: Initial planning meeting
Chat 2: Architecture decisions
"""

        with patch('src.core.agents.project_manager.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="New project: planning and architecture phase")
            mock_get_llm.return_value = mock_llm

            result = await agent.summarize_project(chats_summary, None)

            assert result == "New project: planning and architecture phase"

            # Verify prompt shows "None" for empty context
            call_args = mock_llm.generate.call_args
            assert "None" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_summarize_project_uses_system_prompt(self):
        """Test that summarization uses correct system prompt."""
        agent = ProjectSummarizerAgent()

        with patch('src.core.agents.project_manager.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Summary")
            mock_get_llm.return_value = mock_llm

            await agent.summarize_project("chats", None)

            call_args = mock_llm.generate.call_args
            assert call_args[1]["system"] == agent.system_prompt

    @pytest.mark.asyncio
    async def test_summarize_project_uses_low_temperature(self):
        """Test that summarization uses low temperature for consistency."""
        agent = ProjectSummarizerAgent()

        with patch('src.core.agents.project_manager.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.generate = AsyncMock(return_value="Summary")
            mock_get_llm.return_value = mock_llm

            await agent.summarize_project("chats", None)

            call_args = mock_llm.generate.call_args
            assert call_args[1]["options"]["temperature"] == 0.3


class TestProjectSummarizerSingleton:
    """Test cases for project_summarizer singleton."""

    def test_singleton_exists(self):
        """Test that project_summarizer singleton exists."""
        assert isinstance(project_summarizer, ProjectSummarizerAgent)
