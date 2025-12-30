import google.generativeai as genai
from backend.config import Config

class PostGenerationAgent:
    def __init__(self):
        # Using 2.0 Flash Lite for fast generation
        self.model = genai.GenerativeModel('models/gemini-2.0-flash-lite')

    async def generate(self, news_item, user_prefs):
        """
        Generates LinkedIn post content and visual structure.
        """
        prompt = f"""
        Act as a top-tier LinkedIn Content Strategist. 
        News: {news_item['headline']}
        Context: {news_item['context']}
        
        User Preferences:
        - Tone: {user_prefs['tone']}
        - Target Audience: {user_prefs['audience']}
        - Length: {user_prefs['length']}

        TASKS:
        1. Write a high-engagement LinkedIn caption. Use {user_prefs['tone']} tone.
        2. Create a 'Structured Visual Plan' for an infographic. 
           Describe specific blocks (e.g., 'Block 1: Problem statement', 'Block 2: Key stat', 'Block 3: Flowchart').
        3. Visual Style: Recommend minimal editorial colors (Hex: {news_item['palette']['accent']}).

        Return the response in a structured format:
        [CAPTION]
        ...
        [/CAPTION]
        [VISUAL_PLAN]
        ...
        [/VISUAL_PLAN]
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating post: {e}"
