from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DATABASE_URL: str
    
    # AI Configuration
    GOOGLE_GEMINI_API_KEY: str
    GEMINI_MODEL_FLASH: str = "gemini-2.0-flash-lite"
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    
    # Authentication
    JWT_SECRET: str
    JWT_EXPIRES_IN: str = "7d"
    JWT_ALGORITHM: str = "HS256"
    
    # WhatsApp Configuration
    WHATSAPP_BOT_URL: str = "http://localhost:3000"
    SKIP_WHATSAPP_IN_DEV: bool = True  # Skip WhatsApp in development mode

    class Config:
        env_file = ".env"

settings = Settings()
