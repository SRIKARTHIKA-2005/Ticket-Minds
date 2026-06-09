import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import database configs
from backend.database import engine, Base, get_db
from backend.models import User, Ticket, Message
from backend.schemas import (
    UserCreate, UserResponse, LoginRequest, Token,
    TicketCreate, TicketResponse, TicketDetailResponse,
    MessageCreate, MessageResponse
)
from backend.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_client, require_engineer
)
from backend.translator_service import (
    detect_language_code, translate_text, analyze_message_with_ai
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Multilingual Customer Support Platform API",
    description="Backend service with JWT auth, SQLAlchemy SQLite DB, translation, and optional Ollama support.",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables on startup
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def seed_database():
    """Seeds the database with default demo accounts and sample tickets if empty."""
    db = next(get_db())
    try:
        # Check if users already seeded
        user_count = db.query(User).count()
        if user_count == 0:
            logger.info("Database is empty. Seeding default demo accounts...")
            
            # Create users
            users_to_seed = [
                User(
                    username="juan",
                    password_hash=get_password_hash("password123"),
                    role="client",
                    preferred_language="es"
                ),
                User(
                    username="arun",
                    password_hash=get_password_hash("password123"),
                    role="client",
                    preferred_language="ta"
                ),
                User(
                    username="engineer",
                    password_hash=get_password_hash("admin123"),
                    role="engineer",
                    preferred_language="en"
                )
            ]
            
            for user in users_to_seed:
                db.add(user)
            db.commit()
            
            # Refresh to get IDs
            juan_user = db.query(User).filter(User.username == "juan").first()
            arun_user = db.query(User).filter(User.username == "arun").first()
            
            # Create a sample ticket for Arun (Tamil)
            arun_msg_ta = "என் இணையம் வேலை செய்யவில்லை மற்றும் ரூட்டரில் சிவப்பு விளக்கு எரிகிறது"
            arun_msg_en = translate_text(arun_msg_ta, source_lang="ta", target_lang="en")
            arun_ai = analyze_message_with_ai(arun_msg_en)
            
            arun_ticket = Ticket(
                id=f"TICK-{uuid.uuid4().hex[:6].upper()}",
                client_id=arun_user.id,
                title="இணைய இணைப்பு பிரச்சனை",
                status="open",
                priority=arun_ai["priority"],
                sentiment=arun_ai["sentiment"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(arun_ticket)
            
            arun_first_msg = Message(
                ticket_id=arun_ticket.id,
                sender_id=arun_user.id,
                sender_role="client",
                original_text=arun_msg_ta,
                translated_text=arun_msg_en,
                language="ta",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(arun_first_msg)
            
            # Create a sample ticket for Juan (Spanish)
            juan_msg_es = "No puedo acceder a mi cuenta, dice contraseña incorrecta"
            juan_msg_en = translate_text(juan_msg_es, source_lang="es", target_lang="en")
            juan_ai = analyze_message_with_ai(juan_msg_en)
            
            juan_ticket = Ticket(
                id=f"TICK-{uuid.uuid4().hex[:6].upper()}",
                client_id=juan_user.id,
                title="Problema de inicio de sesión",
                status="open",
                priority=juan_ai["priority"],
                sentiment=juan_ai["sentiment"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(juan_ticket)
            
            juan_first_msg = Message(
                ticket_id=juan_ticket.id,
                sender_id=juan_user.id,
                sender_role="client",
                original_text=juan_msg_es,
                translated_text=juan_msg_en,
                language="es",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(juan_first_msg)
            
            db.commit()
            logger.info("Database seeding completed successfully.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

# --- PUBLIC ENDPOINTS ---

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Multilingual Customer Support Platform API",
        "docs": "/docs"
    }

# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/auth/signup", response_model=UserResponse)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user and stores password securely."""
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken."
        )
    
    # Validate role
    if user_data.role not in ["client", "engineer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Supported roles: 'client', 'engineer'."
        )
        
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        role=user_data.role,
        preferred_language=user_data.preferred_language
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates credentials and returns a JWT access token."""
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        preferred_language=user.preferred_language
    )

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the details of the currently authenticated user."""
    return current_user


# --- TICKET ENDPOINTS ---

@app.post("/api/tickets", response_model=TicketDetailResponse)
def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db)
):
    """
    Creates a new support ticket. 
    Detects language of initial message, translates to English, and performs AI analysis.
    """
    initial_text = payload.initial_message.strip()
    if not initial_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial message cannot be empty."
        )
        
    # 1. Detect language
    lang = detect_language_code(initial_text)
    
    # 2. Translate title & message to English
    translated_title = translate_text(payload.title, source_lang=lang, target_lang="en")
    translated_msg = translate_text(initial_text, source_lang=lang, target_lang="en")
    
    # 3. Analyze message sentiment/priority (Ollama or Fallback)
    ai_insights = analyze_message_with_ai(translated_msg)
    
    # 4. Create Ticket
    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    new_ticket = Ticket(
        id=ticket_id,
        client_id=current_user.id,
        title=payload.title,  # Store original title
        status="open",
        priority=ai_insights["priority"],
        sentiment=ai_insights["sentiment"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_ticket)
    
    # 5. Save message
    first_message = Message(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_role="client",
        original_text=initial_text,
        translated_text=translated_msg,
        language=lang,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(first_message)
    
    db.commit()
    db.refresh(new_ticket)
    
    # Format and return detail response
    messages_list = [first_message]
    return TicketDetailResponse(
        id=new_ticket.id,
        client_id=new_ticket.client_id,
        title=new_ticket.title,
        status=new_ticket.status,
        priority=new_ticket.priority,
        sentiment=new_ticket.sentiment,
        created_at=new_ticket.created_at,
        updated_at=new_ticket.updated_at,
        client_username=current_user.username,
        messages=messages_list
    )

@app.get("/api/tickets", response_model=List[TicketResponse])
def get_all_tickets(
    current_user: User = Depends(require_engineer),
    db: Session = Depends(get_db)
):
    """Retrieves all tickets. (Engineers only)"""
    tickets = db.query(Ticket).all()
    # Populate client usernames
    response_tickets = []
    for t in tickets:
        client_username = db.query(User.username).filter(User.id == t.client_id).scalar()
        res = TicketResponse.model_validate(t)
        res.client_username = client_username
        response_tickets.append(res)
    return response_tickets

@app.get("/api/tickets/my", response_model=List[TicketResponse])
def get_my_tickets(
    current_user: User = Depends(require_client),
    db: Session = Depends(get_db)
):
    """Retrieves tickets created by the logged-in client."""
    tickets = db.query(Ticket).filter(Ticket.client_id == current_user.id).all()
    response_tickets = []
    for t in tickets:
        res = TicketResponse.model_validate(t)
        res.client_username = current_user.username
        response_tickets.append(res)
    return response_tickets

@app.get("/api/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves a single ticket and its message list. Also marks incoming client messages as read if engineer opens it."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found."
        )
        
    # Security: Clients can only access their own tickets
    if current_user.role == "client" and ticket.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this ticket."
        )
        
    # Mark messages as read
    if current_user.role == "engineer":
        db.query(Message).filter(
            Message.ticket_id == ticket_id,
            Message.sender_role == "client",
            Message.is_read == False
        ).update({"is_read": True})
        db.commit()
        db.refresh(ticket)
        
    client_username = db.query(User.username).filter(User.id == ticket.client_id).scalar()
    
    # Sort messages chronologically
    sorted_messages = sorted(ticket.messages, key=lambda x: x.created_at)
    
    return TicketDetailResponse(
        id=ticket.id,
        client_id=ticket.client_id,
        title=ticket.title,
        status=ticket.status,
        priority=ticket.priority,
        sentiment=ticket.sentiment,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        client_username=client_username,
        messages=sorted_messages
    )

@app.post("/api/tickets/{ticket_id}/resolve", response_model=TicketResponse)
def resolve_ticket(
    ticket_id: str,
    current_user: User = Depends(require_engineer),
    db: Session = Depends(get_db)
):
    """Resolves a support ticket. (Engineers only)"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found."
        )
        
    ticket.status = "resolved"
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    
    client_username = db.query(User.username).filter(User.id == ticket.client_id).scalar()
    res = TicketResponse.model_validate(ticket)
    res.client_username = client_username
    return res


# --- MESSAGE ENDPOINTS ---

@app.get("/api/tickets/{ticket_id}/messages", response_model=List[MessageResponse])
def get_ticket_messages(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all messages for a ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found."
        )
        
    # Check permissions
    if current_user.role == "client" and ticket.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view messages of this ticket."
        )
        
    # Mark client messages as read if engineer requested
    if current_user.role == "engineer":
        db.query(Message).filter(
            Message.ticket_id == ticket_id,
            Message.sender_role == "client",
            Message.is_read == False
        ).update({"is_read": True})
        db.commit()
        
    # Return sorted messages
    messages = db.query(Message).filter(Message.ticket_id == ticket_id).order_by(Message.created_at.asc()).all()
    return messages

@app.post("/api/tickets/{ticket_id}/messages", response_model=MessageResponse)
def send_message(
    ticket_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sends a message in a ticket.
    Translates automatically based on sender:
    - Client sends native text -> detected lang is translated to English. Update ticket sentiment/priority.
    - Engineer sends English text -> translated back to Client's preferred language.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found."
        )
        
    # Ensure ticket is open
    if ticket.status == "resolved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send messages in a resolved ticket."
        )
        
    # Check permissions
    if current_user.role == "client" and ticket.client_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to message on this ticket."
        )
        
    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    # 1. Translation Routing
    if current_user.role == "client":
        # Client message workflow: Native -> English
        lang = detect_language_code(text)
        translated_text = translate_text(text, source_lang=lang, target_lang="en")
        
        # Update AI sentiment/priority for the ticket based on newest client message
        ai_insights = analyze_message_with_ai(translated_text)
        ticket.priority = ai_insights["priority"]
        ticket.sentiment = ai_insights["sentiment"]
        ticket.updated_at = datetime.utcnow()
        
    else:
        # Engineer message workflow: English -> Client's Preferred Language
        # Find client preferred language
        client = db.query(User).filter(User.id == ticket.client_id).first()
        target_lang = client.preferred_language if client else "en"
        
        lang = target_lang
        translated_text = translate_text(text, source_lang="en", target_lang=target_lang)
        ticket.updated_at = datetime.utcnow()

    # 2. Save Message
    message = Message(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_role=current_user.role,
        original_text=text,
        translated_text=translated_text,
        language=lang,
        is_read=(current_user.role == "engineer"),  # Default: Client messages unread, Engineer messages read
        created_at=datetime.utcnow()
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message
