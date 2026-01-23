from typing import List, Dict

class WhatsAppTemplates:
    @staticmethod
    def alert_template(rule_name: str, content: str, urgency: str = "HIGH"):
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "type": "template",
            "template": {
                "name": "simplii_alert",
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": urgency},
                            {"type": "text", "text": rule_name},
                            {"type": "text", "text": content[:100] + "..." if len(content) > 100 else content}
                        ]
                    }
                ]
            }
        }

    @staticmethod
    def simple_text(to_phone: str, message: str):
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "text",
            "text": {"body": message}
        }

    @staticmethod
    def content_approval(to_phone: str, post_id: str, content: str):
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": f"New Content Pending Approval\n\n{content[:150]}..."
                },
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"approve_{post_id}",
                                "title": "Approve"
                            }
                        },
                        {
                            "type": "reply",
                            "reply": {
                                "id": f"reject_{post_id}",
                                "title": "Reject"
                            }
                        }
                    ]
                }
            }
        }
