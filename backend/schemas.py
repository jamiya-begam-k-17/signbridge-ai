from pydantic import BaseModel
from typing import Optional
from models import UserRole
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[UserRole] = UserRole.student

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ConversationCreate(BaseModel):
    student_id: int

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    teacher_id: int
    student_id: int
    created_at: Optional[datetime] = None
    student_username: Optional[str] = None
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True
