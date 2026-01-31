from src.core.llm.ollama_client import get_llm

class SummarizerAgent:
    def __init__(self):
        self.system_prompt = """You are a helpful assistant that summarizes conversation history.
Your goal is to create a concise summary of the previous conversation while retaining critical information.
Output ONLY the summary text.
"""

    async def summarize(self, history: list[dict]) -> str:
        llm = await get_llm()
        
        conversation_text = ""
        for msg in history:
            conversation_text += f"{msg['role']}: {msg['content']}\n"
            
        prompt = f"Summarize the following conversation:\n\n{conversation_text}"
        
        response = await llm.generate(prompt, system=self.system_prompt, options={"temperature": 0.3})
        return response

summarizer = SummarizerAgent()
