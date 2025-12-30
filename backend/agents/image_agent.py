import google.generativeai as genai
from backend.config import Config
import os
import uuid

class ImageAgent:
    def __init__(self):
        # Using real image generation model
        # Trying standardized Imagen model name
        self.model = genai.GenerativeModel('models/imagen-3.0-generate-001')

    async def generate_image(self, visual_plan: dict) -> str:
        """
        Generates an image based on the visual plan and returns the local URL path.
        If API fails, generates a local fallback image using PIL.
        """
        prompt = visual_plan.get('image_prompt', 'Professional business infographic')
        refined_prompt = f"{prompt}. High quality, 4k, vector art, flat design, white background, no blur, sharp text."
        
        # Ensure static dir exists
        output_dir = os.path.join(os.getcwd(), "frontend", "generated_images")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(output_dir, filename)

        try:
            print(f"Generating image with prompt: {refined_prompt[:50]}...")
            # Try API Generation
            response = self.model.generate_content(
                refined_prompt,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    temperature=0.0
                )
            )
            
            if response.parts:
                try:
                    img = response.parts[0].image
                    img.save(filepath)
                except Exception as e:
                     # Fallback bytes
                    if hasattr(response.parts[0], 'inline_data'):
                         with open(filepath, 'wb') as f:
                            f.write(response.parts[0].inline_data.data)
                    else:
                        raise ValueError("No image data found")
                
                if os.path.getsize(filepath) > 0:
                    print(f"Image saved to {filepath}")
                    return f"/generated_images/{filename}"

        except Exception as e:
            print(f"API Image generation failed: {e}")
            # PROCEED TO LOCAL FALLBACK
            
        # --- LOCAL FALLBACK ---
        print("Generating local fallback image...")
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap

            # create image
            width, height = 800, 1000
            bg_color = (245, 245, 247) # Off-white
            img = Image.new('RGB', (width, height), bg_color)
            draw = ImageDraw.Draw(img)
            
            # Draw header background
            draw.rectangle([(0, 0), (width, 100)], fill=(0, 122, 255)) # Blue header
            
            # Try to load a font, fallback to default
            try:
                # Try standard fonts
                font_title = ImageFont.truetype("arial.ttf", 60)
                font_body = ImageFont.truetype("arial.ttf", 40)
            except:
                font_title = ImageFont.load_default()
                font_body = ImageFont.load_default()

            # Draw Title
            title_text = "SIMPLII INSIGHT"
            draw.text((40, 20), title_text, fill="white", font=font_title)
            
            # Draw visual plan text (visual representation)
            visual_text = visual_plan.get('visual_type', 'Infographic').upper()
            draw.text((40, 150), f"VISUAL: {visual_text}", fill="black", font=font_body)
            
            # Wrap and draw description
            desc = visual_plan.get('elements', 'Business Chart')
            lines = textwrap.wrap(desc, width=30)
            y = 250
            for line in lines:
                draw.text((40, y), line, fill=(50, 50, 50), font=font_body)
                y += 50
                
            # Draw Palette
            y += 50
            draw.text((40, y), "PALETTE:", fill="black", font=font_body)
            y += 50
            palette_desc = visual_plan.get('color_palette', 'Blue & White')
            draw.text((40, y), palette_desc, fill="gray", font=font_body)
            
            # Save
            img.save(filepath)
            print(f"Fallback image saved to {filepath}")
            return f"/generated_images/{filename}"
            
        except Exception as local_e:
            print(f"Local fallback failed: {local_e}")
            # Ultimate robust return
            return "https://via.placeholder.com/800x1000?text=Image+System+Offline"

