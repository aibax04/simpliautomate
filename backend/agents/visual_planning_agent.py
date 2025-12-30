import google.generativeai as genai
from typing import Dict

class VisualPlanningAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def plan_visual(self, news_item: Dict, caption_data: Dict) -> Dict:
        """
        Creates a structured blueprint for an ultra-high-quality editorial infographic.
        """
        category = news_item.get('category', 'General')
        headline = news_item.get('headline', 'Breaking News')
        context = news_item.get('context', '')
        
        prompt = f"""
        Design a premium, professional editorial infographic blueprint for this news story.
        
        NEWS HEADLINE: {headline}
        CONTEXT: {context}
        PRIMARY DOMAIN: {category}
        
        EDITORIAL DESIGN PRINCIPLES:
        1. Resolution: 4K quality, ultra-sharp typography, pixel-perfect alignment.
        2. Style: Senior Visual Journalist aesthetic. Minimalist, high information density, credible.
        3. Visual Metaphor: Use a central visual related to the domain (e.g., Gavel for Legal, Stethoscope/DNA for Health, Dashboard for Business).
        4. Structure: 
           - BOLD HEADLINE at the top.
           - 1-line Subheading for context.
           - Balanced grid with charts (bar/flow/comparison) and labeled icons.
           - Small text blocks for "What happened", "Why it matters", and "Impact".
        
        SPECIFIC DOMAIN PALETTES:
        - Legal AI -> Charcoal, Slate, Muted Blue, Parchment.
        - Healthcare AI -> Clinical White, Teal, Soft Green, Clinical Grey.
        - Business AI -> Black, Muted Navy, Accent Orange, Grey.
        
        STRICT RULES:
        - NO neon colors, NO glowing effects, NO surreal/generic AI art.
        - Background: Subtle premium texture (e.g., fine paper, frosted glass).
        
        OUTPUT FORMAT (JSON):
        {{
            "visual_type": "workflow | data_comparison | impact_map | timeline",
            "title": "Editorial Headline for the image",
            "subheading": "One line context",
            "central_metaphor": "Specific description of the main center element",
            "color_palette": "List of specific hex-like color names",
            "image_prompt": "An ultra-detailed, descriptive 4K prompt for an image generator. Include 'professional visual journalism', 'data visualization', 'modern editorial layout', 'crisp vector text', 'no surrealism', 'flat premium design', 'high information density'."
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
                "visual_type": "impact_map",
                "image_prompt": f"Professional 4K editorial infographic about {category}, {headline}. Flat design, slate and charcoal palette, crisp typography, clean visual journalism style, high resolution."
            }
