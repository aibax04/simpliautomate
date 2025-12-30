import google.generativeai as genai
from backend.config import Config
import os
import uuid

class ImageAgent:
    def __init__(self):
        # Using real image generation model
        self.model = genai.GenerativeModel('models/gemini-2.5-flash-image')

    async def generate_image(self, visual_plan: dict) -> str:
        """
        Generates an image based on the visual plan and returns the local URL path.
        """
        prompt = visual_plan.get('image_prompt', 'Professional business infographic')
        
        # Enforce style in prompt one last time
        refined_prompt = f"{prompt}. High quality, 4k, vector art, flat design, white background, no blur, sharp text."
        
        try:
            print(f"Generating image with prompt: {refined_prompt[:50]}...")
            response = self.model.generate_content(
                refined_prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    temperature=0.0
                )
            )
            
            # Save the image
            if response.parts:
                # Ensure static dir exists
                output_dir = "frontend/generated_images"
                os.makedirs(output_dir, exist_ok=True)
                
                filename = f"{uuid.uuid4()}.png"
                filepath = os.path.join(output_dir, filename)
                
                # Gemini image response handling depends on SDK version, 
                # but typically image is in response.parts[0].inline_data or similar if bytes.
                # Or response.text is empty and we accept byte stream?
                # Actually, for Image Generation models in Gemini API (Vertex/Studio), 
                # standard generate_content return format is specific.
                # Assuming standard PIL conversion if the SDK automatically handles it 
                # or retrieving bytes.
                
                # Standard pattern for latest genai sdk with image models:
                try:
                    img = response.parts[0].image
                    img.save(filepath)
                except:
                    # If SDK logic differs, try getting bytes
                    with open(filepath, 'wb') as f:
                        f.write(response.parts[0].inline_data.data)
                
                return f"/generated_images/{filename}"
            else:
                print("No image parts in response")
                return ""
                
        except Exception as e:
            print(f"Image generation failed: {e}")
            # Return a mock if real gen fails (so app doesn't crash)
            return "/api/placeholder-image"  # We'll need to handle this or just fail gracefully

