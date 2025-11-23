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

    class Config:
        env_file = ".env"

settings = Settings()
