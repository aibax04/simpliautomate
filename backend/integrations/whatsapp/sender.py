import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional
import logging
from backend.config import Config

logger = logging.getLogger(__name__)

class WhatsAppSender:
    BASE_URL = "https://graph.facebook.com/v17.0"

    def __init__(self):
        self.phone_id = Config.WHATSAPP_PHONE_ID
        self.access_token = Config.WHATSAPP_ACCESS_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a raw payload to WhatsApp API.
        """
        if not self.phone_id or not self.access_token:
            logger.error("Missing configuration (PHONE_ID or ACCESS_TOKEN)")
            return {"error": "Missing configuration"}

        url = f"{self.BASE_URL}/{self.phone_id}/messages"
        
        async with aiohttp.ClientSession() as session:
            # logger.debug(f"Sending Payload: {json.dumps(payload)}")
            try:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    data = await response.json()
                    
                    if response.status not in [200, 201]:
                        logger.error(f"WhatsApp API Error: {data}")
                        return {"status": "failed", "error": data}
                    
                    logger.info(f"WhatsApp Message Sent (WA_ID: {data.get('messages', [{}])[0].get('id')})")
                    return {"status": "success", "data": data}
            except Exception as e:
                logger.error(f"Network Error: {e}")
                return {"status": "failed", "error": str(e)}

    async def send_text(self, to_phone: str, message: str):
        """Helper to send simple text message."""
        from backend.integrations.whatsapp.templates import WhatsAppTemplates
        payload = WhatsAppTemplates.simple_text(to_phone, message)
        return await self.send_message(payload)
    
    async def send_template(self, to_phone: str, template_name: str, language_code: str = "en_US", components: list = None):
        """Helper to send a template message."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code}
            }
        }
        if components:
            payload["template"]["components"] = components
            
        return await self.send_message(payload)
