import requests
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger("Chat")


class GoogleChatMessenger:
    """Send messages to Google Chat via webhook."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
    
    def send_message(self, text: str) -> bool:
        """Send a message to Google Chat."""
        if not self.webhook_url:
            logger.warning("No webhook URL configured, skipping message send")
            return False
        
        try:
            payload = {"text": text}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully: {text[:50]}...")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def send_task_reminder(self, task: str) -> bool:
        """Send a task reminder."""
        message = f"📋 Hey! Just checking in - have you made progress on: *{task}*?"
        return self.send_message(message)
    
    def send_encouragement(self) -> bool:
        """Send encouragement."""
        message = "💪 You're doing great! Keep up the good work!"
        return self.send_message(message)
