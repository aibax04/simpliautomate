import google.generativeai as genai
from typing import Dict

class CaptionStrategyAgent:
    def __init__(self):
        # Using 2.5 Flash for high quality text generation
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate_caption(self, news_item: Dict, prefs: Dict) -> Dict:
        """
        Generates a LinkedIn caption, hook, and CTA based on preferences.
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

        prompt = f"""
        Act as a top-tier LinkedIn Content Strategist.
        
        INPUT DATA:
        - Headline: {news_item.get('headline')}
        - Summary: {news_item.get('context')}
        - Category: {news_item.get('category')}
        
        USER PREFERENCES:
        - Tone: {tone}
        - Target Audience: {audience}
        - Length: {length_str}
        
        STRICT RULES:
        1. Context: Write for industry professionals.
        2. Hook: First 2 sentences must be engaging and visible "above the fold" (LinkedIn preview).
        3. Structure: Use short paragraphs (1-2 sentences). Clean spacing.
        4. Emojis: NO emojis unless Tone is "Founder-style".
        5. Hashtags: Max 3 relevant hashtags at the bottom.
        6. Call to Action: Subtle, engaging question or thought-starter at the end.
        
        OUTPUT FORMAT (JSON):
        {{
            "hook": "The first 2 gripping lines...",
            "body": "The main content...",
            "cta": "The closing question...",
            "hashtags": "#tag1 #tag2 #tag3",
            "full_caption": "The complete combined text..."
        }}
        Return ONLY valid JSON.
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(text)
        except Exception as e:
            print(f"Caption generation error: {e}")
            # Fallback
            return {
                "hook": f"Breaking news in {news_item.get('category')}.",
                "body": news_item.get('context'),
                "cta": "What are your thoughts?",
                "hashtags": "#news #update",
                "full_caption": f"Breaking news: {news_item.get('headline')}\n\n{news_item.get('context')}"
            }
