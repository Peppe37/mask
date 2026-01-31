"""Tests for User Profile Manager."""

import pytest
import pytest_asyncio
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, mock_open
from src.core.memory.user_profile import UserProfileManager, user_profile_manager, WARNING_MSG


class TestUserProfileManager:
    """Test cases for UserProfileManager."""

    def test_initialization_creates_file(self, tmp_path):
        """Test that initialization creates WHO.md if it doesn't exist."""
        file_path = tmp_path / "WHO.md"
        manager = UserProfileManager(file_path=str(file_path))

        assert file_path.exists()
        content = file_path.read_text()
        assert "# User Profile" in content
        assert "Name: unknown" in content

    def test_initialization_existing_file(self, tmp_path):
        """Test that initialization doesn't overwrite existing file."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# Existing Profile\n\nCustom content")

        manager = UserProfileManager(file_path=str(file_path))

        content = file_path.read_text()
        assert "Custom content" in content
        assert "Name: unknown" not in content

    def test_get_profile_success(self, tmp_path):
        """Test reading profile successfully."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# Test Profile\n\nTest content")

        manager = UserProfileManager(file_path=str(file_path))
        content = manager.get_profile()

        assert "# Test Profile" in content
        assert "Test content" in content

    def test_get_profile_error(self, tmp_path):
        """Test handling error when reading profile."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("content")

        manager = UserProfileManager(file_path=str(file_path))

        # Make file unreadable by removing read permissions
        os.chmod(file_path, 0o000)

        try:
            content = manager.get_profile()
            assert "Error reading" in content
        finally:
            # Restore permissions for cleanup
            os.chmod(file_path, 0o644)

    @pytest.mark.asyncio
    async def test_update_profile_no_update(self, tmp_path):
        """Test when no update is needed."""
        file_path = tmp_path / "WHO.md"
        original_content = "# User Profile\n\n## Personal Information\n- Name: Test\n"
        file_path.write_text(original_content)

        manager = UserProfileManager(file_path=str(file_path))

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "NO_UPDATE"})
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("I am going to the store")

            # Verify file wasn't changed
            content = file_path.read_text()
            assert content == original_content

    @pytest.mark.asyncio
    async def test_update_profile_success(self, tmp_path):
        """Test successful profile update."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# User Profile\n\n## Personal Information\n- Name: unknown\n")

        manager = UserProfileManager(file_path=str(file_path))

        new_content = """# User Profile

## Personal Information
- Name: John

## Interests
- Programming
"""

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": new_content})
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("My name is John and I like programming")

            content = file_path.read_text()
            assert "John" in content
            assert "Programming" in content

    @pytest.mark.asyncio
    async def test_update_profile_rejects_invalid_markdown(self, tmp_path):
        """Test that invalid markdown is rejected."""
        file_path = tmp_path / "WHO.md"
        original_content = "# User Profile\n"
        file_path.write_text(original_content)

        manager = UserProfileManager(file_path=str(file_path))

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            # Response doesn't contain "# User Profile"
            mock_llm.chat = AsyncMock(return_value={"content": "Just some text"})
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("My name is John")

            # Verify file wasn't changed (invalid response rejected)
            content = file_path.read_text()
            assert content == original_content

    @pytest.mark.asyncio
    async def test_update_profile_retries_on_error(self, tmp_path):
        """Test that update retries on LLM error."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# User Profile\n")

        manager = UserProfileManager(file_path=str(file_path))

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            # First two calls fail, third succeeds
            mock_llm.chat = AsyncMock(side_effect=[
                Exception("Error 1"),
                Exception("Error 2"),
                {"content": "NO_UPDATE"}
            ])
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("Test input")

            # Should have been called 3 times (2 retries + 1 success)
            assert mock_llm.chat.call_count == 3

    @pytest.mark.asyncio
    async def test_update_profile_sanity_check_passes(self, tmp_path):
        """Test that valid markdown passes sanity check."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# User Profile\n")

        manager = UserProfileManager(file_path=str(file_path))

        valid_content = "# User Profile\n\n## Updated Info\n- Name: Jane\n"

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": valid_content})
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("My name is Jane")

            content = file_path.read_text()
            assert "Jane" in content

    @pytest.mark.asyncio
    async def test_update_profile_prompt_contains_current_profile(self, tmp_path):
        """Test that update prompt includes current profile."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# User Profile\n\n## Personal Information\n- Name: Current\n")

        manager = UserProfileManager(file_path=str(file_path))

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "NO_UPDATE"})
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("Test input")

            # Check that prompt contains current profile
            call_args = mock_llm.chat.call_args
            prompt = call_args[0][0][1]["content"]  # user message content
            assert "Current Profile:" in prompt
            assert "Name: Current" in prompt

    @pytest.mark.asyncio
    async def test_update_profile_prompt_contains_user_input(self, tmp_path):
        """Test that update prompt includes user input."""
        file_path = tmp_path / "WHO.md"
        file_path.write_text("# User Profile\n")

        manager = UserProfileManager(file_path=str(file_path))

        with patch('src.core.memory.user_profile.get_llm', new_callable=AsyncMock) as mock_get_llm:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(return_value={"content": "NO_UPDATE"})
            mock_get_llm.return_value = mock_llm

            await manager.update_profile("My new information")

            # Check that prompt contains user input
            call_args = mock_llm.chat.call_args
            prompt = call_args[0][0][1]["content"]
            assert "User Input:" in prompt
            assert "My new information" in prompt


class TestUserProfileManagerSingleton:
    """Test cases for user_profile_manager singleton."""

    def test_singleton_exists(self):
        """Test that user_profile_manager singleton exists."""
        assert isinstance(user_profile_manager, UserProfileManager)

    def test_singleton_default_path(self):
        """Test that singleton uses default WHO.md path."""
        assert user_profile_manager.file_path == "WHO.md"

    def test_warning_message_constant(self):
        """Test that warning message exists."""
        assert "sensitive data" in WARNING_MSG.lower()
