import os
import json
import re
import urllib.parse
import requests
from backend.config.config import Config

def load_glossary():
    """Loads glossary terms dynamically from the JSON file."""
    try:
        if os.path.exists(Config.GLOSSARY_PATH):
            with open(Config.GLOSSARY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading glossary: {e}")
        return {}

def protect_text(text, glossary):
    """
    Replaces glossary terms in text with placeholders (__GL_index__).
    Returns (protected_text, placeholder_map).
    """
    if not glossary:
        return text, {}
        
    placeholder_map = {}
    
    # Sort terms by length in descending order to avoid partial matches (e.g. 'API Gateway' before 'API')
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    
    # Compile regex pattern to match any of the glossary keys case-insensitively with word boundaries
    pattern_str = r'\b(' + '|'.join(map(re.escape, sorted_terms)) + r')\b'
    pattern = re.compile(pattern_str, re.IGNORECASE)
    
    # We use a mutable container to track placeholders sequentially
    match_index = [0]
    
    def replace_match(match):
        original_word = match.group(1)
        placeholder = f"__GL_{match_index[0]}__"
        placeholder_map[placeholder] = original_word
        match_index[0] += 1
        return placeholder
        
    protected_text = pattern.sub(replace_match, text)
    return protected_text, placeholder_map

def restore_text(translated_text, placeholder_map):
    """
    Restores the original glossary terms in place of placeholders.
    Handles potential translation engine formatting changes like casing and extra spacing.
    """
    restored = translated_text
    for placeholder, original_word in placeholder_map.items():
        # Extracted number from __GL_N__ is placeholder[5:-2]
        # Match pattern allowing for casing variation and arbitrary spaces around characters
        num_str = placeholder[5:-2]
        pattern_str = r'__\s*GL\s*_\s*' + num_str + r'\s*__'
        pattern = re.compile(pattern_str, re.IGNORECASE)
        restored = pattern.sub(original_word, restored)
    return restored

def detect_language(text):
    """
    Detects the language of the provided text using Google Translate services.
    Falls back to 'en' on failure.
    """
    if not text or not text.strip():
        return 'en'
        
    try:
        # If API key is configured, we can use official API (for future production extensibility)
        if Config.GOOGLE_TRANSLATE_API_KEY:
            url = f"https://translation.googleapis.com/language/translate/v2/detect?key={Config.GOOGLE_TRANSLATE_API_KEY}"
            payload = {'q': text}
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                data = r.json()
                return data['data']['detections'][0][0]['language']
        
        # Free fallback / default
        quoted = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={quoted}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            res_json = r.json()
            if len(res_json) > 2 and isinstance(res_json[2], str):
                return res_json[2]
                
    except Exception as e:
        print(f"Error detecting language: {e}")
        
    return 'en'

def translate_text(text, target_lang, source_lang='auto'):
    """
    Translates text with glossary protection using Google Translate API.
    """
    if not text or not text.strip():
        return text
        
    # 1. Load glossary and apply protection
    glossary = load_glossary()
    protected_text, placeholder_map = protect_text(text, glossary)
    
    # 2. Call translation API
    translated_text = protected_text
    try:
        # Official Google API Key Translation
        if Config.GOOGLE_TRANSLATE_API_KEY:
            url = f"https://translation.googleapis.com/language/translate/v2?key={Config.GOOGLE_TRANSLATE_API_KEY}"
            payload = {
                'q': protected_text,
                'target': target_lang,
                'source': source_lang if source_lang != 'auto' else None
            }
            r = requests.post(url, json=payload, timeout=5)
            if r.status_code == 200:
                data = r.json()
                translated_text = data['data']['translations'][0]['translatedText']
        else:
            # Free fallback endpoint using gtx client
            # Split lines or process long text safely (Google Translate gtx supports up to 5000 chars)
            quoted = urllib.parse.quote(protected_text)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={quoted}"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                res_json = r.json()
                # Parse translated parts
                parts = []
                if res_json and isinstance(res_json[0], list):
                    for item in res_json[0]:
                        if item and isinstance(item, list) and len(item) > 0:
                            parts.append(item[0])
                translated_text = "".join(parts)
    except Exception as e:
        print(f"Error during translation: {e}")
        # In case of network errors or API limits, we return the original/protected text as fallback
        return text

    # 3. Restore glossary terms
    final_text = restore_text(translated_text, placeholder_map)
    return final_text

if __name__ == '__main__':
    # Test cases
    test_spanish = "Mi VPN no funciona, por favor revisa el Firewall y la base de datos."
    print("Original Text:", test_spanish)
    
    detected = detect_language(test_spanish)
    print("Detected Language:", detected)
    
    translated = translate_text(test_spanish, 'en')
    print("Translated English:", translated)
    
    translated_back = translate_text("I have reset the Firewall and configured the VPN. Please test your connection.", detected)
    print("Translated back to original language:", translated_back)
