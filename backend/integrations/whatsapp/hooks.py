from typing import Optional
from backend.integrations.whatsapp.sender import WhatsAppSender
from backend.integrations.whatsapp.templates import WhatsAppTemplates
from backend.config import Config
import logging

logger = logging.getLogger(__name__)

# This is where we would ideally look up the user's phone number from DB
# For MVP, we might use a default or assume it's passed in
DEFAULT_PHONE = Config.WHATSAPP_ADMIN_PHONE 

async def send_rule_alert(rule_name: str, matched_content: str, urgency: str = "HIGH", phone_id: Optional[str] = None):
    """
    Triggered when a rule is matched.
    """
    sender = WhatsAppSender()
    target_phone = phone_id or DEFAULT_PHONE
    
    # 1. Send Template Alert
    # Note: Template must exist in Meta Business Manager. 
    # Fallback to text if template not set up
    try:
        payload = WhatsAppTemplates.alert_template(rule_name, matched_content, urgency)
        payload["to"] = target_phone
        await sender.send_message(payload)
    except Exception as e:
        logger.warning(f"Failed to send template alert, falling back to text: {e}")
        text = f"🚨 *{urgency} ALERT: {rule_name}*\n\n{matched_content}"
        await sender.send_text(target_phone, text)

async def send_daily_summary(summary_text: str, phone_id: Optional[str] = None):
    """
    Triggered by daily scheduler.
    """
    sender = WhatsAppSender()
    target_phone = phone_id or DEFAULT_PHONE
    text = f"☀️ *Daily Summary*\n\n{summary_text}"
    await sender.send_text(target_phone, text)

async def request_approval(post_id: str, content: str, phone_id: Optional[str] = None):
    """
    Triggered when AI generates a post requiring approval.
    """
    sender = WhatsAppSender()
    target_phone = phone_id or DEFAULT_PHONE
    
    # Use interactive template
    payload = WhatsAppTemplates.content_approval(target_phone, post_id, content)
    await sender.send_message(payload)
