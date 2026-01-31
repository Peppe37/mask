from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
from src.core.agents.coordinator import coordinator
from src.core.agents.enhanced_coordinator import enhanced_coordinator  # With web search
from src.core.tool_registry import tool_registry
from src.core.memory.manager import memory_manager
from src.core.memory.models import ChatSession, Project
from src.core.agents.project_manager import project_summarizer
from src.core.agents.title_generator import title_generator
from pydantic import BaseModel

app = FastAPI(title="Mask Agent API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str

class CreateSessionRequest(BaseModel):
    title: str = "New Chat"
    project_id: Optional[str] = None

class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None

class MessageResponse(BaseModel):
    id: Optional[int]
    role: str
    content: str
    created_at: Optional[datetime] = None
    session_id: str
    
    class Config:
        from_attributes = True

@app.on_event("startup")
async def startup_event():
    tool_registry.initialize()
    # Tables are now managed by Alembic migrations
    # Run: alembic upgrade head
    # memory_manager.create_tables()

# --- Projects ---
@app.post("/api/projects", response_model=Project)
async def create_project(request: CreateProjectRequest):
    return memory_manager.create_project(name=request.name, description=request.description)

@app.get("/api/projects", response_model=List[Project])
async def list_projects():
    return memory_manager.list_projects()

@app.post("/api/projects/{project_id}/summary")
async def update_project_summary(project_id: str):
    chats_summary = memory_manager.get_project_chats_summary(project_id)
    project = memory_manager.get_project(project_id)
    new_summary = await project_summarizer.summarize_project(chats_summary, project.context_summary if project else None)
    memory_manager.update_project_context(project_id, new_summary)
    return {"status": "ok", "summary": new_summary}

@app.patch("/api/projects/{project_id}/color")
async def update_project_color(project_id: str, color: str = Body(..., embed=True)):
    memory_manager.update_project_color(project_id, color)
    return {"status": "ok"}

@app.patch("/api/projects/{project_id}/icon")
async def update_project_icon(project_id: str, icon: str = Body(..., embed=True)):
    memory_manager.update_project_icon(project_id, icon)
    return {"status": "ok"}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    memory_manager.delete_project(project_id)
    return {"status": "ok"}

# --- Sessions ---
@app.post("/api/sessions", response_model=ChatSession)
async def create_session(request: CreateSessionRequest):
    return memory_manager.create_session(title=request.title, project_id=request.project_id)

@app.get("/api/sessions", response_model=List[ChatSession])
async def list_sessions():
    return memory_manager.list_sessions()

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    memory_manager.delete_session(session_id)
    return {"status": "ok"}

@app.patch("/api/sessions/{session_id}/rename")
async def rename_session(session_id: str, title: str = Body(..., embed=True)):
    memory_manager.rename_session(session_id, title)
    return {"status": "ok"}

@app.patch("/api/sessions/{session_id}/project")
async def assign_session_to_project(session_id: str, project_id: Optional[str] = Body(None, embed=True)):
    memory_manager.assign_session_to_project(session_id, project_id)
    return {"status": "ok"}

@app.post("/api/sessions/{session_id}/generate-title")
async def generate_session_title(session_id: str, first_message: str = Body(..., embed=True)):
    title = await title_generator.generate_title(first_message)
    memory_manager.rename_session(session_id, title)
    return {"title": title}

@app.get("/api/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(session_id: str):
    messages = memory_manager.get_messages(session_id)
    return messages

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Stream chat responses with web search capabilities."""
    async def generate():
        async for chunk in enhanced_coordinator.run_stream(request.session_id, request.message):
            yield chunk
    
    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
