import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
    LINKEDIN_USER_URN = os.getenv("LINKEDIN_USER_URN")
    
    # Production Security
    SECRET_KEY = os.getenv("SECRET_KEY", "prod-secret-change-this-in-render-env")
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Expanded Categories for variety and domain-specific news
    CATEGORIES = [
        "HealthTech", "FinTech", "LLMOps", "Industrial IoT", 
        "Urban Tech", "LegalTech", "HR Tech", "Generative NLP", 
        "Industrial AI", "Secure AI", "Consumer AI", "EdTech", 
        "AI in Marketing", "CivicTech"
    ]

    @staticmethod
    def validate():
        if not Config.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY is not set. News fetching will fail.")
