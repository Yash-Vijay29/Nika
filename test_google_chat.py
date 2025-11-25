#!/usr/bin/env python3
"""
Test script to verify Google Chat webhook is working.

Usage:
    python test_google_chat.py
"""

import sys
import os
from actions.chat import GoogleChatMessenger

def test_webhook():
    """Test the Google Chat webhook configuration."""
    
    print("=" * 60)
    print("Google Chat Webhook Test")
    print("=" * 60)
    print()
    
    # Try to get webhook from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    webhook = os.getenv("GOOGLE_CHAT_WEBHOOK")
    
    if not webhook:
        print("❌ ERROR: GOOGLE_CHAT_WEBHOOK not configured")
        print()
        print("To fix:")
        print("1. Open .env file (or create it from .env.template)")
        print("2. Add your webhook URL:")
        print("   GOOGLE_CHAT_WEBHOOK=https://chat.googleapis.com/v1/spaces/.../messages?key=...&token=...")
        print()
        print("📖 See GOOGLE_CHAT_SETUP.md for detailed setup instructions")
        print()
        return False
    
    print(f"✓ Webhook URL found")
    print(f"  URL: {webhook[:50]}...")
    print()
    
    # Test sending a message
    print("Sending test message...")
    messenger = GoogleChatMessenger(webhook)
    
    success = messenger.send_message("🧪 Test message from Living Assistant!\n\n✅ Your Google Chat webhook is working correctly!")
    
    print()
    if success:
        print("✅ SUCCESS! Message sent successfully")
        print()
        print("Check your Google Chat space - you should see the test message!")
        print()
        print("Your scheduled reminders will now work. Try:")
        print("  python main.py")
        print('  Then say: "Add a reminder at [time] saying [message]"')
        return True
    else:
        print("❌ FAILED to send message")
        print()
        print("Common issues:")
        print("1. Webhook URL is incorrect or incomplete")
        print("2. Webhook was deleted from Google Chat")
        print("3. Space no longer exists")
        print()
        print("📖 See GOOGLE_CHAT_SETUP.md for troubleshooting")
        return False

if __name__ == "__main__":
    success = test_webhook()
    sys.exit(0 if success else 1)
