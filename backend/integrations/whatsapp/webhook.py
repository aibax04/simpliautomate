from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks, Query
from typing import Dict, Any, List
import logging
from backend.config import Config
from backend.integrations.whatsapp.command_parser import CommandParser
from backend.integrations.whatsapp.sender import WhatsAppSender

router = APIRouter()
logger = logging.getLogger(__name__)

async def process_message(message_body: str, sender_phone: str):
    """
    Background task to process the incoming message and reply.
    """
    parser = CommandParser()
    sender = WhatsAppSender()
    
    try:
        response_text = await parser.parse_and_execute(message_body, sender_phone)
        await sender.send_text(sender_phone, response_text)
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        await sender.send_text(sender_phone, "⚠️ Error processing command.")

@router.get("/webhook/whatsapp")
async def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge")
):
    """
    Meta Verification Challenge.
    """
    if mode and token:
        if mode == "subscribe" and token == Config.WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp Webhook Verified!")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    
    raise HTTPException(status_code=400, detail="Missing parameters")

@router.post("/webhook/whatsapp")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Receive messages from WhatsApp.
    """
    # 1. Signature Validation (TODO: Implement HMAC-SHA256 check with APP_SECRET)
    # signature = request.headers.get("X-Hub-Signature-256")
    
    data = await request.json()
    logger.info(f"Received WhatsApp Payload: {data}")

    try:
        # Parse standard WhatsApp Message structure
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            msg_type = msg.get("type")
            sender_phone = msg.get("from")
            
            # Handle Text Messages
            if msg_type == "text":
                body = msg.get("text", {}).get("body")
                # Offload processing to background task to keep API fast
                background_tasks.add_task(process_message, body, sender_phone)
            
            # Handle Interactive (Button) Replies
            elif msg_type == "interactive":
                reply = msg.get("interactive", {}).get("button_reply", {})
                reply_id = reply.get("id")
                # Treat ID as a command
                if reply_id:
                     background_tasks.add_task(process_message, reply_id, sender_phone)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Always return 200 to Meta to prevent retries on logic errors
        return {"status": "error", "message": str(e)}
