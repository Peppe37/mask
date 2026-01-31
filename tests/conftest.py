"""Pytest configuration and fixtures for the MASK multi-agent framework."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import uuid
import tempfile
import os
from datetime import datetime

# Set test environment variables before importing config
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "test-model")


@pytest.fixture
def mock_settings():
    """Return mock settings for testing."""
    from src.core.config import Settings
    return Settings(
        POSTGRES_USER="test",
        POSTGRES_PASSWORD="test",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_DB="test_db",
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USER="neo4j",
        NEO4J_PASSWORD="test",
        QDRANT_HOST="localhost",
        QDRANT_PORT=6333,
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="test-model",
        MAX_HISTORY_TOKENS=4000
    )


@pytest.fixture
def sample_project_data():
    """Return sample project data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Project",
        "description": "A test project",
        "color": "#7c3aed",
        "icon": "📁",
        "created_at": datetime.utcnow(),
        "context_summary": None
    }


@pytest.fixture
def sample_session_data():
    """Return sample chat session data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": None,
        "title": "Test Chat",
        "created_at": datetime.utcnow()
    }


@pytest.fixture
def sample_message_data():
    """Return sample message data for testing."""
    return {
        "id": 1,
        "session_id": str(uuid.uuid4()),
        "role": "user",
        "content": "Hello, this is a test message",
        "created_at": datetime.utcnow()
    }


@pytest.fixture
def mock_ollama_response():
    """Return mock Ollama API response."""
    return {
        "response": "This is a test response",
        "message": {
            "role": "assistant",
            "content": "This is a test response"
        },
        "done": True
    }


@pytest.fixture
def mock_search_results():
    """Return mock DuckDuckGo search results."""
    return [
        {
            "title": "Test Result 1",
            "href": "https://example.com/1",
            "body": "This is the first test search result"
        },
        {
            "title": "Test Result 2",
            "href": "https://example.com/2",
            "body": "This is the second test search result"
        }
    ]


@pytest.fixture
def mock_html_content():
    """Return mock HTML content for scraping tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <main>
            <h1>Main Content</h1>
            <p>This is the main content of the page.</p>
            <p>More content here with <b>bold</b> text.</p>
        </main>
        <nav>Navigation items</nav>
        <footer>Footer content</footer>
    </body>
    </html>
    """


@pytest.fixture
def temp_who_md():
    """Create a temporary WHO.md file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""# User Profile

## Personal Information
- Name: Test User

## Interests
- Testing
- Programming

## Notes
- None
""")
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def mock_tool():
    """Return a mock tool for testing."""
    return {
        "name": "test_tool",
        "description": "A test tool",
        "input_schema": {
            "type": "object",
            "properties": {
                "arg1": {"type": "string"}
            }
        },
        "handler": AsyncMock(return_value="tool result")
    }


@pytest.fixture
def mock_agent_state():
    """Return a mock agent state for LangGraph testing."""
    return {
        "messages": [],
        "session_id": str(uuid.uuid4()),
        "user_query": "Test query",
        "needs_search": False,
        "search_queries": [],
        "search_results": [],
        "urls_to_scrape": [],
        "scraped_content": [],
        "web_context": "",
        "sources": [],
        "final_response": "",
        "response_chunks": []
    }


@pytest_asyncio.fixture
async def mock_ollama_client():
    """Return a mock Ollama client."""
    with patch('src.core.llm.ollama_client.OllamaClient') as mock:
        instance = mock.return_value
        instance.chat = AsyncMock(return_value={"role": "assistant", "content": "Test response"})
        instance.generate = AsyncMock(return_value="Test generation")
        instance.chat_stream = AsyncMock(return_value=AsyncMock(
            __aiter__=lambda s: (yield from [
                {"message": {"content": "chunk1"}},
                {"message": {"content": "chunk2"}},
                {"done": True}
            ])
        ))
        yield instance


@pytest.fixture
def mock_memory_manager():
    """Return a mock memory manager."""
    with patch('src.core.memory.manager.memory_manager') as mock:
        mock.create_project = Mock(return_value=Mock(
            id=str(uuid.uuid4()),
            name="Test Project",
            description="Test"
        ))
        mock.get_project = Mock(return_value=None)
        mock.list_projects = Mock(return_value=[])
        mock.create_session = Mock(return_value=Mock(
            id=str(uuid.uuid4()),
            title="Test Session"
        ))
        mock.get_session = Mock(return_value=None)
        mock.get_messages = Mock(return_value=[])
        mock.add_message = Mock(return_value=Mock(id=1))
        yield mock


@pytest.fixture
def mock_workflow():
    """Return a mock LangGraph workflow."""
    with patch('src.core.graph.workflow.get_workflow') as mock:
        workflow = mock.return_value
        workflow.stream = AsyncMock(return_value=AsyncMock(
            __aiter__=lambda s: (yield from [
                {"router": {"needs_search": True}},
                {"search": {"search_results": []}},
                {"scrape": {"scraped_content": []}},
                {"coordinator": {"final_response": "Test response"}}
            ])
        ))
        workflow.run = AsyncMock(return_value="Test response")
        yield workflow
