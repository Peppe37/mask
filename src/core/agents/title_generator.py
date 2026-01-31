from src.core.llm.ollama_client import get_llm

class TitleGenerator:
    """Generates concise chat titles from the first user message."""
    
    async def generate_title(self, first_message: str) -> str:
        """Generate a 3-5 word title from the first user message."""
        llm = await get_llm()
        
        prompt = f"""Generate a concise, descriptive title (3-5 words maximum) for a chat conversation that starts with this message:

"{first_message}"

Return ONLY the title, nothing else. No quotes, no extra explanation."""
        
        try:
            response = await llm.chat([
                {"role": "system", "content": "You are a title generator. Generate short, descriptive titles."},
                {"role": "user", "content": prompt}
            ], options={"temperature": 0.5})
            
            title = response.get("content", "").strip().strip('"\'')
            
            # Fallback: truncate first message if LLM fails
            if not title or len(title) > 50:
                title = first_message[:47] + "..." if len(first_message) > 50 else first_message
            
            return title
        except Exception as e:
            print(f"Title generation error: {e}")
            # Fallback to truncated message
            return first_message[:47] + "..." if len(first_message) > 50 else first_message

title_generator = TitleGenerator()
