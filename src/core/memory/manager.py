from datetime import datetime
import uuid
from typing import List, Optional
from sqlmodel import Session, select, desc, SQLModel
from src.core.database.postgres import get_postgres_engine
from src.core.memory.models import ChatSession, ChatMessage, Project

class MemoryManager:
    def __init__(self):
        self.engine = get_postgres_engine()
    
    def create_tables(self):
        SQLModel.metadata.create_all(self.engine)

    # --- Projects ---
    def create_project(self, name: str, description: str = None) -> Project:
        project_id = str(uuid.uuid4())
        project = Project(id=project_id, name=name, description=description)
        with Session(self.engine) as session:
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def get_project(self, project_id: str) -> Optional[Project]:
        with Session(self.engine) as session:
            return session.get(Project, project_id)

    def list_projects(self) -> List[Project]:
        with Session(self.engine) as session:
            statement = select(Project).order_by(desc(Project.created_at))
            return session.exec(statement).all()

    def update_project_context(self, project_id: str, context: str):
        with Session(self.engine) as session:
            project = session.get(Project, project_id)
            if project:
                project.context_summary = context
                session.add(project)
                session.commit()
    
    def update_project_color(self, project_id: str, color: str):
        with Session(self.engine) as session:
            project = session.get(Project, project_id)
            if project:
                project.color = color
                session.add(project)
                session.commit()
    
    def update_project_icon(self, project_id: str, icon: str):
        with Session(self.engine) as session:
            project = session.get(Project, project_id)
            if project:
                project.icon = icon
                session.add(project)
                session.commit()
    
    def delete_project(self, project_id: str):
        with Session(self.engine) as session:
            project = session.get(Project, project_id)
            if project:
                session.delete(project)
                session.commit()

    def get_project_chats_summary(self, project_id: str) -> str:
        """Collects summaries/last messages from all chats in the project for context generation."""
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.project_id == project_id)
            chats = session.exec(statement).all()
            
            summary_parts = []
            for chat in chats:
                # Naive: get last few messages or a stored summary if we had one per chat
                msgs = self.get_messages(chat.id)
                chat_text = "\n".join([f"{m.role}: {m.content}" for m in msgs[-5:]]) # Last 5 messages
                if chat_text:
                    summary_parts.append(f"--- Chat '{chat.title or chat.id}' ---\n{chat_text}\n")
            
            return "\n".join(summary_parts)

    # --- Sessions ---
    def create_session(self, title: str = None, project_id: str = None) -> ChatSession:
        session_id = str(uuid.uuid4())
        chat_session = ChatSession(id=session_id, title=title, project_id=project_id)
        with Session(self.engine) as session:
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        with Session(self.engine) as session:
            return session.get(ChatSession, session_id)

    def list_sessions(self) -> List[ChatSession]:
        with Session(self.engine) as session:
            statement = select(ChatSession).order_by(desc(ChatSession.created_at))
            results = session.exec(statement)
            return results.all()

    def delete_session(self, session_id: str):
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session:
                session.delete(chat_session)
                session.commit()
    
    def rename_session(self, session_id: str, new_title: str):
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session:
                chat_session.title = new_title
                session.add(chat_session)
                session.commit()
    
    def assign_session_to_project(self, session_id: str, project_id: str | None):
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if chat_session:
                chat_session.project_id = project_id
                session.add(chat_session)
                session.commit()

    def add_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        with Session(self.engine) as session:
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        with Session(self.engine) as session:
            statement = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
            results = session.exec(statement)
            return results.all()

    def update_messages(self, session_id: str, messages: List[dict]):
        """
        Replaces all messages in a session with a new list (useful for summarization).
        """
        with Session(self.engine) as session:
            # Delete existing messages
            statement = select(ChatMessage).where(ChatMessage.session_id == session_id)
            results = session.exec(statement)
            for msg in results:
                session.delete(msg)
            
            # Add new messages
            for msg_data in messages:
                msg = ChatMessage(session_id=session_id, role=msg_data["role"], content=msg_data["content"])
                session.add(msg)
            
            session.commit()

memory_manager = MemoryManager()
