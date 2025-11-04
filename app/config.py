"""
Configuration module for LLM Analysis Quiz Solver.
Handles environment variables, secrets, and settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Security
SECRET: str = os.getenv("SECRET", "super-secret-string-change-me")
EMAIL: str = os.getenv("EMAIL", "your-email@example.com")

# Server settings
PORT: int = int(os.getenv("PORT", "8000"))
HOST: str = os.getenv("HOST", "0.0.0.0")

# Timeout settings (in seconds)
QUIZ_TIMEOUT: int = int(os.getenv("QUIZ_TIMEOUT", "180"))  # 3 minutes total
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))  # 60 seconds per request
PLAYWRIGHT_TIMEOUT: int = int(os.getenv("PLAYWRIGHT_TIMEOUT", "60000"))  # 60 seconds for page load

# Retry settings
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))  # seconds

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# File handling
MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
TEMP_DIR: str = os.getenv("TEMP_DIR", "/tmp/llm-quiz-agent")

# Create temp directory if it doesn't exist
os.makedirs(TEMP_DIR, exist_ok=True)

