import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class AssistantState:
    """Thread-safe shared state for the assistant."""
    
    # User presence
    user_present: bool = False
    last_seen: Optional[datetime] = None
    
    # Screen activity
    current_activity: str = "Unknown"
    last_screen_analysis: Optional[datetime] = None
    
    # Assistant state
    last_spoke: Optional[datetime] = None
    last_chat_message: Optional[datetime] = None
    mood: str = "neutral"  # neutral, excited, concerned, etc.
    
    # Lock for thread safety
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    
    def update_user_presence(self, present: bool):
        """Update user presence status."""
        with self._lock:
            self.user_present = present
            if present:
                self.last_seen = datetime.now()
    
    def update_activity(self, activity: str):
        """Update current activity."""
        with self._lock:
            self.current_activity = activity
            self.last_screen_analysis = datetime.now()
    
    def update_interaction(self, interaction_type: str):
        """Update last interaction timestamp."""
        with self._lock:
            now = datetime.now()
            if interaction_type == "voice":
                self.last_spoke = now
            elif interaction_type == "chat":
                self.last_chat_message = now
    
    def get_snapshot(self) -> dict:
        """Get a snapshot of current state."""
        with self._lock:
            return {
                "user_present": self.user_present,
                "last_seen": self.last_seen,
                "current_activity": self.current_activity,
                "last_screen_analysis": self.last_screen_analysis,
                "last_spoke": self.last_spoke,
                "last_chat_message": self.last_chat_message,
                "mood": self.mood
            }
