from qdrant_client import QdrantClient, AsyncQdrantClient
from src.core.config import settings

# Async client for actual usage
qdrant_client = AsyncQdrantClient(
    host=settings.QDRANT_HOST,
    port=settings.QDRANT_PORT,
)

async def check_qdrant_connection():
    try:
        # get_collections returns a list of collections, if we can call it, we are connected
        await qdrant_client.get_collections()
        return True
    except Exception as e:
        print(f"Qdrant connection failed: {e}")
        return False
