from backend.agents.caption_agent import CaptionStrategyAgent
from backend.agents.visual_planning_agent import VisualPlanningAgent
from backend.agents.image_agent import ImageAgent

class PostGenerationAgent:
    def __init__(self):
        self.caption_agent = CaptionStrategyAgent()
        self.visual_agent = VisualPlanningAgent()
        self.image_agent = ImageAgent()

    async def generate(self, news_item, user_prefs):
        """
        Orchestrates the full post generation pipeline:
        1. Caption Strategy (Text)
        2. Visual Planning (Blueprint)
        3. Image Generation (Pixel)
        4. Assembly
        """
        print(f"--- GENERATING POST FOR: {news_item.get('headline')} ---")
        
        # 1. Generate Caption
        print("1. Running Caption Strategy...")
        caption_data = await self.caption_agent.generate_caption(news_item, user_prefs)
        
        # 2. Plan Visual
        print("2. Planning Visuals...")
        visual_plan = await self.visual_agent.plan_visual(news_item, caption_data)
        
        # 3. Generate Image
        print("3. Generating Image (this may take a few seconds)...")
        image_url = await self.image_agent.generate_image(visual_plan)
        
        # 4. Assembly
        final_content = f"{caption_data.get('full_caption')}"
        
        return {
            "text": final_content,
            "preview_text": caption_data.get('hook'),
            "caption_data": caption_data,
            "image_url": image_url,
            "visual_plan": visual_plan
        }
