# Google Chat Webhook Setup Guide

Follow these steps to enable your living assistant to send messages to Google Chat.

## Prerequisites

- A Google account (Gmail, Workspace, etc.)
- Access to Google Chat (chat.google.com or the mobile app)

## Step-by-Step Setup

### 1. Create or Select a Space

**Option A: Create a new space (recommended)**
1. Open Google Chat (https://chat.google.com)
2. Click the **+** button next to "Spaces"
3. Select **Create space**
4. Name it something like "Living Assistant" or "My Reminders"
5. Click **Create**

**Option B: Use an existing space**
- You can use any space you're an admin of
- Note: The assistant will post to this space, so choose wisely!

### 2. Get the Webhook URL

1. **Open your space** (click on it in the left sidebar)

2. **Click the space name** at the top to open the space menu

3. **Select "Apps & integrations"**
   - On desktop: Click the space name → Apps & integrations
   - You may need to click the ⋮ (three dots) menu

4. **Click "Add webhooks"** or "Manage webhooks"

5. **Create a new webhook:**
   - Name: `Living Assistant` (or any name you prefer)
   - Avatar URL: (optional, leave blank)
   - Click **Save**

6. **Copy the webhook URL**
   - It will look like: `https://chat.googleapis.com/v1/spaces/AAAA.../messages?key=...&token=...`
   - This is a long URL with your space ID and authentication token
   - **Keep this URL private** - anyone with it can post to your space!

### 3. Configure Your Assistant

Now add the webhook URL to your environment configuration:

#### Option 1: Using .env file (recommended)

1. Open or create `.env` file in your project directory:
   ```bash
   nano .env
   ```

2. Add this line (replace with your actual webhook URL):
   ```
   GOOGLE_CHAT_WEBHOOK=https://chat.googleapis.com/v1/spaces/AAAA.../messages?key=...&token=...
   ```

3. Save and close the file

#### Option 2: Edit config.py directly

1. Open `config.py`
2. Find the line: `GOOGLE_CHAT_WEBHOOK = os.getenv("GOOGLE_CHAT_WEBHOOK")`
3. Replace it with:
   ```python
   GOOGLE_CHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAAA.../messages?key=...&token=..."
   ```

> [!WARNING]
> **Option 2 is not recommended** because it exposes your webhook URL in the code. Use .env instead!

### 4. Test the Connection

Test that your webhook works:

```bash
cd /home/yash/PycharmProjects/living_assistant
python -c "
from actions.chat import GoogleChatMessenger

webhook = 'YOUR_WEBHOOK_URL_HERE'
messenger = GoogleChatMessenger(webhook)
messenger.send_message('🎉 Hello from Living Assistant! Setup successful!')
"
```

Replace `YOUR_WEBHOOK_URL_HERE` with your actual webhook URL.

If successful, you should see a message appear in your Google Chat space!

## What's Already Implemented

✅ **All messaging functionality is ready:**
- `GoogleChatMessenger` class - sends messages via webhook
- Scheduled reminders - sends messages at specific times
- Ad-hoc messages - brain can decide to send check-ins
- Error handling - graceful failures if webhook is unavailable

You just needed the webhook URL configuration!

## Troubleshooting

### "No webhook URL configured" warning

**Cause**: The `GOOGLE_CHAT_WEBHOOK` environment variable is not set or is empty.

**Fix**: Follow Step 3 above to configure your webhook URL.

### "Failed to send message: 400 - Bad Request"

**Cause**: Invalid webhook URL format.

**Fix**: 
- Double-check you copied the entire URL
- Make sure there are no extra spaces or line breaks
- The URL should start with `https://chat.googleapis.com/v1/spaces/`

### "Failed to send message: 404 - Not Found"

**Cause**: Webhook was deleted or space no longer exists.

**Fix**: Create a new webhook following Steps 1-2.

### Messages not appearing in space

**Possible causes**:
1. Webhook is for a different space - check which space you created the webhook in
2. You're not a member of the space - make sure you're in the space
3. Space notifications are muted - check your notification settings

## Security Best Practices

🔒 **Keep your webhook URL private:**
- Don't commit it to Git (use `.env` which is in `.gitignore`)
- Don't share it publicly
- Anyone with the URL can post to your space

🔄 **Rotate webhooks regularly:**
- Delete old webhooks you're not using
- Create new ones if you suspect the URL was exposed

## Visual Guide

**Finding webhook settings:**
```
Google Chat
  → [Your Space]
    → Click space name at top
      → Apps & integrations
        → Manage webhooks
          → Add webhook
            → Copy URL
```

## Alternative: Using Google Chat API (Advanced)

If you want more features (like receiving messages, seeing who's online, etc.), you can use the full Google Chat API instead of webhooks. This requires:
- Google Cloud Project
- Chat API enabled
- Service account credentials
- OAuth 2.0 setup

For now, webhooks are simpler and sufficient for sending scheduled reminders!

## Next Steps

Once configured:
1. ✅ Start your assistant: `python main.py`
2. ✅ Add a test schedule: Say "Add a reminder at [current time + 2 minutes] saying test"
3. ✅ Wait for the message to arrive in Google Chat
4. ✅ Enjoy your scheduled reminders!
