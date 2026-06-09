import requests
import json
import logging
from typing import Dict, Tuple
from deep_translator import GoogleTranslator
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from backend.config import OLLAMA_URL

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "ta": "Tamil",
    "hi": "Hindi",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German"
}

def detect_language_code(text: str) -> str:
    """
    Detects the language code of the text. Defaults to 'en' on failure.
    Enforces check against our supported list; defaults to 'en' if unsupported.
    """
    if not text or not text.strip():
        return "en"
    
    try:
        lang = detect(text)
        logger.info(f"Detected language: {lang} for text: '{text[:30]}...'")
        if lang in SUPPORTED_LANGUAGES:
            return lang
        return "en"
    except LangDetectException as e:
        logger.warning(f"langdetect failed: {e}. Defaulting to 'en'.")
        return "en"
    except Exception as e:
        logger.error(f"Unexpected error in language detection: {e}")
        return "en"

def translate_text(text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
    """
    Translates text from source_lang to target_lang.
    """
    if not text or not text.strip():
        return ""
    
    # If source and target are same, no translation needed
    if source_lang == target_lang:
        return text

    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        logger.info(f"Translated: '{text[:30]}...' ({source_lang}) -> '{translated[:30]}...' ({target_lang})")
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text

def get_available_ollama_model() -> str:
    """
    Checks if Ollama is running and finds a suitable model to use (llama3).
    Returns the name of the model, or an empty string if Ollama is not available.
    """
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if response.status_code == 200:
            models_data = response.json()
            models = [m["name"] for m in models_data.get("models", [])]
            if not models:
                return ""
            
            # Look for llama3
            for model in models:
                if "llama3" in model:
                    return model
            
            logger.info(f"Ollama running. Llama3 not found, using first available: {models[0]}")
            return models[0]
    except requests.exceptions.RequestException:
        pass
    return ""

def rule_based_ai_fallback(message_english: str) -> Tuple[str, str]:
    """
    Rule-based fallback for sentiment and priority detection when Ollama is unavailable.
    """
    msg_lower = message_english.lower()
    
    critical_keywords = [
        "urgent", "not working", "broken", "fail", "error", "down", "crash", 
        "stop", "payment", "charge", "card", "money", "bug", "stuck", 
        "cannot login", "login issue", "security", "hacked", "leak"
    ]
    positive_keywords = [
        "thanks", "thank you", "great", "awesome", "perfect", "good", 
        "solved", "fixed", "appreciate", "love", "fantastic"
    ]
    negative_keywords = [
        "bad", "terrible", "worst", "hate", "angry", "broken", "fail", 
        "error", "stupid", "annoying", "frustrated", "help", "poor"
    ]
    
    is_critical = any(kw in msg_lower for kw in critical_keywords)
    is_positive = any(kw in msg_lower for kw in positive_keywords)
    is_negative = any(kw in msg_lower for kw in negative_keywords)
    
    # Priority
    if is_critical:
        priority = "high"
    elif is_positive:
        priority = "low"
    else:
        priority = "medium"
        
    # Sentiment
    if is_positive:
        sentiment = "positive"
    elif is_negative or is_critical:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    logger.info(f"Rule-based AI Fallback activated. Sentiment: {sentiment}, Priority: {priority}")
    return sentiment, priority

def analyze_message_with_ai(message_english: str) -> Dict[str, str]:
    """
    Analyzes the English translation of the customer's message using Ollama.
    If Ollama is not running or doesn't have models, it falls back to the rule-based system.
    """
    model_to_use = get_available_ollama_model()
    
    if not model_to_use:
        sentiment, priority = rule_based_ai_fallback(message_english)
        return {
            "sentiment": sentiment,
            "priority": priority
        }
    
    prompt = (
        f"You are a helpful customer support AI analyzer. Analyze the following support message:\n"
        f"\" {message_english} \"\n\n"
        f"Provide analysis in JSON format with exactly two fields:\n"
        f"1. \"sentiment\": classification of the message tone. Options: \"positive\", \"neutral\", \"negative\".\n"
        f"2. \"priority\": classification of the ticket urgency. Options: \"low\", \"medium\", \"high\".\n\n"
        f"Do not include any thinking process, introduction, or Markdown wrapping. Return only the JSON object."
    )
    
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model_to_use,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            analysis = json.loads(response_text)
            
            sentiment = str(analysis.get("sentiment", "neutral")).lower()
            priority = str(analysis.get("priority", "medium")).lower()
            
            if sentiment not in ["positive", "neutral", "negative"]:
                sentiment = "neutral"
            if priority not in ["low", "medium", "high"]:
                priority = "medium"
                
            logger.info(f"Ollama AI Success. Model: {model_to_use}. Sentiment: {sentiment}, Priority: {priority}")
            return {
                "sentiment": sentiment,
                "priority": priority
            }
            
    except Exception as e:
        logger.error(f"Ollama query failed: {e}. Falling back to rule-based analysis.")
        
    sentiment, priority = rule_based_ai_fallback(message_english)
    return {
        "sentiment": sentiment,
        "priority": priority
    }
