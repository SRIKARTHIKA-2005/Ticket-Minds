from flask import Blueprint, request, jsonify, session
from backend.database.db_mgr import get_db_connection
from backend.translations import translator
from backend.routes.tickets import login_required

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('', methods=['POST'])
@login_required()
def send_message():
    data = request.get_json() or {}
    ticket_id = data.get('ticket_id', '').strip()
    text = data.get('text', '').strip()
    
    if not ticket_id or not text:
        return jsonify({"error": "ticket_id and text are required"}), 400
        
    sender_type = session['role'] # 'user' or 'engineer'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check ticket existence and retrieve original language
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404
            
        # If user, ensure they own the ticket
        if sender_type == 'user' and ticket['user_id'] != session['user_id']:
            return jsonify({"error": "Access denied"}), 403
            
        original_lang = ticket['original_language']
        
        if sender_type == 'user':
            # User types in native language
            # Detect language to handle if they write in a different language than ticket startup
            detected_lang = translator.detect_language(text)
            
            # Translate user message to English (keeps glossary protected)
            translated_text = translator.translate_text(text, 'en', detected_lang)
            
            # If the user changed their input language, update ticket original language so engineer knows
            if detected_lang != original_lang and detected_lang != 'en':
                cursor.execute(
                    "UPDATE tickets SET original_language = ? WHERE ticket_id = ?",
                    (detected_lang, ticket_id)
                )
                
            original_text = text
            translated_text = translated_text
            
        else: # sender_type == 'engineer'
            # Engineer replies in English
            # Translate reply to user's native language
            translated_text = translator.translate_text(text, original_lang, 'en')
            
            original_text = translated_text # The user's language text is stored in original_text
            translated_text = text          # The engineer's English text is stored in translated_text
            
            # Auto-update status to "In Progress" if the status is "Open" when engineer replies
            if ticket['status'] == 'Open':
                cursor.execute(
                    "UPDATE tickets SET status = 'In Progress', updated_at = CURRENT_TIMESTAMP WHERE ticket_id = ?",
                    (ticket_id,)
                )
        
        # Insert message
        cursor.execute(
            "INSERT INTO messages (ticket_id, sender_type, original_text, translated_text) VALUES (?, ?, ?, ?)",
            (ticket_id, sender_type, original_text, translated_text)
        )
        conn.commit()
        
        return jsonify({
            "message": "Message sent successfully.",
            "data": {
                "ticket_id": ticket_id,
                "sender_type": sender_type,
                "original_text": original_text,
                "translated_text": translated_text,
                "created_at": "Just now"
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Database error sending message: {str(e)}"}), 500
    finally:
        conn.close()
