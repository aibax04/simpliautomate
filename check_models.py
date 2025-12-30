import google.generativeai as genai
from backend.config import Config
import os

genai.configure(api_key=Config.GEMINI_API_KEY)

print("Listing models...")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Name: {m.name}")
        # print(f"Supported methods: {m.supported_generation_methods}")
