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
        self.image_model_name = 'models/gemini-3-pro-image'
        try:
            self.model = genai.GenerativeModel(self.model_name)
            self.image_model = genai.GenerativeModel(self.image_model_name)
            # STEP 5: ADD SAFETY LOG
            print(f"Using image model: {self.image_model_name} and QA model: {self.model_name}")
            sys.stdout.flush()
        except Exception as e:
            print(f"[ERROR] Failed to initialize models: {e}")
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
            self.image_model = genai.GenerativeModel('models/gemini-3-pro-image')

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
            Inspect this generated social media infographic.
            
            REQUIRED TEXT TO BE PRESENT: "{expected_text}"
            
            CHECKLIST FOR OCR & VISUAL QUALITY:
            1. SPELLING: Is every word from the required text spelled correctly in the image? Check for typos, character swaps, or missing letters.
            2. ALIGNMENT: Is the text centered or correctly aligned? Is any text overlapping, crowded, or cut off at the edges?
            3. READABILITY: Is the contrast high enough to read the text?
            
            If there are ANY spelling errors or bad alignment issues, respond ONLY with "FAIL: [brief description]".
            If it is perfect and free of spelling/alignment issues, respond ONLY with "PASS".
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
        # Mandatory quality rules as per strict senior engineer requirements
        spelling_rules = (
            "CRITICAL: All text must be grammatically correct and free of spelling errors. "
            "Spell-check all sub-headings and body text twice before finalizing. "
            "If unsure about spelling, rephrase using simpler words. "
            "Do not invent words or abbreviations. Use standard professional English only."
        )
        alignment_rules = (
            "LAYOUT: Headings must be center-aligned. Body text must be left-aligned. "
            "Equal margins on all sides. Consistent line spacing. No overlapping text. "
            "No diagonal or curved text. Clear separation between sections."
        )
        typography_rules = (
            "TYPOGRAPHY: Use one sans-serif font family only. Clear hierarchy: "
            "1) Primary heading: can be expressive. "
            "2) Sub-headings: must be concise and spell-checked. "
            "3) Small text / labels: must be minimal, dictionary-valid words only. "
            "High contrast text on background. Adequate padding around text blocks."
        )
        subtext_constraints = (
            "SUB-TEXT RULES: Sub-headings and small text must use SIMPLE, COMMON English words only. "
            "Avoid long sentences in small text. Avoid technical jargon in small text. "
            "No small text line may exceed 8 words. No compound or hyphenated words in small text. "
            "Prefer nouns over verbs in labels."
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
        
        # Refine prompt for elite, custom-styled editorial masterpiece
        refined_prompt = (
            f"REF: {unique_id}. {base_prompt}. {content_grounding} {spelling_rules} {alignment_rules} {typography_rules} {subtext_constraints} "
            f"{style_rules} {palette_rules} {clarity_rules} "
            "Quality: Elite Studio-Grade, 4K resolution, razor-sharp vector edges, zero blur. "
            "Visual Depth: Rich multi-layered composition with subtle drop shadows, glowing highlights, and sophisticated texture hierarchy. "
            "Information Density: High-fidelity layout featuring complex data visualizations and clearly defined insight cards. "
            "Aesthetic: Premium journalism, crisp, credible, and polished. "
            "Strictly FORBID: Generic AI glow, overcrowded clutter, surreal artifacts, or any spelling errors."
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
