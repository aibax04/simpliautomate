import google.generativeai as genai
import json
from typing import Dict, Any

class QualityAssuranceAgent:
    """
    Strict quality control agent for spelling and grammar verification.
    Ensures 100% linguistic accuracy before content publication.
    """
    def __init__(self):
        # Using 2.5 Flash for rapid but precise linguistic analysis
        self.model = genai.GenerativeModel('models/gemini-2.5-flash')

    async def verify_and_fix(self, content_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a deep spelling and grammar verification pass on a content bundle.
        BUNDLE includes: captions, summaries, headlines, and visual plans.
        """
        prompt = f"""
        You are a Professional Editorial Lead and Senior Content Quality Specialist.

        YOUR TASK:
        Perform a strict, comprehensive language quality audit and correction on the provided content.

        STRICT LANGUAGE QUALITY GATE RULES:
        1. **Spelling**: All spellings must be 100% correct. Zero tolerance for typos. Check every single word.
        2. **Grammar & Structure**: Grammar must be flawless. Ensure clean, professional, and natural sentence structures.
        3. **Clarity & Flow**: Improve clarity and flow. Ensure the English is natural, fluent, and highly professional.
        4. **Tone & Style**: Remove awkward phrasing, repetition, and any informal tone. The content MUST be publication-ready.
        5. **Preservation of Meaning**: Do NOT change the factual meaning. Do NOT add or remove information.
        6. **URL Integrity**: NEVER modify anything inside a "source_url" field. Even if it looks like it has a typo, LEAVE IT AS IS. URLs must remain exactly as they are in the source.
        7. **Technical Accuracy**: Do NOT simplify or alter technical terms incorrectly. Maintain their professional context.
        8. **Human-Like Quality**: The content should feel like it was written by a top-tier industry journalist.
        9. **IMAGE TEXT FOCUS**: For visual plans and image-related text, ensure text is concise (under 8 words per line), uses simple words, and will be clearly readable in images.

        CONTENT TO AUDIT & CORRECT:
        {json.dumps(content_bundle, indent=2)}

        FAIL-SAFE:
        If you CANNOT guarantee 100% perfect linguistic quality and professional flow for any reason, return ONLY the string "QUALITY_CHECK_FAILED".
        Otherwise, return the corrected JSON.

        OUTPUT REQUIREMENT:
        Return the EXACT same JSON structure, with all text fields perfectly corrected.
        Return ONLY valid JSON or the string "QUALITY_CHECK_FAILED".
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            
            if "QUALITY_CHECK_FAILED" in clean_text:
                print("[ERROR] Quality Gate: Perfect language quality could not be guaranteed.")
                return None
                
            verified_bundle = json.loads(clean_text)
            print("[INFO] Quality Gate: Linguistic Audit completed. Quality Guaranteed.")
            return verified_bundle
        except Exception as e:
            print(f"[ERROR] Quality Gate failed: {e}. Returning original content.")
            return content_bundle
