import asyncio
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from backend.agents.image_agent import ImageAgent
from backend.agents.visual_planning_agent import VisualPlanningAgent
from backend.config import Config

load_dotenv()
genai.configure(api_key=Config.GEMINI_API_KEY)

async def test_futuristic_image():
    print("Testing FUTURISTIC Image Generation Style...")
    vpa = VisualPlanningAgent()
    ia = ImageAgent()
    
    news_item = {
        "headline": "Next-Gen Business AI Predicts Market Shifts with Neural Precision",
        "summary": "Enterprise AI is moving beyond simple analysis into predictive neural modeling, allowing startups to outpace incumbents in real-time decision making.",
        "domain": "Business AI"
    }
    caption_data = {"strategic_insights": ["Neural predictive models", "Real-time decision speed", "Startup advantage"]}
    
    print("Step 1: Planning visual...")
    plan = await vpa.plan_visual(news_item, caption_data)
    print(f"Plan image_prompt: {plan.get('image_prompt')}")
    print(f"Aesthetic Tokens: {plan.get('aesthetic_tokens')}")
    
    print("\nStep 2: Generating image...")
    try:
        image_url = await ia.generate_image(plan)
        print(f"\n[SUCCESS] Image generated: {image_url}")
        
        project_root = os.path.abspath(os.path.dirname(__file__))
        path_parts = image_url.split('/')
        filepath = os.path.join(project_root, "frontend", "generated_images", path_parts[-1])
        
        if os.path.exists(filepath):
            print(f"Verified: File exists at {filepath}")
            print(f"File size: {os.path.getsize(filepath)} bytes")
        else:
            print(f"Error: File NOT found at {filepath}")
            
    except Exception as e:
        print(f"\n[FAILURE] Image generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_futuristic_image())
