import os
import google.generativeai as genai
from dotenv import load_dotenv
import sys

import os
import google.generativeai as genai
from dotenv import load_dotenv
import sys

# Removed manual stdout encoding setting to avoid detachment issues

def test_gemini_key():
    # 1. Load the .env file
    load_dotenv()
    
    # 2. Retrieve the key
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Clean the key in case it has quotes
    if api_key:
        api_key = api_key.replace('"', '').replace("'", "").strip()
    
    if not api_key or "your_gemini_api_key_here" in api_key:
        print("[Error] GEMINI_API_KEY not found or is still a placeholder in .env")
        return

    print(f"[Info] Testing API Key (ends in ...{api_key[-4:]})")

    # 3. Configure the SDK
    genai.configure(api_key=api_key)

    try:
        # 4. Use a lightweight model to test connectivity
        # Note: Using gemini-1.5-flash as it is widely available
        # model = genai.GenerativeModel('gemini-1.5-flash')
        # response = model.generate_content("Say 'Gemini is active!' if you can read this.")
        
        print("Listing available models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")

        print("\n[Success] API Key is valid (Models listed successfully).")
        # print(f"Response: {response.text}")
        
    except Exception as e:
        print("\n[Failure] API Connection Failed!")
        print(f"Error Details: {e}")
        print("\nTip: Ensure your key is valid.")

if __name__ == "__main__":
    test_gemini_key()
