from typing import List, Dict, Any
from src.core.llm.ollama_client import get_llm
from src.core.database.neo4j import get_neo4j
import json

class GraphMemory:
    """Manages knowledge graph operations (Neo4j)."""
    
    def __init__(self):
        pass

    async def extract_and_store(self, text: str, user_id: str = None):
        """Extract entities and relationships and store in Neo4j."""
        llm = await get_llm()
        
        prompt = f"""
        Analyze the following text and extract entities (Person, Technology, Company, Project, Concept) and relationships between them.
        Return a JSON object with "nodes" and "edges".
        
        Text: "{text}"
        
        Rules:
        1. Nodes must have "id", "label" (Person, Tech, etc), and optional "properties".
        2. Edges must have "source", "target", "type" (relationship name), and "properties".
        3. Keep relationship types uppercase (e.g., USES, WORKS_ON, INTERESTED_IN).
        4. Return ONLY valid JSON.
        
        Example:
        {{
            "nodes": [
                {{"id": "John", "label": "Person"}},
                {{"id": "Python", "label": "Technology"}}
            ],
            "edges": [
                {{"source": "John", "target": "Python", "type": "KNOWS"}}
            ]
        }}
        """
        
        try:
            response_msg = await llm.chat([
                {"role": "system", "content": "You are a Knowledge Graph extraction expert. Output JSON only."},
                {"role": "user", "content": prompt}
            ])
            content = response_msg.get("content", "")
            
            # Simple cleanup for JSON parsing
            content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            await self._store_subgraph(data)
            return data
            
        except Exception as e:
            print(f"Graph extraction error: {e}")
            return None

    async def _store_subgraph(self, data: Dict[str, Any]):
        """Store nodes and edges in Neo4j."""
        neo4j = await get_neo4j()
        
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        
        # 1. Merge Nodes
        for node in nodes:
            cypher = f"""
            MERGE (n:{node['label']} {{id: $id}})
            SET n += $props
            """
            # Move extra keys to props
            props = {k:v for k,v in node.items() if k not in ["id", "label"]}
            await neo4j.execute_write(cypher, {"id": node["id"], "props": props})
            
        # 2. Merge Edges
        for edge in edges:
            cypher = f"""
            MATCH (a {{id: $source}}), (b {{id: $target}})
            MERGE (a)-[r:{edge['type']}]->(b)
            SET r += $props
            """
            props = {k:v for k,v in edge.items() if k not in ["source", "target", "type"]}
            await neo4j.execute_write(cypher, {
                "source": edge["source"],
                "target": edge["target"],
                "props": props
            })

    async def retrieve_context(self, text: str) -> str:
        """Retrieve relevant graph context based on keywords in text."""
        # Simple implementation: extract entities from query -> find 1-hop neighbors
        # For now, let's just match any word that looks like a known entity?
        # Or better: Ask LLM to extract "Potential Entites" from query, then search.
        
        # Let's try searching for exact matches of words in text against Node IDs for simplicity first.
        neo4j = await get_neo4j()
        
        words = [w.strip() for w in text.split() if len(w) > 3] # naive tokenizer
        
        found_facts = []
        
        for word in words:
            query = """
            MATCH (n)-[r]-(m)
            WHERE toLower(n.id) CONTAINS toLower($word)
            RETURN n.id, type(r), m.id
            LIMIT 5
            """
            results = await neo4j.execute_read(query, {"word": word})
            if results:
                for r in results:
                    fact = f"{r['n.id']} --[{r['type(r)']}]--> {r['m.id']}"
                    if fact not in found_facts:
                        found_facts.append(fact)
                        
        if found_facts:
            return "GRAPH KNOWLEDGE:\n" + "\n".join(found_facts)
        return ""

graph_memory = GraphMemory()
