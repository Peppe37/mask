import os
from src.core.llm.ollama_client import get_llm

WARNING_MSG = "> [!NOTE]\n> Storing sensitive data in a plain text file is not secure."

class UserProfileManager:
    def __init__(self, file_path: str = "WHO.md"):
        self.file_path = file_path
        # Ensure file exists
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                f.write("# User Profile\n\n## Personal Information\n- Name: unknown\n\n## Interests\n- unknown\n\n## Notes\n- None\n")

    def get_profile(self) -> str:
        """Reads the WHO.md file."""
        try:
            with open(self.file_path, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error reading profile: {e}"

    async def update_profile(self, user_input: str):
        """Extracts info from user input and updates WHO.md."""
        current_profile = self.get_profile()
        llm = await get_llm()

        system_prompt = """You are a Profile Manager. Your job is to update the User Profile (Markdown) based on the User's latest message.
Rules:
1. ONLY extract permanent attributes: Name, Email, Phone, Interests, Skills, Preferences.
2. DO NOT extract temporary states (e.g., "I am hungry", "I am going to the shop").
3. Update the existing Markdown structure sensibly.
4. If the user input contains NO relevant personal info, return "NO_UPDATE".
5. Output the FULL updated Markdown content if there is an update.
"""

        prompt = f"""
Current Profile:
{current_profile}

User Input:
"{user_input}"

Return updated Markdown or "NO_UPDATE".
"""
        max_retries = 3
        for _ in range(max_retries):
            try:
                response_msg = await llm.chat([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ])
                new_content = response_msg.get("content", "").strip()
                
                if new_content == "NO_UPDATE":
                    return

                # Sanity check: ensure it looks like markdown
                if "# User Profile" in new_content:
                    with open(self.file_path, "w") as f:
                        f.write(new_content)
                    print("[UserProfileManager] Profile updated.")
                    return
            except Exception as e:
                print(f"[UserProfileManager] extraction error: {e}")

user_profile_manager = UserProfileManager()
