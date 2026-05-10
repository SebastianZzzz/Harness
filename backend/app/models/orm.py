from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from datetime import datetime
import uuid
from app.database import Base

class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_prompt = Column(Text, nullable=False)
    structured_prompt = Column(Text, nullable=True)
    bug_list_constraints = Column(JSON, default=list)
    current_phase = Column(String, default="1_INTENT_PARSING")
    search_provider = Column(String, default="github")
    difficulty_score = Column(Integer, nullable=True)
    selected_model = Column(String, nullable=True)
    generated_code = Column(Text, nullable=True)
    sandbox_iterations = Column(Integer, default=0)
    max_iterations = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
