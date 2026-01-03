import google.generativeai as genai
from typing import Dict

class VisualPlanningAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def plan_visual(self, news_item: Dict, caption_data: Dict, user_prefs: Dict) -> Dict:
        """
        Creates an elite-tier studio-grade blueprint for a professional editorial infographic.
        If it's a custom post, it sticks strictly to the user's prompt and creative style.
        """
        is_custom = news_item.get('is_custom', False)
        domain = news_item.get('domain', 'AI Intelligence')
        headline = news_item.get('headline', 'Breaking News')
        summary = news_item.get('summary', '')
        # Leverage high-level strategic insights from the caption strategist
        strategic_insights = caption_data.get('strategic_insights', [])
        
        image_style = user_prefs.get('image_style', 'Futuristic')
        image_palette = user_prefs.get('image_palette', 'Multi-color vibrant')

        if is_custom:
            persona = "Elite Creative Director and Visual Strategist"
            objective = f"Design a high-fidelity visual based strictly on this custom request: '{summary}'."
            guidelines = f"""
            1. CONTENT FIDELITY: The visual MUST focus 100% on the user's prompt: '{summary}'. Do NOT frame this as 'news' or an 'article' if it's a creative or abstract request.
            2. THEMATIC FOCUS: If the user asks for an object (e.g., 'a robot'), the core of the visual should be that object in the requested style.
            3. STYLE ADHERENCE: Strictly follow the style '{image_style}' and palette '{image_palette}'.
            4. INFO OVERLAY: Integrate the strategic insights ({strategic_insights}) as elegant, non-intrusive textual overlays that complement the main subject.
            """
            visual_type = "custom_creative_piece"
        else:
            persona = "Elite Data Journalist and Visual Editor at a top-tier newsroom (NYT, Bloomberg)"
            objective = f"Design an elite editorial infographic for this news update: '{headline}'."
            guidelines = """
            1. Information Density: Rich layout with multiple visual layers.
            2. Supporting Elements: A primary data visualization and at least two 'Insight Cards' using the provided strategic insights.
            3. Editorial Hierarchy: Clear visual flow from Headline -> Summary -> Deep Dive.
            """
            visual_type = "studio_grade_infographic"

        prompt = f"""
        Act as an {persona}.
        {objective}
        
        GOAL: {guidelines}
        
        MANDATORY STYLE: {image_style}
        MANDATORY COLOR PALETTE: {image_palette}
        
        STRATEGIC INSIGHTS TO INCLUDE: {strategic_insights}
        
        STRICT RULES:
        1. Linguistic Excellence: All text must be 100% free of spelling errors.
        2. Alignment: Headings center-aligned, body text left-aligned.
        3. Constraints: No small text line may exceed 8 words. Use simple, common English only.
        
        OUTPUT FORMAT (JSON):
        {{
            "visual_type": "{visual_type}",
            "style": "{image_style}",
            "palette_preference": "{image_palette}",
            "headline_hierarchy": {{
                "main": "{summary if is_custom else headline}",
                "sub": "{'' if is_custom else 'Contextual sub-headline'}"
            }},
            "visual_layers": [
                {{"type": "primary_subject", "description": "The core visual representation of the prompt"}},
                {{"type": "insight_overlays", "description": "How the strategic insights are visually integrated"}}
            ],
            "image_prompt": "An elite-tier 4K 4:5 vertical masterpiece. SUBJECT: {summary if is_custom else headline}. STYLE: {image_style}. PALETTE: {image_palette}. {f'Ensure it strictly represents {summary} without generic news framing.' if is_custom else 'High-fidelity editorial infographic layout.'} Razor-sharp edges, perfect alignment, zero spelling errors."
        }}
        Return ONLY valid JSON.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(text)
        except Exception as e:
            print(f"Visual planning error: {e}")
            return {
                "visual_type": "studio_grade_infographic",
                "image_prompt": f"Elite 4K editorial infographic about {domain}, {headline}. High-fidelity design studio output, complex visual hierarchy, rich data visualization, modern layout, premium slate palette, razor-sharp text."
            }
