from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http import models
from src.core.config import settings
import uuid
import time

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

async def ensure_collection(collection_name: str, vector_size: int = 4096):
    """Ensure that a collection exists with the given vector size."""
    try:
        collections_response = await qdrant_client.get_collections()
        exists = any(c.name == collection_name for c in collections_response.collections)
        
        if not exists:
            print(f"Creating Qdrant collection '{collection_name}' with size {vector_size}...")
            await qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            return True
        return False
    except Exception as e:
        print(f"Error ensuring collection {collection_name}: {e}")
        return False

async def store_memory(collection_name: str, content: str, metadata: dict, embedding: list[float]):
    """Store a memory vector."""
    try:
        # Ensure collection exists (lazy check, optimistically assumes standard size or previously created)
        # For robustness, we check once or rely on the caller to ensure init.
        # But here we can just try to upsert.
        
        point_id = str(uuid.uuid4())
        
        await qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "content": content,
                        **metadata,
                        "timestamp": time.time()
                    }
                )
            ]
        )
        return True
    except Exception as e:
        print(f"Error storing memory in Qdrant: {e}")
        # If error is about collection not found or dimension mismatch, we might need to handle it.
        # For now, just log.
        return False

async def search_memory(collection_name: str, query_vector: list[float], limit: int = 5, score_threshold: float = 0.7):
    """Search for relevant memories."""
    try:
        results = await qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
        return results
    except Exception as e:
        print(f"Error searching Qdrant: {e}")
        return []
