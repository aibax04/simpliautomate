import google.generativeai as genai
from typing import Dict

class VisualPlanningAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def plan_visual(self, news_item: Dict, caption_data: Dict) -> Dict:
        """
        Creates a structured blueprint for an infographic.
        """
        category = news_item.get('category', 'General')
        
        prompt = f"""
        Design a professional infographic blueprint for this news story.
        
        NEWS: {news_item.get('headline')}
        CONTEXT: {news_item.get('context')}
        CATEGORY: {category}
        
        DESIGN RULES:
        1. Style: Editorial, minimal, "Consulting Slide" aesthetic.
        2. Color Palette:
           - Judiciary/Legal -> Greys, Muted Blues, Slate
           - Tech -> Calm Blues, Teals, Clean White
           - Business -> Neutrals, Dark Greens, Beige
           - NO neon, NO gradients.
        3. Content: Convert the text into a visual structure (Pie Chart, Workflow, or Comparison).
        
        OUTPUT FORMAT (JSON):
        {{
            "visual_type": "workflow | pie_chart | comparison | key_stats",
            "title": "Main Chart Title",
            "elements": [
                {{"label": "Step 1/Point A", "detail": "Short text"}},
                {{"label": "Step 2/Point B", "detail": "Short text"}}
            ],
            "color_palette_description": "Descriptive text of colors to be used",
            "image_prompt": "A detailed, descriptive text prompt suitable for an image generation model to create this exact infographic. Mention flat design, white background, high resolution, specific colors, and vector style."
        }}
        Return ONLY valid JSON.
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(text)
        except Exception as e:
            print(f"Visual planning error: {e}")
            return {
                "visual_type": "key_stats",
                "image_prompt": f"A clean, minimal infographic about {category}, flat vector style, white background, professional chart."
            }
