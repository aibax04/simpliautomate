import google.generativeai as genai
from typing import Dict

class VisualPlanningAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def plan_visual(self, news_item: Dict, caption_data: Dict) -> Dict:
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
        
        prompt = f"""
        Design an elite, studio-grade editorial infographic blueprint for a premium LinkedIn post.
        
        GOAL: Elevate visual richness and professional data journalism to the highest possible level. 
        It MUST look like a handcrafted masterpiece from a top-tier newsroom (NYT, Bloomberg, Reuters) or strategy firm (McKinsey, BCG).

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
        4. Typography: Ultra-clean sans-serif for body, sophisticated bold serif or heavy sans for headlines. 
        5. Sophistication: Use subtle depth (soft drop shadows, layered glassmorphism elements) and professional textures (matte finish, fine grain).
        6. Linguistic Excellence: Ensure all text in headlines, sub-headlines, and insight cards is 100% spelling-perfect. It will be audited and MUST be flawless for image generation.

        DOMAIN-SPECIFIC DIRECTION:
        - Legal AI: Use Slate, Charcoal, and Champagne Gold accents. Focus on flow diagrams of rulings or comparisons.
        - Healthcare AI: Clinical Teal, Soft Sage, and Slate Grey. Focus on anatomical micro-icons or data timelines.
        - Business AI: Deep Navy, Graphite, and a sharp Tangerine or Copper accent. Focus on dashboard-style charts or workflow maps.

        OUTPUT FORMAT (JSON):
        {{
            "visual_type": "studio_grade_infographic",
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
                "palette": "Detailed hex-like list of professional contextual colors",
                "texture": "Description of professional background finish (e.g., 'brushed matte paper with subtle depth')",
                "lighting": "Soft editorial lighting with clean shadows"
            }},
            "image_prompt": "An elite-tier 4K 4:5 vertical editorial infographic. Mention: 'Studio-grade design', 'elite visual journalism', 'rich multi-layered layout', 'razor-sharp vector typography', 'complex data visualization', 'hand-crafted precision', 'subtle shadows and depth', 'matte finish', 'premium color palette', 'no neon', 'no generic AI glow', 'Bloomberg and McKinsey aesthetic'."
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
                "visual_type": "studio_grade_infographic",
                "image_prompt": f"Elite 4K editorial infographic about {domain}, {headline}. High-fidelity design studio output, complex visual hierarchy, rich data visualization, modern layout, premium slate palette, razor-sharp text."
            }
