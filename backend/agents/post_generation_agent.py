from backend.agents.caption_agent import CaptionStrategyAgent
from backend.agents.visual_planning_agent import VisualPlanningAgent
from backend.agents.image_agent import ImageAgent
from backend.agents.qa_agent import QualityAssuranceAgent

class PostGenerationAgent:
    def __init__(self):
        self.caption_agent = CaptionStrategyAgent()
        self.visual_agent = VisualPlanningAgent()
        self.image_agent = ImageAgent()
        self.qa_agent = QualityAssuranceAgent()

    async def generate(self, news_item, user_prefs, on_progress=None):
        """
        Orchestrates the full post generation pipeline with mandatory Quality Gate:
        1. Caption Strategy (Text)
        2. Quality Verification (Spelling/Grammar Pass)
        3. Visual Planning (Blueprint)
        4. Quality Verification (Visual Content Pass)
        5. Image Generation (Pixel)
        6. Assembly
        """
        print(f"--- GENERATING POST FOR: {news_item.get('headline')} ---")
        
        # 1. Generate Caption
        print("1. Running Caption Strategy...")
        if on_progress: await on_progress("generating_caption", 20)
        caption_data = await self.caption_agent.generate_caption(news_item, user_prefs)
        
        # QUALITY GATE 1: Verify Caption Text
        print("   [Quality Gate] Verifying Caption Language...")
        if on_progress: await on_progress("quality_check_caption", 35)
        caption_data = await self.qa_agent.verify_and_fix(caption_data)
        if not caption_data:
            return None
        
        # 2. Plan Visual
        print("2. Planning Visuals...")
        if on_progress: await on_progress("generating_visual_plan", 50)
        visual_plan = await self.visual_agent.plan_visual(news_item, caption_data)
        
        # QUALITY GATE 2: Verify Visual Plan Text (Crucial for Image Generation)
        print("   [Quality Gate] Verifying Visual Blueprint Language...")
        if on_progress: await on_progress("quality_check_visual", 65)
        visual_plan = await self.qa_agent.verify_and_fix(visual_plan)
        if not visual_plan:
            return None
        
        # 3. Generate Image using only spelling-verified visual plan
        print("3. Generating Image (based on 100% verified text)...")
        if on_progress: await on_progress("generating_image", 85)
        image_url = await self.image_agent.generate_image(visual_plan)
        
        # 4. Assembly
        final_content = f"{caption_data.get('full_caption')}"
        
        if on_progress: await on_progress("ready", 100)
        
        return {
            "text": final_content,
            "preview_text": caption_data.get('hook'),
            "caption_data": caption_data,
            "image_url": image_url,
            "visual_plan": visual_plan
        }
