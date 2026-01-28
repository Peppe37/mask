from neo4j import GraphDatabase, AsyncGraphDatabase
from src.core.config import settings

class Neo4jDatabase:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    async def close(self):
        await self.driver.close()

    async def check_connection(self):
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            return False

neo4j_db = Neo4jDatabase()

async def get_neo4j():
    return neo4j_db
