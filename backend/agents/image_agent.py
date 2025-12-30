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
        prompt = visual_plan.get('image_prompt', 'Professional news infographic')
        # Refine prompt for elite, studio-grade editorial masterpiece
        refined_prompt = (
            f"{prompt}. Quality: Elite Studio-Grade, handcrafted by a world-class design team. "
            "Visual Depth: Rich multi-layered composition with subtle drop shadows, layered glassmorphism, and sophisticated texture hierarchy. "
            "Information Density: High-fidelity layout featuring complex data visualizations (charts/flows), micro-illustrations, and clearly defined insight callout cards. "
            "Typography: Razor-sharp editorial typography with strong hierarchy, modern sans-serif and elite serif faces, perfectly readable. "
            "Resolution: 4K studio clarity, pixel-perfect vector edges, zero blur. "
            "Aesthetic: Bloomberg-inspired visual journalism, crisp, credible, and premium. "
            "Strictly FORBID: Generic AI neon, glowing artificial gradients, overcrowded clutter, or surreal artifacts. "
            "Focus: A professional, informative, and screenshot-worthy editorial infographic that feels human-crafted and credible."
        )
        
        # Absolute path normalization
        current_dir = os.path.dirname(os.path.abspath(__file__)) # agents/
        project_root = os.path.dirname(os.path.dirname(current_dir)) # simplii/
        output_dir = os.path.join(project_root, "frontend", "generated_images")
        
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(output_dir, filename)

        try:
            print(f"[DEBUG] Calling GenerateContent with model {self.model_name} for prompt: {refined_prompt[:60]}...")
            sys.stdout.flush()
            
            response = self.model.generate_content(
                refined_prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    temperature=0.0
                )
            )
            
            if not response.candidates or not response.candidates[0].content.parts:
                raise ValueError("API returned an empty response (no candidates or parts)")

            # STEP 4: KEEP RESPONSE HANDLING SAME (but robust to multiple parts)
            img_part = None
            candidate = response.candidates[0]
            
            for part in candidate.content.parts:
                # Some models return text followed by image. Find the image part.
                if hasattr(part, 'inline_data') and part.inline_data.data:
                    img_part = part
                    break
                if hasattr(part, 'image') and part.image:
                    img_part = part
                    break
            
            if not img_part:
                raise ValueError("Response does not contain image data.")

            # Extract image data
            if hasattr(img_part, 'image') and img_part.image:
                img_part.image.save(filepath)
            elif hasattr(img_part, 'inline_data'):
                b64_data = img_part.inline_data.data
                
                # The SDK might return this as bytes or string
                if isinstance(b64_data, bytes):
                    # Check if it's already PNG bytes
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
                raise RuntimeError(f"File at {filepath} is missing or too small")

        except Exception as e:
            print(f"[ERROR] Image Generation Pipeline Failed: {str(e)}")
            sys.stdout.flush()
            raise e
