from pydantic import BaseModel, Field
from typing import Callable, Any, Optional, List, Dict, Awaitable

class Tool(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Awaitable[Any]]

class Agent(BaseModel):
    name: str
    description: str
    system_prompt: str
    tools: List[Tool] = Field(default_factory=list)

class Plugin(BaseModel):
    name: str
    description: str
    version: str = "0.1.0"
    agents: List[Agent] = Field(default_factory=list)
    tools: List[Tool] = Field(default_factory=list)

    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        pass
