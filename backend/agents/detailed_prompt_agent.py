import google.generativeai as genai
from typing import Dict, Optional

class DetailedPromptAgent:
    def __init__(self):
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def generate(self, content: any, source_type: str) -> str:
        """
        Generates a detailed, structured prompt for a LinkedIn post based on input content.
        Content can be a string or a dictionary from our readers.
        """
        if isinstance(content, dict):
            # Extract meaningful strings from the dictionary
            topics = ", ".join(content.get("topics", []))
            entities = ", ".join(content.get("entities", []))
            sector = content.get("sector", "General")
            content_str = f"Topics: {topics}\nEntities: {entities}\nSector: {sector}"
            if "summary" in content: content_str += f"\nSummary: {content['summary']}"
        else:
            content_str = str(content)

        prompt = f"""
        Act as an expert Social Media Strategist and Content Architect.
        Your task is to take the provided raw input and expand it into a high-fidelity, detailed 'Content Brief' or 'Detailed Prompt' that can be used to generate a viral, high-quality LinkedIn post.

        INPUT TYPE: {source_type}
        RAW CONTENT:
        {content_str}

        YOUR GOAL:
        Create a detailed, multi-dimensional prompt that includes:
        1. CORE THEME: A clear statement of what the post is about.
        2. STRATEGIC ANGLE: A unique perspective or "take" on the content.
        3. KEY ARGUMENTS: 3-4 specific points or data insights to highlight.
        4. TARGET EMOTION/ACTION: What the reader should feel or do.
        5. VISUAL GUIDANCE: Brief suggestion for what the accompanying image should represent.
        6. Make sure the generated post has no spelling errors.

        FORMAT:
        Write this as a single, cohesive, highly descriptive paragraph or a set of clear bullet points. 
        It should be written in a way that another AI can use it to generate the final caption.
        Do NOT write the actual LinkedIn post yet. Just the DETAILED PROMPT/BRIEF.

        STRICT RULE: Focus on clarity, depth, and strategic value.
        """

        try:
            response = await self.model.generate_content_async(prompt)
            if response and response.text:
                return response.text.strip()
            return "Failed to generate detailed prompt. Please try again or enter a manual prompt."
        except Exception as e:
            print(f"[DetailedPromptAgent Error] {e}")
            return f"Error generating detailed prompt: {str(e)}"
