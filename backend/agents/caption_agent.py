import google.generativeai as genai
from typing import Dict

class CaptionStrategyAgent:
    def __init__(self):
        # Using 2.5 Flash for high quality text generation
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate_caption(self, news_item: Dict, prefs: Dict, product_info: Dict = None) -> Dict:
        """
        Generates a premium LinkedIn caption, hook, and strategic highlights.
        If it's a custom/personal request, it switches to a personal branding persona.
        """
        tone = prefs.get('tone', 'Professional')
        audience = prefs.get('audience', 'General')
        length_opt = prefs.get('length', 'Medium')
        is_custom = news_item.get('is_custom', False)
        
        # approximate word counts
        word_counts = {
            'Short': 'approx 70 words',
            'Medium': 'approx 120 words',
            'Long': 'approx 180 words'
        }
        length_str = word_counts.get(length_opt, 'approx 120 words')

        headline = news_item.get('headline')
        summary = news_item.get('summary')
        domain = news_item.get('domain')

        branding_context = ""
        if product_info:
            branding_context = f"""
            BRANDING CONTEXT (Crucial):
            The user wants this post to relate to their product/service:
            - Product Name: {product_info.get('name')}
            - Product Description: {product_info.get('description')}
            
            MANDATORY RULE: Find a natural and professional way to connect the news/topic to this product. 
            The product should be mentioned or alluded to as a solution, relevant example, or related entity.
            """

        if is_custom:
            persona = "elite Creative Copywriter and Professional Brand Voice Expert"
            objective = f"Create a highly engaging post based strictly on this specific user request: \"{summary}\"."
            rules = f"""
            1. Literal Fidelity: Focus 100% on the user's specific prompt. If they ask for 'a robot', write about that robot. Do NOT try to frame it as a 'news update' or 'industry analysis' unless requested.
            2. Authentic Tone: Write with a natural, human voice that matches the user's creative intent.
            3. Hook: Start with a powerful opening relevant to the specific subject.
            4. Strategic Highlights: Extract 3 'Key Points' or 'Subject Specialities' from the request that would look great as overlays.
            5. No Fluff: Keep it focused and impactful.
            {branding_context}
            """
        else:
            persona = "elite LinkedIn Content Strategist and Industry Analyst for high-level business networks"
            objective = f"Analyze and summarize this news update: \"{headline}\"."
            rules = f"""
            1. Professional Grade: Write for C-suite and Industry Leaders. No fluff.
            2. Visual Framing: First 2 sentences MUST be "scroll-stopping" hooks.
            3. Strategic Highlights: Extract 3 specific 'Power Insights' or 'Data Trends' from the news.
            4. Precision: Use industry-specific terminology correctly.
            {branding_context}
            """

        prompt = f"""
        Act as an {persona}.
        
        {objective}
        
        INPUT DATA:
        - Topic/Request: {summary if is_custom else headline}
        - Context: {summary if not is_custom else ""}
        - Domain: {domain}
        
        PREFERENCES:
        - Tone: {tone}
        - Audience: {audience}
        - Word Count: {length_str}
        
        STRICT EDITORIAL RULES:
        {rules}
        6. Linguistic Excellence: 100% correct spelling and flawless grammar.
        
        OUTPUT FORMAT (JSON):
        {{
            "hook": "Grip the reader instantly...",
            "body": "The main content text...",
            "strategic_insights": [
                {{"label": "Key Insight 1", "analysis": "Why this matters in 5 words"}},
                {{"label": "Key Insight 2", "analysis": "Impact/Value"}},
                {{"label": "Key Insight 3", "analysis": "Outlook/Action"}}
            ],
            "cta": "Engaging prompt/question...",
            "hashtags": "#tag1 #tag2 #tag3",
            "full_caption": "Complete combined post text..."
        }}
        Return ONLY valid JSON.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(text)
        except Exception as e:
            print(f"Caption strategy error: {e}")
            return {
                "hook": f"Strategic update on {headline}.",
                "body": summary,
                "strategic_insights": [{"label": "Market Shift", "analysis": "Impact on domain"}],
                "cta": "How does this affect your roadmap?",
                "hashtags": "#industry #analysis",
                "full_caption": f"{headline}\n\n{summary}"
            }
