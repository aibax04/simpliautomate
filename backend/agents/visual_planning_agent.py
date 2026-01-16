import google.generativeai as genai
from typing import Dict

class VisualPlanningAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def plan_visual(self, news_item: Dict, caption_data: Dict, user_prefs: Dict, product_info: Dict = None) -> Dict:
        """
        Creates an elite-tier studio-grade blueprint for a professional editorial infographic.
        If it's a custom post, it sticks strictly to the user's prompt and creative style.
        """
        is_custom = news_item.get('is_custom', False)
        domain = news_item.get('domain', 'AI Intelligence')
        headline = news_item.get('headline', 'Breaking News')
        summary = news_item.get('summary', '')
        # Leverage high-level strategic insights AND HOOK from the caption strategist
        strategic_insights = caption_data.get('strategic_insights', [])
        hook_line = caption_data.get('hook', '')
        
        # FEATURE: Logo Path Initialization
        logo_path = None
        
        image_style = user_prefs.get('image_style', 'Futuristic')
        image_palette = user_prefs.get('image_palette', 'Multi-color vibrant')

        branding_note = ""
        if product_info:
            collateral_info = ""
            if product_info.get('collateral'):
                photos = [c['file_name'] for c in product_info['collateral'] if c['file_type'] == 'photo']
                # FEATURE: Logo Extraction
                logo_files = [c for c in product_info['collateral'] if c.get('file_type') == 'logo' or 'logo' in c.get('file_name', '').lower()]
                if logo_files:
                    logo_path = logo_files[0].get('file_path')
                
                if photos:
                    collateral_info = f"\n            - Available Brand Photos for reference: {', '.join(photos)}"

            branding_note = f"""
            BRANDING REQUIREMENTS (Crucial):
            This post is branded for: {product_info.get('name')}.
            - The visual should subtly reflect the brand's identity.{collateral_info}
            - Website URL for reference: {product_info.get('website_url') or 'N/A'}
            - Ensure the product name '{product_info.get('name')}' is elegantly placed as a 'Presented by' or 'Powered by' badge in the corner of the visual.
            """

        if is_custom:
            persona = "Elite Creative Director and Visual Strategist"
            objective = f"Design a high-fidelity visual based strictly on this custom request: '{summary}'."
            guidelines = f"""
            1. CONTENT FIDELITY: The visual MUST focus 100% on the user's prompt: '{summary}'. Do NOT frame this as 'news' or an 'article' if it's a creative or abstract request.
            2. THEMATIC FOCUS: If the user asks for an object (e.g., 'a robot'), the core of the visual should be that object in the requested style.
            3. STYLE ADHERENCE: Strictly follow the style '{image_style}' and palette '{image_palette}'.
            4. INFO OVERLAY: Integrate the strategic insights ({strategic_insights}) as elegant, non-intrusive textual overlays that complement the main subject.
            {branding_note}
            """
            visual_type = "custom_creative_piece"
        else:
            persona = "Elite Data Visualization Designer and Information Architect"
            objective = f"Design a rich, graphical visualization for this news: '{headline}'."
            guidelines = f"""
            1. RICH GRAPHICS-FIRST APPROACH: Prioritize detailed 3D charts, diagrams, and high-fidelity visual metaphors.
            2. IMPACTFUL HOOK: Use the hook line '{hook_line}' as the main headline if text is used.
            3. VISUAL ELEMENTS: Include complex flowcharts, bar charts, pie charts, timelines, icons, or conceptual diagrams.
            4. INFORMATION ARCHITECTURE: Structure information visually through shapes, colors, and spatial relationships.
            5. NO WALLS OF TEXT: Replace text-heavy sections with corresponding visual representations.
            {branding_note}
            """
            visual_type = "minimal_visual_infographic"

        prompt = f"""
        Act as an {persona}.
        {objective}
        
        GOAL: {guidelines}
        
        MANDATORY STYLE: {image_style}
        MANDATORY COLOR PALETTE: {image_palette}
        
        STRATEGIC INSIGHTS TO VISUALIZE: {strategic_insights}
        SUGGESTED HOOK LINE: {hook_line}

        STRICT RULES FOR GRAPHICS-FIRST DESIGN:
        1. TEXT MINIMIZATION: Use ONLY the hook line and very short phrases.
        2. GRAPHICAL REPRESENTATION: Convert concepts into charts, diagrams, flowcharts, icons, or visual metaphors.
        3. VISUAL HIERARCHY: Use size, color, and position to show importance instead of text labels.
        4. SPELLING PERFECTION: Every letter in every word must be spelled correctly.
        5. NO WALLS OF TEXT: Replace any text-heavy areas with corresponding graphical representations.
        
        OUTPUT FORMAT (JSON):
        {{
            "visual_type": "{visual_type}",
            "style": "{image_style}",
            "palette_preference": "{image_palette}",
            "headline_hierarchy": {{
                "main": "{summary if is_custom else hook_line if hook_line else headline}",
                "sub": "{'' if is_custom else 'Contextual sub-headline'}"
            }},
            "visual_layers": [
                {{"type": "primary_chart_diagram", "description": "Main visual element: flowchart, bar chart, pie chart, timeline, or conceptual diagram representing the core idea"}},
                {{"type": "supporting_graphics", "description": "Additional visual elements: icons, arrows, connecting elements, or secondary diagrams that support the main graphic"}},
                {{"type": "data_visualization", "description": "Any metrics or data points represented visually through graphs, progress bars, or comparative visuals"}}
            ],
            "image_prompt": "A rich, stunning, graphics-focused 4K 4:5 vertical design. Deep visual texture, elite design aesthetics, professional color grading. SUBJECT: {summary if is_custom else headline}. HEADLINE: {hook_line if hook_line else headline}. STYLE: {image_style}. PALETTE: {image_palette}. PRIORITIZE: detailed charts, diagrams, flowcharts, icons, and visual metaphors over text explanations. Use a strong, catchy HOOK LINE as the main text element. Replace any text-heavy areas with corresponding graphical representations. Use visual hierarchy through size, color, and position. {f'Ensure it strictly represents {summary} as a visual concept.' if is_custom else 'Graphics-first information design with profound visual depth.'} Perfect alignment, zero spelling errors in any text present. {f'Subtly include {product_info.get('name')} branding elements.' if product_info else ''}"
        }}
        Return ONLY valid JSON.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            plan = json.loads(text)
            # Inject Logo Path if found
            if logo_path:
                plan['logo_path'] = logo_path
            return plan
        except Exception as e:
            print(f"Visual planning error: {e}")
            return {
                "visual_type": "studio_grade_infographic",
                "image_prompt": f"Elite 4K editorial infographic about {domain}, {headline}. High-fidelity design studio output, complex visual hierarchy, rich data visualization, modern layout, premium slate palette, razor-sharp text.",
                "logo_path": logo_path
            }
