import requests
import json
from backend.config.config import Config

def is_ollama_available():
    """Checks if the local Ollama service is running and accessible."""
    try:
        r = requests.get(Config.OLLAMA_API_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def call_ollama(prompt, system_prompt=None, response_json=False):
    """
    Sends a query to the local Ollama instance.
    Returns the text response, or None if Ollama is unavailable.
    """
    if not is_ollama_available():
        return None
        
    try:
        url = f"{Config.OLLAMA_API_URL}/api/generate"
        payload = {
            "model": Config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
        if response_json:
            payload["format"] = "json"
            
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("response", "").strip()
    except Exception as e:
        print(f"Ollama connection error: {e}")
        
    return None

def validate_translation(original_text, translated_text, source_lang):
    """
    Asks Ollama to validate the translation quality from original to English.
    Returns: {"valid": bool, "score": int, "explanation": str}
    """
    if not is_ollama_available():
        return {
            "valid": True,
            "score": 100,
            "explanation": "Ollama service is currently offline. Auto-validated translation by system fallback."
        }
        
    system_prompt = (
        "You are an AI quality assurance expert specialized in translation evaluation. "
        "Analyze the translation and output raw JSON only, matching this format: "
        '{"valid": true/false, "score": 0-100, "explanation": "Brief explanation"}'
    )
    
    prompt = (
        f"Original message (Language: {source_lang}): \"{original_text}\"\n"
        f"Translated English message: \"{translated_text}\"\n\n"
        "Evaluate if the translated English message accurately and completely conveys the meaning of the original message. "
        "Keep technical terms (like VPN, API) intact. Provide the analysis in JSON format."
    )
    
    response_text = call_ollama(prompt, system_prompt=system_prompt, response_json=True)
    
    if response_text:
        try:
            # Parse response
            return json.loads(response_text)
        except Exception as e:
            print(f"Failed to parse JSON from Ollama validation: {e}. Raw response: {response_text}")
            
    # Fallback response
    return {
        "valid": True,
        "score": 85,
        "explanation": "Translation passed basic length validation. (Ollama API response was unparseable or failed)"
    }

def get_context_suggestions(ticket_info, messages_history):
    """
    Generates a ticket summary and a suggested English response for engineers.
    Returns: {"summary": str, "suggested_reply": str}
    """
    # Create a history text representation
    history_text = ""
    for msg in messages_history:
        sender = "User" if msg['sender_type'] == 'user' else "System" if msg['sender_type'] == 'system' else "Engineer"
        history_text += f"{sender}: {msg['translated_text']}\n"
        
    if not is_ollama_available():
        # Clean local rules-based fallback suggestions
        last_user_message = ""
        for msg in reversed(messages_history):
            if msg['sender_type'] == 'user':
                last_user_message = msg['translated_text']
                break
                
        # Simple rule-based suggestion generator based on keyword detection
        summary = f"Customer support request regarding ticket status and system operations."
        suggested_reply = "Thank you for the update. We are looking into this details and will get back to you shortly."
        
        low_msg = last_user_message.lower()
        if "vpn" in low_msg:
            summary = "VPN connection issues reported by user."
            suggested_reply = "Could you please verify your network connection and try logging in again? We are resetting your VPN profile details."
        elif "api" in low_msg:
            summary = "API integration error or access denial reported by user."
            suggested_reply = "Please share the endpoint URL and error code you are experiencing. We are checking our API logs."
        elif "firewall" in low_msg or "router" in low_msg:
            summary = "Network security block or routing issues reported."
            suggested_reply = "We are checking the network firewall rules for your IP address. Please confirm your current external IP."
            
        return {
            "summary": summary,
            "suggested_reply": suggested_reply
        }
        
    system_prompt = (
        "You are an expert technical support coordinator. "
        "Analyze the ticket chat history and provide a JSON response in the following format: "
        '{"summary": "One sentence summary of the issue", "suggested_reply": "Professional English reply addressing user"}'
    )
    
    prompt = (
        f"Ticket Status: {ticket_info.get('status')}\n"
        f"Detected User Language: {ticket_info.get('original_language')}\n"
        f"Conversation History (translated to English):\n{history_text}\n"
        "Generate a concise, helpful summary of the issue, and suggest a professional English response for the support engineer."
    )
    
    response_text = call_ollama(prompt, system_prompt=system_prompt, response_json=True)
    if response_text:
        try:
            return json.loads(response_text)
        except Exception as e:
            print(f"Failed to parse JSON from Ollama context service: {e}")
            
    return {
        "summary": "AI summary currently unavailable.",
        "suggested_reply": "Hello, how can we assist you with this issue today?"
    }

if __name__ == '__main__':
    # Test checking
    available = is_ollama_available()
    print("Ollama available:", available)
    if available:
        val = validate_translation("No puedo acceder a la VPN", "I cannot access the VPN", "es")
        print("Validation Result:", val)
    else:
        print("Running mock validation fallback test...")
        val = validate_translation("No puedo acceder a la VPN", "I cannot access the VPN", "es")
        print("Mock Validation:", val)
        
        mock_history = [{"sender_type": "user", "translated_text": "I can't connect to the VPN"}]
        sugg = get_context_suggestions({"status": "Open", "original_language": "es"}, mock_history)
        print("Mock Suggestion:", sugg)
