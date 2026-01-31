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

    async def execute_read(self, query: str, parameters: dict = None):
        """Execute a read transaction."""
        async def work(tx):
            result = await tx.run(query, parameters)
            # Use async iteration instead of .data() which caused "coroutine object has no attribute data" error
            return [record.data() async for record in result]

        async with self.driver.session() as session:
            return await session.execute_read(work)

    async def execute_write(self, query: str, parameters: dict = None):
        """Execute a write transaction."""
        async def work(tx):
            result = await tx.run(query, parameters)
            return [record.data() async for record in result]

        async with self.driver.session() as session:
            return await session.execute_write(work)

neo4j_db = Neo4jDatabase()

async def get_neo4j():
    return neo4j_db
