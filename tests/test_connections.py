import pytest
from unittest.mock import AsyncMock, patch
from src.core.database.postgres import check_postgres_connection
from src.core.database.neo4j import neo4j_db
from src.core.database.qdrant import check_qdrant_connection

@pytest.mark.asyncio
async def test_postgres_connection():
    with patch("src.core.database.postgres.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn

        result = await check_postgres_connection()
        assert result is True
        mock_engine.connect.assert_called_once()

@pytest.mark.asyncio
async def test_neo4j_connection():
    with patch.object(neo4j_db.driver, "verify_connectivity", new_callable=AsyncMock) as mock_verify:
        result = await neo4j_db.check_connection()
        assert result is True
        mock_verify.assert_called_once()

@pytest.mark.asyncio
async def test_qdrant_connection():
    with patch("src.core.database.qdrant.qdrant_client.get_collections", new_callable=AsyncMock) as mock_get_collections:
        result = await check_qdrant_connection()
        assert result is True
        mock_get_collections.assert_called_once()
