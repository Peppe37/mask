from src.core.llm.ollama_client import get_llm

class ProjectSummarizerAgent:
    def __init__(self):
        self.system_prompt = """You are a Project Manager expert at synthesizing information.
Your task is to create a high-level "Project Context" based on summaries of multiple chat logs within a project.
Identify key decisions, recurring themes, and ongoing tasks.
Output ONLY the summary text.
"""

    async def summarize_project(self, chats_summary: str, current_summary: str = None) -> str:
        llm = await get_llm()

        prompt = f"""
Existing Project Context:
{current_summary or "None"}

Updates from Chats:
{chats_summary}

Based on the above, create an updated, consolidated Project Context.
"""
        response = await llm.generate(prompt, system=self.system_prompt, options={"temperature": 0.3})
        return response

project_summarizer = ProjectSummarizerAgent()
