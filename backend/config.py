import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database/support.db")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-123456789-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 1 day
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
