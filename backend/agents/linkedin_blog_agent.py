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

    async def generate_blog(self, topic: str, tone: str = "Professional", length: str = "Medium", product_info: Dict = None) -> Dict:
        """
        Orchestrates the blog generation workflow:
        1. Fetch data from DuckDuckGo
        2. Validate sources
        3. Generate blog using Gemini 2.5
        4. Append sources
        """
        print(f"[BLOG_AGENT] Starting blog generation for topic: {topic}")
        sys.stdout.flush()

        # ... rest of the fetch logic ...
        search_results = search_duckduckgo(topic, max_results=10)
        
        # ... rest of validation logic ...
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
            "LinkedIn Post": "STRICTLY less than 1400 characters. This must fit in a single LinkedIn post.",
            "Short": "approx 400-600 words",
            "Medium": "approx 800-1000 words",
            "Long": "approx 1200-1500 words"
        }
        length_str = word_count_guide.get(length, "approx 800-1000 words")

        branding_context = ""
        if product_info:
            branding_context = f"""
            BRANDING CONTEXT (Crucial):
            The user wants this piece to relate to their product/venture:
            - Product Name: {product_info.get('name')}
            - Description: {product_info.get('description')}
            
            MANDATORY RULE: Connect the factual data from the sources to this product. 
            The blog should position the product as a relevant solution or example in the context of the topic.
            """

        prompt = f"""
        Act as an elite LinkedIn Thought Leader and Professional Ghostwriter.
        Your goal is to write a high-quality, professional LinkedIn piece based ONLY on the provided factual data.

        TOPIC: {topic}
        TONE: {tone}
        TARGET LENGTH/CONSTRAINT: {length_str}

        {branding_context}

        INPUT DATA FROM DUCKDUCKGO:
        {source_data_str}

        STRICT EDITORIAL RULES:
        1. HUMAN LANGUAGE: Write in a natural, professional human voice.
        2. NO AI PHRASES: Avoid common AI-sounding words like 'delve', 'tapestry', 'testament', 'ever-evolving', 'In conclusion', etc.
        3. NO EMOJIS: Do not use any emojis in the article.
        4. NO UNWANTED CHARACTERS: The generated content MUST NOT start with a hash symbol (#), a single quote ('), or any other non-alphabetic character unless it's part of the headline title.
        5. STRUCTURE: 
           - Start with a compelling, scroll-stopping headline in ALL CAPS or Bold-style text (using plain text).
           - A strong introduction that sets the stage.
           - DO NOT use '#' or Markdown headers for sub-headings. Instead, use bullet marks (● or ■) or ALL CAPS for sub-headings to make them stand out.
           - Use bullet points for lists to ensure readability and structure the core arguments.
           - A concluding section with a professional call-to-reflection (not a salesy CTA).
        6. FACTUAL GROUNDING: Use ONLY the information provided in the input data. Do not hallucinate or invent facts.
        7. NO MARKETING FLUFF: Stay focused on data-driven insights and professional analysis.
        8. LENGTH CONSTRAINT: If the target length is "LinkedIn Post", ensure the ENTIRE content (including headline and sources) is strictly under 1400 characters.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            if not response or not response.text:
                raise Exception("Empty response from Gemini API")
                
            raw_text = response.text.strip()
            print(f"[BLOG_AGENT] Raw response received (first 100 chars): {raw_text[:100]}...")
            sys.stdout.flush()

            clean_text = raw_text
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                parts = clean_text.split("```")
                if len(parts) >= 3:
                    clean_text = parts[1].strip()
                else:
                    clean_text = parts[0].strip()
            
            # Remove any trailing/leading characters that aren't part of the JSON object
            start_idx = clean_text.find('{')
            end_idx = clean_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx+1]
            
            try:
                result = json.loads(clean_text)
            except json.JSONDecodeError as je:
                print(f"[BLOG_AGENT] JSON parse error: {je}. Attempting to recover...")
                # Fallback: if it's not valid JSON, try to wrap the raw text into a result
                result = {
                    "title": topic,
                    "content": raw_text,
                    "sources": [src['link'] for src in unique_sources]
                }
            
            # Ensure sources are exactly as provided from DDG
            final_sources = [src['link'] for src in unique_sources]
            if 'sources' not in result or not result['sources']:
                result['sources'] = final_sources
            
            # Append Sources section to content if not already there
            if "Sources" not in result['content']:
                sources_list = "\n\nSources\n" + "\n".join([f"- {url}" for url in final_sources])
                result['content'] += sources_list
            
            result['success'] = True
            
            print(f"[BLOG_AGENT] Blog generation successful.")
            sys.stdout.flush()
            return result
        except Exception as e:
            logger.error(f"Error in LinkedInBlogAgent: {e}")
            print(f"[BLOG_AGENT] Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            return {
                "success": False,
                "error": f"Failed to generate blog: {str(e)}"
            }
