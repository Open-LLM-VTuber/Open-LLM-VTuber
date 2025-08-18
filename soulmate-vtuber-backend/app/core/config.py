from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = "YOUR_API_KEY_HERE"

    class Config:
        env_file = ".env"

settings = Settings()
