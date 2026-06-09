from flask import Blueprint, request, jsonify, session
import json
import os
from functools import wraps
from backend.database.db_mgr import get_db_connection
from backend.config.config import Config
from backend.translations import translator
from backend.ai import ollama_service

tickets_bp = Blueprint('tickets', __name__)

def login_required(role=None):
    """Decorator to enforce authentication and optional role-based access control."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({"error": "Unauthorized. Please log in first."}), 401
            if role and session.get('role') != role:
                return jsonify({"error": f"Forbidden. Requires role: {role}"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def load_system_config():
    """Loads system configuration messages dynamically."""
    try:
        if os.path.exists(Config.SYSTEM_MESSAGES_PATH):
            with open(Config.SYSTEM_MESSAGES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading system messages: {e}")
    return {
        "acknowledgement_template": "Thank you for contacting TicketMinds. Your request has been received successfully. Our support team will review your issue and respond as soon as possible.",
        "default_status": "Open"
    }

@tickets_bp.route('', methods=['POST'])
@login_required(role='user')
def create_ticket():
    data = request.get_json() or {}
    message_text = data.get('message', '').strip()
    
    if not message_text:
        return jsonify({"error": "Message content is required to raise a ticket."}), 400
        
    user_id = session['user_id']
    
    # 1. Detect language
    original_lang = translator.detect_language(message_text)
    
    # 2. Translate user message to English (with glossary protection applied internally)
    translated_text = translator.translate_text(message_text, 'en', original_lang)
    
    # Optional validation with Ollama if running
    ollama_service.validate_translation(message_text, translated_text, original_lang)
    
    # 3. Generate system acknowledgement
    sys_config = load_system_config()
    ack_template = sys_config.get(
        "acknowledgement_template", 
        "Thank you for contacting TicketMinds. Your request has been received successfully. Our support team will review your issue and respond as soon as possible."
    )
    
    # Translate acknowledgement to user's native language
    # If the user's language is English, translation will return the same string.
    translated_ack = translator.translate_text(ack_template, original_lang, 'en')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Generate sequential Ticket ID
        cursor.execute("SELECT COUNT(*) as cnt FROM tickets")
        row = cursor.fetchone()
        count = row['cnt'] if row else 0
        ticket_id = f"TM-{1001 + count}"
        
        # Insert Ticket
        status = sys_config.get("default_status", "Open")
        cursor.execute(
            "INSERT INTO tickets (ticket_id, user_id, original_language, status) VALUES (?, ?, ?, ?)",
            (ticket_id, user_id, original_lang, status)
        )
        
        # Insert User's original & translated message
        cursor.execute(
            "INSERT INTO messages (ticket_id, sender_type, original_text, translated_text) VALUES (?, ?, ?, ?)",
            (ticket_id, 'user', message_text, translated_text)
        )
        
        # Insert System acknowledgement message (original translated ack, and translated_text holds the English template)
        cursor.execute(
            "INSERT INTO messages (ticket_id, sender_type, original_text, translated_text) VALUES (?, ?, ?, ?)",
            (ticket_id, 'system', translated_ack, ack_template)
        )
        
        conn.commit()
        
        return jsonify({
            "message": "Ticket raised successfully.",
            "ticket": {
                "ticket_id": ticket_id,
                "status": status,
                "original_language": original_lang,
                "created_at": "Just now"
            },
            "user_message": {
                "original": message_text,
                "translated": translated_text
            },
            "system_ack": {
                "original": ack_template,
                "translated": translated_ack
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Database error during ticket creation: {str(e)}"}), 500
    finally:
        conn.close()

@tickets_bp.route('', methods=['GET'])
def list_tickets():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    role = session['role']
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if role == 'user':
            # Users only see their own tickets
            cursor.execute("""
                SELECT t.*, u.email as user_email 
                FROM tickets t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.user_id = ? 
                ORDER BY t.created_at DESC
            """, (user_id,))
        else:
            # Engineers see all tickets
            cursor.execute("""
                SELECT t.*, u.email as user_email 
                FROM tickets t 
                JOIN users u ON t.user_id = u.id 
                ORDER BY t.created_at DESC
            """)
            
        tickets_list = []
        for row in cursor.fetchall():
            tickets_list.append({
                "id": row["id"],
                "ticket_id": row["ticket_id"],
                "user_id": row["user_id"],
                "user_email": row["user_email"],
                "original_language": row["original_language"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
            
        return jsonify({"tickets": tickets_list}), 200
    except Exception as e:
        return jsonify({"error": f"Database error fetching tickets: {str(e)}"}), 500
    finally:
        conn.close()

@tickets_bp.route('/<ticket_id>', methods=['GET'])
def get_ticket_details(ticket_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    role = session['role']
    user_id = session['user_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch ticket details
        cursor.execute("""
            SELECT t.*, u.email as user_email 
            FROM tickets t 
            JOIN users u ON t.user_id = u.id 
            WHERE t.ticket_id = ?
        """, (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # Ensure user can only view their own ticket
        if role == 'user' and ticket['user_id'] != user_id:
            return jsonify({"error": "Access denied"}), 403
            
        # Fetch ticket messages
        cursor.execute("""
            SELECT * FROM messages 
            WHERE ticket_id = ? 
            ORDER BY created_at ASC
        """, (ticket_id,))
        
        messages_list = []
        for msg in cursor.fetchall():
            messages_list.append({
                "id": msg["id"],
                "sender_type": msg["sender_type"],
                "original_text": msg["original_text"],
                "translated_text": msg["translated_text"],
                "created_at": msg["created_at"]
            })
            
        ticket_info = {
            "ticket_id": ticket["ticket_id"],
            "user_email": ticket["user_email"],
            "original_language": ticket["original_language"],
            "status": ticket["status"],
            "created_at": ticket["created_at"],
            "updated_at": ticket["updated_at"]
        }
        
        response_data = {
            "ticket": ticket_info,
            "messages": messages_list
        }
        
        # If engineer, load context suggestions and summary from Ollama
        if role == 'engineer':
            ai_suggestions = ollama_service.get_context_suggestions(ticket_info, messages_list)
            response_data["ai_suggestions"] = ai_suggestions
            
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": f"Database error fetching ticket details: {str(e)}"}), 500
    finally:
        conn.close()

@tickets_bp.route('/<ticket_id>/status', methods=['PUT'])
@login_required(role='engineer')
def update_ticket_status(ticket_id):
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()
    
    sys_config = load_system_config()
    allowed_statuses = sys_config.get("ticket_statuses", ["Open", "In Progress", "Resolved", "Closed"])
    
    if new_status not in allowed_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(allowed_statuses)}"}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check existence
        cursor.execute("SELECT id FROM tickets WHERE ticket_id = ?", (ticket_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Ticket not found"}), 404
            
        cursor.execute(
            "UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = ?",
            (new_status, ticket_id)
        )
        conn.commit()
        return jsonify({"message": f"Ticket status updated to {new_status} successfully.", "status": new_status}), 200
    except Exception as e:
        return jsonify({"error": f"Database error updating status: {str(e)}"}), 500
    finally:
        conn.close()

@tickets_bp.route('/glossary', methods=['GET'])
def get_glossary():
    """Returns the protected glossary terms list."""
    from backend.translations.translator import load_glossary
    return jsonify(load_glossary()), 200

