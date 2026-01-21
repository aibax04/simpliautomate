import os
from google import genai
from backend.config import Config

class LLMClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMClient, cls).__new__(cls)
            api_key = Config.GEMINI_API_KEY
            if not api_key:
                from dotenv import load_dotenv
                load_dotenv(encoding='utf-8-sig')
                api_key = os.getenv("GEMINI_API_KEY")
            
            cls._instance.client = genai.Client(api_key=api_key)
            cls._instance.default_model = 'gemini-2.0-flash'
        return cls._instance

    @property
    def raw_client(self):
        return self.client

    async def generate_content(self, prompt, model=None, config=None, contents=None):
        if contents is None:
            contents = prompt
        
        return await self.client.aio.models.generate_content(
            model=model or self.default_model,
            contents=contents,
            config=config
        )

    async def generate_image(self, prompt, model='models/imagen-4.0-generate-001'):
        # Note: Imagen models might not support aio yet or have different API
        # but for native Gemini 2.0 image gen, we can use generate_content
        if 'imagen' in model:
            # Sync call for now if aio doesn't support imagen
            return self.client.models.generate_image(
                model=model,
                prompt=prompt
            )
        else:
            return await self.client.aio.models.generate_content(
                model=model,
                contents=prompt
            )

# global instance
llm = LLMClient()
