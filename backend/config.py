import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
    
    # Categories for filtering as requested
    CATEGORIES = ["Technology", "Judiciary/Legal Tech", "Business"]

    @staticmethod
    def validate():
        if not Config.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY is not set. News fetching will fail.")
