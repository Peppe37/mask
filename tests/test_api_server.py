"""Tests for FastAPI Server."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid

# Import after mocking
from src.api.server import app, ChatRequest, CreateSessionRequest, CreateProjectRequest
from src.core.memory.models import Project, ChatSession, ChatMessage


@pytest.fixture
def client():
    """Create a TestClient for the API."""
    return TestClient(app)


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager for testing."""
    with patch('src.api.server.memory_manager') as mock:
        mock.create_project = Mock(return_value=Project(
            id=str(uuid.uuid4()),
            name="Test Project",
            description="Test",
            color="#7c3aed",
            icon="📁"
        ))
        mock.list_projects = Mock(return_value=[])
        mock.get_project = Mock(return_value=None)
        mock.update_project_context = Mock()
        mock.update_project_color = Mock()
        mock.update_project_icon = Mock()
        mock.delete_project = Mock()
        mock.create_session = Mock(return_value=ChatSession(
            id=str(uuid.uuid4()),
            title="Test Session",
            project_id=None
        ))
        mock.list_sessions = Mock(return_value=[])
        mock.delete_session = Mock()
        mock.rename_session = Mock()
        mock.assign_session_to_project = Mock()
        mock.get_messages = Mock(return_value=[])
        mock.add_message = Mock()
        yield mock


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestProjectsEndpoints:
    """Test cases for project endpoints."""

    def test_create_project(self, client, mock_memory_manager):
        """Test creating a project."""
        response = client.post(
            "/api/projects",
            json={"name": "New Project", "description": "A new project"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        mock_memory_manager.create_project.assert_called_once_with(
            name="New Project",
            description="A new project"
        )

    def test_create_project_without_description(self, client, mock_memory_manager):
        """Test creating a project without description."""
        response = client.post(
            "/api/projects",
            json={"name": "Project Only"}
        )
        assert response.status_code == 200
        mock_memory_manager.create_project.assert_called_once_with(
            name="Project Only",
            description=None
        )

    def test_list_projects(self, client, mock_memory_manager):
        """Test listing projects."""
        mock_projects = [
            Project(id="1", name="Project 1", description="Desc 1"),
            Project(id="2", name="Project 2", description="Desc 2")
        ]
        mock_memory_manager.list_projects.return_value = mock_projects

        response = client.get("/api/projects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        mock_memory_manager.list_projects.assert_called_once()

    def test_update_project_summary(self, client, mock_memory_manager):
        """Test updating project summary."""
        project_id = str(uuid.uuid4())

        with patch('src.api.server.project_summarizer') as mock_summarizer:
            mock_summarizer.summarize_project = AsyncMock(return_value="New summary")

            response = client.post(f"/api/projects/{project_id}/summary")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
            assert response.json()["summary"] == "New summary"

    def test_update_project_color(self, client, mock_memory_manager):
        """Test updating project color."""
        project_id = str(uuid.uuid4())

        response = client.patch(
            f"/api/projects/{project_id}/color",
            json={"color": "#FF0000"}
        )
        assert response.status_code == 200
        mock_memory_manager.update_project_color.assert_called_once_with(project_id, "#FF0000")

    def test_update_project_icon(self, client, mock_memory_manager):
        """Test updating project icon."""
        project_id = str(uuid.uuid4())

        response = client.patch(
            f"/api/projects/{project_id}/icon",
            json={"icon": "🚀"}
        )
        assert response.status_code == 200
        mock_memory_manager.update_project_icon.assert_called_once_with(project_id, "🚀")

    def test_delete_project(self, client, mock_memory_manager):
        """Test deleting a project."""
        project_id = str(uuid.uuid4())

        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200
        mock_memory_manager.delete_project.assert_called_once_with(project_id)


class TestSessionsEndpoints:
    """Test cases for session endpoints."""

    def test_create_session(self, client, mock_memory_manager):
        """Test creating a session."""
        response = client.post(
            "/api/sessions",
            json={"title": "New Chat"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Session"
        mock_memory_manager.create_session.assert_called_once_with(
            title="New Chat",
            project_id=None
        )

    def test_create_session_with_project(self, client, mock_memory_manager):
        """Test creating a session with project association."""
        project_id = str(uuid.uuid4())

        response = client.post(
            "/api/sessions",
            json={"title": "Project Chat", "project_id": project_id}
        )
        assert response.status_code == 200
        mock_memory_manager.create_session.assert_called_once_with(
            title="Project Chat",
            project_id=project_id
        )

    def test_list_sessions(self, client, mock_memory_manager):
        """Test listing sessions."""
        mock_sessions = [
            ChatSession(id="1", title="Chat 1"),
            ChatSession(id="2", title="Chat 2")
        ]
        mock_memory_manager.list_sessions.return_value = mock_sessions

        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_delete_session(self, client, mock_memory_manager):
        """Test deleting a session."""
        session_id = str(uuid.uuid4())

        response = client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        mock_memory_manager.delete_session.assert_called_once_with(session_id)

    def test_rename_session(self, client, mock_memory_manager):
        """Test renaming a session."""
        session_id = str(uuid.uuid4())

        response = client.patch(
            f"/api/sessions/{session_id}/rename",
            json={"title": "New Title"}
        )
        assert response.status_code == 200
        mock_memory_manager.rename_session.assert_called_once_with(session_id, "New Title")

    def test_assign_session_to_project(self, client, mock_memory_manager):
        """Test assigning session to project."""
        session_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())

        response = client.patch(
            f"/api/sessions/{session_id}/project",
            json={"project_id": project_id}
        )
        assert response.status_code == 200
        mock_memory_manager.assign_session_to_project.assert_called_once_with(session_id, project_id)

    def test_assign_session_remove_project(self, client, mock_memory_manager):
        """Test removing session from project."""
        session_id = str(uuid.uuid4())

        response = client.patch(
            f"/api/sessions/{session_id}/project",
            json={"project_id": None}
        )
        assert response.status_code == 200
        mock_memory_manager.assign_session_to_project.assert_called_once_with(session_id, None)

    def test_generate_session_title(self, client, mock_memory_manager):
        """Test generating session title."""
        session_id = str(uuid.uuid4())

        with patch('src.api.server.title_generator') as mock_generator:
            mock_generator.generate_title = AsyncMock(return_value="Python Help")

            response = client.post(
                f"/api/sessions/{session_id}/generate-title",
                json={"first_message": "How do I use Python?"}
            )
            assert response.status_code == 200
            assert response.json()["title"] == "Python Help"
            mock_generator.generate_title.assert_called_once_with("How do I use Python?")

    def test_get_session_messages(self, client, mock_memory_manager):
        """Test getting session messages."""
        session_id = str(uuid.uuid4())

        from src.core.memory.models import ChatMessage
        mock_messages = [
            ChatMessage(id=1, session_id=session_id, role="user", content="Hello"),
            ChatMessage(id=2, session_id=session_id, role="assistant", content="Hi!")
        ]
        mock_memory_manager.get_messages.return_value = mock_messages

        response = client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestChatEndpoint:
    """Test cases for chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_endpoint(self):
        """Test chat streaming endpoint."""
        from httpx import AsyncClient

        with patch('src.api.server.enhanced_coordinator') as mock_coordinator:
            async def mock_stream(*args, **kwargs):
                yield "Hello "
                yield "world!"

            mock_coordinator.run_stream = mock_stream

            from httpx import ASGITransport
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/chat",
                    json={"message": "Hi", "session_id": "test-session"}
                )
                assert response.status_code == 200
                assert "Hello world!" in response.text


class TestRequestModels:
    """Test cases for request/response models."""

    def test_chat_request_model(self):
        """Test ChatRequest model."""
        request = ChatRequest(message="Hello", session_id="session-123")
        assert request.message == "Hello"
        assert request.session_id == "session-123"

    def test_create_session_request_defaults(self):
        """Test CreateSessionRequest default values."""
        request = CreateSessionRequest()
        assert request.title == "New Chat"
        assert request.project_id is None

    def test_create_project_request(self):
        """Test CreateProjectRequest model."""
        request = CreateProjectRequest(name="My Project")
        assert request.name == "My Project"
        assert request.description is None

        request_with_desc = CreateProjectRequest(name="My Project", description="A project")
        assert request_with_desc.description == "A project"


class TestStartupEvent:
    """Test cases for startup event."""

    @pytest.mark.asyncio
    async def test_startup_initializes_tool_registry(self):
        """Test that startup event initializes tool registry."""
        with patch('src.api.server.tool_registry') as mock_registry:
            mock_registry.initialize = Mock()

            # Simulate startup
            from src.api.server import startup_event
            await startup_event()

            mock_registry.initialize.assert_called_once()
