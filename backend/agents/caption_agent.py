import google.generativeai as genai
from typing import Dict

class CaptionStrategyAgent:
    def __init__(self):
        # Using 2.5 Flash for high quality text generation
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate_caption(self, news_item: Dict, prefs: Dict) -> Dict:
        """
        Generates a premium LinkedIn caption, hook, and strategic highlights.
        Extracts key data points and insights to fuel high-density infographics.
        """
        tone = prefs.get('tone', 'Professional')
        audience = prefs.get('audience', 'General')
        length_opt = prefs.get('length', 'Medium')
        
        # approximate word counts
        word_counts = {
            'Short': 'approx 70 words',
            'Medium': 'approx 120 words',
            'Long': 'approx 180 words'
        }
        length_str = word_counts.get(length_opt, 'approx 120 words')

        # Updated to use new field names: headline, summary, domain
        headline = news_item.get('headline')
        summary = news_item.get('summary')
        domain = news_item.get('domain')

        prompt = f"""
        Act as an elite LinkedIn Content Strategist and Industry Analyst for high-level business networks.
        
        INPUT DATA:
        - Headline: {headline}
        - Summary: {summary}
        - Domain: {domain}
        
        PREFERENCES:
        - Tone: {tone}
        - Audience: {audience}
        - Word Count: {length_str}
        
        STRICT EDITORIAL RULES:
        1. Professional Grade: Write for C-suite and Industry Leaders. No fluff.
        2. Visual Framing: First 2 sentences MUST be "scroll-stopping" hooks.
        3. Strategic Highlights: Extract 3 specific 'Power Insights' or 'Data Trends' from the news that are crucial for an infographic.
        4. Aesthetics: Clean paragraph breaks. NO emojis (unless Founder-style). 
        5. Precision: Use industry-specific terminology correctly.
        6. Linguistic Excellence: Your output will be subjected to a strict spelling and grammar audit. Ensure 100% correct spelling, flawless grammar, and professional flow from the start.
        
        OUTPUT FORMAT (JSON):
        {{
            "hook": "Grip the reader instantly...",
            "body": "Expert-level industry analysis and summary...",
            "strategic_insights": [
                {{"label": "Insight/Data Point 1", "analysis": "Why this matters in 5 words"}},
                {{"label": "Insight/Data Point 2", "analysis": "The hidden impact"}},
                {{"label": "Insight/Data Point 3", "analysis": "Future outlook"}}
            ],
            "cta": "Subtle, high-value prompt/question...",
            "hashtags": "#tag1 #tag2 #tag3",
            "full_caption": "Complete combined post text..."
        }}
        Return ONLY valid JSON.
        """
        
        try:
            response = self.model.generate_content(prompt)
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
