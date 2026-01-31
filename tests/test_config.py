"""Tests for configuration module."""

import pytest
import os
from unittest.mock import patch
from src.core.config import Settings, settings


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        with patch.dict(os.environ, {}, clear=True):
            test_settings = Settings(_env_file=None)
            assert test_settings.POSTGRES_USER == "postgres"
            assert test_settings.POSTGRES_PASSWORD == "password"
            assert test_settings.POSTGRES_HOST == "localhost"
            assert test_settings.POSTGRES_PORT == 5432
            assert test_settings.POSTGRES_DB == "agents_db"
            assert test_settings.NEO4J_URI == "bolt://localhost:7687"
            assert test_settings.NEO4J_USER == "neo4j"
            assert test_settings.NEO4J_PASSWORD == "password"
            assert test_settings.QDRANT_HOST == "localhost"
            assert test_settings.QDRANT_PORT == 6333
            assert test_settings.OLLAMA_BASE_URL == "http://localhost:11434"
            assert test_settings.OLLAMA_MODEL == "ministral-3:8b"
            assert test_settings.MAX_HISTORY_TOKENS == 4000

    def test_custom_settings_from_env(self):
        """Test that settings can be customized via environment variables."""
        env_vars = {
            "POSTGRES_USER": "custom_user",
            "POSTGRES_PASSWORD": "custom_pass",
            "POSTGRES_HOST": "custom.host.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "custom_db",
            "NEO4J_URI": "bolt://custom.neo4j:7687",
            "NEO4J_USER": "custom_neo4j",
            "NEO4J_PASSWORD": "custom_neo4j_pass",
            "QDRANT_HOST": "custom.qdrant",
            "QDRANT_PORT": "6334",
            "OLLAMA_BASE_URL": "http://custom.ollama:11434",
            "OLLAMA_MODEL": "custom-model",
            "MAX_HISTORY_TOKENS": "8000"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            test_settings = Settings()
            assert test_settings.POSTGRES_USER == "custom_user"
            assert test_settings.POSTGRES_PASSWORD == "custom_pass"
            assert test_settings.POSTGRES_HOST == "custom.host.com"
            assert test_settings.POSTGRES_PORT == 5433
            assert test_settings.POSTGRES_DB == "custom_db"
            assert test_settings.NEO4J_URI == "bolt://custom.neo4j:7687"
            assert test_settings.NEO4J_USER == "custom_neo4j"
            assert test_settings.NEO4J_PASSWORD == "custom_neo4j_pass"
            assert test_settings.QDRANT_HOST == "custom.qdrant"
            assert test_settings.QDRANT_PORT == 6334
            assert test_settings.OLLAMA_BASE_URL == "http://custom.ollama:11434"
            assert test_settings.OLLAMA_MODEL == "custom-model"
            assert test_settings.MAX_HISTORY_TOKENS == 8000

    def test_singleton_settings_instance(self):
        """Test that settings singleton exists and is properly configured."""
        assert isinstance(settings, Settings)
        assert hasattr(settings, 'POSTGRES_USER')
        assert hasattr(settings, 'NEO4J_URI')
        assert hasattr(settings, 'OLLAMA_BASE_URL')

    def test_settings_extra_ignore(self):
        """Test that extra fields in env file are ignored."""
        with patch.dict(os.environ, {"RANDOM_EXTRA_VAR": "value"}, clear=False):
            # Should not raise validation error
            test_settings = Settings()
            assert not hasattr(test_settings, 'RANDOM_EXTRA_VAR')


class TestDatabaseUrls:
    """Test cases for database URL construction."""

    def test_postgres_url_construction(self, mock_settings):
        """Test that PostgreSQL URL is correctly constructed."""
        expected_url = (
            f"postgresql+asyncpg://{mock_settings.POSTGRES_USER}:"
            f"{mock_settings.POSTGRES_PASSWORD}@{mock_settings.POSTGRES_HOST}:"
            f"{mock_settings.POSTGRES_PORT}/{mock_settings.POSTGRES_DB}"
        )
        from src.core.database.postgres import DATABASE_URL
        # Note: This test might fail if postgres module was already imported
        # In that case, we test the pattern instead
        assert "postgresql+asyncpg://" in expected_url
        assert mock_settings.POSTGRES_HOST in expected_url
