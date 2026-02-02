import os
from dotenv import load_dotenv

# Load environment variables from .env file
try:
    load_dotenv(encoding='utf-8-sig')  # Try with BOM handling
except UnicodeDecodeError:
    try:
        load_dotenv(encoding='utf-8')  # Try without BOM
    except UnicodeDecodeError:
        # If both fail, continue without .env loading
        print("WARNING: Could not load .env file due to encoding issues. Using system environment variables only.")

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
    
    # Focused Categories for top 5 ventures only
    CATEGORIES = [
        "HealthTech", "Legal", "Judiciary AI",
        "LLM Models", "Media AI"
    ]

    # Email SMTP Settings
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "notifications@simplii.ai")

    # Social Media API Credentials
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    NEWS_PROVIDER = os.getenv("NEWS_PROVIDER", "newsapi")  # 'newsapi' or 'gnews'
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
    GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
    
    # WhatsApp Integration
    WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
    WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
    WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
    WHATSAPP_ADMIN_PHONE = os.getenv("WHATSAPP_ADMIN_PHONE")

    @staticmethod
    def validate():
        if not Config.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY is not set. News fetching will fail.")
