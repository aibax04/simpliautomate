import google.generativeai as genai
from typing import Dict

class CaptionStrategyAgent:
    def __init__(self):
        # Using 2.5 Flash for high quality text generation
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate_caption(self, news_item: Dict, prefs: Dict) -> Dict:
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

        if is_custom:
            persona = "elite Personal Branding Expert and Ghostwriter for top-tier executives"
            objective = f"Create a personal, highly engaging post based strictly on this user request: \"{summary}\"."
            rules = """
            1. Personal Touch: Write with a human, authentic voice. Avoid generic 'news' language.
            2. Content Fidelity: Focus 100% on the user's specific request. If they want a story, tell a story. If they want an opinion, be bold.
            3. Hook: Start with a powerful, relatable opening.
            4. Strategic Highlights: Extract 3 'Key Takeaways' or 'Personal Insights' that would look great on an infographic.
            5. Aesthetics: Clean breaks, no clutter.
            """
        else:
            persona = "elite LinkedIn Content Strategist and Industry Analyst for high-level business networks"
            objective = f"Analyze and summarize this news update: \"{headline}\"."
            rules = """
            1. Professional Grade: Write for C-suite and Industry Leaders. No fluff.
            2. Visual Framing: First 2 sentences MUST be "scroll-stopping" hooks.
            3. Strategic Highlights: Extract 3 specific 'Power Insights' or 'Data Trends' from the news.
            4. Precision: Use industry-specific terminology correctly.
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
