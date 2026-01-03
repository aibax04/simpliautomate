import google.generativeai as genai
from typing import Dict

class VisualPlanningAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def plan_visual(self, news_item: Dict, caption_data: Dict, user_prefs: Dict) -> Dict:
        """
        Creates an elite-tier studio-grade blueprint for a professional editorial infographic.
        Pushes for maximum visual richness, information density, and sophisticated hierarchy.
        """
        # Updated to use new field names: headline, summary, domain
        domain = news_item.get('domain', 'AI Intelligence')
        headline = news_item.get('headline', 'Breaking News')
        summary = news_item.get('summary', '')
        # Leverage high-level strategic insights from the caption strategist
        strategic_insights = caption_data.get('strategic_insights', [])
        
        image_style = user_prefs.get('image_style', 'Futuristic')
        image_palette = user_prefs.get('image_palette', 'Multi-color vibrant')

        prompt = f"""
        Design an elite, studio-grade editorial infographic blueprint for a premium LinkedIn post.
        
        GOAL: Elevate visual richness and professional data journalism to the highest possible level. 
        It MUST look like a handcrafted masterpiece from a top-tier newsroom (NYT, Bloomberg, Reuters) or strategy firm (McKinsey, BCG).

        MANDATORY STYLE: {image_style}
        MANDATORY COLOR PALETTE: {image_palette}

        NEWS DETAILS:
        - HEADLINE: {headline}
        - SUMMARY: {summary}
        - DOMAIN: {domain}
        - STRATEGIC INSIGHTS: {strategic_insights}
        
        VISUAL ENHANCEMENT GUIDELINES:
        1. Information Density: Rich layout with multiple visual layers. Do NOT simplify. 
        2. Supporting Elements: Mandate at least THREE distinct visual components:
           - A primary data visualization (e.g., trend line, complex flow diagram, or multi-axis comparison).
           - A set of 3-4 micro-illustrations or high-fidelity labeled icons.
           - At least two "Insight Cards" (callout boxes) using the 'STRATEGIC INSIGHTS' provided.
        3. Hierarchy & Depth: Use a strong editorial grid. Plan for clear visual flow from Headline -> Summary -> Deep Dive -> Conclusion.
        6. Linguistic Excellence: All text must be grammatically correct and 100% free of spelling errors. Do not invent words. Use standard professional English only.
        7. Sub-Text & Labels: Sub-headings and small text MUST use simple, common English words. Avoid technical jargon or complex terminology in secondary/tertiary layers. Prefer nouns over verbs.
        8. Length Constraints: No small text or label may exceed 8 words. No compound or hyphenated words in small text. Rephrase to be concise.
        9. Text Alignment: All headings must be center-aligned. Body text must be left-aligned. Ensure clear separation between sections and consistent line spacing.
        10. Hierarchy & Contrast: Implement a clear hierarchy: (1) Bold primary headline, (2) Concise sub-headlines, (3) Minimal dictionary-valid labels. Maintain high contrast. No overlapping or diagonal text.

        OUTPUT FORMAT (JSON):
        {{
            "visual_type": "studio_grade_infographic",
            "style": "{image_style}",
            "palette_preference": "{image_palette}",
            "headline_hierarchy": {{
                "main": "Punchy, bold editorial headline",
                "sub": "Contextual one-line sub-headline"
            }},
            "visual_layers": [
                {{"type": "primary_chart", "description": "Description of a rich, non-generic data visualization or process map"}},
                {{"type": "icon_cluster", "description": "3-4 specific labeled icons representing key entities"}},
                {{"type": "insight_cards", "description": "Content for 2 callout boxes highlighting impact"}}
            ],
            "aesthetic_tokens": {{
                "palette": "Strictly use {image_palette}",
                "texture": "Clean professional matte according to {image_style} style",
                "lighting": "High-energy editorial lighting"
            }},
            "image_prompt": f"An elite-tier 4K 4:5 vertical editorial infographic about {headline}. DOMAIN: {domain}. SUMMARY: {summary}. STRATEGIC INSIGHTS: {', '.join([str(i) for i in strategic_insights])}. STYLE: {image_style}. PALETTE: {image_palette}. High-fidelity design studio output, multi-layered layout, razor-sharp text, center-aligned headings, simple common English words only, no jargon in small text, clean margins, complex data visualization, ZERO spelling errors, perfect alignment."
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
