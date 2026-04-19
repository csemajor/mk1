import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Eventra API"
    VERSION: str = "1.0.0"
    MONGO_URI: str = os.getenv("MONGO_URI", "")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "mark_one")
    GEOAPIFY_API_KEY: str = os.getenv("GEOAPIFY_API_KEY", "")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")


settings = Settings()
