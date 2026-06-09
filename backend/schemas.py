from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "client"  # "client" or "engineer"
    preferred_language: str = "en"  # "en", "es", "ta", "hi", "fr", "de"

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    preferred_language: str

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str


# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    preferred_language: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# --- Message Schemas ---
class MessageCreate(BaseModel):
    text: str

class MessageResponse(BaseModel):
    id: int
    ticket_id: str
    sender_id: int
    sender_role: str
    original_text: str
    translated_text: str
    language: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Ticket Schemas ---
class TicketCreate(BaseModel):
    title: str
    initial_message: str

class TicketResponse(BaseModel):
    id: str
    client_id: int
    title: str
    status: str
    priority: str
    sentiment: str
    created_at: datetime
    updated_at: datetime
    client_username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TicketDetailResponse(TicketResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
