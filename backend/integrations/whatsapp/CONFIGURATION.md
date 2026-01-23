# WhatsApp Integration Configuration

## 1. Environment Variables

Add these to your `.env` file:

```env
WHATSAPP_PHONE_ID=your_phone_id_here
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
```

## 2. Webhook Setup on Meta

- **Callback URL**: `https://postflow.panscience.ai/webhook/whatsapp`
- **Verify Token**: Must match the `WHATSAPP_VERIFY_TOKEN` you set in `.env`.

## 3. Server Port
Your application is running on port **35000** (via `run.py`).
Ensure your tunnel (postflow.panscience.ai) forwards traffic to `localhost:35000`.

## 4. Verification

The endpoint is live.
You can verify it by successfully saving the Configuration in the Meta App Dashboard. If Meta accepts the Verify Token, the integration is working.
