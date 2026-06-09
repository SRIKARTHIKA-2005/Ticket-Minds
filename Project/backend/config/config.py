import os

class Config:
    # Flask application secret key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ticketminds-super-secret-key-1337')
    
    # Paths
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'ticketminds.db')
    GLOSSARY_PATH = os.path.join(BASE_DIR, 'data', 'glossary.json')
    SYSTEM_MESSAGES_PATH = os.path.join(BASE_DIR, 'data', 'system_messages.json')
    
    # AI and Translation Configurations
    OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3')  # Fallback to llama3, customizable
    
    # Optional Official Google Translate API key
    GOOGLE_TRANSLATE_API_KEY = os.environ.get('GOOGLE_TRANSLATE_API_KEY', None)
