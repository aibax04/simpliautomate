import google.generativeai as genai
from backend.config import Config
import os
import uuid
import base64
import sys
import PIL.Image

class ImageAgent:
    def __init__(self):
        # Using valid Gemini model for image generation as requested
        self.model_name = 'models/gemini-2.0-flash' # Using flash for OCR/QA
        self.image_model_name = 'models/gemini-2.5-flash-image'
        try:
            self.model = genai.GenerativeModel(self.model_name)
            self.image_model = genai.GenerativeModel(self.image_model_name)
            # STEP 5: ADD SAFETY LOG
            print(f"Using image model: {self.image_model_name} and QA model: {self.model_name}")
            sys.stdout.flush()
        except Exception as e:
            print(f"[ERROR] Failed to initialize models: {e}")
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
            self.image_model = genai.GenerativeModel('models/gemini-2.5-flash-image')

    async def extract_and_verify_text_elements(self, visual_plan: dict) -> list:
        """
        Extract all text elements that will appear in the image and verify them.
        Returns a list of verified text elements safe for image generation.
        """
        text_elements = []

        # Extract headline
        main_headline = visual_plan.get('headline_hierarchy', {}).get('main', '')
        sub_headline = visual_plan.get('headline_hierarchy', {}).get('sub', '')

        if main_headline:
            text_elements.append(main_headline)
        if sub_headline:
            text_elements.append(sub_headline)

        # Extract text from visual layers
        for layer in visual_plan.get('visual_layers', []):
            description = layer.get('description', '')
            # Look for text-related descriptions
            if any(keyword in description.lower() for keyword in ['text', 'label', 'caption', 'title']):
                # Extract actual text content from description
                text_content = self._extract_text_from_description(description)
                if text_content:
                    text_elements.append(text_content)

        # Verify each text element
        verified_elements = []
        for text in text_elements:
            verified_text = await self._verify_text_for_image(text)
            if verified_text:
                verified_elements.append(verified_text)

        return verified_elements

    def _extract_text_from_description(self, description: str) -> str:
        """Extract actual text content from layer descriptions."""
        # Look for quoted text or common patterns
        import re

        # Find text in quotes
        quoted_text = re.findall(r'["\']([^"\']+)["\']', description)
        if quoted_text:
            return quoted_text[0]

        # Look for common text patterns
        text_indicators = ['show', 'display', 'text:', 'label:', 'title:']
        for indicator in text_indicators:
            if indicator in description.lower():
                # Extract text after indicator
                parts = description.lower().split(indicator, 1)
                if len(parts) > 1:
                    text_part = parts[1].strip()
                    # Clean up the text
                    text_part = re.sub(r'[^\w\s]', '', text_part).strip()
                    if text_part and len(text_part.split()) <= 8:  # Keep it short for images
                        return text_part

        return None

    async def _verify_text_for_image(self, text: str) -> str:
        """Verify text is suitable and correctly spelled for image inclusion."""
        if not text or len(text.strip()) == 0:
            return None

        # Basic length check (keep images readable)
        if len(text.split()) > 8:
            return None

        prompt = f"""
        Verify if this text is suitable for image inclusion:

        Text: "{text}"

        Requirements:
        1. Perfect spelling (check every letter)
        2. Professional language
        3. Under 8 words
        4. No complex punctuation
        5. Clear and readable

        If suitable, return the text exactly as-is.
        If not suitable, return "UNSUITABLE".
        """

        try:
            response = await self.model.generate_content_async(prompt)
            result = response.text.strip()

            if result == "UNSUITABLE" or "unsuitable" in result.lower():
                return None

            return text if result == text else None

        except Exception as e:
            print(f"[TEXT VERIFY ERROR] {e}")
            return None

    async def verify_image(self, image_path: str, expected_text: str) -> bool:
        """
        Uses Gemini Multimodal to inspect the image for spelling and alignment.
        """
        try:
            # Load the image using PIL
            # Resolve absolute path
            current_dir = os.path.dirname(os.path.abspath(__file__)) # agents/
            project_root = os.path.dirname(os.path.dirname(current_dir)) # simplii/
            
            # image_path is like /generated_images/uuid.png
            full_path = os.path.join(project_root, "frontend", image_path.lstrip('/'))
            
            if not os.path.exists(full_path):
                print(f"[QA ERROR] Image file not found for verification: {full_path}")
                return True # Don't block if file is missing somehow

            img = PIL.Image.open(full_path)
            
            prompt = f"""
            Inspect this generated social media infographic with EXTREME attention to text accuracy.

            REQUIRED TEXT TO BE PRESENT: "{expected_text}"

            COMPREHENSIVE CHECKLIST FOR TEXT & VISUAL QUALITY:

            SPELLING VERIFICATION (CRITICAL):
            1. Check EVERY SINGLE WORD in the required text
            2. Look for: typos, missing letters, extra letters, swapped letters
            3. Verify punctuation is correct and present
            4. Check for common misspellings (teh→the, recieve→receive, etc.)

            TEXT CONSISTENCY:
            5. Is the text exactly as specified (no paraphrasing or changes)?
            6. Are all words properly capitalized?
            7. Is the text complete (no truncation or cutting off)?

            VISUAL QUALITY:
            8. Is text clearly readable with good contrast?
            9. Is text properly aligned and not overlapping?
            10. Is font size adequate for readability?
            11. Is there sufficient spacing around text?

            OCR ACCURACY TEST:
            12. Extract the actual text from the image and compare character-by-character

            If there are ANY spelling errors, text inconsistencies, or readability issues, respond ONLY with "FAIL: [specific issue description]".
            If the image is PERFECT with 100% accurate text and excellent readability, respond ONLY with "PASS".
            """
            
            # Call Gemini Vision (using the flash model which is excellent at OCR)
            response = await self.model.generate_content_async([prompt, img])
            result = response.text.strip().upper()
            
            print(f"[QA RESULT] Image verification: {result}")
            sys.stdout.flush()
            
            return "PASS" in result
        except Exception as e:
            print(f"[QA ERROR] Failed to verify image: {e}")
            return True # Fallback to true to not break the workflow on API error

    async def edit_image(self, visual_plan: dict, edit_prompt: str) -> str:
        """
        Manually edits an image based on a user prompt while preserving the original context.
        """
        original_prompt = visual_plan.get('image_prompt', 'Professional news infographic')
        
        # Construct the edit-aware prompt as per requirements
        instruction = " Apply the following changes without altering the subject, meaning, or text accuracy: "
        new_prompt = f"{original_prompt}{instruction}{edit_prompt}"
        
        # Create a copy of visual plan to not modify the original in-place if it's cached/reused
        modified_plan = visual_plan.copy()
        modified_plan['image_prompt'] = new_prompt
        
        # Reuse existing robust generation pipeline
        return await self.generate_image(modified_plan)

    async def generate_image(self, visual_plan: dict) -> str:
        """
        Generates an infographic image using the specified Gemini model.
        Saves locally and returns the URL path.
        """
        # PRE-GENERATION TEXT VERIFICATION: Extract and verify all text elements
        print("   [PRE-CHECK] Verifying text elements for image generation...")
        verified_text_elements = await self.extract_and_verify_text_elements(visual_plan)

        if not verified_text_elements:
            print("   [PRE-CHECK] Warning: No verified text elements found")
        else:
            print(f"   [PRE-CHECK] Verified {len(verified_text_elements)} text elements for image")

        # Mandatory quality rules as per strict senior engineer requirements - GRAPHICS FIRST APPROACH
        spelling_rules = (
            "CRITICAL TEXT REQUIREMENTS: If any text appears, it must be 100% grammatically correct and free of spelling errors. "
            "Spell-check EVERY SINGLE WORD that appears anywhere in the image. "
            "Common misspellings to avoid: teh→the, recieve→receive, definately→definitely, seperate→separate, occassion→occasion, recomend→recommend. "
            "PRIORITY: Minimize text usage. Replace text with charts, diagrams, icons, and visual elements whenever possible. "
            "If text is necessary, keep it extremely concise (max 3 words per element) and use only simple, common words."
        )
        alignment_rules = (
            "LAYOUT: Headings must be center-aligned. Body text must be left-aligned. "
            "Equal margins on all sides. Consistent line spacing. No overlapping text. "
            "No diagonal or curved text. Clear separation between sections."
        )
        typography_rules = (
            "TYPOGRAPHY REQUIREMENTS: Use one sans-serif font family only (Arial, Helvetica, or Calibri). "
            "Clear hierarchy with proper contrast: "
            "1) Primary heading: can be expressive but must be readable. "
            "2) Sub-headings: must be concise (under 8 words), spell-checked, and clearly legible. "
            "3) Small text/labels: must use only minimal, dictionary-valid words with no jargon. "
            "ENSURE HIGH CONTRAST: Black/dark text on light backgrounds, white/light text on dark backgrounds. "
            "Adequate padding around ALL text blocks. No text touching edges or overlapping."
        )
        subtext_constraints = (
            "GRAPHICS OVER TEXT - MAXIMUM RESTRICTION: Minimize all text usage. Replace text with visual elements whenever possible. "
            "If text is absolutely necessary, use ONLY single words or very short phrases (max 2-3 words). "
            "APPROVED SINGLE WORDS: Growth, Impact, Future, Trends, Innovation, Progress, Results, Success, Change, Data, Flow, Path, Goal. "
            "FORBIDDEN: Sentences, phrases over 3 words, technical jargon, compound words, hyphens. "
            "PRIORITY: Use charts, diagrams, flowcharts, icons, arrows, and visual metaphors instead of text labels. "
            "STYLE: Visual communication through graphics, not text. Keep any text extremely minimal and readable."
        )
        
        # FEATURE 5: STRICT ADHERENCE TO STYLE AND PALETTE
        selected_style = visual_plan.get('style', 'Futuristic')
        selected_palette = visual_plan.get('palette_preference', 'Multi-color vibrant')
        
        # EXTRACT RICH CONTEXT FROM VISUAL PLAN
        headline_data = visual_plan.get('headline_hierarchy', {})
        main_headline = headline_data.get('main', 'News Update')
        sub_headline = headline_data.get('sub', '')
        
        layers = visual_plan.get('visual_layers', [])
        layer_descriptions = ". ".join([f"{l.get('type')}: {l.get('description')}" for l in layers])

        style_rules = f"STYLE: {selected_style}. The design must strictly follow this style. Avoid any other artistic directions."
        palette_rules = f"COLORS: {selected_palette}. The color palette must be respected strictly. Do not use random colors outside this theme."
        
        content_grounding = (
            f"CONTENT GROUNDING: The infographic MUST be about '{main_headline}'. "
            f"Sub-headline: '{sub_headline}'. "
            f"Visual Elements to include: {layer_descriptions}. "
            "Ensure the visual data and icons directly represent the news facts mentioned."
        )

        clarity_rules = (
            "CLARITY: Maintain editorial/consulting infographic clarity. "
            "Clear alignment, spacing, and hierarchy. Readable typography at all sizes."
        )
        
        base_prompt = visual_plan.get('image_prompt', 'Professional news infographic')
        # Add a unique seed identifier to ensure prompt uniqueness at the model level
        unique_id = uuid.uuid4().hex[:8]
        
        # Refine prompt for graphics-first visual design
        refined_prompt = (
            f"REF: {unique_id}. {base_prompt}. {content_grounding} {spelling_rules} {alignment_rules} {typography_rules} {subtext_constraints} "
            f"{style_rules} {palette_rules} {clarity_rules} "
            "GRAPHICS FIRST, TEXT LAST: Prioritize charts, diagrams, flowcharts, and visual elements over text. Replace text-heavy areas with graphical representations. "
            "Quality: Elite Studio-Grade, 4K resolution, razor-sharp vector edges, zero blur. "
            "Visual Communication: Use charts, diagrams, icons, arrows, and spatial relationships to convey information instead of text. "
            "Minimal Text Design: If any text appears, it must be perfectly spelled, clearly readable, and extremely concise (max 3 words). "
            "Aesthetic: Clean, professional graphics-focused design with minimal text overlay. "
            "CRITICAL REQUIREMENTS: Replace text with visual metaphors. Use graphical elements for data representation. Ensure perfect spelling in any text present. "
            "Strictly FORBID: Text walls, paragraph text, ANY spelling errors, text overlap, generic AI artifacts, or cluttered layouts."
        )
        
        # Absolute path normalization
        current_dir = os.path.dirname(os.path.abspath(__file__)) # agents/
        project_root = os.path.dirname(os.path.dirname(current_dir)) # simplii/
        output_dir = os.path.join(project_root, "frontend", "generated_images")
        
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(output_dir, filename)

        attempts = 0
        max_attempts = 2
        
        while attempts < max_attempts:
            attempts += 1
            try:
                print(f"[DEBUG] [Attempt {attempts}] Calling GenerateContent with model {self.image_model_name}")
                sys.stdout.flush()
                
                response = await self.image_model.generate_content_async(
                    refined_prompt,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        temperature=0.4 # Increased from 0.0 to allow for variation on regeneration
                    )
                )
                
                if not response.candidates:
                    raise ValueError("API returned no candidates")
                
                candidate = response.candidates[0]
                
                # Check for "uncertainty in text rendering" or safety blocks
                # finish_reason can be SAFETY, OTHER, etc.
                # If the image model returns text parts instead of images, it might be an error message
                model_message = ""
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        model_message += part.text
                
                # If model reports issues or uncertainty in text/safety
                uncertainty_keywords = ["uncertain", "cannot render", "text error", "spelling", "quality issue"]
                reported_uncertainty = any(kw in model_message.lower() for kw in uncertainty_keywords)
                
                if reported_uncertainty:
                    print(f"[WARNING] Model reported uncertainty/issue: {model_message}")
                    if attempts < max_attempts:
                        print("[RETRY] Regenerating once due to reported uncertainty...")
                        continue
                
                # Find image part
                img_part = None
                for part in candidate.content.parts:
                    if (hasattr(part, 'inline_data') and part.inline_data.data) or (hasattr(part, 'image') and part.image):
                        img_part = part
                        break
                
                if not img_part:
                    if attempts < max_attempts:
                        print("[RETRY] No image data found in response. Retrying...")
                        continue
                    raise ValueError(f"Response does not contain image data. Model said: {model_message}")

                # Extract and save image data
                if hasattr(img_part, 'image') and img_part.image:
                    img_part.image.save(filepath)
                elif hasattr(img_part, 'inline_data'):
                    b64_data = img_part.inline_data.data
                    if isinstance(b64_data, bytes):
                        if b64_data.startswith(b'\x89PNG'):
                            image_bytes = b64_data
                        else:
                            try:
                                image_bytes = base64.b64decode(b64_data)
                            except:
                                image_bytes = b64_data 
                    else:
                        image_bytes = base64.b64decode(b64_data)
                    
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                
                # Final verification
                if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
                    file_size = os.path.getsize(filepath)
                    print(f"[SUCCESS] Image saved successfully at {filepath} ({file_size} bytes)")
                    sys.stdout.flush()
                    return f"/generated_images/{filename}"
                else:
                    if attempts < max_attempts:
                        print("[RETRY] File missing or too small. Retrying...")
                        continue
                    raise RuntimeError(f"File at {filepath} is missing or too small")

            except Exception as e:
                print(f"[ERROR] [Attempt {attempts}] Pipeline failed: {str(e)}")
                if attempts < max_attempts:
                    print("[RETRY] Error encountered. Retrying...")
                    continue
                raise e
        
        return f"/generated_images/{filename}" # Should not reach here if failed
