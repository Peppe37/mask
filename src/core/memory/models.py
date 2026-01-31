from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship
import uuid

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    description: Optional[str] = None
    context_summary: Optional[str] = None
    color: str = Field(default="#7c3aed")  # Default purple accent
    icon: str = Field(default="📁")  # Default folder emoji
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    sessions: List["ChatSession"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class ChatSession(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    project_id: Optional[str] = Field(default=None, foreign_key="projects.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    
    project: Optional[Project] = Relationship(back_populates="sessions")
    messages: List["ChatMessage"] = Relationship(back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id")
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    session: ChatSession = Relationship(back_populates="messages")
