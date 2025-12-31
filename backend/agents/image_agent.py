import google.generativeai as genai
from backend.config import Config
import os
import uuid
import base64
import sys

class ImageAgent:
    def __init__(self):
        # Using valid Gemini model for image generation as requested
        self.model_name = 'models/gemini-2.5-flash-image'
        try:
            self.model = genai.GenerativeModel(self.model_name)
            # STEP 5: ADD SAFETY LOG
            print(f"Using image model: {self.model_name}")
            sys.stdout.flush()
        except Exception as e:
            print(f"[ERROR] Failed to initialize model {self.model_name}: {e}")
            self.model = genai.GenerativeModel('models/gemini-2.5-flash-image')

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
        
        futuristic_style_rules = (
            "STYLE: Use a vibrant, futuristic color palette. Incorporate multiple bright colors harmoniously. "
            "Design must be high-energy, modern tech/sci-fi inspired. Neon accents are allowed but controlled. "
            "Use clean gradients and glowing highlights. Avoid dull greys and muted tones. "
            "High contrast but perfect readability. White or very dark background only."
        )
        color_palette = (
            "COLORS: Use a combination of Electric Blue, Cyan, Teal, Magenta, Purple, Lime/Neon Green, "
            "and warm Orange or Yellow accents. Ensure multi-color richness."
        )
        futuristic_clarity = (
            "CLARITY: Futuristic does NOT mean chaotic. Maintain editorial/consulting infographic clarity. "
            "Clear alignment, spacing, and hierarchy. Readable typography at all sizes."
        )
        
        prompt = visual_plan.get('image_prompt', 'Professional futuristic news infographic')
        # Refine prompt for elite, high-energy futuristic editorial masterpiece
        refined_prompt = (
            f"{prompt}. {spelling_rules} {alignment_rules} {typography_rules} {subtext_constraints} "
            f"{futuristic_style_rules} {color_palette} {futuristic_clarity} "
            "Quality: Elite Studio-Grade, 4K resolution, razor-sharp vector edges, zero blur. "
            "Visual Depth: Rich multi-layered composition with subtle drop shadows, glowing highlights, and sophisticated texture hierarchy. "
            "Information Density: High-fidelity layout featuring complex data visualizations and clearly defined insight cards. "
            "Aesthetic: High-energy tech journalism, crisp, credible, and premium. "
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
                print(f"[DEBUG] [Attempt {attempts}] Calling GenerateContent with model {self.model_name}")
                sys.stdout.flush()
                
                response = await self.model.generate_content_async(
                    refined_prompt,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        temperature=0.0
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
