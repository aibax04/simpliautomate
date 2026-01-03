import google.generativeai as genai
from typing import Dict, List
import json
import logging
import sys
from backend.tools.duckduckgo_search import search_duckduckgo

logger = logging.getLogger(__name__)

class LinkedInBlogAgent:
    def __init__(self):
        # Using 2.5 Flash as requested for high-quality long-form content
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate_blog(self, topic: str, tone: str = "Professional", length: str = "Medium") -> Dict:
        """
        Orchestrates the blog generation workflow:
        1. Fetch data from DuckDuckGo
        2. Validate sources
        3. Generate blog using Gemini 2.5
        4. Append sources
        """
        print(f"[BLOG_AGENT] Starting blog generation for topic: {topic}")
        sys.stdout.flush()

        # 1. Fetch data from DuckDuckGo
        search_results = search_duckduckgo(topic, max_results=10)
        
        # 2. Validate sources (at least 3 unique sources)
        unique_sources = []
        seen_urls = set()
        for res in search_results:
            url = res.get("link")
            if url and url not in seen_urls:
                unique_sources.append(res)
                seen_urls.add(url)
        
        if len(unique_sources) < 3:
            print(f"[BLOG_AGENT] Not enough sources found: {len(unique_sources)}")
            sys.stdout.flush()
            return {
                "success": False,
                "error": "Not enough reliable sources found. DuckDuckGo returned fewer than 3 unique results."
            }
        
        print(f"[BLOG_AGENT] Found {len(unique_sources)} unique sources. Generating content...")
        sys.stdout.flush()

        # 3. Gemini 2.5 blog generation
        # Prepare data for prompt
        source_data_str = ""
        for i, src in enumerate(unique_sources):
            source_data_str += f"Source {i+1}:\nTitle: {src['title']}\nSnippet: {src['snippet']}\nURL: {src['link']}\n\n"
        
        word_count_guide = {
            "Short": "approx 400-600 words",
            "Medium": "approx 800-1000 words",
            "Long": "approx 1200-1500 words"
        }
        length_str = word_count_guide.get(length, "approx 800-1000 words")

        prompt = f"""
        Act as an elite LinkedIn Thought Leader and Professional Ghostwriter.
        Your goal is to write a high-quality, long-form LinkedIn Article (Blog) based ONLY on the provided factual data.

        TOPIC: {topic}
        TONE: {tone}
        TARGET LENGTH: {length_str}

        INPUT DATA FROM DUCKDUCKGO:
        {source_data_str}

        STRICT EDITORIAL RULES:
        1. HUMAN LANGUAGE: Write in a natural, professional human voice.
        2. NO AI PHRASES: Avoid common AI-sounding words like 'delve', 'tapestry', 'testament', 'ever-evolving', 'In conclusion', etc.
        3. NO EMOJIS: Do not use any emojis in the article.
        4. STRUCTURE: 
           - Start with a compelling, scroll-stopping headline in ALL CAPS or Bold-style text (using plain text).
           - A strong introduction that sets the stage.
           - DO NOT use '#' or Markdown headers for sub-headings. Instead, use bullet marks (● or ■) or ALL CAPS for sub-headings to make them stand out.
           - Use bullet points for lists to ensure readability.
           - A concluding section with a professional call-to-reflection (not a salesy CTA).
        5. FACTUAL GROUNDING: Use ONLY the information provided in the input data. Do not hallucinate or invent facts.
        6. NO MARKETING FLUFF: Stay focused on data-driven insights and professional analysis.

        OUTPUT FORMAT (JSON):
        {{
            "title": "The article headline",
            "content": "The full body text (using markdown for formatting, excluding the sources list)",
            "sources": ["URL1", "URL2", "URL3", ...]
        }}
        Return ONLY valid JSON.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            clean_text = response.text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(clean_text)
            
            # Ensure sources are exactly as provided from DDG
            final_sources = [src['link'] for src in unique_sources]
            result['sources'] = final_sources
            
            # Append Sources section to content
            sources_list = "\n\nSources\n" + "\n".join([f"- {url}" for url in final_sources])
            result['content'] += sources_list
            result['success'] = True
            
            print(f"[BLOG_AGENT] Blog generation successful.")
            sys.stdout.flush()
            return result
        except Exception as e:
            logger.error(f"Error in LinkedInBlogAgent: {e}")
            print(f"[BLOG_AGENT] Error: {e}")
            sys.stdout.flush()
            return {
                "success": False,
                "error": f"Failed to generate blog: {str(e)}"
            }
