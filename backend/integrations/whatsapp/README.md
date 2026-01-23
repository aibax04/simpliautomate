# WhatsApp Integration Module

This module provides integration with the Meta WhatsApp Cloud API for Simplii.

## Features

- **Outbound Notifications**: Send alerts, daily summaries, and approval requests.
- **Inbound Commands**: Handle commands like `LATEST NEWS`, `STATS`, etc.
- **Webhook**: Verifies and processes incoming messages.

## Configuration

Ensure the following environment variables are set in your `.env` file:

```env
WHATSAPP_PHONE_ID=your_phone_id_here
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
```

## Architecture

- **`sender.py`**: Handles API communication with Meta.
- **`webhook.py`**: FastAPI router handling the `/webhook/whatsapp` endpoint.
- **`command_parser.py`**: Interpretation logic for user commands.
- **`hooks.py`**: easy-to-use functions for other modules (`send_rule_alert`, `request_approval`).
- **`templates.py`**: JSON templates for WhatsApp messages.

## Usage

### Sending an Alert
```python
from backend.integrations.whatsapp.hooks import send_rule_alert
await send_rule_alert("Competitor Mention", "Competitor X just launched Y", urgency="HIGH")
```

### Webhook Setup
The webhook is exposed at `POST /webhook/whatsapp`.
Configure this URL in your Meta App Dashboard.
Verify Token: Matches `WHATSAPP_VERIFY_TOKEN`.

## Extending Commands
Add new commands in `backend/integrations/whatsapp/command_parser.py` in the `parse_and_execute` method.
